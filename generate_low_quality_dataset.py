import json
import random
import argparse
import os
import re
from typing import List, Dict, Any

class LowQualityDataGenerator:
    def __init__(self):
        # 定义各种质量问题类型及其实现方法
        self.quality_issues = {
            "字段缺失": self.introduce_missing_fields,
            "信息不一致": self.introduce_inconsistencies, 
            "术语错误": self.introduce_terminology_errors,
            "逻辑矛盾": self.introduce_logical_contradictions,
            "格式错误": self.introduce_format_errors,
            "冗余信息": self.introduce_redundancy,
            "关系错误": self.introduce_relationship_errors,
            "实体类型错误": self.introduce_entity_type_errors,
            "孤立节点制造": self.introduce_isolated_nodes,
            "层级冲突制造": self.introduce_hierarchy_conflicts,
            "重复三元组制造": self.introduce_duplicate_triples
        }
    
    def load_jsonl(self, filepath: str) -> List[Dict[str, Any]]:
        """加载JSONL文件"""
        data = []
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        data.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        return data
    
    def save_jsonl(self, data: List[Dict[str, Any]], filepath: str):
        """保存JSONL文件"""
        os.makedirs(os.path.dirname(filepath) if os.path.dirname(filepath) else ".", exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            for item in data:
                f.write(json.dumps(item, ensure_ascii=False) + '\n')
        print(f"✅ 已保存 {len(data)} 条低质量记录到 {filepath}")
    
    def introduce_missing_fields(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """引入字段缺失问题"""
        corrupted = record.copy()
        
        # 随机删除一些字段
        optional_fields = ["承办机构", "监管电话", "实施依据"]
        for field in optional_fields:
            if field in corrupted and random.random() < 0.3:  # 30%概率删除
                del corrupted[field]
        
        # 将重要字段置空
        important_fields = ["服务事项", "权力类型", "行驶主体", "责任事项"]
        for field in important_fields:
            if field in corrupted and random.random() < 0.1:  # 10%概率置空
                corrupted[field] = ""
        
        return corrupted
    
    def introduce_inconsistencies(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """引入信息不一致问题"""
        corrupted = record.copy()
        
        # 日期不一致
        if "责任事项" in corrupted:
            content = corrupted["责任事项"]
            # 随机改变日期
            if "日期" in content:
                # 添加冲突的日期信息
                content += f"\n备注：实际处理日期为{random.choice(['2019-12-31', '2025-01-01', '1999-13-32'])}"
                corrupted["责任事项"] = content
        
        # 金额不一致
        if "责任事项" in corrupted and "万元" in corrupted["责任事项"]:
            content = corrupted["责任事项"]
            # 添加冲突的金额信息
            content += f"\n说明：另据文件显示金额为{random.choice(['0万元', '999999万元', '-50万元'])}）"
            corrupted["责任事项"] = content
        
        # 机构名称不一致
        if "行驶主体" in corrupted and "承办机构" in corrupted:
            if random.random() < 0.2:  # 20%概率引入不一致
                corrupted["承办机构"] = random.choice([
                    "某不存在的机构", "已撤销的部门", "未成立的办公室"
                ])
        
        return corrupted
    
    def introduce_terminology_errors(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """引入术语错误"""
        corrupted = record.copy()
        
        # 金融领域术语错误
        if "金融" in str(record):
            finance_errors = {
                "银行": random.choice(["钱庄", "存钱罐", "银库"]),
                "监管": random.choice(["监视", "看管", "监控"]),
                "违规": random.choice(["不对", "错误", "不好"]),
                "处罚": random.choice(["惩罚", "责骂", "批评"]),
                "合规": random.choice(["听话", "正确", "好的"])
            }
            
            for field in ["服务事项", "责任事项"]:
                if field in corrupted:
                    for correct, wrong in finance_errors.items():
                        if correct in corrupted[field] and random.random() < 0.3:
                            corrupted[field] = corrupted[field].replace(correct, wrong)
        
        # 环境领域术语错误
        if "环境" in str(record):
            env_errors = {
                "污染": random.choice(["脏乱", "不干净", "有毒"]),
                "排放": random.choice(["丢弃", "倒出", "扔掉"]),
                "监测": random.choice(["看看", "瞧瞧", "观察"]),
                "治理": random.choice(["清理", "打扫", "整理"]),
                "废水": random.choice(["脏水", "坏水", "臭水"])
            }
            
            for field in ["服务事项", "责任事项"]:
                if field in corrupted:
                    for correct, wrong in env_errors.items():
                        if correct in corrupted[field] and random.random() < 0.3:
                            corrupted[field] = corrupted[field].replace(correct, wrong)
        
        # 政务领域术语错误
        if "政务" in str(record) or "行政" in str(record) or any(keyword in str(record) for keyword in ["处罚", "许可", "审批", "服务事项"]):
            gov_errors = {
                "行政处罚": random.choice(["行政惩罚", "行政责骂", "行政教育"]),
                "行政许可": random.choice(["行政允许", "行政同意", "行政批准"]),
                "服务事项": random.choice(["服务项目", "办事内容", "业务活动"]),
                "权力类型": random.choice(["权利种类", "职能分类", "业务类别"]),
                "行驶主体": random.choice(["执行单位", "办理机关", "负责部门"]),
                "承办机构": random.choice(["经办单位", "处理部门", "操作机关"]),
                "实施依据": random.choice(["执行根据", "办理理由", "操作标准"]),
                "责任事项": random.choice(["义务内容", "职责范围", "工作要求"]),
                "监管": random.choice(["监视", "看管", "盯着"]),
                "审批": random.choice(["审查", "检查", "看看"]),
                "办理": random.choice(["处理", "搞定", "弄好"]),
                "申请": random.choice(["请求", "要求", "希望"]),
                "受理": random.choice(["接受", "收到", "拿到"])
            }
            
            for field in ["服务事项", "责任事项", "实施依据"]:
                if field in corrupted:
                    for correct, wrong in gov_errors.items():
                        if correct in corrupted[field] and random.random() < 0.3:
                            corrupted[field] = corrupted[field].replace(correct, wrong)
        
        return corrupted
    
    def introduce_logical_contradictions(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """引入逻辑矛盾"""
        corrupted = record.copy()
        
        # 权力类型与服务事项矛盾
        if "权力类型" in corrupted and "服务事项" in corrupted:
            if "处罚" in corrupted["服务事项"] and random.random() < 0.2:
                corrupted["权力类型"] = random.choice(["行政许可", "公共服务", "信息公开"])
            elif "许可" in corrupted["服务事项"] and random.random() < 0.2:
                corrupted["权力类型"] = random.choice(["行政处罚", "行政强制", "行政征收"])
        
        # 机构与职权矛盾
        if "行驶主体" in corrupted and "服务事项" in corrupted:
            if random.random() < 0.15:  # 15%概率引入矛盾
                if "金融" in corrupted["服务事项"]:
                    corrupted["行驶主体"] = random.choice([
                        "教育部", "农业农村部", "文化和旅游部", "体育总局"
                    ])
                elif "环境" in corrupted["服务事项"]:
                    corrupted["行驶主体"] = random.choice([
                        "商务部", "工信部", "发改委", "统计局"
                    ])
                elif any(keyword in corrupted["服务事项"] for keyword in ["行政处罚", "行政许可", "政务服务"]):
                    # 政务领域的机构职权矛盾
                    corrupted["行驶主体"] = random.choice([
                        "中国足球协会", "中国烹饪协会", "某民间组织", "个人工作室",
                        "已注销企业", "外国政府", "国际组织"
                    ])
        
        # 处罚对象与处罚机关层级矛盾
        if "责任事项" in corrupted:
            if random.random() < 0.1:  # 10%概率
                content = corrupted["责任事项"]
                content += "\n备注：下级机构对上级机构进行处罚"
                corrupted["责任事项"] = content
        
        return corrupted
    
    def introduce_format_errors(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """引入格式错误"""
        corrupted = record.copy()
        
        # 电话号码格式错误
        if "监管电话" in corrupted:
            if random.random() < 0.3:
                corrupted["监管电话"] = random.choice([
                    "1234", "电话号码", "请联系相关部门", "029-12345-abc"
                ])
        
        # 案件编号格式错误
        if "责任事项" in corrupted and "编号" in corrupted["责任事项"]:
            if random.random() < 0.2:
                content = corrupted["责任事项"]
                content = re.sub(r'[编号：].*?号', f"编号：{random.choice(['ABC123', '无编号', '待定'])}", content)
                corrupted["责任事项"] = content
        
        # 日期格式错误
        if "责任事项" in corrupted:
            content = corrupted["责任事项"]
            # 随机引入错误日期格式
            if random.random() < 0.2:
                wrong_dates = ["2024年13月45日", "2024/2/30", "24-2-29", "tomorrow"]
                content = re.sub(r'\d{4}-\d{1,2}-\d{1,2}', random.choice(wrong_dates), content)
                corrupted["责任事项"] = content
        
        return corrupted
    
    def introduce_redundancy(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """引入冗余信息"""
        corrupted = record.copy()
        
        # 重复内容
        if "责任事项" in corrupted:
            if random.random() < 0.25:  # 25%概率
                original_content = corrupted["责任事项"]
                # 添加重复信息
                redundant_info = [
                    f"\n重复：{original_content[:50]}...",
                    "\n以上信息重复确认无误。",
                    "\n再次说明：" + original_content.split('\n')[0] if '\n' in original_content else original_content[:30],
                    "\n备注：同上述内容一致。"
                ]
                corrupted["责任事项"] = original_content + random.choice(redundant_info)
        
        # 无意义信息
        if random.random() < 0.2:  # 20%概率
            meaningless_info = [
                "本信息仅供参考", "具体情况以实际为准", "相关负责人已确认",
                "此信息经过多次核实", "数据来源可靠", "信息真实有效"
            ]
            corrupted["备注"] = random.choice(meaningless_info)
        
        return corrupted
    
    def introduce_relationship_errors(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """引入关系错误"""
        corrupted = record.copy()
        
        # 颠倒主客体关系
        if "服务事项" in corrupted and random.random() < 0.15:
            content = corrupted["服务事项"]
            if "监管处罚" in content:
                # 将"A监管B"改为"B监管A"
                corrupted["服务事项"] = content.replace("监管处罚", "被监管表扬")
        
        # 错误的因果关系
        if "责任事项" in corrupted and random.random() < 0.1:
            content = corrupted["责任事项"]
            wrong_causality = [
                "\n原因：因为被处罚所以违法",
                "\n说明：由于合规导致处罚",
                "\n注：处罚是为了违法"
            ]
            corrupted["责任事项"] = content + random.choice(wrong_causality)
        
        return corrupted
    
    def introduce_entity_type_errors(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """引入实体类型错误"""
        corrupted = record.copy()
        
        # 错误的机构分类
        if "行驶主体" in corrupted and random.random() < 0.1:
            wrong_entities = {
                "银保监会": "银保监个人",
                "生态环境局": "生态环境个体户", 
                "证监会": "证监个人工作室",
                "市场监管局": "市场监管私人公司"
            }
            
            for correct, wrong in wrong_entities.items():
                if correct in corrupted["行驶主体"]:
                    corrupted["行驶主体"] = corrupted["行驶主体"].replace(correct, wrong)
                    break
        
        # 混淆概念类型
        if "服务事项" in corrupted and random.random() < 0.1:
            concept_errors = {
                "处罚": random.choice(["物品", "地点", "颜色"]),
                "监管": random.choice(["动物", "植物", "天气"]),
                "违法": random.choice(["美食", "运动", "音乐"])
            }
            
            for correct, wrong in concept_errors.items():
                if correct in corrupted["服务事项"]:
                    corrupted["服务事项"] = corrupted["服务事项"].replace(correct, wrong, 1)
                    break
        
        return corrupted
    
    def introduce_isolated_nodes(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """专门制造孤立节点问题"""
        corrupted = record.copy()
        
        # 策略1: 引入无关联的实体
        if "责任事项" in corrupted and random.random() < 0.3:
            isolated_entities = [
                "某无关联企业", "独立第三方机构", "无业务往来单位", 
                "历史遗留实体", "已停业企业", "虚拟测试实体",
                "某孤立部门", "无管辖权机构", "临时工作组"
            ]
            
            content = corrupted["责任事项"]
            isolated_entity = random.choice(isolated_entities)
            content += f"\n备注：{isolated_entity}不参与此事项但被记录在案"
            corrupted["责任事项"] = content
        
        # 策略2: 删除关键关联信息
        if "承办机构" in corrupted and random.random() < 0.4:
            # 删除承办机构，使行驶主体变成孤立节点
            del corrupted["承办机构"]
        
        # 策略3: 引入断裂的引用链
        if "实施依据" in corrupted and random.random() < 0.2:
            content = corrupted["实施依据"]
            content += "\n相关文件：《已废止的某某规定》（注：该文件已不存在关联）"
            corrupted["实施依据"] = content
        
        return corrupted
    
    def introduce_hierarchy_conflicts(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """专门制造层级冲突问题"""
        corrupted = record.copy()
        
        # 策略1: 下级监管上级的矛盾
        if "行驶主体" in corrupted and "服务事项" in corrupted:
            if "处罚" in corrupted["服务事项"] and random.random() < 0.25:
                # 根据不同领域设置层级冲突
                if any(keyword in str(corrupted) for keyword in ["金融", "银行", "证券"]):
                    # 金融领域：让下级机构处罚上级
                    hierarchy_conflicts = [
                        ("某村镇银行", "处罚中国人民银行违规行为"),
                        ("某证券营业部", "监管证监会工作失误"), 
                        ("某保险代理", "审查银保监会决定")
                    ]
                elif any(keyword in str(corrupted) for keyword in ["环境", "污染", "生态"]):
                    # 环境领域：让下级部门管理上级
                    hierarchy_conflicts = [
                        ("某县环保所", "监管省生态环境厅工作"),
                        ("某镇环保站", "审批市环境局决定"),
                        ("某企业环保部", "指导生态环境部政策")
                    ]
                else:
                    # 政务领域：让下级政府管理上级
                    hierarchy_conflicts = [
                        ("某街道办事处", "监管市政府工作"),
                        ("某村委会", "审批县政府决定"),
                        ("某社区", "管理省政府事务")
                    ]
                
                conflict_actor, conflict_action = random.choice(hierarchy_conflicts)
                corrupted["行驶主体"] = conflict_actor
                corrupted["服务事项"] = conflict_action
        
        # 策略2: 在责任事项中引入明显的层级矛盾
        if "责任事项" in corrupted and random.random() < 0.2:
            content = corrupted["责任事项"]
            hierarchy_errors = [
                "\n特殊说明：下级机构有权监管上级机构",
                "\n注意：被管理方可以管理管理方",
                "\n备注：子公司监管母公司业务",
                "\n说明：县级部门指导省级部门工作"
            ]
            content += random.choice(hierarchy_errors)
            corrupted["责任事项"] = content
        
        return corrupted
    
    def introduce_duplicate_triples(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """专门制造重复三元组问题"""
        corrupted = record.copy()
        
        # 策略1: 在责任事项中重复相同的关系表述
        if "责任事项" in corrupted and random.random() < 0.35:
            content = corrupted["责任事项"]
            
            # 提取关键实体和关系
            if "行驶主体" in corrupted and "服务事项" in corrupted:
                actor = corrupted["行驶主体"]
                service = corrupted["服务事项"]
                
                # 生成重复的三元组表述
                duplicate_statements = [
                    f"\n重复确认：{actor}负责{service}",
                    f"\n再次明确：{actor}执行{service}",
                    f"\n重申：{actor}实施{service}",
                    f"\n重复：{actor}办理{service}相关事宜"
                ]
                
                # 添加2-3个重复表述
                num_duplicates = random.randint(2, 3)
                selected_duplicates = random.sample(duplicate_statements, num_duplicates)
                
                for dup in selected_duplicates:
                    content += dup
                
                corrupted["责任事项"] = content
        
        # 策略2: 创建同义但表述不同的关系
        if "实施依据" in corrupted and random.random() < 0.25:
            content = corrupted["实施依据"]
            if "法" in content:
                synonym_laws = [
                    "\n同时依据：上述法律条文",
                    "\n另外参考：相同法律规定", 
                    "\n补充依据：同等法律条款",
                    "\n参照执行：相关法律条文"
                ]
                content += random.choice(synonym_laws)
                corrupted["实施依据"] = content
        
        # 策略3: 重复的统一发布平台unid（模拟ID冲突）
        if random.random() < 0.1:  # 10%概率
            # 使用一个常见的ID模式
            common_ids = ["DUPLICATE_001", "REPEAT_ID_999", "SAME_UNID_123"]
            corrupted["统一发布平台unid"] = random.choice(common_ids)
        
        return corrupted
    
    def generate_low_quality_dataset(self, input_file: str, output_file: str, 
                                   corruption_rate: float = 0.8, 
                                   issues_per_record: int = 2) -> Dict[str, Any]:
        """生成低质量数据集"""
        print(f"📥 加载数据集: {input_file}")
        data = self.load_jsonl(input_file)
        
        if not data:
            print("❌ 数据集为空或加载失败")
            return {"total": 0, "corrupted": 0, "issues_introduced": {}}
        
        print(f"📊 原始数据集大小: {len(data)} 条记录")
        print(f"🎯 腐化率: {corruption_rate*100:.1f}%")
        print(f"🎯 每条记录平均问题数: {issues_per_record}")
        
        corrupted_data = []
        issues_stats = {issue: 0 for issue in self.quality_issues.keys()}
        total_corrupted = 0
        
        for i, record in enumerate(data):
            # 决定是否腐化这条记录
            if random.random() < corruption_rate:
                corrupted_record = record.copy()
                record_issues = 0
                
                # 优先选择KG特有的问题类型（孤立节点、层级冲突、重复三元组）
                kg_specific_issues = ["孤立节点制造", "层级冲突制造", "重复三元组制造"]
                other_issues = [k for k in self.quality_issues.keys() if k not in kg_specific_issues]
                
                selected_issues = []
                
                # 50%概率必须包含至少一个KG特有问题
                if random.random() < 0.5:
                    selected_issues.append(random.choice(kg_specific_issues))
                
                # 填充剩余的问题类型
                remaining_slots = issues_per_record - len(selected_issues)
                if remaining_slots > 0:
                    available_issues = kg_specific_issues + other_issues
                    # 从所有问题中选择剩余的
                    additional_issues = random.sample(
                        [issue for issue in available_issues if issue not in selected_issues],
                        min(remaining_slots, len(available_issues) - len(selected_issues))
                    )
                    selected_issues.extend(additional_issues)
                
                # 应用选中的质量问题
                for issue_type in selected_issues:
                    try:
                        corrupted_record = self.quality_issues[issue_type](corrupted_record)
                        issues_stats[issue_type] += 1
                        record_issues += 1
                    except Exception as e:
                        print(f"⚠️ 应用问题类型 {issue_type} 时出错: {e}")
                
                if record_issues > 0:
                    total_corrupted += 1
                    # 标记这条记录为低质量
                    corrupted_record["质量标签"] = "低质量"
                    corrupted_record["引入问题"] = selected_issues
                
                corrupted_data.append(corrupted_record)
            else:
                # 保持原始记录不变
                record_copy = record.copy()
                record_copy["质量标签"] = "正常质量"
                corrupted_data.append(record_copy)
            
            # 打印进度
            if (i + 1) % 100 == 0:
                print(f"  已处理 {i+1}/{len(data)} 条记录...")
        
        # 保存低质量数据集
        self.save_jsonl(corrupted_data, output_file)
        
        # 统计信息
        stats = {
            "total": len(data),
            "corrupted": total_corrupted,
            "corruption_rate": total_corrupted / len(data) if len(data) > 0 else 0,
            "issues_introduced": issues_stats
        }
        
        return stats
    
    def generate_reports(self, stats: Dict[str, Any], domain: str, output_dir: str):
        """生成低质量数据集报告"""
        report = f"""
        ======== {domain}领域低质量数据集生成报告 ========
        生成时间: {__import__('time').ctime()}
        
        数据统计:
        - 原始记录数: {stats['total']}
        - 腐化记录数: {stats['corrupted']}
        - 腐化率: {stats['corruption_rate']:.2%}
        
        引入的质量问题统计:
        """
        
        for issue, count in stats['issues_introduced'].items():
            percentage = (count / stats['total'] * 100) if stats['total'] > 0 else 0
            report += f"        - {issue}: {count} 次 ({percentage:.1f}%)\n"
        
        report += f"""
        
        质量问题说明:
        1. 字段缺失: 删除或置空重要字段
        2. 信息不一致: 日期、金额、机构名称冲突
        3. 术语错误: 使用错误的专业术语
        4. 逻辑矛盾: 权力类型与事项不符、层级关系错误
        5. 格式错误: 电话号码、日期、编号格式不规范
        6. 冗余信息: 重复内容、无意义信息
        7. 关系错误: 主客体颠倒、因果关系错误
        8. 实体类型错误: 机构性质分类错误、概念混淆
        
        使用说明:
        - 低质量数据集可用于测试知识图谱质量评估工具
        - 对比正常数据与低质量数据的评估结果
        - 验证质量检测算法的有效性
        """
        
        # 保存报告
        os.makedirs(output_dir, exist_ok=True)
        report_file = os.path.join(output_dir, f"{domain}_低质量数据集报告.txt")
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)
        
        print(report)
        print(f"📋 详细报告已保存至: {report_file}")

def main():
    parser = argparse.ArgumentParser(description="生成低质量数据集用于质量评估实验")
    parser.add_argument("--input-finance", default="data/金融.jsonl", 
                       help="金融数据集输入文件")
    parser.add_argument("--input-environment", default="data/环境.jsonl", 
                       help="环境数据集输入文件")
    parser.add_argument("--input-government", default="data/政务.jsonl", 
                       help="政务数据集输入文件")
    parser.add_argument("--output-dir", default="data", 
                       help="输出目录")
    parser.add_argument("--corruption-rate", type=float, default=0.8,
                       help="数据腐化率 (0-1)")
    parser.add_argument("--issues-per-record", type=int, default=2,
                       help="每条记录平均引入的问题数")
    parser.add_argument("--domain", choices=["finance", "environment", "government", "all"], 
                       default="all", help="处理的领域")
    
    args = parser.parse_args()
    
    generator = LowQualityDataGenerator()
    
    print("🚀 开始生成低质量数据集...")
    print("=" * 60)
    
    if args.domain in ["finance", "all"]:
        if os.path.exists(args.input_finance):
            print(f"\n💰 处理金融领域数据...")
            finance_output = os.path.join(args.output_dir, "金融_低质量.jsonl")
            finance_stats = generator.generate_low_quality_dataset(
                args.input_finance, finance_output, 
                args.corruption_rate, args.issues_per_record
            )
            generator.generate_reports(finance_stats, "金融", args.output_dir)
        else:
            print(f"❌ 金融数据集文件不存在: {args.input_finance}")
    
    if args.domain in ["environment", "all"]:
        if os.path.exists(args.input_environment):
            print(f"\n🌱 处理环境领域数据...")
            env_output = os.path.join(args.output_dir, "环境_低质量.jsonl")
            env_stats = generator.generate_low_quality_dataset(
                args.input_environment, env_output,
                args.corruption_rate, args.issues_per_record
            )
            generator.generate_reports(env_stats, "环境", args.output_dir)
        else:
            print(f"❌ 环境数据集文件不存在: {args.input_environment}")
    
    if args.domain in ["government", "all"]:
        if os.path.exists(args.input_government):
            print(f"\n🏛️ 处理政务领域数据...")
            gov_output = os.path.join(args.output_dir, "政务_低质量.jsonl")
            gov_stats = generator.generate_low_quality_dataset(
                args.input_government, gov_output,
                args.corruption_rate, args.issues_per_record
            )
            generator.generate_reports(gov_stats, "政务", args.output_dir)
        else:
            print(f"❌ 政务数据集文件不存在: {args.input_government}")
    
    print("\n🎉 低质量数据集生成完成！")
    print("\n💡 使用建议:")
    print("1. 用evaluate_finance.py和evaluate_environment.py分别评估正常与低质量数据")
    print("2. 对比评估结果，验证质量评估工具的有效性")
    print("3. 用generate_rules_from_gov_texts.py在低质量数据上测试规则生成")

if __name__ == "__main__":
    main()

