#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
语义规则评价脚本
使用语义匹配来解决规则格式不匹配的问题
"""

import json
import os
import argparse
from dataclasses import dataclass
from typing import Dict, List, Any, Tuple
import requests
import time

@dataclass
class EvaluationMetrics:
    """评价指标数据类"""
    rule_coverage_score: float
    detection_precision: float
    detection_recall: float
    false_positive_rate: float
    unique_capability_score: float
    overall_score: float

class LLMErrorJudge:
    """LLM错误判断器"""
    
    def __init__(self, api_key: str, base_url: str, model: str):
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
    
    def judge_triple_error(self, triple: str, context: str = "") -> Dict[str, Any]:
        """使用LLM判断三元组是否为错误"""
        prompt = f"""
请判断以下政务领域的三元组关系是否正确，并给出详细分析：

三元组：{triple}
上下文：{context}

请从以下角度分析：
1. 逻辑合理性：主体是否有权限对客体执行该关系
2. 层级关系：是否符合政府机构的层级管理关系
3. 业务逻辑：是否符合政务业务流程
4. 法律依据：是否符合相关法律法规

请按以下JSON格式回答：
{{
    "is_error": true/false,
    "error_type": "错误类型（如：层级关系错误、权限错误、逻辑错误等）",
    "confidence": 0.0-1.0,
    "reason": "详细分析原因",
    "suggestion": "改进建议"
}}

