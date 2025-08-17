import pandas as pd
import numpy as np
import os
import hashlib
import time
import json
import requests
import zhipuai

# 配置参数（用户需修改这些路径）
CONFIG = {
    "node_files": ["./政务_nodes.csv"],          # 节点CSV文件路径列表
    "relationship_files": ["./政务_relationships.csv"],  # 关系CSV文件路径列表
    "zhipuai_api_key": "d6f40a1ca6144ac4ab4b7192183dea66.LaW6LubtbzutMdxW",      # 智谱AI API密钥
    "zhipuai_model": "glm-4",               # 智谱AI模型名称
    "output_dir": "./qa_report",            # 报告输出目录
    "semantic_eval_sample_size": 0.1,       # 语义评估采样比例(0-1)
    "logical_rules": {                      # 政务文本场景的逻辑规则
        "不允许的节点类型": ["NONE", ""],  # 暂时允许Unknown，因为服务器默认输出
        "无效关系类型": ["NONE", "", "未知关系"],
        "类型冲突规则": {
            # 政府机构相关规则
            ("政府机构", "隶属于", "政府机构"): "允许",
            ("政府机构", "管理", "企业"): "允许",
            ("政府机构", "监管", "行业"): "允许",
            ("政府机构", "发布", "政策"): "允许",
            ("政府机构", "提供", "服务"): "允许",
            
            # 政策法规相关规则
            ("政策", "适用于", "地区"): "允许",
            ("政策", "规范", "行业"): "允许",
            ("法规", "约束", "企业"): "允许",
            ("法规", "保护", "公民权利"): "允许",
            
            # 服务事项相关规则
            ("服务事项", "属于", "政府机构"): "允许",
            ("服务事项", "需要", "材料"): "允许",
            ("服务事项", "收费标准", "金额"): "允许",
            ("公民", "申请", "服务事项"): "允许",
            ("企业", "申请", "服务事项"): "允许",
            
            # 地区相关规则
            ("地区", "位于", "地区"): "允许",
            ("地区", "管辖", "地区"): "允许",
            ("地区", "实施", "政策"): "允许",
            
            # 明显错误的规则（禁止）
            ("政府机构", "购买", "政府机构"): "禁止",
            ("政策", "吃", "任何实体"): "禁止",
            ("服务事项", "杀死", "任何实体"): "禁止",
            ("地区", "结婚", "任何实体"): "禁止",
            ("法规", "睡觉", "任何实体"): "禁止",
            
            # 语义矛盾规则
            ("下级机构", "管理", "上级机构"): "禁止",
            ("子级地区", "管辖", "父级地区"): "禁止",
            ("被监管对象", "监管", "监管机构"): "禁止"
        },
        # 政务领域的实体类型层次关系
        "实体层次关系": {
            "政府机构": ["国务院", "省政府", "市政府", "县政府", "乡镇政府", "街道办事处"],
            "地区": ["国家", "省份", "城市", "区县", "乡镇", "村社区"],
            "政策类型": ["法律", "法规", "规章", "政策", "通知", "公告"],
            "服务类型": ["行政许可", "行政确认", "行政给付", "公共服务", "便民服务"]
        }
    }
}

