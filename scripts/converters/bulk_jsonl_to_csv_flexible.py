#!/usr/bin/env python3
"""
灵活的批量处理 JSONL 文件脚本，支持自定义字段提取
使用非增强模式（kg_server.py）提取三元组
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
                return json.loads(content.text)
        
        return {"success": False, "error": "No content returned"}
    
    except Exception as e:
        print(f"处理第 {idx} 行时出错: {str(e)}")
        return {"success": False, "error": str(e)}


def extract_text_from_json(data: Dict, field_config: List[str], separator: str = "。") -> str:
    """根据配置从 JSON 数据中提取文本"""
    # 如果有标准字段，优先使用
    text = data.get('text') or data.get('sentence') or data.get('content', '')
    if text:
        return text
    
    # 使用配置的字段
    parts = []
    for field in field_config:
        if ':' in field:
            # 格式为 "field:label"
            field_name, label = field.split(':', 1)
            if field_name in data and data[field_name]:
                value = str(data[field_name])
                # 限制长度避免过长的文本
                if len(value) > 500:
                    value = value[:500] + "..."
                parts.append(f"{label}：{value}")
        else:
            # 只有字段名，不带标签
            if field in data and data[field]:
                value = str(data[field])
                if len(value) > 500:
                    value = value[:500] + "..."
                parts.append(value)
    
    return separator.join(parts) if parts else ""


def aggregate_results(all_results: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
    """聚合所有结果为节点和关系列表"""
    node_to_id = {}
    node_id = 1
    nodes_list = []
    relationships_list = []
    
    for idx, result in enumerate(all_results):
        if not result.get("success", False):
            continue
            
        stages = result.get("stages", {})
        kg_construction = stages.get("knowledge_graph_construction", {})
        
        # 获取实体类型映射
        entities = kg_construction.get("entities", [])
        entity_types = {}
        
        # entities 可能是字符串列表或字典列表
        for entity in entities:
            if isinstance(entity, dict):
                name = entity.get("name", entity.get("entity", ""))
                etype = entity.get("type", "Unknown")
                entity_types[name] = etype
            elif isinstance(entity, str):
                # 如果是字符串，暂时设为 Unknown 类型
                entity_types[entity] = "Unknown"
        
        # 处理三元组
        triples = kg_construction.get("triples", [])
        for triple in triples:
            if isinstance(triple, dict):
                head = triple.get("head", "")
                relation = triple.get("relation", "")
                tail = triple.get("tail", "")
                
                # 为节点分配ID
                for node_name in [head, tail]:
                    if node_name and node_name not in node_to_id:
                        node_to_id[node_name] = node_id
                        node_type = entity_types.get(node_name, "Unknown")
                        nodes_list.append({
                            "id": node_id,
                            "name": node_name,
                            "node_type": node_type
                        })
                        node_id += 1
                
                # 添加关系
                if head in node_to_id and tail in node_to_id:
                    relationships_list.append({
                        "start_id": node_to_id[head],
                        "end_id": node_to_id[tail],
                        "relation_type": relation,
                        "source": "extraction"
                    })
    
    return nodes_list, relationships_list


def write_csv_files(nodes_list: List[Dict], relationships_list: List[Dict], 
                   base_path: str):
    """写入 CSV 文件"""
    nodes_csv = f"{base_path}_nodes.csv"
    relationships_csv = f"{base_path}_relationships.csv"
    
    # 写入 nodes.csv
    with open(nodes_csv, 'w', encoding='utf-8') as f:
        f.write("id,name,node_type\n")
        for node in nodes_list:
            # 对包含逗号的字段进行引号包裹
            name = node['name'].replace('"', '""')  # 转义引号
            node_type = node['node_type'].replace('"', '""')
            if ',' in name or '"' in name:
                name = f'"{name}"'
            if ',' in node_type or '"' in node_type:
                node_type = f'"{node_type}"'
            f.write(f"{node['id']},{name},{node_type}\n")
    
    # 写入 relationships.csv
    with open(relationships_csv, 'w', encoding='utf-8') as f:
        f.write("start_id,end_id,relation_type,source\n")
        for rel in relationships_list:
            # 对包含逗号的字段进行引号包裹
            relation_type = rel['relation_type'].replace('"', '""')
            if ',' in relation_type or '"' in relation_type:
                relation_type = f'"{relation_type}"'
            f.write(f"{rel['start_id']},{rel['end_id']},{relation_type},{rel['source']}\n")
    
    print(f"\n✅ 已生成 CSV 文件:")
    print(f"  - {nodes_csv} ({len(nodes_list)} 个节点)")
    print(f"  - {relationships_csv} ({len(relationships_list)} 条关系)")


async def run_bulk(jsonl_path: str, out_base: str, 
                  field_config: List[str],
                  separator: str = "。",
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
                    text = extract_text_from_json(data, field_config, separator)
                    
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
    
    # 启动服务器并处理
    cmd = [server_cmd] + server_args
    server_params = StdioServerParameters(command=server_cmd, args=server_args)
    
    all_results = []
    
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
            
            # 并发处理，但限制并发数以避免过载
            batch_size = 10  # 每批处理10条
            for i in range(0, len(texts), batch_size):
                batch = texts[i:i+batch_size]
                batch_tasks = []
                
                for j, text in enumerate(batch):
                    idx = i + j + 1
                    print(f"  处理第 {idx}/{len(texts)} 条...", end='\r')
                    batch_tasks.append(process_single_line(session, text, idx))
                
                # 等待当前批次完成
                batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
                
                for result in batch_results:
                    if isinstance(result, Exception):
                        all_results.append({"success": False, "error": str(result)})
                    else:
                        all_results.append(result)
            
            print(f"\n✅ 处理完成")
    
    # 聚合并输出结果
    print("📊 聚合结果...")
    nodes_list, relationships_list = aggregate_results(all_results)
    
    if nodes_list or relationships_list:
        write_csv_files(nodes_list, relationships_list, out_base)
    else:
        print("⚠️  没有提取到任何三元组")
    
    # 统计信息
    successful = sum(1 for r in all_results if r.get("success", False))
    print(f"\n📈 处理统计:")
    print(f"  - 成功: {successful}/{len(texts)}")
    print(f"  - 失败: {len(texts) - successful}/{len(texts)}")


def main():
    parser = argparse.ArgumentParser(
        description="灵活批量处理 JSONL 文件生成知识图谱",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  # 处理政务数据
  python bulk_jsonl_to_csv_flexible.py data/政务.jsonl \\
    --fields "服务事项:服务事项" "权力类型:权力类型" "行驶主体:行驶主体" "承办机构:承办机构"
  
  # 处理新闻数据
  python bulk_jsonl_to_csv_flexible.py data/news.jsonl \\
    --fields "title:标题" "content:内容" "author:作者"
  
  # 只提取字段值，不带标签
  python bulk_jsonl_to_csv_flexible.py data/data.jsonl \\
    --fields title content --sep " "
        """
    )
    parser.add_argument("jsonl_file", help="输入的 JSONL 文件路径")
    parser.add_argument("-o", "--output", help="输出文件基础名（默认与输入文件同名）")
    parser.add_argument("--fields", nargs="+", 
                       help="要提取的字段，格式为 'field' 或 'field:label'",
                       default=["服务事项:服务事项", "权力类型:权力类型", 
                               "行驶主体:行驶主体", "承办机构:承办机构"])
    parser.add_argument("--sep", "--separator", dest="separator",
                       help="字段之间的分隔符（默认：。）", default="。")
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
        args.fields,
        args.separator,
        args.server_cmd,
        args.server_args
    ))


if __name__ == "__main__":
    main()
