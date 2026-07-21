#!/usr/bin/env python3
"""
使用增强版服务器批量处理 JSONL 文件，输出分离的 CSV 格式
专门用于测试质量增强功能
"""

import json
import asyncio
import os
import sys
import argparse
from typing import List, Dict, Set, Tuple
from dotenv import load_dotenv
from mcp.client.stdio import StdioServerParameters, stdio_client
from mcp import ClientSession
from mcp.types import TextContent


async def process_single_line(session, text: str, idx: int) -> Dict:
    """处理单行文本"""
    try:
        # 调用增强版服务器工具
        result = await session.call_tool(
            "build_and_analyze_kg", 
            arguments={
                "text": text, 
                "output_file": "off",
                "enable_analysis": True,
                "auto_enhance": True
            }
        )
        
        # 提取返回的内容
        if result.content and len(result.content) > 0:
            content = result.content[0]
            if hasattr(content, 'text'):
                parsed_result = json.loads(content.text)
                return parsed_result
        
        return {"success": False, "error": "No content returned"}
    
    except Exception as e:
        print(f"\n处理第 {idx} 行时出错: {str(e)}")
        return {"success": False, "error": str(e)}


def extract_text_from_json(data: Dict) -> str:
    """从政务 JSON 数据中提取文本"""
    # 如果有标准字段，优先使用
    text = data.get('text') or data.get('sentence') or data.get('content', '')
    if text:
        return text
    
    # 提取政务相关字段
    parts = []
    if '服务事项' in data:
        parts.append(f"服务事项：{data['服务事项']}")
    if '权力类型' in data:
        parts.append(f"权力类型：{data['权力类型']}")
    if '行驶主体' in data:
        parts.append(f"行驶主体：{data['行驶主体']}")
    if '承办机构' in data:
        parts.append(f"承办机构：{data['承办机构']}")
    if '实施依据' in data and len(data['实施依据']) < 500:
        parts.append(f"实施依据：{data['实施依据'][:500]}")
    
    return "。".join(parts) if parts else ""


def init_csv_files(base_path: str):
    """初始化 CSV 文件，写入表头"""
    nodes_csv = f"{base_path}_nodes.csv"
    relationships_csv = f"{base_path}_relationships.csv"
    
    # 初始化 nodes.csv
    with open(nodes_csv, 'w', encoding='utf-8') as f:
        f.write("id,name,node_type\n")
    
    # 初始化 relationships.csv
    with open(relationships_csv, 'w', encoding='utf-8') as f:
        f.write("start_id,end_id,relation_type,source\n")
    
    return nodes_csv, relationships_csv


def append_to_csv_files(new_nodes: List[Dict], new_relationships: List[Dict], 
                       nodes_csv: str, relationships_csv: str, 
                       existing_nodes: Dict[str, int]) -> Dict[str, int]:
    """追加写入新的节点和关系到 CSV 文件"""
    
    # 追加写入 nodes.csv
    with open(nodes_csv, 'a', encoding='utf-8') as f:
        for node in new_nodes:
            name = node['name'].replace('"', '""')
            node_type = node['node_type'].replace('"', '""')
            if ',' in name or '"' in name:
                name = f'"{name}"'
            if ',' in node_type or '"' in node_type:
                node_type = f'"{node_type}"'
            f.write(f"{node['id']},{name},{node_type}\n")
            existing_nodes[node['name']] = node['id']
    
    # 追加写入 relationships.csv
    with open(relationships_csv, 'a', encoding='utf-8') as f:
        for rel in new_relationships:
            relation_type = rel['relation_type'].replace('"', '""')
            if ',' in relation_type or '"' in relation_type:
                relation_type = f'"{relation_type}"'
            f.write(f"{rel['start_id']},{rel['end_id']},{relation_type},{rel['source']}\n")
    
    return existing_nodes