class KnowledgeGraphEvaluator:
    def __init__(self, config):
        self.config = config
        self.nodes = pd.DataFrame()
        self.relationships = pd.DataFrame()
        os.makedirs(config['output_dir'], exist_ok=True)
        
        if config.get('zhipuai_api_key'):
            try:
                from zhipuai import ZhipuAI  # 新版SDK导入方式
                self.zhipuai_client = ZhipuAI(api_key=config['zhipuai_api_key'])
                print("智谱AI客户端已初始化（新版SDK）")
            except ImportError:
                print("警告：未安装新版zhipuai库，请执行 pip install --upgrade zhipuai")
                self.zhipuai_client = None
        else:
            self.zhipuai_client = None
            print("未配置智谱AI API密钥")

    def load_data(self):
        """加载节点和关系CSV文件"""
        # 合并所有节点文件
        node_dfs = []
        for path in self.config['node_files']:
            if os.path.exists(path):
                df = pd.read_csv(path, keep_default_na=False)
                # 确保必要的列存在
                if 'id' not in df.columns:
                    if 'node_id' in df.columns:
                        df = df.rename(columns={'node_id': 'id'})
                    elif 'Node_ID' in df.columns:
                        df = df.rename(columns={'Node_ID': 'id'})
                    else:
                        # 如果没有找到ID列，使用索引作为ID
                        df['id'] = df.index
                if 'node_type' not in df.columns:
                    df['node_type'] = 'Unknown'
                node_dfs.append(df)
        
        # 如果有节点数据则合并
        if node_dfs:
            self.nodes = pd.concat(node_dfs, ignore_index=True)

        # 合并所有关系文件
        rel_dfs = []
        for path in self.config['relationship_files']:
            if os.path.exists(path):
                df = pd.read_csv(path, keep_default_na=False)
                # 重命名列以匹配标准格式
                if 'start_id' not in df.columns:
                    if 'source' in df.columns:
                        df = df.rename(columns={'source': 'start_id'})
                    elif 'from' in df.columns:
                        df = df.rename(columns={'from': 'start_id'})
                
                if 'end_id' not in df.columns:
                    if 'target' in df.columns:
                        df = df.rename(columns={'target': 'end_id'})
                    elif 'to' in df.columns:
                        df = df.rename(columns={'to': 'end_id'})
                
                if 'relation_type' not in df.columns:
                    if 'type' in df.columns:
                        df = df.rename(columns={'type': 'relation_type'})
                    elif 'relationship' in df.columns:
                        df = df.rename(columns={'relationship': 'relation_type'})
                    else:
                        df['relation_type'] = 'RELATED_TO'
                
                # 如果列名称仍然找不到，使用默认值
                if 'start_id' not in df.columns:
                    df['start_id'] = df.index
                if 'end_id' not in df.columns:
                    df['end_id'] = df.index
                if 'relation_type' not in df.columns:
                    df['relation_type'] = 'RELATED_TO'
                
                rel_dfs.append(df)
        
        # 如果有关系数据则合并
        if rel_dfs:
            self.relationships = pd.concat(rel_dfs, ignore_index=True)

        print(f"加载完成: {len(self.nodes)} 个节点, {len(self.relationships)} 条关系")

    def detect_isolated_nodes(self):
        """检测孤立节点"""
        if self.nodes.empty or self.relationships.empty:
            return 0, pd.DataFrame()
        
        connected_nodes = set(self.relationships['start_id']).union(
            set(self.relationships['end_id']))
        
        isolated = self.nodes[~self.nodes['id'].isin(connected_nodes)]
        
        # 检查节点数量以避免除以零错误
        isolation_rate = len(isolated) / len(self.nodes) if len(self.nodes) > 0 else 0
        
        isolated.to_csv(f"{self.config['output_dir']}/isolated_nodes.csv", index=False)
        return isolation_rate, isolated

    def detect_redundant_triples(self):
        """检测冗余三元组"""
        if self.relationships.empty:
            return 0, pd.DataFrame()
        
        # 生成唯一三元组标识
        self.relationships['triple_hash'] = self.relationships.apply(
            lambda x: hashlib.sha256(
                f"{x['start_id']}-{x['relation_type']}-{x['end_id']}".encode()
            ).hexdigest(), axis=1)
        
        duplicates = self.relationships.duplicated(subset=['triple_hash'], keep='first')
        
        redundant_rate = duplicates.mean() if len(duplicates) > 0 else 0
        
        redundant = self.relationships[duplicates]
        redundant.to_csv(f"{self.config['output_dir']}/redundant_triples.csv", index=False)
        return redundant_rate, redundant

    def check_logical_consistency(self):
        """逻辑一致性检测 - 增强政务领域检测"""
        conflicts = []
        rules = self.config['logical_rules']
        
        # 如果没有节点或关系数据
        if self.nodes.empty or self.relationships.empty:
            return 0, pd.DataFrame()
        
        # 规则1: 禁止的节点类型
        if 'node_type' in self.nodes.columns:
            invalid_nodes = self.nodes[self.nodes['node_type'].isin(
                rules['不允许的节点类型'])]
            if not invalid_nodes.empty:
                conflicts.append(invalid_nodes.assign(issue_type='无效节点类型'))
        
        # 规则2: 无效关系类型检测
        if 'relation_type' in self.relationships.columns:
            invalid_rels = self.relationships[self.relationships['relation_type'].isin(
                rules['无效关系类型'])]
            if not invalid_rels.empty:
                conflicts.append(invalid_rels.assign(issue_type='无效关系类型'))
        
        # 规则3: 类型冲突检测
        type_conflicts = []
        if 'node_type' in self.nodes.columns and not self.relationships.empty:
            merged = self.relationships.copy()
            
            # 添加起始节点类型和名称
            if 'node_type' in self.nodes.columns:
                start_info = self.nodes[['id', 'node_type', 'name']].rename(columns={
                    'id': 'start_id', 
                    'node_type': 'start_node_type',
                    'name': 'start_node_name'
                })
                merged = pd.merge(merged, start_info, on='start_id', how='left')
            
            # 添加结束节点类型和名称
            if 'node_type' in self.nodes.columns:
                end_info = self.nodes[['id', 'node_type', 'name']].rename(columns={
                    'id': 'end_id', 
                    'node_type': 'end_node_type',
                    'name': 'end_node_name'
                })
                merged = pd.merge(merged, end_info, on='end_id', how='left')
            
            # 应用类型冲突规则
            for (src_type, rel_type, tgt_type), action in rules['类型冲突规则'].items():
                if action == "禁止":
                    # 处理"任何实体"的特殊情况
                    if tgt_type == "任何实体":
                        mask = (merged['start_node_type'] == src_type) & (merged['relation_type'] == rel_type)
                    elif src_type == "任何实体":
                        mask = (merged['relation_type'] == rel_type) & (merged['end_node_type'] == tgt_type)
                    else:
                        mask = (merged['start_node_type'] == src_type) & \
                               (merged['relation_type'] == rel_type) & \
                               (merged['end_node_type'] == tgt_type)
                    
                    conflicts_df = merged[mask]
                    
                    if not conflicts_df.empty:
                        type_conflicts.append(conflicts_df.assign(issue_type=f"类型冲突: {src_type}-{rel_type}-{tgt_type}"))
        
        # 规则4: 政务领域特有的层级关系检测
        hierarchy_conflicts = self._check_government_hierarchy_conflicts(merged if 'merged' in locals() else self.relationships)
        if not hierarchy_conflicts.empty:
            type_conflicts.append(hierarchy_conflicts.assign(issue_type="政务层级关系冲突"))
        
        # 规则5: 地理层级关系检测
        geo_conflicts = self._check_geographical_hierarchy_conflicts(merged if 'merged' in locals() else self.relationships)
        if not geo_conflicts.empty:
            type_conflicts.append(geo_conflicts.assign(issue_type="地理层级关系冲突"))
        
        # 合并所有冲突
        all_conflicts = []
        if conflicts:
            all_conflicts.extend(conflicts)
        if type_conflicts:
            all_conflicts.extend(type_conflicts)
        
        if all_conflicts:
            all_conflicts = pd.concat(all_conflicts, ignore_index=True)
        else:
            all_conflicts = pd.DataFrame()
        
        conflict_rate = len(all_conflicts) / len(self.relationships) if len(self.relationships) > 0 else 0
        
        if not all_conflicts.empty:
            all_conflicts.to_csv(f"{self.config['output_dir']}/logical_conflicts.csv", index=False)
        return conflict_rate, all_conflicts
    
    def _check_government_hierarchy_conflicts(self, merged_df):
        """检测政府机构层级关系冲突"""
        if merged_df.empty or 'start_node_name' not in merged_df.columns:
            return pd.DataFrame()
        
        conflicts = []
        
        # 定义政府层级顺序（级别越低数字越大）
        gov_levels = {
            "国务院": 1, "中央": 1,
            "省": 2, "自治区": 2, "直辖市": 2,
            "市": 3, "地级市": 3, "州": 3,
            "县": 4, "区": 4, "县级市": 4,
            "乡": 5, "镇": 5, "街道": 5
        }
        
        # 检测"管理"、"隶属于"等关系中的层级冲突
        hierarchy_relations = ["管理", "隶属于", "下属", "上级", "领导"]
        
        for _, row in merged_df.iterrows():
            if row['relation_type'] in hierarchy_relations:
                start_name = str(row.get('start_node_name', ''))
                end_name = str(row.get('end_node_name', ''))
                
                start_level = self._get_gov_level(start_name, gov_levels)
                end_level = self._get_gov_level(end_name, gov_levels)
                
                # 如果下级机构管理上级机构，则为冲突
                if start_level and end_level and start_level > end_level and row['relation_type'] in ["管理", "领导"]:
                    conflicts.append(row)
                elif start_level and end_level and start_level < end_level and row['relation_type'] in ["隶属于"]:
                    conflicts.append(row)
        
        return pd.DataFrame(conflicts) if conflicts else pd.DataFrame()
    
    def _check_geographical_hierarchy_conflicts(self, merged_df):
        """检测地理层级关系冲突"""
        if merged_df.empty or 'start_node_name' not in merged_df.columns:
            return pd.DataFrame()
        
        conflicts = []
        
        # 定义地理层级顺序
        geo_levels = {
            "国家": 1, "中国": 1,
            "省": 2, "自治区": 2, "直辖市": 2,
            "市": 3, "地级市": 3, "州": 3,
            "县": 4, "区": 4, "县级市": 4,
            "乡": 5, "镇": 5, "街道": 5, "村": 6, "社区": 6
        }
        
        geo_relations = ["管辖", "位于", "属于", "包含"]
        
        for _, row in merged_df.iterrows():
            if row['relation_type'] in geo_relations:
                start_name = str(row.get('start_node_name', ''))
                end_name = str(row.get('end_node_name', ''))
                
                start_level = self._get_geo_level(start_name, geo_levels)
                end_level = self._get_geo_level(end_name, geo_levels)
                
                # 检测层级冲突
                if start_level and end_level:
                    if row['relation_type'] in ["管辖", "包含"] and start_level > end_level:
                        conflicts.append(row)
                    elif row['relation_type'] in ["位于", "属于"] and start_level < end_level:
                        conflicts.append(row)
        
        return pd.DataFrame(conflicts) if conflicts else pd.DataFrame()
    
    def _get_gov_level(self, name, levels_dict):
        """获取政府机构层级"""
        for keyword, level in levels_dict.items():
            if keyword in name:
                return level
        return None
    
    def _get_geo_level(self, name, levels_dict):
        """获取地理区域层级"""
        for keyword, level in levels_dict.items():
            if keyword in name:
                return level
        return None


    def call_zhipuai_api(self, prompt):
        """调用智谱AI API并获取响应 - 增强解析"""
        if not self.zhipuai_client:
            return {"score": 0, "reason": "API客户端未初始化"}
        
        try:
            # 调用智谱AI API
            response = self.zhipuai_client.chat.completions.create(
                model=self.config.get("zhipuai_model", "glm-4"),
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1
            )
            
            # 提取响应内容
            content = response.choices[0].message.content.strip()
            
            # 增强解析逻辑
            return self.parse_ai_response(content)
        
        except Exception as e:
            print(f"智谱AI API调用异常: {str(e)}")
            return {"score": 0, "reason": str(e)}

    def parse_ai_response(self, content):
        """解析AI响应，处理各种可能的格式"""
        # 尝试直接解析JSON
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass
        
        # 尝试去除代码块标记
        clean_content = content
        if clean_content.startswith('```json'):
            clean_content = clean_content[7:]  # 移除```json
        if clean_content.endswith('```'):
            clean_content = clean_content[:-3]  # 移除```
        clean_content = clean_content.strip()
        
        # 尝试解析清理后的内容
        try:
            return json.loads(clean_content)
        except json.JSONDecodeError:
            pass
        
        # 尝试提取可能的JSON部分
        try:
            # 处理转义双引号
            normalized = clean_content.replace('""', '"')
            # 尝试解析
            return json.loads(normalized)
        except:
            pass
        
        # 尝试使用正则表达式提取JSON
        import re
        json_match = re.search(r'\{[\s\S]*\}', clean_content)
        if json_match:
            try:
                return json.loads(json_match.group())
            except:
                pass
        
        # 作为最后手段，尝试手动解析评分
        try:
            score_match = re.search(r'"score":\s*([0-9.]+)', content)
            reason_match = re.search(r'"reason":\s*"([^"]+)"', content)
            
            score = float(score_match.group(1)) if score_match else 0
            reason = reason_match.group(1) if reason_match else "无法解析响应"
            
            return {"score": score, "reason": reason}
        except:
            return {"score": 0, "reason": f"无法解析的响应: {content[:100]}"}


    def evaluate_semantic_consistency(self):
        """使用智谱AI API评估语义一致性"""
        if self.relationships.empty or not self.config.get('zhipuai_api_key') or self.config['semantic_eval_sample_size'] <= 0:
            return 0.0, pd.DataFrame()
        
        sample_size = max(5, int(len(self.relationships) * self.config['semantic_eval_sample_size']))
        sample_size = min(sample_size, len(self.relationships))
        sample = self.relationships.sample(n=sample_size)
        
        results = []
        # 政务文本专用的评估提示词
        SYSTEM_PROMPT = """
        你是一个政务知识图谱质量评估专家。请严格评估以下政务领域三元组的语义合理性，重点关注：
        
        1. 政务关系的准确性：政府机构层级关系、行政管辖关系、政策适用关系等
        2. 语义逻辑性：主谓宾关系是否符合政务常识，是否存在颠倒、错位等问题
        3. 行政层级合理性：上下级关系是否正确，管辖范围是否合理
        4. 政务术语准确性：是否使用了正确的政务专业术语和表述
        
        评分标准（0-1分）：
        1.0分: 完全符合政务常识和行政逻辑，关系表述准确
        0.8分: 基本合理，但可能存在轻微的表述不准确
        0.6分: 部分合理但有歧义或不够准确
        0.4分: 存在明显的逻辑问题或术语使用错误
        0.2分: 严重违背政务常识或行政逻辑
        0.0分: 完全不合理、荒谬或违反基本常识
        
        特别注意：
        - 政府机构不能管理其上级机构
        - 下级地区不能管辖上级地区
        - 政策法规的适用范围和层级要符合实际
        - 服务事项的主体和客体关系要正确
        
        请直接返回纯JSON格式，不要包含任何额外文本或代码块标记：
        {"score": 分数值, "reason": "简要说明原因"}
        """
        
        for _, row in sample.iterrows():
            try:
                # 获取节点名称
                start_node_info = self.nodes[self.nodes['id'] == row['start_id']]
                start_node = start_node_info.iloc[0].get('name', row['start_id']) if not start_node_info.empty else row['start_id']
                
                end_node_info = self.nodes[self.nodes['id'] == row['end_id']]
                end_node = end_node_info.iloc[0].get('name', row['end_id']) if not end_node_info.empty else row['end_id']
                
                triple = f"{start_node} --[{row['relation_type']}]-> {end_node}"
                
                # 组合提示词
                prompt = SYSTEM_PROMPT + f"\n评估以下三元组的合理性:\n{triple}"
                
                # 调用智谱AI API
                result = self.call_zhipuai_api(prompt)
                
                results.append({
                    "triple": triple,
                    "score": float(result.get('score', 0)),
                    "reason": result.get('reason', '')
                })
                time.sleep(1.5)  # API速率限制
            except Exception as e:
                print(f"语义评估失败: {str(e)}")
                results.append({
                    "triple": triple if 'triple' in locals() else "",
                    "score": -1,
                    "reason": str(e)
                })
        
        semantic_df = pd.DataFrame(results)
        # 计算有效分数的平均值
        valid_scores = semantic_df[semantic_df['score'] >= 0]['score']
        avg_score = valid_scores.mean() if not valid_scores.empty else 0
        semantic_df.to_csv(f"{self.config['output_dir']}/semantic_evaluation.csv", index=False)
        return avg_score, semantic_df


    def generate_report(self, metrics):
        """生成评估报告，包含原有输出和新的质量评分"""
        # 原有报告内容
        original_report = f"""
        ======== 知识图谱质量评估报告 ========
        生成时间: {time.ctime()}
        数据集概览:
        - 节点数量: {len(self.nodes)}
        - 关系数量: {len(self.relationships)}
        
        质量指标:
        1. 孤立节点比例: {metrics['isolation_rate']:.2%}
        2. 冗余三元组比例: {metrics['redundancy_rate']:.2%}
        3. 逻辑冲突比例: {metrics['logical_conflict_rate']:.2%}
        4. 语义一致性平均分: {metrics['semantic_score']:.2%}
        
        详细报告已保存至: {self.config['output_dir']}
        """
        
        # 新的质量评分系统
        # 计算各维度的质量得分（问题比例转换为质量分数）
        isolation_score = (1 - metrics['isolation_rate']) * 100
        redundancy_score = (1 - metrics['redundancy_rate']) * 100
        logical_score = (1 - metrics['logical_conflict_rate']) * 100
        
        # 语义一致性得分（直接使用平均分乘以100）
        semantic_score = metrics['semantic_score'] * 100
        
        # 计算总分（四个维度各占25%权重）
        total_score = (
            isolation_score * 0.25 +
            redundancy_score * 0.25 +
            logical_score * 0.25 +
            semantic_score * 0.25
        )
        
        # 创建政务知识图谱质量评分报告
        quality_report = f"""
        ======== 政务知识图谱质量评分系统 ========
        评分标准:
        - 每个评估维度分配25%权重
        - 满分100分，得分越高表示图谱质量越好
        - 专门针对政务领域进行优化评估
        
        各维度得分:
        1. 节点连通性: {isolation_score:.2f}/100
            (基于孤立节点比例: {metrics['isolation_rate']:.2%})
            说明: 评估政务实体间的关联完整性
        
        2. 三元组唯一性: {redundancy_score:.2f}/100
            (基于冗余三元组比例: {metrics['redundancy_rate']:.2%})
            说明: 检测重复的政务关系表述
        
        3. 逻辑一致性: {logical_score:.2f}/100
            (基于逻辑冲突比例: {metrics['logical_conflict_rate']:.2%})
            说明: 评估政务层级关系、地理关系等的逻辑合理性
        
        4. 语义合理性: {semantic_score:.2f}/100
            (基于语义一致性平均分: {metrics['semantic_score']:.2%})
            说明: 评估政务关系表述的专业性和准确性
        
        最终质量得分: {total_score:.2f}/100
        
        质量等级判定:
        - 90-100分: 优秀 - 图谱质量很高，可直接应用
        - 80-89分: 良好 - 图谱质量较好，少量问题需要修正
        - 70-79分: 中等 - 图谱质量一般，存在一些质量问题
        - 60-69分: 及格 - 图谱可用但需要大量改进
        - <60分: 不合格 - 图谱质量较差，需要重新构建
        """
        
        # 合并两个报告
        full_report = original_report + "\n" + quality_report
        
        # 保存报告
        with open(f"{self.config['output_dir']}/report.txt", "w") as f:
            f.write(full_report)
        
        # 打印报告
        print(full_report)
        
        # 保存评分数据为JSON
        score_data = {
            "isolation_score": isolation_score,
            "redundancy_score": redundancy_score,
            "logical_score": logical_score,
            "semantic_score": semantic_score,
            "total_score": total_score,
            "timestamp": time.ctime()
        }
        with open(f"{self.config['output_dir']}/quality_scores.json", "w") as f:
            json.dump(score_data, f, indent=2)

    # def run_evaluation(self):
    #     """执行完整评估流程"""
    #     self.load_data()
    #     metrics = {}
        
    #     print(">>> 检测孤立节点...")
    #     metrics['isolation_rate'], _ = self.detect_isolated_nodes()
        
    #     print(">>> 检测冗余三元组...")
    #     metrics['redundancy_rate'], _ = self.detect_redundant_triples()
        
    #     print(">>> 检测逻辑一致性...")
    #     metrics['logical_conflict_rate'], _ = self.check_logical_consistency()
        
    #     print(">>> 评估语义一致性...")
    #     metrics['semantic_score'], _ = self.evaluate_semantic_consistency()
        
    #     self.generate_report(metrics)


    def run_evaluation(self):
        """执行完整评估流程"""
        self.load_data()
        metrics = {}
        
        print(">>> 检测孤立节点...")
        metrics['isolation_rate'], isolated_df = self.detect_isolated_nodes()
        
        print(">>> 检测冗余三元组...")
        metrics['redundancy_rate'], redundant_df = self.detect_redundant_triples()
        
        print(">>> 检测逻辑一致性...")
        metrics['logical_conflict_rate'], conflicts_df = self.check_logical_consistency()
        
        print(">>> 评估语义一致性...")
        metrics['semantic_score'], semantic_df = self.evaluate_semantic_consistency()
        
        # 保存问题三元组数据
        all_issues = pd.concat([
            isolated_df.assign(issue_type="孤立节点"),
            redundant_df.assign(issue_type="冗余三元组"),
            conflicts_df.assign(issue_type="逻辑冲突")
        ], ignore_index=True)
        if not all_issues.empty:
            all_issues.to_csv(f"{self.config['output_dir']}/all_issues.csv", index=False)
        
        # 生成报告
        self.generate_report(metrics)
        
        # 返回评估结果
        return {
            "metrics": metrics,
            "scores": {
                "isolation_score": (1 - metrics['isolation_rate']) * 100,
                "redundancy_score": (1 - metrics['redundancy_rate']) * 100,
                "logical_score": (1 - metrics['logical_conflict_rate']) * 100,
                "semantic_score": metrics['semantic_score'] * 100,
                "total_score": (
                    (1 - metrics['isolation_rate']) * 0.25 +
                    (1 - metrics['redundancy_rate']) * 0.25 +
                    (1 - metrics['logical_conflict_rate']) * 0.25 +
                    metrics['semantic_score'] * 0.25
                ) * 100
            }
        }