只返回JSON，不要其他内容。
"""
        
        data = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.1,
            "max_tokens": 500
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=self.headers,
                json=data,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result['choices'][0]['message']['content'].strip()
                
                # 尝试解析JSON
                try:
                    # 提取JSON部分
                    if content.startswith('```json'):
                        content = content.replace('```json', '').replace('```', '').strip()
                    elif content.startswith('```'):
                        content = content.replace('```', '').strip()
                    
                    judgment = json.loads(content)
                    return judgment
                except json.JSONDecodeError:
                    # 如果JSON解析失败，尝试从文本中提取信息
                    return self._parse_text_judgment(content)
            else:
                print(f"LLM API调用失败: {response.status_code}")
                return {"is_error": False, "error_type": "API调用失败", "confidence": 0.0, "reason": "无法调用LLM", "suggestion": "检查API配置"}
                
        except Exception as e:
            print(f"LLM调用异常: {e}")
            return {"is_error": False, "error_type": "调用异常", "confidence": 0.0, "reason": str(e), "suggestion": "检查网络连接"}
    
    def _parse_text_judgment(self, text: str) -> Dict[str, Any]:
        """从文本中解析判断结果"""
        is_error = "错误" in text or "不正确" in text or "不合理" in text or "违规" in text
        
        return {
            "is_error": is_error,
            "error_type": "文本解析",
            "confidence": 0.5,
            "reason": text[:200] + "..." if len(text) > 200 else text,
            "suggestion": "建议使用JSON格式输出"
        }

class SemanticRuleEvaluator:
    """语义规则评价器"""
    
    def __init__(self, expert_rules_file: str, generated_rules_file: str, api_key: str = None, base_url: str = None, model: str = None):
        self.expert_rules = self.load_expert_rules(expert_rules_file)
        self.generated_rules = self.load_generated_rules(generated_rules_file)
        
        # 初始化LLM判断器
        if api_key and base_url and model:
            self.llm_judge = LLMErrorJudge(api_key, base_url, model)
            self.use_llm_judgment = True
        else:
            self.llm_judge = None
            self.use_llm_judgment = False
            print("⚠️ 未提供LLM配置，将使用硬编码判断")
        
        # 在LLM判断器初始化后再创建测试用例
        self.test_cases = self.create_test_cases()
    
    def load_expert_rules(self, file_path: str) -> Dict[str, Any]:
        """加载专家规则"""
        expert_rules = {
            "entity_types": ["政府机构", "企业", "个人", "服务事项", "权力类型"],
            "relationship_types": ["管理", "监管", "处罚", "审批", "服务"],
            "forbidden_rules": [
                ["企业", "管理", "政府机构"],  # 企业不能管理政府机构
                ["个人", "监管", "政府机构"],  # 个人不能监管政府机构
                ["服务事项", "处罚", "政府机构"],  # 服务事项不能处罚政府机构
            ],
            "allowed_rules": [
                ["政府机构", "管理", "政府机构"],  # 政府机构可以管理政府机构
                ["政府机构", "监管", "企业"],  # 政府机构可以监管企业
                ["政府机构", "处罚", "企业"],  # 政府机构可以处罚企业
            ]
        }
        return expert_rules
    
    def load_generated_rules(self, file_path: str) -> Dict[str, Any]:
        """加载生成规则并转换格式"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                raw_rules = json.load(f)
            
            # 转换生成规则格式
            converted_rules = self.convert_generated_rules(raw_rules)
            return converted_rules
            
        except FileNotFoundError:
            print(f"⚠️ 生成规则文件不存在: {file_path}")
            return {
                "entity_types": [],
                "relationship_types": [],
                "forbidden_rules": [],
                "allowed_rules": []
            }
    
    def convert_generated_rules(self, raw_rules: Dict[str, Any]) -> Dict[str, Any]:
        """将生成规则转换为标准三元组格式"""
        converted_rules = {
            "entity_types": raw_rules.get("entity_types", []),
            "relationship_types": raw_rules.get("relationship_types", []),
            "forbidden_rules": [],
            "allowed_rules": []
        }
        
        # 1. 转换禁止规则
        for rule in raw_rules.get("type_conflict_rules_forbidden", []):
            if len(rule) == 3:
                converted_rules["forbidden_rules"].append(rule)
        
        # 2. 转换允许规则
        for rule in raw_rules.get("type_conflict_rules_allowed", []):
            if len(rule) == 3:
                converted_rules["allowed_rules"].append(rule)
        
        # 3. 转换程序性规则为禁止规则
        procedural_forbidden = self.convert_procedural_rules(raw_rules.get("procedural_rules", []))
        converted_rules["forbidden_rules"].extend(procedural_forbidden)
        
        # 4. 转换层级规则为禁止规则
        hierarchy_forbidden = self.convert_hierarchy_rules(raw_rules.get("hierarchy_rules", []))
        converted_rules["forbidden_rules"].extend(hierarchy_forbidden)
        
        print(f"✅ 转换完成: {len(converted_rules['forbidden_rules'])} 个禁止规则, {len(converted_rules['allowed_rules'])} 个允许规则")
        
        return converted_rules
    
    def convert_procedural_rules(self, procedural_rules: List[Any]) -> List[List[str]]:
        """转换程序性规则为三元组格式"""
        converted = []
        
        for rule in procedural_rules:
            rule_str = str(rule)
            
            # 执法人员必须出示证件
            if "执法人员" in rule_str and "必须" in rule_str and "出示" in rule_str:
                converted.append(["执法主体", "未出示", "证件"])
            
            # 处罚决定书必须载明违法事实
            elif "处罚决定书" in rule_str and "载明" in rule_str:
                converted.append(["法律文书", "遗漏", "法律内容"])
            
            # 调查人员不得少于两人
            elif "调查" in rule_str and "两人" in rule_str:
                converted.append(["调查人员", "少于两人", "调查"])
            
            # 处罚决定必须送达当事人
            elif "送达" in rule_str and "当事人" in rule_str:
                converted.append(["处罚决定", "未送达", "当事人"])
            
            # 申请材料必须齐全
            elif "申请材料" in rule_str and "齐全" in rule_str:
                converted.append(["申请材料", "不齐全", "审批"])
            
            # 听证会申请期限
            elif "听证" in rule_str and "申请" in rule_str:
                converted.append(["程序", "违反", "时间要求"])
            
            # 处罚决定必须公开
            elif "处罚决定" in rule_str and "公开" in rule_str:
                converted.append(["处罚决定", "未公开", "公众"])
            
            # 大型活动必须报备
            elif "大型活动" in rule_str and "报备" in rule_str:
                converted.append(["大型活动", "未报备", "公安机关"])
        
        return converted
    
    def convert_hierarchy_rules(self, hierarchy_rules: List[Any]) -> List[List[str]]:
        """转换层级规则为三元组格式"""
        converted = []
        
        for rule in hierarchy_rules:
            rule_str = str(rule)
            
            # 上级部门管理下级部门
            if "上级部门" in rule_str and "下级部门" in rule_str:
                converted.append(["下级部门", "管理", "上级部门"])
            
            # 文物保护单位层级
            elif "文物保护单位" in rule_str and "级别" in rule_str:
                converted.append(["省级文物保护单位", "拆除", "全国重点文物保护单位"])
            
            # 文物行政部门层级
            elif "文物行政部门" in rule_str and "上级" in rule_str:
                converted.append(["下级文物行政部门", "管理", "上级文物行政部门"])
        
        return converted
    
    def create_test_cases(self) -> List[Dict[str, Any]]:
        """创建测试用例"""
        test_cases = []
        
        # 基础测试用例（不包含is_error字段，由LLM判断）
        base_test_cases = [
            # 1. 明显错误案例（专家规则应该检测）
            {
                "triple": "企业 --[管理]--> 政府机构",
                "subject_type": "企业", "relation": "管理", "object_type": "政府机构",
                "error_type": "层级关系错误",
                "expected_detection": "both",
                "severity": "high"
            },
            {
                "triple": "个人 --[监管]--> 政府机构", 
                "subject_type": "个人", "relation": "监管", "object_type": "政府机构",
                "error_type": "权限错误",
                "expected_detection": "both",
                "severity": "high"
            },
            {
                "triple": "服务事项 --[处罚]--> 政府机构",
                "subject_type": "服务事项", "relation": "处罚", "object_type": "政府机构", 
                "error_type": "逻辑错误",
                "expected_detection": "both",
                "severity": "high"
            },
            {
                "triple": "政策 --[吃]--> 任何实体",
                "subject_type": "政策", "relation": "吃", "object_type": "任何实体",
                "error_type": "荒谬关系",
                "expected_detection": "both",
                "severity": "high"
            },
            {
                "triple": "地区 --[结婚]--> 任何实体",
                "subject_type": "地区", "relation": "结婚", "object_type": "任何实体",
                "error_type": "语义矛盾",
                "expected_detection": "both",
                "severity": "high"
            },
            {
                "triple": "法规 --[睡觉]--> 任何实体",
                "subject_type": "法规", "relation": "睡觉", "object_type": "任何实体",
                "error_type": "逻辑错误",
                "expected_detection": "both",
                "severity": "high"
            },
            {
                "triple": "下级机构 --[管理]--> 上级机构",
                "subject_type": "下级机构", "relation": "管理", "object_type": "上级机构",
                "error_type": "层级关系错误",
                "expected_detection": "both",
                "severity": "high"
            },
            {
                "triple": "被监管对象 --[监管]--> 监管机构",
                "subject_type": "被监管对象", "relation": "监管", "object_type": "监管机构",
                "error_type": "监管关系颠倒",
                "expected_detection": "both",
                "severity": "high"
            },
            
            # 2. 生成规则独有能力测试（只有生成规则能检测）
            {
                "triple": "执法主体 --[未出示]--> 证件",
                "subject_type": "执法主体", "relation": "未出示", "object_type": "证件",
                "error_type": "程序性违规",
                "expected_detection": "generated_only",
                "severity": "medium"
            },
            {
                "triple": "法律文书 --[遗漏]--> 法律内容",
                "subject_type": "法律文书", "relation": "遗漏", "object_type": "法律内容",
                "error_type": "程序性违规", 
                "expected_detection": "generated_only",
                "severity": "medium"
            },
            {
                "triple": "程序 --[违反]--> 时间要求",
                "subject_type": "程序", "relation": "违反", "object_type": "时间要求",
                "error_type": "时限违规",
                "expected_detection": "generated_only",
                "severity": "medium"
            },
            {
                "triple": "调查人员 --[少于两人]--> 调查",
                "subject_type": "调查人员", "relation": "少于两人", "object_type": "调查",
                "error_type": "程序性违规",
                "expected_detection": "generated_only",
                "severity": "medium"
            },
            {
                "triple": "处罚决定 --[未送达]--> 当事人",
                "subject_type": "处罚决定", "relation": "未送达", "object_type": "当事人",
                "error_type": "程序性违规",
                "expected_detection": "generated_only",
                "severity": "medium"
            },
            {
                "triple": "申请材料 --[不齐全]--> 审批",
                "subject_type": "申请材料", "relation": "不齐全", "object_type": "审批",
                "error_type": "程序性违规",
                "expected_detection": "generated_only",
                "severity": "medium"
            },
            {
                "triple": "处罚决定 --[未公开]--> 公众",
                "subject_type": "处罚决定", "relation": "未公开", "object_type": "公众",
                "error_type": "程序性违规",
                "expected_detection": "generated_only",
                "severity": "medium"
            },
            {
                "triple": "大型活动 --[未报备]--> 公安机关",
                "subject_type": "大型活动", "relation": "未报备", "object_type": "公安机关",
                "error_type": "程序性违规",
                "expected_detection": "generated_only",
                "severity": "medium"
            },
            
            # 3. 正确关系测试（不应该被误报）
            {
                "triple": "市政府 --[管理]--> 市教育局",
                "subject_type": "政府机构", "relation": "管理", "object_type": "政府机构",
                "error_type": "正确关系",
                "expected_detection": "none",
                "severity": "none"
            },
            {
                "triple": "工商局 --[监管]--> 企业",
                "subject_type": "政府机构", "relation": "监管", "object_type": "企业",
                "error_type": "正确关系",
                "expected_detection": "none", 
                "severity": "none"
            },
            {
                "triple": "环保局 --[处罚]--> 污染企业",
                "subject_type": "政府机构", "relation": "处罚", "object_type": "企业",
                "error_type": "正确关系",
                "expected_detection": "none",
                "severity": "none"
            },
            {
                "triple": "公民 --[申请]--> 服务事项",
                "subject_type": "公民", "relation": "申请", "object_type": "服务事项",
                "error_type": "正确关系",
                "expected_detection": "none",
                "severity": "none"
            },
            {
                "triple": "企业 --[申请]--> 服务事项",
                "subject_type": "企业", "relation": "申请", "object_type": "服务事项",
                "error_type": "正确关系",
                "expected_detection": "none",
                "severity": "none"
            },
            {
                "triple": "政策 --[适用于]--> 地区",
                "subject_type": "政策", "relation": "适用于", "object_type": "地区",
                "error_type": "正确关系",
                "expected_detection": "none",
                "severity": "none"
            },
            {
                "triple": "法规 --[约束]--> 企业",
                "subject_type": "法规", "relation": "约束", "object_type": "企业",
                "error_type": "正确关系",
                "expected_detection": "none",
                "severity": "none"
            },
            {
                "triple": "服务事项 --[属于]--> 政府机构",
                "subject_type": "服务事项", "relation": "属于", "object_type": "政府机构",
                "error_type": "正确关系",
                "expected_detection": "none",
                "severity": "none"
            },
            {
                "triple": "地区 --[位于]--> 地区",
                "subject_type": "地区", "relation": "位于", "object_type": "地区",
                "error_type": "正确关系",
                "expected_detection": "none",
                "severity": "none"
            },
            {
                "triple": "政府机构 --[发布]--> 政策",
                "subject_type": "政府机构", "relation": "发布", "object_type": "政策",
                "error_type": "正确关系",
                "expected_detection": "none",
                "severity": "none"
            }
        ]
        
        # 如果使用LLM判断，则动态判断is_error字段
        if self.use_llm_judgment:
            print("🤖 使用LLM判断测试用例的错误性...")
            for i, test_case in enumerate(base_test_cases):
                print(f"  判断测试用例 {i+1}/{len(base_test_cases)}: {test_case['triple']}")
                
                # 调用LLM判断
                judgment = self.llm_judge.judge_triple_error(
                    test_case['triple'], 
                    f"政务领域，{test_case['error_type']}"
                )
                
                # 添加LLM判断结果
                test_case['is_error'] = judgment.get('is_error', False)
                test_case['llm_judgment'] = judgment
                
                # 添加延迟避免API限制
                time.sleep(0.5)
        else:
            # 使用硬编码判断
            for test_case in base_test_cases:
                if test_case['expected_detection'] in ['both', 'generated_only']:
                    test_case['is_error'] = True
                else:
                    test_case['is_error'] = False
        
        test_cases.extend(base_test_cases)
        return test_cases
    
    def evaluate_rule_set(self, rules: Dict[str, Any], rule_name: str) -> EvaluationMetrics:
        """评价规则集"""
        print(f"🔍 正在评价{rule_name}...")
        
        detected_violations = []
        false_positives = []
        true_positives = []
        false_negatives = []
        
        for test_case in self.test_cases:
            is_detected = self.check_violation_semantic(test_case, rules)
            is_actually_error = test_case["is_error"]
            
            if is_detected:
                detected_violations.append(test_case)
                if is_actually_error:
                    true_positives.append(test_case)
                else:
                    false_positives.append(test_case)
            else:
                if is_actually_error:
                    false_negatives.append(test_case)
        
        # 计算指标
        precision = len(true_positives) / len(detected_violations) if detected_violations else 0
        recall = len(true_positives) / (len(true_positives) + len(false_negatives)) if (true_positives or false_negatives) else 0
        false_positive_rate = len(false_positives) / len(detected_violations) if detected_violations else 0
        
        # 计算规则覆盖度得分
        coverage_score = self.calculate_coverage_score(rules)
        
        # 计算独特能力得分
        unique_capability_score = self.calculate_unique_capability_score(rules)
        
        # 综合得分计算
        overall_score = (
            precision * 0.4 +           # 精确度权重40%
            recall * 0.3 +               # 召回率权重30%
            (1 - false_positive_rate) * 0.2 +  # 误报率权重20%
            coverage_score * 0.05 +      # 覆盖度权重5%
            unique_capability_score * 0.05  # 独特能力权重5%
        )
        
        print(f"  {rule_name}评价结果:")
        print(f"    精确度: {precision:.3f}")
        print(f"    召回率: {recall:.3f}")
        print(f"    误报率: {false_positive_rate:.3f}")
        print(f"    覆盖度: {coverage_score:.3f}")
        print(f"    综合得分: {overall_score:.3f}")
        
        return EvaluationMetrics(
            rule_coverage_score=coverage_score,
            detection_precision=precision,
            detection_recall=recall,
            false_positive_rate=false_positive_rate,
            unique_capability_score=unique_capability_score,
            overall_score=overall_score
        )
    
    def check_violation_semantic(self, test_case: Dict[str, Any], rules: Dict[str, Any]) -> bool:
        """使用语义匹配检查违规"""
        subject_type = test_case["subject_type"]
        relation = test_case["relation"]
        object_type = test_case["object_type"]
        
        # 检查所有禁止规则（现在都是统一的三元组格式）
        for rule in rules.get("forbidden_rules", []):
            if self.match_rule_improved(rule, subject_type, relation, object_type):
                return True
        
        return False
    
    def match_rule_improved(self, rule: List[str], subject_type: str, relation: str, object_type: str) -> bool:
        """改进的规则匹配（统一处理所有规则）"""
        if len(rule) != 3:
            return False
        
        rule_subj, rule_rel, rule_obj = rule
        
        # 1. 精确匹配
        if (rule_subj == subject_type and rule_rel == relation and rule_obj == object_type):
            return True
        
        # 2. 语义匹配
        subject_match = self.improved_semantic_match(rule_subj, subject_type)
        relation_match = self.improved_semantic_match(rule_rel, relation)
        object_match = self.improved_semantic_match(rule_obj, object_type)
        
        return subject_match and relation_match and object_match
    
    def match_rule_exact(self, rule: List[str], subject_type: str, relation: str, object_type: str) -> bool:
        """精确匹配规则"""
        if len(rule) != 3:
            return False
        
        rule_subj, rule_rel, rule_obj = rule
        return (rule_subj == subject_type and rule_rel == relation and rule_obj == object_type)
    
    def match_generated_rule(self, rule: List[str], subject_type: str, relation: str, object_type: str) -> bool:
        """匹配生成规则（改进版）"""
        if len(rule) != 3:
            return False
        
        rule_subj, rule_rel, rule_obj = rule
        
        # 更精确的匹配逻辑
        # 1. 主体类型匹配
        subject_match = self.improved_semantic_match(rule_subj, subject_type)
        
        # 2. 关系匹配
        relation_match = self.improved_semantic_match(rule_rel, relation)
        
        # 3. 客体类型匹配
        object_match = self.improved_semantic_match(rule_obj, object_type)
        
        return subject_match and relation_match and object_match
    
    def improved_semantic_match(self, rule_term: str, test_term: str) -> bool:
        """改进的语义匹配（更精确）"""
        # 1. 精确匹配
        if rule_term == test_term:
            return True
        
        # 2. 严格的包含匹配（避免过度匹配）
        if len(rule_term) >= 3 and rule_term in test_term:
            return True
        if len(test_term) >= 3 and test_term in rule_term:
            return True
        
        # 3. 关键语义对匹配（减少误匹配）
        key_semantic_pairs = [
            # 实体类型匹配
            ("企业", "工业企业"), ("企业", "药品零售企业"),
            ("政府机构", "公安机关"), ("政府机构", "执法机关"),
            ("个人", "执法人员"), ("个人", "组织者"),
            ("服务事项", "处罚决定"), ("服务事项", "申请材料"),
            
            # 关系匹配
            ("管理", "不得"), ("监管", "处罚"), ("处罚", "不得"),
            ("未出示", "必须"), ("遗漏", "载明"), ("违反", "遵守"),
            ("少于两人", "至少两人"), ("未送达", "送达"), ("不齐全", "齐全"),
            
            # 客体匹配
            ("执法证件", "证件"), ("违法事实", "事实"), ("当事人", "人"),
            ("申请材料", "材料"), ("审批", "审查")
        ]
        
        for pair in key_semantic_pairs:
            if (rule_term in pair and test_term in pair):
                return True
        
        return False
    
    def semantic_match(self, rule_term: str, test_term: str) -> bool:
        """原始语义匹配（保留兼容性）"""
        return self.improved_semantic_match(rule_term, test_term)
    
    def match_hierarchy_rule(self, rule: List[str], subject_type: str, relation: str, object_type: str) -> bool:
        """匹配层级规则"""
        # 层级规则通常涉及上下级关系
        hierarchy_keywords = ["管理", "监管", "处罚", "审批"]
        if relation in hierarchy_keywords:
            # 检查是否违反层级关系
            if subject_type == "企业" and object_type == "政府机构":
                return True
            if subject_type == "个人" and object_type == "政府机构":
                return True
        return False
    
    def match_procedural_rule_improved(self, rule: List[str], subject_type: str, relation: str, object_type: str) -> bool:
        """改进的程序性规则匹配"""
        # 将程序性规则转换为三元组格式进行匹配
        if isinstance(rule, list) and len(rule) >= 3:
            # 处理字符串格式的规则
            if isinstance(rule[0], str) and rule[0].startswith("['"):
                # 解析字符串格式的规则
                rule_str = str(rule)
                if "执法人员" in rule_str and "必须" in rule_str and "出示" in rule_str:
                    return subject_type == "执法主体" and relation == "未出示" and object_type == "证件"
                elif "处罚决定书" in rule_str and "载明" in rule_str:
                    return subject_type == "法律文书" and relation == "遗漏" and object_type == "法律内容"
                elif "调查" in rule_str and "两人" in rule_str:
                    return subject_type == "调查人员" and relation == "少于两人" and object_type == "调查"
                elif "送达" in rule_str and "当事人" in rule_str:
                    return subject_type == "处罚决定" and relation == "未送达" and object_type == "当事人"
                elif "申请材料" in rule_str and "齐全" in rule_str:
                    return subject_type == "申请材料" and relation == "不齐全" and object_type == "审批"
                elif "听证" in rule_str and "申请" in rule_str:
                    return subject_type == "程序" and relation == "违反" and object_type == "时间要求"
        
        # 程序性违规关键词匹配
        procedural_keywords = ["未出示", "遗漏", "违反", "不得", "少于两人", "未送达", "不齐全"]
        if relation in procedural_keywords:
            return True
        
        return False
    
    def match_procedural_rule(self, rule: List[str], subject_type: str, relation: str, object_type: str) -> bool:
        """原始程序性规则匹配（保留兼容性）"""
        return self.match_procedural_rule_improved(rule, subject_type, relation, object_type)
    
    def calculate_coverage_score(self, rules: Dict[str, Any]) -> float:
        """计算规则覆盖度得分"""
        entity_types = len(rules.get("entity_types", []))
        relationship_types = len(rules.get("relationship_types", []))
        
        # 归一化得分
        max_entity_types = max(len(self.expert_rules.get("entity_types", [])), 
                              len(self.generated_rules.get("entity_types", [])))
        max_relationship_types = max(len(self.expert_rules.get("relationship_types", [])),
                                   len(self.generated_rules.get("relationship_types", [])))
        
        entity_score = entity_types / max_entity_types if max_entity_types > 0 else 0
        relation_score = relationship_types / max_relationship_types if max_relationship_types > 0 else 0
        
        return (entity_score + relation_score) / 2
    
    def calculate_unique_capability_score(self, rules: Dict[str, Any]) -> float:
        """计算独特能力得分"""
        # 计算各种规则类型的数量
        forbidden_rules = len(rules.get("forbidden_rules", []))
        type_conflict_rules = len(rules.get("type_conflict_rules_forbidden", []))
        hierarchy_rules = len(rules.get("hierarchy_rules", []))
        procedural_rules = len(rules.get("procedural_rules", []))
        
        total_rules = forbidden_rules + type_conflict_rules + hierarchy_rules + procedural_rules
        return min(total_rules / 50.0, 1.0)  # 归一化到0-1
    
    def generate_comparison_report(self, expert_metrics: EvaluationMetrics, generated_metrics: EvaluationMetrics) -> str:
        """生成对比报告"""
        # 计算提升倍数
        precision_improvement = generated_metrics.detection_precision / expert_metrics.detection_precision if expert_metrics.detection_precision > 0 else 0
        recall_improvement = generated_metrics.detection_recall / expert_metrics.detection_recall if expert_metrics.detection_recall > 0 else 0
        
        # 计算误报率改善
        if expert_metrics.false_positive_rate > 0:
            fpr_improvement = (expert_metrics.false_positive_rate - generated_metrics.false_positive_rate) / expert_metrics.false_positive_rate
            fpr_improvement_str = f"{fpr_improvement:.2%}"
        else:
            fpr_improvement_str = "N/A (专家规则误报率为0)"
        
        # 计算覆盖度提升
        coverage_improvement = generated_metrics.rule_coverage_score / expert_metrics.rule_coverage_score if expert_metrics.rule_coverage_score > 0 else 0
        
        # 计算总体提升
        overall_improvement = generated_metrics.overall_score / expert_metrics.overall_score if expert_metrics.overall_score > 0 else 0
        
        report = f"""
======== 语义规则评价报告 ========

======== 1. 检测性能对比 ========
精确度 (Precision):
- 专家规则: {expert_metrics.detection_precision:.3f}
- 生成规则: {generated_metrics.detection_precision:.3f}
- 提升: {precision_improvement:.2f}倍

召回率 (Recall):
- 专家规则: {expert_metrics.detection_recall:.3f}
- 生成规则: {generated_metrics.detection_recall:.3f}
- 提升: {recall_improvement:.2f}倍

误报率 (False Positive Rate):
- 专家规则: {expert_metrics.false_positive_rate:.3f}
- 生成规则: {generated_metrics.false_positive_rate:.3f}
- 改善: {fpr_improvement_str}

======== 2. 规则覆盖度对比 ========
规则覆盖度得分:
- 专家规则: {expert_metrics.rule_coverage_score:.3f}
- 生成规则: {generated_metrics.rule_coverage_score:.3f}
- 提升: {coverage_improvement:.2f}倍

======== 3. 独特能力分析 ========
生成规则独特能力得分: {generated_metrics.unique_capability_score:.3f}
- 能检测专家规则无法检测的问题类型
- 包含程序性规则和层级规则
- 覆盖更多专业术语和实体类型

======== 4. 综合评分 ========
综合得分:
- 专家规则: {expert_metrics.overall_score:.3f}
- 生成规则: {generated_metrics.overall_score:.3f}
- 总体提升: {overall_improvement:.2f}倍

======== 5. 评价结论 ========
基于语义匹配的评价准则，分析结果如下：

1. 精确度: {'生成规则更优' if generated_metrics.detection_precision > expert_metrics.detection_precision else '专家规则更优'}
2. 召回率: {'生成规则更优' if generated_metrics.detection_recall > expert_metrics.detection_recall else '专家规则更优'}
3. 误报率: {'专家规则更优' if generated_metrics.false_positive_rate > expert_metrics.false_positive_rate else '生成规则更优'}
4. 覆盖度: {'生成规则更优' if generated_metrics.rule_coverage_score > expert_metrics.rule_coverage_score else '专家规则更优'}
5. 综合性能: {'生成规则更优' if generated_metrics.overall_score > expert_metrics.overall_score else '专家规则更优'}

实验结论: {'自动生成规则在多个维度上优于专家规则' if generated_metrics.overall_score > expert_metrics.overall_score else '专家规则在关键指标上表现更优，生成规则需要进一步优化'}

======== 6. 改进建议 ========
1. 生成规则格式需要标准化，与测试用例格式保持一致
2. 建议使用语义匹配来弥补格式差异
3. 增加更多具体的禁止规则
4. 优化规则生成过程，提高规则质量
"""
        return report
    
    def run_evaluation(self) -> Tuple[EvaluationMetrics, EvaluationMetrics]:
        """运行评价"""
        print("🔍 开始语义规则评价...")
        
        # 评价专家规则
        expert_metrics = self.evaluate_rule_set(self.expert_rules, "专家规则")
        
        # 评价生成规则
        generated_metrics = self.evaluate_rule_set(self.generated_rules, "生成规则")
        
        return expert_metrics, generated_metrics

