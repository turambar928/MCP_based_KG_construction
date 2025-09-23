#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
为规则对比实验生成测试数据
基于真实政务数据创建包含各种质量问题的测试集
"""

import json
import random
import pandas as pd
from typing import List, Dict, Any
import os

class TestDataGenerator:
    def __init__(self):
        self.positive_samples = []  # 正确的三元组
        self.negative_samples = []  # 错误的三元组（用于测试规则检测效果）
        
    def load_real_data(self, jsonl_file: str) -> List[Dict[str, Any]]:
        """加载真实政务数据"""
        records = []
        if os.path.exists(jsonl_file):
            with open(jsonl_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        try:
                            records.append(json.loads(line))
                        except:
                            continue
        return records[:50]  # 取前50条用于测试

    def create_positive_samples(self, real_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """基于真实数据创建正确的三元组样本"""
        positive_triples = []
        
        for i, record in enumerate(real_data):
            # 提取政务实体和关系
            service_item = record.get('服务事项', f'服务事项_{i}')
            authority = record.get('行驶主体', record.get('承办机构', f'政府部门_{i}'))
            legal_basis = record.get('实施依据', f'法律依据_{i}')
            responsibility = record.get('责任事项', f'责任事项_{i}')
            
            # 生成正确的政务关系三元组
            triples = [
                {
                    'subject': authority,
                    'subject_type': '政府机构',
                    'relation': '负责',
                    'object': service_item,
                    'object_type': '服务事项',
                    'triple_id': f'positive_{i}_1',
                    'data_quality': 'good',
                    'expected_detection': 'pass'
                },
                {
                    'subject': service_item,
                    'subject_type': '服务事项',
                    'relation': '依据',
                    'object': legal_basis,
                    'object_type': '法律法规',
                    'triple_id': f'positive_{i}_2', 
                    'data_quality': 'good',
                    'expected_detection': 'pass'
                },
                {
                    'subject': authority,
                    'subject_type': '政府机构',
                    'relation': '承担',
                    'object': responsibility,
                    'object_type': '责任事项',
                    'triple_id': f'positive_{i}_3',
                    'data_quality': 'good', 
                    'expected_detection': 'pass'
                }
            ]
            positive_triples.extend(triples)
        
        return positive_triples

    def create_negative_samples(self, real_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """创建各种类型的错误三元组，用于测试规则检测能力"""
        negative_triples = []
        
        for i, record in enumerate(real_data[:10]):  # 基于前10条数据生成错误样本
            service_item = record.get('服务事项', f'服务事项_{i}')
            authority = record.get('行驶主体', record.get('承办机构', f'政府部门_{i}'))
            
            # 类型1: 层级关系错误
            negative_triples.append({
                'subject': '县政府',
                'subject_type': '政府机构',
                'relation': '管理',
                'object': '省政府',
                'object_type': '政府机构', 
                'triple_id': f'negative_hierarchy_{i}',
                'data_quality': 'bad',
                'expected_detection': 'fail',
                'error_type': '层级关系错误'
            })
            
            # 类型2: 荒谬关系
            absurd_relations = ['吃', '睡觉', '杀死', '结婚', '跳舞']
            negative_triples.append({
                'subject': service_item,
                'subject_type': '服务事项',
                'relation': random.choice(absurd_relations),
                'object': authority,
                'object_type': '政府机构',
                'triple_id': f'negative_absurd_{i}',
                'data_quality': 'bad',
                'expected_detection': 'fail',
                'error_type': '荒谬关系'
            })
            
            # 类型3: 监管关系颠倒
            negative_triples.append({
                'subject': '企业',
                'subject_type': '企业',
                'relation': '监管',
                'object': '工商局',
                'object_type': '政府机构',
                'triple_id': f'negative_supervision_{i}',
                'data_quality': 'bad',
                'expected_detection': 'fail',
                'error_type': '监管关系错误'
            })
            
            # 类型4: 专家规则无法检测但生成规则可能检测到的复杂错误
            complex_errors = [
                {
                    'subject': '行政处罚决定书',
                    'subject_type': '法律文书',
                    'relation': '遗漏',
                    'object': '违法事实',
                    'object_type': '法律内容',
                    'error_type': '程序性错误'
                },
                {
                    'subject': '执法人员',
                    'subject_type': '执法主体', 
                    'relation': '未出示',
                    'object': '执法证件',
                    'object_type': '证件',
                    'error_type': '程序性错误'
                },
                {
                    'subject': '听证会',
                    'subject_type': '程序',
                    'relation': '违反',
                    'object': '7日内申请期限',
                    'object_type': '时间要求',
                    'error_type': '时限违规'
                }
            ]
            
            for j, error in enumerate(complex_errors):
                negative_triples.append({
                    **error,
                    'triple_id': f'negative_complex_{i}_{j}',
                    'data_quality': 'bad',
                    'expected_detection': 'fail'
                })
        
        return negative_triples

    def create_edge_cases(self) -> List[Dict[str, Any]]:
        """创建边界情况的测试用例"""
        edge_cases = [
            # 实体类型覆盖测试 - 生成规则应该覆盖更多类型
            {
                'subject': '消防设施',
                'subject_type': '设施设备',
                'relation': '配置要求',
                'object': '完好有效',
                'object_type': '状态要求',
                'triple_id': 'edge_entity_coverage_1',
                'data_quality': 'normal',
                'expected_detection': 'specialist_miss',  # 专家规则可能遗漏
                'test_purpose': '测试实体类型覆盖'
            },
            {
                'subject': '特种设备安全管理人员',
                'subject_type': '作业人员',
                'relation': '培训',
                'object': '安全知识',
                'object_type': '培训内容', 
                'triple_id': 'edge_entity_coverage_2',
                'data_quality': 'normal',
                'expected_detection': 'specialist_miss',
                'test_purpose': '测试实体类型覆盖'
            },
            
            # 关系类型覆盖测试
            {
                'subject': '鉴定机构',
                'subject_type': '第三方机构',
                'relation': '鉴定',
                'object': '技术问题',
                'object_type': '专业问题',
                'triple_id': 'edge_relation_coverage_1',
                'data_quality': 'normal',
                'expected_detection': 'specialist_miss',
                'test_purpose': '测试关系类型覆盖'
            },
            
            # 程序性规则测试
            {
                'subject': '案件调查',
                'subject_type': '执法程序',
                'relation': '要求',
                'object': '两人以上执法',
                'object_type': '程序要求',
                'triple_id': 'edge_procedural_1',
                'data_quality': 'normal', 
                'expected_detection': 'specialist_miss',
                'test_purpose': '测试程序性规则'
            }
        ]
        
        return edge_cases

    def generate_complete_test_set(self, jsonl_file: str) -> Dict[str, Any]:
        """生成完整的测试数据集"""
        print("🔄 正在生成测试数据...")
        
        # 加载真实数据
        real_data = self.load_real_data(jsonl_file)
        print(f"加载真实数据: {len(real_data)} 条")
        
        # 生成各类测试样本
        positive_samples = self.create_positive_samples(real_data)
        negative_samples = self.create_negative_samples(real_data)
        edge_cases = self.create_edge_cases()
        
        print(f"生成正例样本: {len(positive_samples)} 个")
        print(f"生成负例样本: {len(negative_samples)} 个") 
        print(f"生成边界用例: {len(edge_cases)} 个")
        
        # 合并所有样本
        all_samples = positive_samples + negative_samples + edge_cases
        
        # 统计信息
        test_statistics = {
            'total_samples': len(all_samples),
            'positive_samples': len(positive_samples),
            'negative_samples': len(negative_samples),
            'edge_cases': len(edge_cases),
            'error_types': {
                '层级关系错误': len([s for s in negative_samples if s.get('error_type') == '层级关系错误']),
                '荒谬关系': len([s for s in negative_samples if s.get('error_type') == '荒谬关系']),
                '监管关系错误': len([s for s in negative_samples if s.get('error_type') == '监管关系错误']),
                '程序性错误': len([s for s in negative_samples if s.get('error_type') == '程序性错误']),
                '时限违规': len([s for s in negative_samples if s.get('error_type') == '时限违规']),
            }
        }
        
        return {
            'test_data': all_samples,
            'statistics': test_statistics,
            'metadata': {
                'data_source': jsonl_file,
                'generation_purpose': '规则对比实验',
                'expected_results': {
                    'expert_rules_should_detect': len([s for s in all_samples if s.get('expected_detection') == 'fail' and s.get('error_type') in ['层级关系错误', '荒谬关系', '监管关系错误']]),
                    'generated_rules_should_detect_additionally': len([s for s in all_samples if s.get('expected_detection') == 'specialist_miss'])
                }
            }
        }

def main():
    generator = TestDataGenerator()
    
    # 生成测试数据
    jsonl_file = "data/政务_test.jsonl"
    if not os.path.exists(jsonl_file):
        jsonl_file = "data/政务.jsonl"
    
    if not os.path.exists(jsonl_file):
        print("❌ 未找到政务数据文件，请确保存在以下文件之一：")
        print("  - data/政务_test.jsonl")
        print("  - data/政务.jsonl")
        return
    
    test_dataset = generator.generate_complete_test_set(jsonl_file)
    
    # 保存测试数据
    output_file = "data/rule_test_dataset.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(test_dataset, f, ensure_ascii=False, indent=2)
    
    # 保存为简化格式供实验脚本使用
    simplified_data = test_dataset['test_data']
    with open("data/rule_test_triples.json", 'w', encoding='utf-8') as f:
        json.dump(simplified_data, f, ensure_ascii=False, indent=2)
    
    print("\n✅ 测试数据生成完成！")
    print(f"📄 完整数据集: {output_file}")
    print(f"📄 简化数据集: data/rule_test_triples.json")
    print(f"\n📊 数据集统计:")
    stats = test_dataset['statistics']
    print(f"  • 总样本数: {stats['total_samples']}")
    print(f"  • 正例样本: {stats['positive_samples']}")
    print(f"  • 负例样本: {stats['negative_samples']}")
    print(f"  • 边界用例: {stats['edge_cases']}")
    print(f"\n🎯 预期结果:")
    metadata = test_dataset['metadata']
    print(f"  • 专家规则应检测到: {metadata['expected_results']['expert_rules_should_detect']} 个错误")
    print(f"  • 生成规则额外检测到: {metadata['expected_results']['generated_rules_should_detect_additionally']} 个问题")

if __name__ == "__main__":
    main()