def process_batch_results(batch_results: List[Dict], existing_nodes: Dict[str, int], 
                         next_node_id: int) -> Tuple[List[Dict], List[Dict], Dict[str, int], int]:
    """处理一个批次的结果，返回新的节点和关系"""
    new_nodes = []
    new_relationships = []
    
    for result in batch_results:
        if not result.get("success", False):
            continue
        
        # 从增强版服务器的返回结构中提取数据
        summary = result.get("summary", {})
        final_triples = summary.get("final_triples", [])
        
        # 如果没有增强结果，尝试从原始结果获取
        if not final_triples:
            stages = result.get("stages", {})
            original_kg = stages.get("original_knowledge_graph", {})
            # 这里需要从其他地方获取三元组数据
            continue
        
        # 构建实体类型映射（增强版暂时都设为Unknown）
        entity_types = {}
        
        # 处理三元组，添加新节点
        for triple in final_triples:
            if isinstance(triple, dict):
                head = triple.get("head", "")
                relation = triple.get("relation", "")
                tail = triple.get("tail", "")
                
                # 为新节点分配ID
                for node_name in [head, tail]:
                    if node_name and node_name not in existing_nodes:
                        node_type = "Enhanced"  # 标记为增强版提取的节点
                        new_nodes.append({
                            "id": next_node_id,
                            "name": node_name,
                            "node_type": node_type
                        })
                        existing_nodes[node_name] = next_node_id
                        next_node_id += 1
                
                # 添加关系
                if head in existing_nodes and tail in existing_nodes:
                    new_relationships.append({
                        "start_id": existing_nodes[head],
                        "end_id": existing_nodes[tail],
                        "relation_type": relation,
                        "source": "enhanced_extraction"
                    })
    
    return new_nodes, new_relationships, existing_nodes, next_node_id


