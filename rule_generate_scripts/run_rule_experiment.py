#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
规则对比实验 - 快速运行脚本
证明自动生成规则比专家规则更好的实验
"""

import os
import sys
from rule_comparison_experiment import RuleComparisonExperiment

def main():
    print("🚀 启动规则对比实验...")
    print("="*60)
    
    # 检查必要文件
    data_file = "data/政务_test.jsonl"
    generated_rules_file = "data/rule_suggestions/aggregated_rules.json"
    output_dir = "data/rule_comparison_report"
    
    if not os.path.exists(generated_rules_file):
        print(f"❌ 错误：未找到生成的规则文件: {generated_rules_file}")
        print("请先运行规则生成脚本：")
        print("python generate_rules_from_gov_texts.py --limit 20")
        return
    
    print(f"📄 数据文件: {data_file}")
    print(f"📋 生成规则文件: {generated_rules_file}")
    print(f"📊 输出目录: {output_dir}")
    print()
    
    try:
        # 运行实验
        experiment = RuleComparisonExperiment(data_file, generated_rules_file)
        comparison_result = experiment.compare_rules()
        experiment.generate_report(comparison_result, output_dir)
        
        print("\n" + "="*60)
        print("✅ 实验完成！")
        print("="*60)
        
        # 显示关键结果
        perf = comparison_result['detection_performance']
        quantity = comparison_result['rule_quantity_comparison']
        unique = comparison_result['unique_capabilities']
        
        print("\n🎯 关键实验结果:")
        print(f"• 规则数量提升: {quantity['quantity_improvement']:.1f}倍")
        print(f"• 实体类型覆盖提升: {quantity['entity_coverage_improvement']:.1f}倍")
        print(f"• 关系类型覆盖提升: {quantity['relationship_coverage_improvement']:.1f}倍")
        print(f"• 检测能力提升: {perf['detection_improvement']:.1f}倍")
        print(f"• 独有实体类型: {len(unique['generated_only_entity_types'])}种")
        print(f"• 独有关系类型: {len(unique['generated_only_relations'])}种")
        print(f"• 程序性规则: {unique['procedural_rules_count']}条")
        
        print(f"\n📋 详细报告位置: {output_dir}/")
        print("   - rule_comparison_report.txt  (详细文本报告)")
        print("   - comparison_data.json       (实验数据)")
        print("   - visualization_data.json    (可视化数据)")
        
    except Exception as e:
        print(f"❌ 实验执行失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
