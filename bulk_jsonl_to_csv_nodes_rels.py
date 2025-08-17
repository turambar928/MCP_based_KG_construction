#!/usr/bin/env python3
"""
批量处理 JSONL 文件，使用非增强模式（kg_server.py）提取三元组
输出为分离的 nodes.csv 和 relationships.csv 格式
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
import subprocess


async def process_single_line(session, text: str, idx: int) -> Dict:
    """处理单行文本"""
    try:
        # 调用服务器工具构建知识图谱（输出文件名设为 off 避免生成文件）
        result = await session.call_tool(
            "build_knowledge_graph", 
            arguments={"text": text, "output_file": "off"}
        )
        
        # 提取返回的内容
        if result.content and len(result.content) > 0:
            content = result.content[0]
            if hasattr(content, 'text'):
                parsed_result = json.loads(content.text)
                # 可选的调试信息（默认关闭）
                if False and idx == 1:  # 设为 False 关闭调试信息
                    print(f"\n调试信息 - 服务器返回:")
                    print(f"  成功: {parsed_result.get('success', False)}")
                    stages = parsed_result.get('stages', {})
                    kg_const = stages.get('knowledge_graph_construction', stages.get('knowledge_graph', {}))
                    print(f"  实体数: {len(kg_const.get('entities', []))}")
                    print(f"  三元组数: {len(kg_const.get('triples', []))}")
                return parsed_result
        
        return {"success": False, "error": "No content returned"}
    
    except Exception as e:
        import traceback
        print(f"\n处理第 {idx} 行时出错: {str(e)}")
        print(f"错误类型: {type(e).__name__}")
        print(f"详细错误:\n{traceback.format_exc()}")
        return {"success": False, "error": str(e)}





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
            # 对包含逗号的字段进行引号包裹
            name = node['name'].replace('"', '""')  # 转义引号
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
            # 对包含逗号的字段进行引号包裹
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
            
        # 先尝试从 data 字段获取
        data = result.get("data", {})
        if data:
            entities = data.get("entities", [])
            triples = data.get("triples", [])
        else:
            # 兼容旧格式
            stages = result.get("stages", {})
            kg_construction = stages.get("knowledge_graph_construction", stages.get("knowledge_graph", {}))
            entities = kg_construction.get("entities", [])
            triples = kg_construction.get("triples", [])
        
        # 构建实体类型映射
        entity_types = {}
        for entity in entities:
            if isinstance(entity, dict):
                name = entity.get("name", entity.get("entity", ""))
                etype = entity.get("type", "Unknown")
                entity_types[name] = etype
            elif isinstance(entity, str):
                entity_types[entity] = "Unknown"
        
        # 处理三元组，添加新节点
        for triple in triples:
            if isinstance(triple, dict):
                head = triple.get("head", "")
                relation = triple.get("relation", "")
                tail = triple.get("tail", "")
                
                # 为新节点分配ID
                for node_name in [head, tail]:
                    if node_name and node_name not in existing_nodes:
                        node_type = entity_types.get(node_name, "Unknown")
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
                        "source": "extraction"
                    })
    
    return new_nodes, new_relationships, existing_nodes, next_node_id


async def run_bulk(jsonl_path: str, out_base: str, 
                  server_cmd: str = "python", 
                  server_args: List[str] = None):
    """批量处理 JSONL 文件"""
    server_args = server_args or ["kg_server.py"]
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
                    # 支持多种格式
                    text = data.get('text') or data.get('sentence') or data.get('content', '')
                    
                    # 如果没有找到标准字段，尝试从政务数据格式中提取
                    if not text:
                        # 尝试组合政务相关字段
                        parts = []
                        if '服务事项' in data:
                            parts.append(f"服务事项：{data['服务事项']}")
                        if '权力类型' in data:
                            parts.append(f"权力类型：{data['权力类型']}")
                        if '行驶主体' in data:
                            parts.append(f"行驶主体：{data['行驶主体']}")
                        if '承办机构' in data:
                            parts.append(f"承办机构：{data['承办机构']}")
                        if '实施依据' in data and len(data['实施依据']) < 500:  # 限制长度
                            parts.append(f"实施依据：{data['实施依据'][:500]}")
                        
                        if parts:
                            text = "。".join(parts)
                    
                    if text:
                        texts.append(text)
                    else:
                        print(f"警告: 第 {idx} 行没有找到文本内容")
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
    print(f"📁 初始化文件:")
    print(f"  - 节点文件: {nodes_csv}")
    print(f"  - 关系文件: {relationships_csv}")
    
    # 跟踪已存在的节点和ID
    existing_nodes = {}  # {节点名: ID}
    next_node_id = 1
    total_nodes = 0
    total_relationships = 0
    
    # 启动服务器并处理
    cmd = [server_cmd] + server_args
    server_params = StdioServerParameters(command=server_cmd, args=server_args)
    
    print(f"🚀 启动服务器: {' '.join(cmd)}")
    
    async with stdio_client(server_params) as (stdio, write):
        async with ClientSession(stdio, write) as session:
            print("📡 连接到服务器...")
            
            # 初始化会话
            await session.initialize()
            
            # 验证工具是否存在
            tools_response = await session.list_tools()
            tool_names = [t.name for t in tools_response.tools]
            if "build_knowledge_graph" not in tool_names:
                print("错误：服务器未提供 'build_knowledge_graph' 工具")
                print(f"可用工具: {tool_names}")
                return
            
            # 批量处理所有文本
            print(f"⚙️  开始批量处理 {len(texts)} 条文本...")
            print("💡 文件将实时更新，你可以随时查看进度！")
            
            # 并发处理，但限制并发数以避免过载
            batch_size = 10  # 每批处理10条
            successful_count = 0
            failed_count = 0
            
            for i in range(0, len(texts), batch_size):
                batch = texts[i:i+batch_size]
                batch_tasks = []
                
                # 准备批次任务
                for j, text in enumerate(batch):
                    idx = i + j + 1
                    batch_tasks.append(process_single_line(session, text, idx))
                
                print(f"\n📦 处理批次 {i//batch_size + 1} (第 {i+1}-{min(i+batch_size, len(texts))} 条)...")
                
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
                else:
                    print(f"  ⚠️  本批次未提取到新的三元组")
                
                # 强制刷新文件缓冲区
                import os
                os.sync() if hasattr(os, 'sync') else None
            
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


def main():
    parser = argparse.ArgumentParser(description="批量处理 JSONL 文件生成知识图谱")
    parser.add_argument("jsonl_file", help="输入的 JSONL 文件路径")
    parser.add_argument("-o", "--output", help="输出文件基础名（默认与输入文件同名）")
    parser.add_argument("--server-cmd", default="python", help="服务器命令（默认: python）")
    parser.add_argument("--server-args", nargs="+", help="服务器参数（默认: kg_server.py）")
    
    args = parser.parse_args()
    
    # 确定输出路径
    if args.output:
        out_base = args.output
    else:
        out_base = os.path.splitext(args.jsonl_file)[0]
    
    # 运行批量处理
    asyncio.run(run_bulk(
        args.jsonl_file, 
        out_base,
        args.server_cmd,
        args.server_args
    ))


if __name__ == "__main__":
    main()
