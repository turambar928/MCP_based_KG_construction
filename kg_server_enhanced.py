#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
知识图谱构建 MCP 服务器 - 增强版
提供全自动化的知识图谱构建服务 + 高级分析功能
"""

import asyncio
import json
import time
import sys
import os
from typing import Any, Sequence, Dict
from dotenv import load_dotenv
from dataclasses import asdict

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
from dataclasses import asdict # 确保 asdict 被导入

# 原有模块
from data_quality import DataQualityAssessor
from knowledge_completion import KnowledgeCompletor
from kg_utils import KnowledgeGraphBuilder
from kg_visualizer import KnowledgeGraphVisualizer

# 新增分析模块
try:
    from content_enhancement.analysis_pipeline import analyze_knowledge_graph, AnalysisConfig
    from content_enhancement.enhancement_executor import EnhancementExecutor
    from kg_utils import Triple # 确保 Triple 被导入
    ANALYSIS_AVAILABLE = True
    print("分析模块加载成功")
except ImportError as e:
    ANALYSIS_AVAILABLE = False
    print(f"分析模块加载失败: {e}")
    print("高级分析功能将不可用")
except Exception as e:
    ANALYSIS_AVAILABLE = False
    print(f"分析模块初始化错误: {e}")
    print("高级分析功能将不可用")

# 全局组件
try:
    quality_assessor = DataQualityAssessor()
    knowledge_completor = KnowledgeCompletor()
    kg_builder = KnowledgeGraphBuilder(api_key=os.getenv("OPENAI_API_KEY"))
    kg_visualizer = KnowledgeGraphVisualizer()
    if ANALYSIS_AVAILABLE:
        enhancement_executor = EnhancementExecutor()
    print("核心组件初始化成功")
except Exception as e:
    print(f"核心组件初始化失败: {e}")
    raise

# 创建服务器实例
server = Server("knowledge-graph-builder-enhanced")


@server.list_tools()
async def handle_list_tools() -> list[Tool]:
    """
    列出可用的工具
    """
    # 直接构建知识图谱不进行增强，用于对比实验
    tools = [
        Tool(
            name="build_knowledge_graph",
            description="构建知识图谱：直接从文本提取实体与关系并生成可视化（不进行内容增强）",
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
    
    # 如果分析模块可用，添加高级分析工具，对文本进行分析，提供高质量评估和改进建议
    if ANALYSIS_AVAILABLE:
        tools.append(
            Tool(
                name="analyze_knowledge_graph",
                description="高级知识图谱分析：全局分析+细节分析，提供质量评估和改进建议",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "text": {
                            "type": "string",
                            "description": "要分析的文本数据"
                        },
                        "enable_global_analysis": {
                            "type": "boolean",
                            "description": "启用全局分析",
                            "default": True
                        },
                        "enable_detail_analysis": {
                            "type": "boolean",
                            "description": "启用细节分析",
                            "default": True
                        },
                        "similarity_threshold": {
                            "type": "number",
                            "description": "相似度阈值",
                            "default": 0.3
                        },
                        "max_recommendations": {
                            "type": "integer",
                            "description": "最大建议数量",
                            "default": 15
                        }
                    },
                    "required": ["text"]
                }
            )
        )
        
        tools.append(
            Tool(
                name="build_and_analyze_kg",
                description="构建知识图谱并进行高级分析：结合构建和分析功能的一体化工具，支持自动增强",
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
                            "default": "enhanced_knowledge_graph.html"
                        },
                        "enable_analysis": {
                            "type": "boolean",
                            "description": "启用高级分析",
                            "default": True
                        },
                        "auto_enhance": {
                            "type": "boolean",
                            "description": "是否自动增强知识图谱",
                            "default": False
                        }
                    },
                    "required": ["text"]
                }
            )
        )
        
        tools.append(
            Tool(
                name="process_text_file_to_cypher",
                description="批量处理文本文件，提取三元组并生成 Neo4j Cypher 脚本",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "input_file": {
                            "type": "string",
                            "description": "包含待处理文本的输入文件路径（.txt）"
                        },
                        "output_file": {
                            "type": "string",
                            "description": "Cypher脚本的输出文件名（可选）",
                            "default": "neo4j_import.cypher"
                        }
                    },
                    "required": ["input_file"]
                }
            )
        )
    
    return tools


@server.call_tool()
async def handle_call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """
    处理工具调用
    """
    if name == "build_knowledge_graph":
        return await build_knowledge_graph_tool(arguments)
    elif name == "analyze_knowledge_graph" and ANALYSIS_AVAILABLE:
        return await analyze_knowledge_graph_tool(arguments)
    elif name == "build_and_analyze_kg" and ANALYSIS_AVAILABLE:
        return await build_and_analyze_kg_tool(arguments)
    elif name == "process_text_file_to_cypher" and ANALYSIS_AVAILABLE:
        return await process_text_file_to_cypher_tool(arguments)
    else:
        raise ValueError(f"未知工具: {name}")


async def build_knowledge_graph_tool(arguments: dict[str, Any]) -> list[TextContent]:
    """
    构建知识图谱（不进行质量评估、知识补全或其他内容增强）
    """
    try:
        text = arguments.get("text", "")
        output_file = arguments.get("output_file", "knowledge_graph.html")

        if not text.strip():
            return [TextContent(
                type="text",
                text=json.dumps({
                    "success": False,
                    "error": "输入文本不能为空"
                }, ensure_ascii=False, indent=2)
            )]

        start_time = time.time()

        # 直接构建知识图谱
        kg_result = await kg_builder.build_graph(text, use_llm=True)

        # 检查是否成功提取到实体和三元组
        if not kg_result["entities"] and not kg_result["triples"]:
            return [TextContent(
                type="text",
                text=json.dumps({
                    "success": False,
                    "error": "无法从输入文本中提取到有效的实体或关系",
                    "suggestion": "请尝试输入包含明确实体和关系的文本"
                }, ensure_ascii=False, indent=2)
            )]

        # 生成可视化
        visualization_file = kg_visualizer.save_simple_visualization(
            kg_result["triples"],
            kg_result["entities"],
            kg_result["relations"],
            output_file
        )

        abs_path = os.path.abspath(visualization_file)
        visualization_url = f"file:///{abs_path.replace(os.sep, '/')}"
        http_url = f"http://localhost:8000/{visualization_file}"
        server_info = f"可手动启动HTTP服务器访问：在项目目录运行 'python -m http.server 8000'，然后访问 {http_url}"

        processing_time = time.time() - start_time

        # 构建结果
        result = {
            "success": True,
            "input_text": text,
            "processing_time": round(processing_time, 3),
            "knowledge_graph": {
                "entities_count": len(kg_result["entities"]),
                "relations_count": len(kg_result["relations"]),
                "triples_count": len(kg_result["triples"]),
                "entities": kg_result["entities"],
                "relations": kg_result["relations"]
            },
            "visualization": {
                "file_path": visualization_file,
                "file_url": visualization_url,
                "http_url": http_url,
                "server_info": server_info
            }
        }

        return [TextContent(
            type="text",
            text=json.dumps(result, ensure_ascii=False, indent=2)
        )]

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


def _generate_cypher_script(triples: Sequence[Dict[str, Any]]) -> str:
    """将三元组字典列表转换为 Neo4j Cypher MERGE 语句"""
    if not triples:
        return "# 无可导入的三元组。\n"

    nodes = set()
    for t in triples:
        nodes.add(t['head'])
        nodes.add(t['tail'])

    cypher_statements = []

    # MERGE nodes
    cypher_statements.append("// --- 1. 创建或匹配节点 ---")
    for node in sorted(list(nodes)):
        # 正确处理带引号的节点名称
        node_escaped = node.replace("'", "\\'")
        cypher_statements.append(f"MERGE (:`Entity` {{name: '{node_escaped}'}});")

    # 创建索引以加速合并
    cypher_statements.append("\n// --- 2. 创建索引以加速 ---")
    cypher_statements.append("CREATE INDEX IF NOT EXISTS FOR (n:Entity) ON (n.name);")
    
    # MERGE relationships
    cypher_statements.append("\n// --- 3. 创建或匹配关系 ---")
    for t in triples:
        head = t['head'].replace("'", "\\'")
        tail = t['tail'].replace("'", "\\'")
        # 将关系中的非字母数字字符替换为下划线，以符合Cypher标准
        relation_type = ''.join(c if c.isalnum() else '_' for c in t['relation']).upper()
        if not relation_type:  # 避免空关系类型
            relation_type = "RELATED_TO"
        
        cypher_statements.append(
            f"MATCH (h:`Entity` {{name: '{head}'}}), (t:`Entity` {{name: '{tail}'}}) "
            f"MERGE (h)-[:`{relation_type}`]->(t);"
        )

    return "\n".join(cypher_statements)


async def process_text_file_to_cypher_tool(arguments: dict[str, Any]) -> list[TextContent]:
    """
    批量处理文本文件并生成 Cypher 脚本的工具
    """
    try:
        input_file = arguments.get("input_file")
        output_file = arguments.get("output_file", "neo4j_import.cypher")

        if not input_file or not os.path.exists(input_file):
            return [TextContent(text=json.dumps({"success": False, "error": f"输入文件不存在: {input_file}"}, ensure_ascii=False))]

        with open(input_file, 'r', encoding='utf-8') as f:
            lines = [line.strip().split('\t', 1)[-1] for line in f if line.strip()]

        if not lines:
            return [TextContent(text=json.dumps({"success": False, "error": "输入文件为空或格式不正确"}, ensure_ascii=False))]

        start_time = time.time()
        
        # 并发处理每一行
        tasks = [build_and_analyze_kg_tool({"text": line, "auto_enhance": True, "output_file": "off"}) for line in lines]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_triples = []
        processed_lines = 0
        failed_lines = 0

        for res in results:
            if isinstance(res, Exception) or not res:
                failed_lines += 1
                continue
            
            try:
                data = json.loads(res[0].text)
                if data.get("success"):
                    processed_lines += 1
                    # 从 summary 中提取 final_triples
                    summary = data.get("summary", {})
                    triples_from_summary = summary.get("final_triples", [])
                    if triples_from_summary:
                        all_triples.extend(triples_from_summary)
                else:
                    failed_lines += 1
            except (json.JSONDecodeError, IndexError):
                failed_lines += 1

        # 使用去重确保三元组唯一性
        unique_triples = [dict(t) for t in {tuple(d.items()) for d in all_triples}]

        cypher_script = _generate_cypher_script(unique_triples)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(cypher_script)

        processing_time = time.time() - start_time

        result_summary = {
            "success": True,
            "processing_time": round(processing_time, 3),
            "total_lines": len(lines),
            "processed_lines": processed_lines,
            "failed_lines": failed_lines,
            "total_triples_generated": len(unique_triples),
            "cypher_script_file": os.path.abspath(output_file)
        }
        
        return [TextContent(text=json.dumps(result_summary, ensure_ascii=False, indent=2))]

    except Exception as e:
        import traceback
        return [TextContent(text=json.dumps({
            "success": False, 
            "error": str(e),
            "error_details": traceback.format_exc()
        }, ensure_ascii=False, indent=2))]


async def analyze_knowledge_graph_tool(arguments: dict[str, Any]) -> list[TextContent]:
    """
    新增的知识图谱高级分析工具
    """
    try:
        text = arguments.get("text", "")
        enable_global = arguments.get("enable_global_analysis", True)
        enable_detail = arguments.get("enable_detail_analysis", True)
        similarity_threshold = arguments.get("similarity_threshold", 0.3)
        max_recommendations = arguments.get("max_recommendations", 15)

        if not text.strip():
            return [TextContent(
                type="text",
                text=json.dumps({
                    "success": False,
                    "error": "输入文本不能为空"
                }, ensure_ascii=False, indent=2)
            )]

        start_time = time.time()

        # 首先构建基础知识图谱
        kg_result = await kg_builder.build_graph(text, use_llm=True)

        if not kg_result["entities"] and not kg_result["triples"]:
            return [TextContent(
                type="text",
                text=json.dumps({
                    "success": False,
                    "error": "无法从输入文本中提取到有效的实体或关系"
                }, ensure_ascii=False, indent=2)
            )]

        # 转换数据格式用于分析
        entities = [
            {
                'name': entity,
                'type': 'unknown',  # 可以根据需要改进类型推断
                'attributes': {},
                'relations': []
            }
            for entity in kg_result["entities"]
        ]

        relations = [
            {
                'name': triple.relation,
                'source': triple.head,
                'target': triple.tail,
                'type': 'unknown'
            }
            for triple in kg_result["triples"]
        ]

        # 配置分析参数
        config = AnalysisConfig(
            enable_global_analysis=enable_global,
            enable_detail_analysis=enable_detail,
            similarity_threshold=similarity_threshold,
            max_recommendations=max_recommendations
        )

        # 执行高级分析
        analysis_result = await analyze_knowledge_graph(
            text, entities, relations, config
        )

        processing_time = time.time() - start_time

        # 构建结果
        result = {
            "success": True,
            "input_text": text,
            "processing_time": round(processing_time, 3),
            "knowledge_graph": {
                "entities_count": len(kg_result["entities"]),
                "relations_count": len(kg_result["relations"]),
                "triples_count": len(kg_result["triples"]),
                "entities": kg_result["entities"],
                "relations": kg_result["relations"]
            },
            "analysis_results": {
                "llm_status": analysis_result.llm_status,
                "timestamp": analysis_result.timestamp,
                "quality_score": analysis_result.quality_metrics.get('overall_score', 0),
                "total_issues": analysis_result.quality_metrics.get('issue_count', 0),
                "critical_issues": analysis_result.quality_metrics.get('critical_issues', 0),
                "recommendations_count": len(analysis_result.integrated_recommendations),
                "top_recommendations": analysis_result.integrated_recommendations[:5]
            },
            "detailed_analysis": {
                "global_analysis": analysis_result.global_analysis_results is not None,
                "detail_analysis": analysis_result.detail_analysis_results is not None,
                "all_recommendations": analysis_result.integrated_recommendations
            }
        }

        return [TextContent(
            type="text",
            text=json.dumps(result, ensure_ascii=False, indent=2)
        )]

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


async def build_and_analyze_kg_tool(arguments: dict[str, Any]) -> list[TextContent]:
    """
    一体化工具：构建知识图谱、分析、自动增强并生成可视化
    """
    try:
        text = arguments.get("text", "")
        output_file = arguments.get("output_file", "enhanced_knowledge_graph.html")
        enable_analysis = arguments.get("enable_analysis", True)
        auto_enhance = arguments.get("auto_enhance", True)

        if not text.strip():
            return [TextContent(
                type="text",
                text=json.dumps({
                    "success": False,
                    "error": "输入文本不能为空"
                }, ensure_ascii=False, indent=2)
            )]

        start_time = time.time()

        # 阶段1：数据质量评估
        quality_result = await quality_assessor.assess_quality(text)

        # 阶段2：知识补全（如果需要）
        processed_text = text
        completion_info = {"skipped": True, "reason": "数据质量良好"}

        if not quality_result["is_high_quality"]:
            completion_result = await knowledge_completor.complete_knowledge(text, quality_result)
            processed_text = completion_result["enhanced_data"]
            completion_info = {
                "skipped": False,
                "completions": completion_result["completions"],
                "corrections": completion_result["corrections"],
                "confidence": completion_result["confidence"]
            }

        # 阶段3：知识图谱构建
        kg_result = await kg_builder.build_graph(processed_text, use_llm=True)

        if not kg_result["entities"] and not kg_result["triples"]:
            return [TextContent(
                type="text",
                text=json.dumps({
                    "success": False,
                    "error": "无法从输入文本中提取到有效的实体或关系"
                }, ensure_ascii=False, indent=2)
            )]

        # 阶段4：高级分析（如果启用）
        analysis_result = None
        if enable_analysis:
            # 转换数据格式用于分析
            entities = [
                {
                    'name': entity,
                    'type': 'unknown',
                    'attributes': {},
                    'relations': []
                }
                for entity in kg_result["entities"]
            ]

            relations = [
                {
                    'name': triple.relation,
                    'source': triple.head,
                    'target': triple.tail,
                    'type': 'unknown'
                }
                for triple in kg_result["triples"]
            ]

            # 配置分析参数
            config = AnalysisConfig(
                enable_global_analysis=True,
                enable_detail_analysis=True,
                similarity_threshold=0.3,
                max_recommendations=10
            )

            # 执行高级分析
            analysis_result = await analyze_knowledge_graph(
                processed_text, entities, relations, config
            )

        # 阶段5：自动增强（如果启用）
        enhancement_result = None
        final_entities = kg_result["entities"]
        final_relations = kg_result["relations"]
        final_triples = kg_result["triples"]

        if auto_enhance and analysis_result:
            # 确保传递的是结构化的实体和关系列表
            enhancement_result = await enhancement_executor.execute_enhancements(
                processed_text, entities, relations, analysis_result
            )

            # 使用增强后的数据
            final_entities = [e['name'] for e in enhancement_result.enhanced_entities]
            final_relations = [r['name'] for r in enhancement_result.enhanced_relations]

            # 重新计算摘要以获得准确的“原始”与“增强”对比
            enhancement_summary = {
                'status': 'Completed',
                'original_entity_count': len(kg_result["entities"]),
                'enhanced_entity_count': len(final_entities),
                'original_relation_count': len(kg_result["triples"]),
                'enhanced_relation_count': len(enhancement_result.enhanced_triples),
                'applied_enhancements_count': len(enhancement_result.applied_enhancements)
            }
            enhancement_result.enhancement_summary = enhancement_summary


            # 构建增强后的三元组用于可视化
            enhanced_triples = []
            # Triple 对象是 kg_utils 中定义的，需要从 enhanced_triples (dict) 转换
            from kg_utils import Triple
            for triple_dict in enhancement_result.enhanced_triples:
                enhanced_triple = Triple(
                    head=triple_dict['head'],
                    relation=triple_dict['relation'],
                    tail=triple_dict['tail'],
                    confidence=triple_dict.get('confidence', 0.8)
                )
                enhanced_triples.append(enhanced_triple)

            final_triples = enhanced_triples

        # 阶段6：生成可视化
        if output_file != "off":
            visualization_file = kg_visualizer.save_simple_visualization(
                final_triples,
                final_entities,
                final_relations,
                output_file
            )
            abs_path = os.path.abspath(visualization_file)
            visualization_url = f"file:///{abs_path.replace(os.sep, '/')}"
            http_url = f"http://localhost:8000/{visualization_file}"
            viz_info = {
                "file_path": visualization_file,
                "file_url": visualization_url,
                "http_url": http_url,
                "server_info": f"可手动启动HTTP服务器访问：在项目目录运行 'python -m http.server 8000'，然后访问 {http_url}"
            }
        
        
        else:
            visualization_file = "off"
            visualization_url = "off"
            viz_info = {"status": "Visualization disabled"}

        # --- 新增：保存三元组列表到文件 ---
        triples_file = output_file.rsplit('.', 1)[0] + "_triples.txt"
        try:
            with open(triples_file, 'w', encoding='utf-8') as tf:
                for t in final_triples:
                    # t 可能是 Triple 对象或 dict
                    if isinstance(t, dict):
                        h, r, tail = t.get('head'), t.get('relation'), t.get('tail')
                    else:
                        h, r, tail = t.head, t.relation, t.tail
                    tf.write(f"{h}\t{r}\t{tail}\n")
        except Exception as fe:
            print(f"⚠️ 无法写入三元组文件: {fe}")
        
        abs_triples_path = os.path.abspath(triples_file)

        processing_time = time.time() - start_time

        # 构建结果
        result = {
            "success": True,
            "input_text": text,
            "processing_time": round(processing_time, 3),
            "stages": {
                "quality_assessment": {
                    "quality_score": quality_result["quality_score"],
                    "is_high_quality": quality_result["is_high_quality"],
                    "completeness": quality_result["completeness"],
                    "consistency": quality_result["consistency"],
                    "relevance": quality_result["relevance"],
                    "issues": quality_result["issues"],
                    "recommendation": quality_result["recommendation"]
                },
                "knowledge_completion": completion_info,
                "original_knowledge_graph": {
                    "entities_count": len(kg_result["entities"]),
                    "relations_count": len(kg_result["relations"]),
                    "triples_count": len(kg_result["triples"]),
                    "entities": kg_result["entities"],
                    "relations": kg_result["relations"],
                    "average_confidence": sum(kg_result["confidence_scores"]) / len(kg_result["confidence_scores"]) if kg_result["confidence_scores"] else 0
                },
                "analysis_results": {
                    "analysis_enabled": enable_analysis,
                    "llm_status": analysis_result.llm_status if analysis_result else "NOT_APPLICABLE",
                    "analysis_performed": analysis_result is not None,
                    "timestamp": analysis_result.timestamp if analysis_result else None,
                    "quality_score": analysis_result.quality_metrics.get('overall_score', 0) if analysis_result else None,
                    "total_issues": analysis_result.quality_metrics.get('issue_count', 0) if analysis_result else 0,
                    "critical_issues": analysis_result.quality_metrics.get('critical_issues', 0) if analysis_result else 0,
                    "recommendations_count": len(analysis_result.integrated_recommendations) if analysis_result else 0,
                    "top_recommendations": analysis_result.integrated_recommendations[:5] if analysis_result else []
                },
                "enhancement_results": {
                    "auto_enhance_enabled": auto_enhance,
                    "enhancement_applied": enhancement_result is not None,
                    "enhancement_summary": enhancement_result.enhancement_summary if enhancement_result else None,
                    "applied_enhancements": enhancement_result.applied_enhancements if enhancement_result else [],
                    "final_entities_count": len(final_entities),
                    "final_relations_count": len(final_relations),
                    "final_triples_count": len(final_triples)
                },
                "visualization": viz_info | {"triples_file": abs_triples_path}
            },
            "summary": {
                "original_text": text,
                "processed_text": processed_text,
                "quality_improved": not quality_result["is_high_quality"],
                "analysis_performed": analysis_result is not None,
                "enhancement_applied": enhancement_result is not None,
                "final_entities": len(final_entities),
                "final_relations": len(final_relations),
                "final_triples": [asdict(t) for t in final_triples],
                "visualization_ready": visualization_file != "off",
                "visualization_file": visualization_file,
                "triples_file": abs_triples_path
            }
        }

        return [TextContent(
            type="text",
            text=json.dumps(result, ensure_ascii=False, indent=2)
        )]

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
    print("🚀 启动知识图谱构建服务器（增强版）")
    print(f"🔧 高级分析功能: {'✅ 可用' if ANALYSIS_AVAILABLE else '❌ 不可用'}")
    
    try:
        # 确保所有组件都正常初始化
        print("🔧 验证组件状态...")
        if not hasattr(quality_assessor, 'assess_quality'):
            raise RuntimeError("质量评估器未正确初始化")
        if not hasattr(kg_builder, 'build_graph'):
            raise RuntimeError("知识图谱构建器未正确初始化")
        print("✅ 所有组件验证通过")
        
        # 使用 stdio 传输运行服务器
        print("🔗 启动MCP服务器...")
        
        # 创建初始化选项
        init_options = InitializationOptions(
            server_name="knowledge-graph-builder-enhanced",
            server_version="2.0.0",
            capabilities=server.get_capabilities(
                notification_options=NotificationOptions(),
                experimental_capabilities={}
            ),
            timeoutSeconds=300  # 将默认超时从60秒延长到300秒
        )
        
        async with stdio_server() as (read_stream, write_stream):
            # 确保服务器完全初始化
            await asyncio.sleep(3)  # 延长延迟，避免前端过早发送请求
            
            print("✅ 开始运行服务器...")
            await server.run(
                read_stream,
                write_stream,
                init_options,
            )
            
    except KeyboardInterrupt:
        print("\n🛑 服务器收到中断信号，正在关闭...")
    except Exception as e:
        print(f"❌ 服务器启动失败: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        print("🔚 服务器已关闭")


if __name__ == "__main__":
    asyncio.run(main()) 