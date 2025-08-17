#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
知识图谱构建 MCP 服务器
提供全自动化的知识图谱构建服务
"""

import asyncio
import json
import time
import sys
import os
from typing import Any, Sequence
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()


# 设置控制台编码
if sys.platform == "win32":
    os.system("chcp 65001 > nul")
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import (
    Resource,
    Tool,
    TextContent,
    ImageContent,
    EmbeddedResource,
    LoggingLevel
)

from data_quality import DataQualityAssessor
from knowledge_completion import KnowledgeCompletor
from kg_utils import KnowledgeGraphBuilder
from kg_visualizer import KnowledgeGraphVisualizer
from evaluate_kg.evaluate import KnowledgeGraphEvaluator  # 新质量评估
# 移除了simple_file_server依赖，直接生成文件路径

# 全局组件
quality_assessor = DataQualityAssessor()
knowledge_completor = KnowledgeCompletor()
kg_builder = KnowledgeGraphBuilder(api_key=os.getenv("OPENAI_API_KEY"))
kg_visualizer = KnowledgeGraphVisualizer()

# 创建服务器实例
server = Server("knowledge-graph-builder")


@server.list_tools()
async def handle_list_tools() -> list[Tool]:
    """
    列出可用的工具
    """
    return [
        Tool(
            name="build_knowledge_graph",
            description="全自动构建知识图谱：自动评估数据质量、补全知识、构建图谱并生成可视化",
            inputSchema={
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "要处理的文本数据"
                    },
                    "output_file": {
                        "type": "string",
                        "description": "可视化输出文件名（可选）",
                        "default": "knowledge_graph.html"
                    }
                },
                "required": ["text"]
            }
        )
    ]


@server.call_tool()
async def handle_call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """
    处理工具调用
    """
    if name == "build_knowledge_graph":
        return await build_knowledge_graph_tool(arguments)
    else:
        raise ValueError(f"未知工具: {name}")


async def build_knowledge_graph_tool(arguments: dict[str, Any]) -> list[TextContent]:
    """
    全自动知识图谱构建工具（输出 Neo4j 三元组文件，而非可视化 HTML）
    """
    try:
        text = arguments.get("text", "")
        output_file = arguments.get("output_file", "knowledge_graph.cypher")

        if not text.strip():
            return [TextContent(
                type="text",
                text=json.dumps({
                    "success": False,
                    "error": "输入文本不能为空"
                }, ensure_ascii=False, indent=2)
            )]

        start_time = time.time()

        # 阶段：知识图谱构建（先构建后评估）
        kg_result = await kg_builder.build_graph(text, use_llm=True)

        if not kg_result["entities"] and not kg_result["triples"]:
            return [TextContent(
                type="text",
                text=json.dumps({
                    "success": False,
                    "error": "无法从输入文本中提取到有效的实体或关系",
                    "suggestion": "请尝试输入包含明确实体和关系的文本，例如：'张三担任阿里巴巴公司的CEO'"
                }, ensure_ascii=False, indent=2)
            )]

        # 检查是否需要生成文件
        generate_files = output_file.lower() != "off"
        
        # 导出为分离的 CSV 格式（nodes.csv 和 relationships.csv）
        if generate_files:
            base = os.path.splitext(output_file)[0]
            nodes_csv_path = f"{base}_nodes.csv"
            relationships_csv_path = f"{base}_relationships.csv"
        else:
            nodes_csv_path = ""
            relationships_csv_path = ""
            cypher_path = ""
        
        # 收集所有节点并分配 ID
        node_to_id = {}
        node_id = 1
        nodes_data = []
        
        # 从三元组中收集节点
        for t in kg_result["triples"]:
            for node_name in [t.head, t.tail]:
                if node_name and node_name not in node_to_id:
                    node_to_id[node_name] = node_id
                    # 从实体类型映射中获取类型，如果没有则标记为 Unknown
                    node_type = "Unknown"
                    # 检查 kg_builder 是否有 entity_types 属性
                    if hasattr(kg_builder, 'entity_types') and isinstance(kg_builder.entity_types, dict):
                        node_type = kg_builder.entity_types.get(node_name, "Unknown")
                    nodes_data.append([node_id, node_name, node_type])
                    node_id += 1
        
        # 只有在需要生成文件时才写入
        if generate_files:
            # 写入 nodes.csv
            with open(nodes_csv_path, 'w', encoding='utf-8') as nf:
                nf.write("id,name,node_type\n")
                for node_data in nodes_data:
                    nf.write(f"{node_data[0]},{node_data[1]},{node_data[2]}\n")
            
            # 写入 relationships.csv
            with open(relationships_csv_path, 'w', encoding='utf-8') as rf:
                rf.write("start_id,end_id,relation_type,source\n")
                for t in kg_result["triples"]:
                    if t.head in node_to_id and t.tail in node_to_id:
                        start_id = node_to_id[t.head]
                        end_id = node_to_id[t.tail]
                        relation_type = t.relation
                        source = "extraction"  # 标记来源为提取
                        rf.write(f"{start_id},{end_id},{relation_type},{source}\n")
        
        # 同时生成 Cypher 脚本（可选）
        def _generate_cypher(nodes_data, triples, node_to_id) -> str:
            stmts = []
            stmts.append("// 创建或匹配节点")
            for node_data in nodes_data:
                n_id, n_name, n_type = node_data
                n_name_e = str(n_name).replace("'", "\\'")
                n_type_e = str(n_type).replace("'", "\\'")
                stmts.append(f"MERGE (n{n_id}:`Entity` {{id: {n_id}, name: '{n_name_e}', node_type: '{n_type_e}'}});")
            stmts.append("\nCREATE INDEX IF NOT EXISTS FOR (n:Entity) ON (n.id);")
            stmts.append("CREATE INDEX IF NOT EXISTS FOR (n:Entity) ON (n.name);")
            stmts.append("\n// 创建或匹配关系")
            for t in triples:
                if t.head in node_to_id and t.tail in node_to_id:
                    start_id = node_to_id[t.head]
                    end_id = node_to_id[t.tail]
                    r = ''.join(c if str(c).isalnum() else '_' for c in str(t.relation)).upper() or 'RELATED_TO'
                    stmts.append(f"MATCH (h:`Entity` {{id: {start_id}}}) MATCH (t:`Entity` {{id: {end_id}}}) MERGE (h)-[:`{r}`]->(t);")
            return "\n".join(stmts)

        if generate_files:
            cypher_path = f"{base}.cypher"
            with open(cypher_path, 'w', encoding='utf-8') as cf:
                cf.write(_generate_cypher(nodes_data, kg_result["triples"], node_to_id))

        # 导出节点与关系为 CSV，供评估器使用
        import tempfile, csv
        eval_dir = tempfile.mkdtemp(prefix="kg_eval_")
        nodes_csv = os.path.join(eval_dir, "nodes.csv")
        rels_csv = os.path.join(eval_dir, "relationships.csv")

        # 写 nodes.csv: id,name,node_type
        with open(nodes_csv, 'w', newline='', encoding='utf-8') as nf:
            writer = csv.writer(nf)
            writer.writerow(["id", "name", "node_type"]) 
            entity_types = getattr(kg_builder, 'entity_types', {})
            for e in kg_result["entities"]:
                writer.writerow([e, e, entity_types.get(e, "Unknown")])

        # 写 relationships.csv: start_id,end_id,relation_type
        with open(rels_csv, 'w', newline='', encoding='utf-8') as rf:
            writer = csv.writer(rf)
            writer.writerow(["start_id", "end_id", "relation_type"]) 
            for t in kg_result["triples"]:
                writer.writerow([t.head, t.tail, t.relation])

        # 运行评估器
        eval_config = {
            "node_files": [nodes_csv],
            "relationship_files": [rels_csv],
            "zhipuai_api_key": "",   # 默认关闭远程语义评估
            "zhipuai_model": "glm-4",
            "output_dir": eval_dir,
            "semantic_eval_sample_size": 0.0,
            "logical_rules": {
                "不允许的节点类型": ["Unknown"],
                "无效关系类型": ["NONE"],
                "类型冲突规则": {}
            }
        }
        evaluator = KnowledgeGraphEvaluator(eval_config)
        eval_summary = evaluator.run_evaluation()

        processing_time = time.time() - start_time

        result = {
            "success": True,
            "input_text": text,
            "processing_time": round(processing_time, 3),
            "stages": {
                "quality_assessment": {
                    "scores": eval_summary["scores"],
                    "metrics": eval_summary["metrics"],
                    "report_dir": eval_dir
                },
                "knowledge_graph": {
                    "entities_count": len(kg_result["entities"]),
                    "relations_count": len(kg_result["relations"]),
                    "triples_count": len(kg_result["triples"]) 
                },
                "export": {
                    "nodes_csv": os.path.abspath(nodes_csv_path) if generate_files else "",
                    "relationships_csv": os.path.abspath(relationships_csv_path) if generate_files else "",
                    "cypher_file": os.path.abspath(cypher_path) if generate_files else ""
                }
            },
            "summary": {
                "final_entities": len(kg_result["entities"]),
                "final_triples": len(kg_result["triples"]),
                "quality_report": eval_dir
            },
            "data": {
                "entities": kg_result["entities"],
                "relations": list(kg_result["relations"]),
                "triples": [{"head": t.head, "relation": t.relation, "tail": t.tail} for t in kg_result["triples"]]
            }
        }

        return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]

    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        return [TextContent(
            type="text",
            text=json.dumps({
                "success": False,
                "error": str(e),
                "error_details": error_details
            }, ensure_ascii=False, indent=2)
        )]


async def main():
    """
    运行服务器
    """
    # 使用 stdio 传输运行服务器
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="knowledge-graph-builder",
                server_version="1.0.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={}
                ),
            ),
        )


if __name__ == "__main__":
    asyncio.run(main())