def main():
    """主函数，支持命令行参数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="政务知识图谱质量评估工具")
    parser.add_argument("--node-files", nargs='+', default=CONFIG["node_files"],
                       help="节点CSV文件路径列表")
    parser.add_argument("--rel-files", nargs='+', default=CONFIG["relationship_files"],
                       help="关系CSV文件路径列表")
    parser.add_argument("--output-dir", default=CONFIG["output_dir"],
                       help="报告输出目录")
    parser.add_argument("--api-key", default=CONFIG.get("zhipuai_api_key"),
                       help="智谱AI API密钥")
    parser.add_argument("--sample-size", type=float, default=CONFIG["semantic_eval_sample_size"],
                       help="语义评估采样比例 (0-1)")
    parser.add_argument("--no-semantic", action="store_true",
                       help="跳过语义评估（节省API调用）")
    
    args = parser.parse_args()
    
    # 更新配置
    config = CONFIG.copy()
    config["node_files"] = args.node_files
    config["relationship_files"] = args.rel_files
    config["output_dir"] = args.output_dir
    config["semantic_eval_sample_size"] = 0 if args.no_semantic else args.sample_size
    
    if args.api_key:
        config["zhipuai_api_key"] = args.api_key
    
    print(f"📊 开始政务知识图谱质量评估...")
    print(f"📁 节点文件: {args.node_files}")
    print(f"📁 关系文件: {args.rel_files}")
    print(f"📁 输出目录: {args.output_dir}")
    print(f"🤖 语义评估: {'启用' if not args.no_semantic else '禁用'}")
    print("-" * 50)
    
    # 运行评估
    evaluator = KnowledgeGraphEvaluator(config)
    result = evaluator.run_evaluation()
    
    print("-" * 50)
    print(f"✅ 评估完成！")
    print(f"📈 最终得分: {result['scores']['total_score']:.2f}/100")
    
    # 输出质量等级
    score = result['scores']['total_score']
    if score >= 90:
        grade = "优秀"
    elif score >= 80:
        grade = "良好"
    elif score >= 70:
        grade = "中等"
    elif score >= 60:
        grade = "及格"
    else:
        grade = "不合格"
    
    print(f"🏆 质量等级: {grade}")
    print(f"📋 详细报告已保存至: {args.output_dir}")


if __name__ == "__main__":
    main()