async def run_enhanced_bulk(jsonl_path: str, out_base: str, 
                           server_cmd: str = "python", 
                           server_args: List[str] = None):
    """使用增强版服务器批量处理 JSONL 文件"""
    server_args = server_args or ["kg_server_enhanced.py"]
    load_dotenv()
    
    # 读取 JSONL 文件
    texts = []
    try:
        with open(jsonl_path, 'r', encoding='utf-8') as f:
            for idx, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    text = extract_text_from_json(data)
                    
                    if text:
                        texts.append(text)
                    else:
                        print(f"警告: 第 {idx} 行没有提取到文本内容")
                except json.JSONDecodeError as e:
                    print(f"警告: 第 {idx} 行 JSON 解析失败: {e}")
    except FileNotFoundError:
        print(f"错误: 找不到文件 {jsonl_path}")
        return
    except Exception as e:
        print(f"读取文件时出错: {e}")
        return
    
    if not texts:
        print("错误: 没有找到可处理的文本")
        return
    
    print(f"📖 从 {jsonl_path} 读取了 {len(texts)} 条文本")
    
    # 初始化 CSV 文件
    nodes_csv, relationships_csv = init_csv_files(out_base)
    print(f"📁 初始化增强版输出文件:")
    print(f"  - 节点文件: {nodes_csv}")
    print(f"  - 关系文件: {relationships_csv}")
    
    # 跟踪已存在的节点和ID
    existing_nodes = {}  # {节点名: ID}
    next_node_id = 1
    total_nodes = 0
    total_relationships = 0
    
    # 启动增强版服务器并处理
    cmd = [server_cmd] + server_args
    server_params = StdioServerParameters(command=server_cmd, args=server_args, env=os.environ)
    
    print(f"🚀 启动增强版服务器: {' '.join(cmd)}")
    
    async with stdio_client(server_params) as (stdio, write):
        async with ClientSession(stdio, write) as session:
            print("📡 连接到增强版服务器...")
            
            # 初始化会话
            await session.initialize()
            
            # 验证工具是否存在
            tools_response = await session.list_tools()
            tool_names = [t.name for t in tools_response.tools]
            if "build_and_analyze_kg" not in tool_names:
                print("错误：服务器未提供 'build_and_analyze_kg' 工具")
                print(f"可用工具: {tool_names}")
                return
            
            # 批量处理所有文本
            print(f"⚙️  开始批量处理 {len(texts)} 条文本（增强模式）...")
            print("💡 文件将实时更新，增强后的三元组会被标记为 'enhanced_extraction'")
            
            # 并发处理，但限制并发数以避免过载
            batch_size = 5  # 增强版处理较慢，减少批次大小
            successful_count = 0
            failed_count = 0
            
            for i in range(0, len(texts), batch_size):
                batch = texts[i:i+batch_size]
                batch_tasks = []
                
                # 准备批次任务
                for j, text in enumerate(batch):
                    idx = i + j + 1
                    batch_tasks.append(process_single_line(session, text, idx))
                
                print(f"\n📦 处理增强批次 {i//batch_size + 1} (第 {i+1}-{min(i+batch_size, len(texts))} 条)...")
                
                # 等待当前批次完成
                batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
                
                # 转换异常为错误结果
                processed_results = []
                for k, result in enumerate(batch_results):
                    if isinstance(result, Exception):
                        processed_results.append({"success": False, "error": str(result)})
                        failed_count += 1
                    else:
                        processed_results.append(result)
                        if result.get("success", False):
                            successful_count += 1
                        else:
                            failed_count += 1
                
                # 处理这个批次的结果并实时写入
                new_nodes, new_relationships, existing_nodes, next_node_id = process_batch_results(
                    processed_results, existing_nodes, next_node_id
                )
                
                if new_nodes or new_relationships:
                    # 实时写入文件
                    append_to_csv_files(new_nodes, new_relationships, nodes_csv, relationships_csv, existing_nodes)
                    total_nodes += len(new_nodes)
                    total_relationships += len(new_relationships)
                    
                    print(f"  ✅ 本批次: +{len(new_nodes)} 节点, +{len(new_relationships)} 关系")
                    print(f"  📊 累计: {total_nodes} 节点, {total_relationships} 关系")
                    
                    # 显示增强信息
                    enhanced_count = sum(1 for r in processed_results if r.get("success") and 
                                       r.get("stages", {}).get("enhancement_results", {}).get("enhancement_applied", False))
                    print(f"  🔧 本批次增强: {enhanced_count}/{len(processed_results)} 条")
                else:
                    print(f"  ⚠️  本批次未提取到新的三元组")
            
            print(f"\n🎉 所有批次处理完成！")
    
    # 最终统计
    print(f"\n📈 最终统计:")
    print(f"  - 成功: {successful_count}/{len(texts)}")
    print(f"  - 失败: {failed_count}/{len(texts)}")
    print(f"  - 总节点: {total_nodes}")
    print(f"  - 总关系: {total_relationships}")
    print(f"\n📁 输出文件:")
    print(f"  - {nodes_csv} ({total_nodes} 个节点)")
    print(f"  - {relationships_csv} ({total_relationships} 条关系)")
    print(f"\n💡 提示: 可以使用以下命令评估增强后的图谱质量:")
    print(f"  cd data && python evaluate.py --node-files {os.path.basename(nodes_csv)} --rel-files {os.path.basename(relationships_csv)} --output-dir {os.path.basename(out_base)}_评估报告 --no-semantic")


def main():
    parser = argparse.ArgumentParser(description="使用增强版服务器批量处理 JSONL 文件生成知识图谱")
    parser.add_argument("jsonl_file", help="输入的 JSONL 文件路径")
    parser.add_argument("-o", "--output", help="输出文件基础名（默认与输入文件同名_enhanced）")
    parser.add_argument("--server-cmd", default="python", help="服务器命令（默认: python）")
    parser.add_argument("--server-args", nargs="+", default=["kg_server_enhanced.py"], help="服务器参数（默认: kg_server_enhanced.py）")
    
    args = parser.parse_args()
    
    # 确定输出路径
    if args.output:
        out_base = args.output
    else:
        base_name = os.path.splitext(args.jsonl_file)[0]
        out_base = f"{base_name}_enhanced"
    
    # 运行批量处理
    asyncio.run(run_enhanced_bulk(
        args.jsonl_file, 
        out_base,
        args.server_cmd,
        args.server_args
    ))


if __name__ == "__main__":
    main()
