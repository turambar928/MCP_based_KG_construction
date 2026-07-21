#!/usr/bin/env python3
"""
增强执行器 - 自动应用分析结果，增强知识图谱
Enhancement Executor - Automatically apply analysis results to enhance knowledge graph
"""

import json
import re
from typing import Dict, List, Any, Tuple, Set, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
import logging
import asyncio
from .llm_client import LLMClient
from .constraint_optimizer import MultiScaleConstraintOptimizer

# 配置日志
logger = logging.getLogger(__name__)

@dataclass
class EnhancementResult:
    """增强结果数据结构"""
    original_entities: List[str]
    original_relations: List[str]
    enhanced_entities: List[Dict[str, Any]]
    enhanced_relations: List[Dict[str, Any]]
    enhanced_triples: List[Dict[str, Any]]
    enhancement_summary: Dict[str, Any]
    applied_enhancements: List[Dict[str, Any]]
    timestamp: str

class EnhancementExecutor:
    """增强执行器"""
    
    def __init__(self, llm_client: Optional[LLMClient] = None):
        self.llm_client = llm_client
        self.constraint_optimizer = MultiScaleConstraintOptimizer()
        # 移除硬编码的关键词和模板，这些现在由其他模块（或LLM）动态提供
        
    async def execute_enhancements(self, 
                                 original_text: str,
                                 entities: List[Dict[str, Any]], 
                                 relations: List[Dict[str, Any]],
                                 analysis_result: Any) -> EnhancementResult:
        """
        执行增强操作
        - 此版本接收结构化输入，并应用所有类型的建议
        """
        logger.info("开始执行增强操作...")
        
        # 直接使用传入的结构化数据进行操作
        enhanced_entities = [e.copy() for e in entities]
        enhanced_triples = [
            {"head": r['source'], "relation": r['name'], "tail": r['target'], "confidence": r.get('confidence', 0.8)}
            for r in relations
        ]
        
        applied_enhancements = []
        optimizer_diagnostics = {}
        
        if hasattr(analysis_result, 'integrated_recommendations'):
            recommendations = analysis_result.integrated_recommendations

            enhanced_triples, applied_enhancements, optimizer_diagnostics = (
                self.constraint_optimizer.optimize_and_apply(
                    enhanced_entities,
                    enhanced_triples,
                    recommendations,
                    original_text,
                )
            )
        
        # **关键修复**：从最终的三元组列表重建实体和关系
        final_entities, final_relations = self._rebuild_from_triples(enhanced_triples, enhanced_entities)

        enhancement_summary = self._generate_enhancement_summary(
            [e['name'] for e in entities], 
            [r['name'] for r in relations], 
            final_entities, 
            final_relations, 
            applied_enhancements,
            optimizer_diagnostics
        )
        
        result = EnhancementResult(
            original_entities=[e['name'] for e in entities],
            original_relations=[r['name'] for r in relations],
            enhanced_entities=final_entities,
            enhanced_relations=final_relations, # 返回结构化关系
            enhanced_triples=enhanced_triples,
            enhancement_summary=enhancement_summary,
            applied_enhancements=applied_enhancements,
            timestamp=datetime.now().isoformat()
        )
        
        logger.info(f"增强操作完成，应用了 {len(applied_enhancements)} 个增强建议。")
        return result

    def _rebuild_from_triples(self, triples: List[Dict], original_entities: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
        """从增强后的三元组列表重新构建实体和关系列表"""
        entity_map = {e['name']: e for e in original_entities}
        relation_set = set()

        for t in triples:
            for entity_name in [t['head'], t['tail']]:
                if entity_name not in entity_map:
                    entity_map[entity_name] = {'name': entity_name, 'type': 'unknown', 'enhanced': True}
            relation_set.add(t['relation'])

        final_entities = list(entity_map.values())
        final_relations = [{'name': r, 'type': 'inferred'} for r in sorted(list(relation_set))]
        return final_entities, final_relations

    async def _apply_recommendation(self, 
                                  recommendation: Dict[str, Any],
                                  enhanced_entities: List[Dict[str, Any]],
                                  enhanced_triples: List[Dict[str, Any]],
                                  original_text: str) -> Optional[Dict[str, Any]]:
        """应用单个建议"""
        category = recommendation.get('category')
        
        # --- 核心重构: 直接执行逻辑分析器的增强计划 ---
        if category == '逻辑推理':
            return self._apply_logic_enhancement_plan(recommendation, enhanced_triples)
        
        # (其他类型的建议可以在此添加处理分支)
        
        return None

    def _apply_logic_enhancement_plan(self,
                                    recommendation: Dict[str, Any],
                                    enhanced_triples: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        直接解析并应用来自 LogicAnalyzer 的增强计划（actions）。
        不再调用 LLM。
        """
        # 'implementation' 字段包含了原始的增强指令
        implementation_plan = recommendation.get('implementation', {})
        actions = implementation_plan.get('actions', [])
        
        if not actions:
            return None

        applied_count = 0
        
        for instruction in actions:
            action_type = instruction.get('action')
            triple_data = instruction.get('triple')
            
            if not action_type or not triple_data:
                continue

            # 确保三元组是标准格式
            target_triple = {
                "head": triple_data.get('head'),
                "relation": triple_data.get('relation'),
                "tail": triple_data.get('tail')
            }
            # 清理 None 值，以防万一
            target_triple = {k: v for k, v in target_triple.items() if v is not None}
            
            if len(target_triple) != 3:
                continue

            if action_type == 'add':
                # 为确保幂等性，只有当三元组不存在时才添加
                found = False
                for t in enhanced_triples:
                    if t['head'] == target_triple['head'] and t['relation'] == target_triple['relation'] and t['tail'] == target_triple['tail']:
                        found = True
                        break
                if not found:
                    enhanced_triples.append({**target_triple, 'confidence': recommendation.get('confidence', 0.95), 'enhanced': True, 'source': 'logic_analysis'})
                    applied_count += 1
            
            elif action_type == 'remove':
                # 从列表中移除所有匹配的三元组
                original_count = len(enhanced_triples)
                # 我们需要比较核心的 head, relation, tail，忽略 confidence 等
                enhanced_triples[:] = [t for t in enhanced_triples if not (
                    t['head'] == target_triple['head'] and 
                    t['relation'] == target_triple['relation'] and 
                    t['tail'] == target_triple['tail']
                )]
                if len(enhanced_triples) < original_count:
                    applied_count += (original_count - len(enhanced_triples))

        if applied_count > 0:
            logger.info(f"成功应用了 {applied_count} 个来自逻辑分析的增强操作。")
            return recommendation  # 返回被应用的建议，用于统计

        return None

    def _generate_enhancement_summary(self, 
                                    original_entities: List[str],
                                    original_relations: List[str],
                                    enhanced_entities: List[Dict[str, Any]],
                                    enhanced_relations: List[Dict[str, Any]],
                                    applied_enhancements: List[Dict[str, Any]],
                                    optimizer_diagnostics: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """生成增强摘要"""
        optimizer_diagnostics = optimizer_diagnostics or {}
        initial_profile = optimizer_diagnostics.get("initial_profile", {})
        final_profile = optimizer_diagnostics.get("final_profile", {})
        router = optimizer_diagnostics.get("router", {})
        return {
            'status': 'Completed',
            'original_entity_count': len(original_entities),
            'enhanced_entity_count': len(enhanced_entities),
            'original_relation_count': len(original_relations),
            'enhanced_relation_count': len(enhanced_relations),
            'applied_enhancements_count': len(applied_enhancements),
            'constraint_optimizer': {
                'enabled': True,
                'router_source': router.get('source'),
                'p_repair': router.get('p_repair'),
                'scale_prior': router.get('pi'),
                'initial_q_score': initial_profile.get('q_score'),
                'final_q_score': final_profile.get('q_score'),
                'initial_profile': {
                    k: initial_profile.get(k)
                    for k in ['S_iso', 'S_red', 'S_log', 'S_sem', 'n_v', 'n_e', 'density', 'n_viol_feat']
                },
                'final_profile': {
                    k: final_profile.get(k)
                    for k in ['S_iso', 'S_red', 'S_log', 'S_sem', 'n_v', 'n_e', 'density', 'n_viol_feat']
                },
                'candidate_decisions_count': len(optimizer_diagnostics.get('decisions', [])),
                'stopped_reason': optimizer_diagnostics.get('stopped_reason')
            }
        }

# 使用示例
async def main():
    """使用示例"""
    executor = EnhancementExecutor()
    
    # 示例数据
    sample_text = "张三是阿里巴巴的高级工程师，负责人工智能项目。他毕业于清华大学。"
    sample_entities = [{"name": "张三", "type": "Person"}, {"name": "阿里巴巴", "type": "Organization"}, {"name": "清华大学", "type": "Location"}]
    sample_relations = [{"source": "张三", "name": "工作于", "target": "阿里巴巴", "confidence": 0.9}, {"source": "张三", "name": "毕业于", "target": "清华大学", "confidence": 0.8}]
    
    # 模拟分析结果
    class MockAnalysisResult:
        def __init__(self):
            self.integrated_recommendations = [
                {
                    'type': 'similar_entity_relation',
                    'entities': ['张三', '阿里巴巴'],
                    'confidence': 0.8
                }
            ]
    
    analysis_result = MockAnalysisResult()
    
    # 执行增强
    result = await executor.execute_enhancements(
        sample_text, sample_entities, sample_relations, analysis_result
    )
    
    print("增强结果:")
    print(f"原始实体数: {len(result.original_entities)}")
    print(f"增强后实体数: {len(result.enhanced_entities)}")
    print(f"原始关系数: {len(result.original_relations)}")
    print(f"增强后关系数: {len(result.enhanced_relations)}")
    print(f"应用的增强数: {len(result.applied_enhancements)}")

if __name__ == "__main__":
    asyncio.run(main()) 
