#!/usr/bin/env python3
"""
实时监控批量处理进度的脚本
用法：在另一个终端窗口运行此脚本来监控 CSV 文件的增长
"""

import time
import os
import sys


def monitor_csv_files(base_path: str, check_interval: float = 2.0):
    """监控 CSV 文件的增长"""
    nodes_csv = f"{base_path}_nodes.csv"
    relationships_csv = f"{base_path}_relationships.csv"
    
    print(f"🔍 监控文件增长:")
    print(f"  - 节点文件: {nodes_csv}")
    print(f"  - 关系文件: {relationships_csv}")
    print(f"  - 检查间隔: {check_interval} 秒")
    print(f"  - 按 Ctrl+C 停止监控\n")
    
    last_nodes = 0
    last_relationships = 0
    
    try:
        while True:
            # 检查节点文件
            nodes_count = 0
            if os.path.exists(nodes_csv):
                with open(nodes_csv, 'r', encoding='utf-8') as f:
                    nodes_count = max(0, len(f.readlines()) - 1)  # 减去表头
            
            # 检查关系文件
            relationships_count = 0
            if os.path.exists(relationships_csv):
                with open(relationships_csv, 'r', encoding='utf-8') as f:
                    relationships_count = max(0, len(f.readlines()) - 1)  # 减去表头
            
            # 计算增量
            nodes_delta = nodes_count - last_nodes
            relationships_delta = relationships_count - last_relationships
            
            # 显示状态
            current_time = time.strftime("%H:%M:%S")
            if nodes_delta > 0 or relationships_delta > 0:
                print(f"[{current_time}] 📈 更新: +{nodes_delta} 节点, +{relationships_delta} 关系 "
                      f"(总计: {nodes_count} 节点, {relationships_count} 关系)")
            else:
                print(f"[{current_time}] ⏳ 当前: {nodes_count} 节点, {relationships_count} 关系", end='\r')
            
            last_nodes = nodes_count
            last_relationships = relationships_count
            
            time.sleep(check_interval)
            
    except KeyboardInterrupt:
        print(f"\n\n✅ 监控结束")
        print(f"📊 最终结果: {nodes_count} 节点, {relationships_count} 关系")


def main():
    if len(sys.argv) != 2:
        print("用法: python monitor_progress.py <base_path>")
        print("示例: python monitor_progress.py data/政务")
        sys.exit(1)
    
    base_path = sys.argv[1]
    monitor_csv_files(base_path)


if __name__ == "__main__":
    main()
