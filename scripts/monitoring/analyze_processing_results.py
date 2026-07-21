#!/usr/bin/env python3
"""
分析不同数据质量下的知识图谱提取效果
对比普通服务器 vs 增强服务器的处理能力
"""

import json
import os
import csv
import argparse
from typing import Dict, List, Any

def count_csv_records(filepath: str) -> int:
    """统计CSV文件记录数（不含表头）"""
    if not os.path.exists(filepath):
        return 0
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return sum(1 for line in f) - 1  # 减去表头
    except:
        return 0

def analyze_extraction_results(base_path: str, jsonl_path: str) -> Dict[str, Any]:
    """分析知识图谱提取结果"""
    
    # 统计原始数据
    total_records = 0
    low_quality_records = 0
    normal_quality_records = 0
    
    try:
        with open(jsonl_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    try:
                        data = json.loads(line.strip())
                        total_records += 1
                        if data.get('质量标签') == '低质量':
                            low_quality_records += 1
                        else:
                            normal_quality_records += 1
                    except:
                        continue
    except:
        pass
    
    # 统计提取结果
    nodes_file = f"{base_path}_nodes.csv"
    relationships_file = f"{base_path}_relationships.csv"
    checkpoint_file = f"{base_path}_checkpoint.json"
    
    nodes_count = count_csv_records(nodes_file)
    relationships_count = count_csv_records(relationships_file)
    
    # 读取处理进度
    processed_count = 0
    if os.path.exists(checkpoint_file):
        try:
            with open(checkpoint_file, 'r', encoding='utf-8') as f:
                checkpoint = json.load(f)
                processed_count = checkpoint.get('processed_count', 0)
        except:
            pass
    
    # 计算提取率
    node_extraction_rate = (nodes_count / processed_count) if processed_count > 0 else 0
    relationship_extraction_rate = (relationships_count / processed_count) if processed_count > 0 else 0
    processing_rate = (processed_count / total_records) if total_records > 0 else 0
    
    return {
        "原始数据统计": {
            "总记录数": total_records,
            "低质量记录": low_quality_records,
            "正常质量记录": normal_quality_records,
            "低质量比例": f"{(low_quality_records/total_records*100):.1f}%" if total_records > 0 else "0%"
        },
        "处理进度": {
            "已处理记录": processed_count,
            "处理进度": f"{(processed_count/total_records*100):.1f}%" if total_records > 0 else "0%"
        },
        "提取结果": {
            "节点数": nodes_count,
            "关系数": relationships_count,
            "节点提取率": f"{(node_extraction_rate):.3f} 节点/记录",
            "关系提取率": f"{(relationship_extraction_rate):.3f} 关系/记录"
        },
        "质量影响分析": {
            "提取效果": "极差" if node_extraction_rate < 0.1 else "较差" if node_extraction_rate < 0.5 else "一般" if node_extraction_rate < 1.0 else "良好",
            "可能原因": [
                "低质量数据中的术语错误导致实体识别失败",
                "逻辑矛盾使关系抽取模型混淆",
                "格式错误影响文本解析",
                "冗余信息干扰关键信息提取"
            ] if node_extraction_rate < 0.5 else ["数据质量较好，提取正常"]
        }
    }

def compare_with_normal_data(normal_base: str, low_quality_base: str, 
                           normal_jsonl: str, low_quality_jsonl: str):
    """对比正常数据和低质量数据的处理效果"""
    
    print("📊 正在分析正常数据处理结果...")
    normal_results = analyze_extraction_results(normal_base, normal_jsonl)
    
    print("📊 正在分析低质量数据处理结果...")
    low_quality_results = analyze_extraction_results(low_quality_base, low_quality_jsonl)
    
    print("\n" + "="*60)
    print("📈 知识图谱提取效果对比分析")
    print("="*60)
    
    print(f"\n🔵 正常数据处理结果:")
    print_analysis_results(normal_results)
    
    print(f"\n🔴 低质量数据处理结果:")
    print_analysis_results(low_quality_results)
    
    print(f"\n📊 对比分析:")
    
    # 计算性能下降
    normal_node_rate = normal_results["提取结果"]["节点数"] / normal_results["处理进度"]["已处理记录"] if normal_results["处理进度"]["已处理记录"] > 0 else 0
    low_quality_node_rate = low_quality_results["提取结果"]["节点数"] / low_quality_results["处理进度"]["已处理记录"] if low_quality_results["处理进度"]["已处理记录"] > 0 else 0
    
    normal_rel_rate = normal_results["提取结果"]["关系数"] / normal_results["处理进度"]["已处理记录"] if normal_results["处理进度"]["已处理记录"] > 0 else 0
    low_quality_rel_rate = low_quality_results["提取结果"]["关系数"] / low_quality_results["处理进度"]["已处理记录"] if low_quality_results["处理进度"]["已处理记录"] > 0 else 0
    
    node_degradation = ((normal_node_rate - low_quality_node_rate) / normal_node_rate * 100) if normal_node_rate > 0 else 0
    rel_degradation = ((normal_rel_rate - low_quality_rel_rate) / normal_rel_rate * 100) if normal_rel_rate > 0 else 0
    
    print(f"  节点提取性能下降: {node_degradation:.1f}%")
    print(f"  关系提取性能下降: {rel_degradation:.1f}%")
    
    if node_degradation > 50 or rel_degradation > 50:
        print(f"  🎯 结论: 低质量数据严重影响知识图谱提取效果！")
        print(f"  💡 这证明了质量评估和数据清洗的重要性")
    else:
        print(f"  ⚠️  数据质量影响相对较小，可能需要引入更多质量问题")

def print_analysis_results(results: Dict[str, Any]):
    """打印分析结果"""
    for category, data in results.items():
        print(f"  📋 {category}:")
        if isinstance(data, dict):
            for key, value in data.items():
                print(f"    {key}: {value}")
        else:
            print(f"    {data}")

def main():
    parser = argparse.ArgumentParser(description="分析知识图谱提取效果")
    parser.add_argument("--normal-base", default="data/政务", 
                       help="正常数据处理结果基础路径")
    parser.add_argument("--low-quality-base", default="data/政务_低质量",
                       help="低质量数据处理结果基础路径") 
    parser.add_argument("--normal-jsonl", default="data/政务.jsonl",
                       help="正常数据JSONL文件")
    parser.add_argument("--low-quality-jsonl", default="data/政务_低质量.jsonl",
                       help="低质量数据JSONL文件")
    parser.add_argument("--mode", choices=["normal", "low-quality", "compare"], 
                       default="compare", help="分析模式")
    
    args = parser.parse_args()
    
    if args.mode == "normal":
        results = analyze_extraction_results(args.normal_base, args.normal_jsonl)
        print("🔵 正常数据分析结果:")
        print_analysis_results(results)
        
    elif args.mode == "low-quality":
        results = analyze_extraction_results(args.low_quality_base, args.low_quality_jsonl)
        print("🔴 低质量数据分析结果:")
        print_analysis_results(results)
        
    else:  # compare
        compare_with_normal_data(
            args.normal_base, args.low_quality_base,
            args.normal_jsonl, args.low_quality_jsonl
        )

if __name__ == "__main__":
    main()