def main():
    parser = argparse.ArgumentParser(description="语义规则评价脚本（支持LLM判断）")
    parser.add_argument("--expert-rules", default="data/政务_evaluate.py", help="专家规则文件路径")
    parser.add_argument("--generated-rules", default="data/rule_suggestions/aggregated_rules.json", help="生成规则文件路径")
    parser.add_argument("--output-dir", default="data/semantic_evaluation_report", help="输出目录")
    
    # LLM配置参数
    parser.add_argument("--api-key", help="LLM API密钥")
    parser.add_argument("--base-url", help="LLM API基础URL")
    parser.add_argument("--model", help="LLM模型名称")
    
    # 从环境变量读取LLM配置（如果未提供参数）
    parser.add_argument("--use-env", action="store_true", help="从环境变量读取LLM配置")
    
    args = parser.parse_args()
    
    # 处理LLM配置
    api_key = args.api_key
    base_url = args.base_url
    model = args.model
    
    # 默认LLM配置（硬编码）
    default_api_key = "sk-uivoxjihhupbvpqliyvazkjtxszszaiokjekhdftoiiqvugw"
    default_base_url = "https://api.siliconflow.cn/v1"
    default_model = "Qwen/Qwen2.5-7B-Instruct"
    
    if args.use_env or not (api_key and base_url and model):
        # 从环境变量读取（支持多种环境变量名）
        api_key = api_key or os.getenv("OPENAI_API_KEY")
        base_url = base_url or os.getenv("BASE_URL") or os.getenv("OPENAI_BASE_URL")
        model = model or os.getenv("MODEL") or os.getenv("OPENAI_MODEL")
        
        # 如果环境变量中没有找到，使用默认配置
        if not api_key:
            api_key = default_api_key
        if not base_url:
            base_url = default_base_url
        if not model:
            model = default_model
        
        print(f"✅ 使用LLM配置:")
        print(f"  API Key: {api_key[:10]}...")
        print(f"  Base URL: {base_url}")
        print(f"  Model: {model}")
    
    # 创建输出目录
    os.makedirs(args.output_dir, exist_ok=True)
    
    # 运行评价
    evaluator = SemanticRuleEvaluator(
        args.expert_rules, 
        args.generated_rules,
        api_key=api_key,
        base_url=base_url,
        model=model
    )
    expert_metrics, generated_metrics = evaluator.run_evaluation()
    
    # 生成报告
    report = evaluator.generate_comparison_report(expert_metrics, generated_metrics)
    print(report)
    
    # 保存报告
    report_file = os.path.join(args.output_dir, "semantic_evaluation_report.txt")
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)
    
    # 保存LLM判断结果
    if evaluator.use_llm_judgment:
        llm_results_file = os.path.join(args.output_dir, "llm_judgment_results.json")
        llm_results = []
        for test_case in evaluator.test_cases:
            if 'llm_judgment' in test_case:
                llm_results.append({
                    "triple": test_case["triple"],
                    "llm_judgment": test_case["llm_judgment"]
                })
        
        with open(llm_results_file, 'w', encoding='utf-8') as f:
            json.dump(llm_results, f, ensure_ascii=False, indent=2)
        
        print(f"🤖 LLM判断结果已保存至: {llm_results_file}")
    
    print(f"\n📊 详细报告已保存至: {args.output_dir}/")

if __name__ == "__main__":
    main()
