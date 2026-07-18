"""
Content Enhancement Package - 知识图谱内容增强包

此包提供了完整的知识图谱增强功能：
1. 全局分析 - 分析整体结构和模式
2. 细节分析 - 分析单个实体和局部关系
3. 分析流程控制 - 协调各个分析模块
4. 增强执行 - 自动应用分析结果进行增强

使用方法：
    from content_enhancement import analyze_knowledge_graph, enhance_knowledge_graph

示例：
    # 分析知识图谱
    analysis_result = await analyze_knowledge_graph(text, entities, relations)
    
    # 自动增强知识图谱
    enhanced_result = await enhance_knowledge_graph(text, entities, relations, analysis_result)
"""

try:
    from .global_analysis import GlobalAnalyzer, AnalysisResult
except Exception:
    GlobalAnalyzer = None
    AnalysisResult = None

try:
    from .entity_detail_analyzer import EntityDetailAnalyzer, AttributeGap
except Exception:
    EntityDetailAnalyzer = None
    AttributeGap = None

try:
    from .analysis_pipeline import AnalysisPipeline, AnalysisConfig, AnalysisOutput, analyze_knowledge_graph
except Exception:
    AnalysisPipeline = None
    AnalysisConfig = None
    AnalysisOutput = None
    analyze_knowledge_graph = None

from .enhancement_executor import EnhancementExecutor, EnhancementResult

# 版本信息
__version__ = "2.0.0"
__author__ = "Knowledge Graph Enhancement Team"

# 导出的主要类和函数
__all__ = [
    # 分析相关
    'GlobalAnalyzer',
    'EntityDetailAnalyzer', 
    'AnalysisPipeline',
    'AnalysisConfig',
    'AnalysisOutput',
    'AnalysisResult',
    'AttributeGap',
    'analyze_knowledge_graph',
    
    # 增强相关
    'EnhancementExecutor',
    'EnhancementResult',
    'enhance_knowledge_graph'
]

# 便捷函数
async def enhance_knowledge_graph(text: str, 
                                entities: list, 
                                relations: list, 
                                analysis_result=None,
                                config=None):
    """
    便捷的知识图谱增强函数
    
    Args:
        text: 原始文本
        entities: 实体列表
        relations: 关系列表
        analysis_result: 分析结果 (如果为None，会自动分析)
        config: 配置参数
    
    Returns:
        增强结果
    """
    executor = EnhancementExecutor()
    
    # 如果没有分析结果，先进行分析
    if analysis_result is None:
        if analyze_knowledge_graph is None:
            raise RuntimeError("analysis_pipeline is unavailable; install optional analysis dependencies first")
        analysis_result = await analyze_knowledge_graph(text, entities, relations, config)
    
    # 执行增强
    return await executor.execute_enhancements(text, entities, relations, analysis_result)

# 模块级别的配置
DEFAULT_CONFIG = AnalysisConfig(
    enable_global_analysis=True,
    enable_detail_analysis=True,
    similarity_threshold=0.3,
    max_recommendations=20
) if AnalysisConfig is not None else None
