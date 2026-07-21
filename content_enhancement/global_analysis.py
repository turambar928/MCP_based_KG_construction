"""
全局分析模块 - 知识图谱质量增强
Global Analysis Module for Knowledge Graph Quality Enhancement

此模块包含4个子模块：
1. 实体中动词/谓语潜在缺失检测 → 流程性关系/事件逻辑关系
2. 实体关键词频率统计分析 → 相似内容/实体关系性
3. 事情逻辑/因果关系分析 → 实体间层次关系
4. 节点直接逻辑关系分析 → 类别关系
"""
from networkx.classes import selfloop_edges

'''
 todo:现在已经可以实现低质量文本RAG后构建知识图谱，但是需要对应的高质量数据，使用高质量数据构建对应的知识图谱后对比前后知识图谱的相似性
'''
#todo: 需要进行相似性对比的：不使用内容增强的低质量文本直接构建的知识图谱、高质量文本直接构建的知识图谱、低质量文本进行内容增强后构建的知识图谱











import json
import re
import numpy as np
from collections import Counter, defaultdict
from typing import Dict, List, Tuple, Set, Any, Optional
from dataclasses import dataclass
import networkx as nx
from scipy.spatial.distance import cosine
try:
    import jieba
    import jieba.posseg as pseg
except Exception:
    class _FallbackJieba:
        @staticmethod
        def cut(text):
            tokens = re.findall(r"[\u4e00-\u9fa5]{1,4}|[A-Za-z0-9_]+", str(text))
            return tokens or [str(text)] if text else []

    class _FallbackPosSeg:
        VERB_HINTS = {
            "进行", "执行", "实现", "完成", "处理", "分析", "计算", "生成",
            "创建", "建立", "构建", "开发", "设计", "导致", "引起", "影响",
            "管理", "监管", "属于", "位于", "包含", "负责",
        }

        @classmethod
        def cut(cls, text):
            for token in _FallbackJieba.cut(text):
                flag = "v" if any(v in token for v in cls.VERB_HINTS) else "n"
                yield token, flag

    jieba = _FallbackJieba()
    pseg = _FallbackPosSeg()

# 引入 LLMClient
try:
    from .llm_client import LLMClient
except ImportError:
    LLMClient = None  # type: ignore


@dataclass
class Entity:
    """实体数据结构"""
    name: str
    type: str
    attributes: Dict[str, Any]
    relations: List[str]
    
    
@dataclass
class Relation:
    """关系数据结构"""
    name: str
    source: str
    target: str
    type: str
    attributes: Dict[str, Any]


@dataclass
class AnalysisResult:
    """分析结果数据结构"""
    module_name: str
    findings: List[Dict[str, Any]]
    recommendations: List[Dict[str, Any]]
    confidence_score: float


class GlobalAnalyzer:
    """全局分析器主类"""

    def __init__(self, llm_client: Optional["LLMClient"] = None):
        self.entities: Dict[str, Entity] = {}
        self.relations: Dict[str, Relation] = {}
        self.graph = nx.DiGraph()

        self.llm_client = llm_client

        # 动态加载关键词，失败时回退默认
        default_verbs = self._default_verb_keywords()
        default_causals = self._default_causal_keywords()

        if self.llm_client is not None:
            verbs = self.llm_client.get_keywords("verb") or default_verbs
            causals = self.llm_client.get_keywords("causal") or default_causals
        else:
            verbs = default_verbs
            causals = default_causals

        self.verb_keywords: Set[str] = set(verbs)
        self.causal_keywords: Set[str] = set(causals)


        
    # ---------------- 默认关键词（回退用） ----------------

    @staticmethod
    def _default_verb_keywords() -> Set[str]:
        return {
            '进行', '执行', '实现', '完成', '处理', '分析', '计算', '生成',
            '创建', '建立', '构建', '开发', '设计', '制作', '产生', '形成',
            '发生', '出现', '存在', '包含', '具有', '拥有', '展示', '显示',
            '导致', '引起', '造成', '促使', '推动', '影响', '改变', '转换'
        }

    @staticmethod
    def _default_causal_keywords() -> Set[str]:
        return {
            '因为', '由于', '因此', '所以', '导致', '引起', '造成', '促使',
            '结果', '原因', '后果', '影响', '作用', '效果', '产生', '形成',
            '如果', '当', '在', '时候', '条件下', '情况下', '基础上', '前提下'
        }
        
    def load_knowledge_graph(self, kg_data: Dict[str, Any]) -> None:
        """加载知识图谱数据"""
        # 加载实体
        for entity_data in kg_data.get('entities', []):
            entity = Entity(
                name=entity_data['name'],
                type=entity_data.get('type', 'unknown'),
                attributes=entity_data.get('attributes', {}),
                relations=entity_data.get('relations', [])
            )
            self.entities[entity.name] = entity
            self.graph.add_node(entity.name, **entity.attributes)
        
        # 加载关系
        for relation_data in kg_data.get('relations', []):
            relation = Relation(
                name=relation_data['name'],
                source=relation_data['source'],
                target=relation_data['target'],
                type=relation_data.get('type', 'unknown'),
                attributes=relation_data.get('attributes', {})
            )
            self.relations[f"{relation.source}->{relation.target}"] = relation
            self.graph.add_edge(relation.source, relation.target, 
                              relation=relation.name, **relation.attributes)
    
    def analyze_all_modules(self) -> Dict[str, AnalysisResult]:
        """执行所有全局分析模块"""
        results = {}
        
        # 模块1: 实体中动词/谓语潜在缺失分析
        verb_analyzer = VerbPredicateAnalyzer(self)
        results['verb_predicate_analysis'] = verb_analyzer.analyze_missing_verbs()
        
        # 模块2: 实体关键词频率统计分析
        keyword_analyzer = KeywordFrequencyAnalyzer(self)
        results['keyword_frequency_analysis'] = keyword_analyzer.analyze_keyword_frequencies()
        
        # 模块3: 事情逻辑/因果关系分析
        causal_analyzer = CausalRelationshipAnalyzer(self)
        results['causal_relationship_analysis'] = causal_analyzer.analyze_causal_relationships()
        
        # 模块4: 节点直接逻辑关系分析
        logic_analyzer = DirectLogicAnalyzer(self)
        results['direct_logic_analysis'] = logic_analyzer.analyze_direct_logic_relationships()
        
        return results


class VerbPredicateAnalyzer:
    """模块1: 实体中动词/谓语潜在缺失分析"""
    
    def __init__(self, parent: GlobalAnalyzer):
        self.parent = parent
        
    def analyze_missing_verbs(self) -> AnalysisResult:
        """分析实体中缺失的动词/谓语"""
        findings = []
        recommendations = []
        
        for entity_name, entity in self.parent.entities.items():
            # 分析实体名称和描述中的动词
            text = f"{entity.name} {' '.join(str(v) for v in entity.attributes.values())}"
            
            # 使用jieba进行词性标注
            words = pseg.cut(text)
            verbs = [word for word, flag in words if flag.startswith('v')]
            
            # 检查是否缺少动词
            if len(verbs) == 0:
                findings.append({
                    'entity': entity_name,
                    'issue': 'missing_verb',
                    'description': f'实体 {entity_name} 缺少动词/谓语描述',
                    'severity': 'medium'
                })
                
                # 基于关系推断可能的动词
                related_verbs = self._infer_verbs_from_relations(entity_name)
                if related_verbs:
                    recommendations.append({
                        'entity': entity_name,
                        'type': 'add_verb',
                        'suggested_verbs': related_verbs,
                        'rationale': '基于关系推断的动词'
                    })
        
        # 分析流程性关系
        process_relations = self._identify_process_relations()
        
        return AnalysisResult(
            module_name='verb_predicate_analysis',
            findings=findings + process_relations,
            recommendations=recommendations,
            confidence_score=0.8
        )
    
    def _infer_verbs_from_relations(self, entity_name: str) -> List[str]:
        """从关系中推断动词"""
        verbs = []
        
        # 检查出边关系
        for relation_key, relation in self.parent.relations.items():
            if relation.source == entity_name:
                # 从关系名称中提取动词
                relation_verbs = [v for v in self.parent.verb_keywords 
                                if v in relation.name]
                verbs.extend(relation_verbs)
        
        return list(set(verbs))
    
    def _identify_process_relations(self) -> List[Dict[str, Any]]:
        """识别流程性关系"""
        process_findings = []
        
        # 查找序列性关系
        for entity_name in self.parent.entities.keys():
            successors = list(self.parent.graph.successors(entity_name))
            predecessors = list(self.parent.graph.predecessors(entity_name))
            
            if len(successors) > 0 and len(predecessors) > 0:
                process_findings.append({
                    'entity': entity_name,
                    'type': 'process_node',
                    'description': f'{entity_name} 可能是流程中的处理节点',
                    'predecessors': predecessors,
                    'successors': successors,
                    'severity': 'low'
                })
        
        return process_findings


class KeywordFrequencyAnalyzer:
    """模块2: 实体关键词频率统计分析"""
    
    def __init__(self, parent: GlobalAnalyzer):
        self.parent = parent
        
    def analyze_keyword_frequencies(self) -> AnalysisResult:
        """分析实体关键词频率"""
        findings = []
        recommendations = []
        
        # 提取所有实体的关键词
        all_keywords = []
        entity_keywords = {}
        
        for entity_name, entity in self.parent.entities.items():
            text = f"{entity.name} {' '.join(str(v) for v in entity.attributes.values())}"
            keywords = list(jieba.cut(text))
            entity_keywords[entity_name] = keywords
            all_keywords.extend(keywords)
        
        # 计算关键词频率
        keyword_freq = Counter(all_keywords)
        
        # 分析高频关键词
        top_keywords = keyword_freq.most_common(20)
        findings.append({
            'type': 'high_frequency_keywords',
            'description': '高频关键词统计',
            'keywords': top_keywords,
            'severity': 'info'
        })
        
        # 分析相似实体
        similar_entities = self._find_similar_entities(entity_keywords, keyword_freq)
        
        # 生成相似性关系推荐
        for similarity in similar_entities:
            if similarity['score'] > 0.3:  # 相似度阈值
                recommendations.append({
                    'type': 'similar_entity_relation',
                    'entities': [similarity['entity1'], similarity['entity2']],
                    'similarity_score': similarity['score'],
                    'common_keywords': similarity['common_keywords'],
                    'suggested_relation': '相似关系'
                })
        
        return AnalysisResult(
            module_name='keyword_frequency_analysis',
            findings=findings,
            recommendations=recommendations,
            confidence_score=0.9
        )
    
    def _find_similar_entities(self, entity_keywords: Dict[str, List[str]], 
                             keyword_freq: Counter) -> List[Dict[str, Any]]:
        """找出相似实体"""
        similar_entities = []
        entity_names = list(entity_keywords.keys())
        
        # 创建统一的词汇表
        all_unique_keywords = set()
        for keywords in entity_keywords.values():
            all_unique_keywords.update(keywords)
        vocabulary = list(all_unique_keywords)
        
        # 为每个实体生成相同维度的向量
        entity_vectors = {}
        for entity_name in entity_names:
            entity_vectors[entity_name] = self._get_tfidf_vector_unified(
                entity_keywords[entity_name], keyword_freq, vocabulary
            )
        
        for i in range(len(entity_names)):
            for j in range(i + 1, len(entity_names)):
                entity1, entity2 = entity_names[i], entity_names[j]
                
                vec1 = entity_vectors[entity1]
                vec2 = entity_vectors[entity2]
                
                # 计算余弦相似度
                if len(vec1) > 0 and len(vec2) > 0:
                    try:
                        similarity = 1 - cosine(vec1, vec2)
                    except ValueError:
                        # 如果仍然有维度问题，使用简化的相似度计算
                        similarity = 0.1
                    
                    # 找出共同关键词
                    common_keywords = set(entity_keywords[entity1]) & set(entity_keywords[entity2])
                    
                    similar_entities.append({
                        'entity1': entity1,
                        'entity2': entity2,
                        'score': similarity,
                        'common_keywords': list(common_keywords)
                    })
        
        return sorted(similar_entities, key=lambda x: x['score'], reverse=True)
    
    def _get_tfidf_vector_unified(self, keywords: List[str], keyword_freq: Counter, vocabulary: List[str]) -> List[float]:
        """计算统一维度的TF-IDF向量"""
        tf = Counter(keywords)
        total_keywords = len(keywords)
        total_docs = len(self.parent.entities)
        
        tfidf_vector = []
        for keyword in vocabulary:
            if keyword in tf:
                tf_score = tf[keyword] / total_keywords
                idf_score = np.log(total_docs / (keyword_freq[keyword] + 1))
                tfidf_vector.append(tf_score * idf_score)
            else:
                tfidf_vector.append(0.0)  # 不存在的关键词得分为0
        
        return tfidf_vector


class CausalRelationshipAnalyzer:
    """模块3: 事情逻辑/因果关系分析"""
    
    def __init__(self, parent: GlobalAnalyzer):
        self.parent = parent
        
    def analyze_causal_relationships(self) -> AnalysisResult:
        """分析因果关系"""
        findings = []
        recommendations = []
        
        # 分析现有关系中的因果关系
        causal_relations = self._identify_causal_relations()
        
        # 分析实体间的层次关系
        hierarchical_relations = self._analyze_hierarchical_relations()
        
        # 检测缺失的因果关系
        missing_causals = self._detect_missing_causal_relations()
        
        findings.extend(causal_relations)
        findings.extend(hierarchical_relations)
        findings.extend(missing_causals)
        
        # 生成因果关系推荐
        for missing in missing_causals:
            recommendations.append({
                'type': 'add_causal_relation',
                'cause': missing['potential_cause'],
                'effect': missing['potential_effect'],
                'confidence': missing['confidence'],
                'rationale': missing['rationale']
            })
        
        return AnalysisResult(
            module_name='causal_relationship_analysis',
            findings=findings,
            recommendations=recommendations,
            confidence_score=0.75
        )
    
    def _identify_causal_relations(self) -> List[Dict[str, Any]]:
        """识别现有的因果关系"""
        causal_findings = []
        
        for relation_key, relation in self.parent.relations.items():
            # 检查关系名称是否包含因果关键词
            has_causal_keyword = any(keyword in relation.name 
                                   for keyword in self.parent.causal_keywords)
            
            if has_causal_keyword:
                causal_findings.append({
                    'type': 'existing_causal_relation',
                    'relation': relation.name,
                    'cause': relation.source,
                    'effect': relation.target,
                    'description': f'发现因果关系: {relation.source} -> {relation.target}',
                    'severity': 'info'
                })
        
        return causal_findings
    
    def _analyze_hierarchical_relations(self) -> List[Dict[str, Any]]:
        """分析层次关系"""
        hierarchical_findings = []
        
        # 计算节点的入度和出度
        for entity_name in self.parent.entities.keys():
            in_degree = self.parent.graph.in_degree(entity_name)
            out_degree = self.parent.graph.out_degree(entity_name)
            
            # 根据度数推断层次位置
            if in_degree == 0 and out_degree > 0:
                hierarchical_findings.append({
                    'entity': entity_name,
                    'type': 'root_node',
                    'description': f'{entity_name} 可能是根节点或起始点',
                    'level': 'top',
                    'severity': 'info'
                })
            elif out_degree == 0 and in_degree > 0:
                hierarchical_findings.append({
                    'entity': entity_name,
                    'type': 'leaf_node',
                    'description': f'{entity_name} 可能是叶节点或终点',
                    'level': 'bottom',
                    'severity': 'info'
                })
            elif in_degree > 0 and out_degree > 0:
                hierarchical_findings.append({
                    'entity': entity_name,
                    'type': 'intermediate_node',
                    'description': f'{entity_name} 可能是中间节点',
                    'level': 'middle',
                    'severity': 'info'
                })
        
        return hierarchical_findings
    
    def _detect_missing_causal_relations(self) -> List[Dict[str, Any]]:
        """检测缺失的因果关系"""
        missing_relations = []
        
        # 基于实体属性和名称推断潜在因果关系
        entities = list(self.parent.entities.keys())
        
        for i in range(len(entities)):
            for j in range(len(entities)):
                if i != j:
                    entity1, entity2 = entities[i], entities[j]
                    
                    # 检查是否已存在直接关系
                    if not self.parent.graph.has_edge(entity1, entity2):
                        # 基于关键词推断潜在因果关系
                        causal_score = self._calculate_causal_likelihood(entity1, entity2)
                        
                        if causal_score > 0.3:  # 因果关系阈值
                            missing_relations.append({
                                'type': 'missing_causal_relation',
                                'potential_cause': entity1,
                                'potential_effect': entity2,
                                'confidence': causal_score,
                                'rationale': f'基于关键词分析推断的潜在因果关系',
                                'severity': 'medium'
                            })
        
        return missing_relations[:10]  # 限制返回数量
    
    def _calculate_causal_likelihood(self, cause: str, effect: str) -> float:
        """计算因果关系可能性"""
        cause_entity = self.parent.entities[cause]
        effect_entity = self.parent.entities[effect]
        
        # 提取文本
        cause_text = f"{cause_entity.name} {' '.join(str(v) for v in cause_entity.attributes.values())}"
        effect_text = f"{effect_entity.name} {' '.join(str(v) for v in effect_entity.attributes.values())}"
        
        # 计算因果关键词重叠
        cause_keywords = set(jieba.cut(cause_text))
        effect_keywords = set(jieba.cut(effect_text))
        
        causal_overlap = len(cause_keywords & self.parent.causal_keywords) + \
                        len(effect_keywords & self.parent.causal_keywords)
        

        # 计算语义相关性
        semantic_score = len(cause_keywords & effect_keywords) / \
                        (len(cause_keywords | effect_keywords) + 1)
        
        return min(1.0, (causal_overlap * 0.3 + semantic_score * 0.7))


class DirectLogicAnalyzer:
    """模块4: 节点直接逻辑关系分析"""
    
    def __init__(self, parent: GlobalAnalyzer):
        self.parent = parent
        
    def analyze_direct_logic_relationships(self) -> AnalysisResult:
        """分析节点直接逻辑关系"""
        findings = []
        recommendations = []
        
        # 分析类别关系
        category_relations = self._analyze_category_relations()
        
        # 分析逻辑依赖关系
        logical_dependencies = self._analyze_logical_dependencies()
        
        # 检测缺失的逻辑关系
        missing_logical = self._detect_missing_logical_relations()
        
        findings.extend(category_relations)
        findings.extend(logical_dependencies)
        findings.extend(missing_logical)
        
        # 生成逻辑关系推荐
        for missing in missing_logical:
            recommendations.append({
                'type': 'add_logical_relation',
                'source': missing['source'],
                'target': missing['target'],
                'relation_type': missing['relation_type'],
                'confidence': missing['confidence']
            })
        
        return AnalysisResult(
            module_name='direct_logic_analysis',
            findings=findings,
            recommendations=recommendations,
            confidence_score=0.85
        )
    
    def _analyze_category_relations(self) -> List[Dict[str, Any]]:
        """分析类别关系"""
        category_findings = []
        
        # 按实体类型分组
        type_groups = defaultdict(list)
        for entity_name, entity in self.parent.entities.items():
            type_groups[entity.type].append(entity_name)
        
        # 分析类别关系
        for entity_type, entities in type_groups.items():
            if len(entities) > 1:
                category_findings.append({
                    'type': 'category_group',
                    'category': entity_type,
                    'entities': entities,
                    'description': f'发现{entity_type}类别下的{len(entities)}个实体',
                    'severity': 'info'
                })
                
                # 检查同类别实体间的关系
                for i in range(len(entities)):
                    for j in range(i + 1, len(entities)):
                        entity1, entity2 = entities[i], entities[j]
                        
                        if not self.parent.graph.has_edge(entity1, entity2) and \
                           not self.parent.graph.has_edge(entity2, entity1):
                            category_findings.append({
                                'type': 'missing_category_relation',
                                'entity1': entity1,
                                'entity2': entity2,
                                'category': entity_type,
                                'description': f'同类别实体{entity1}和{entity2}间缺少关系',
                                'severity': 'medium'
                            })
        
        return category_findings
    
    def _analyze_logical_dependencies(self) -> List[Dict[str, Any]]:
        """分析逻辑依赖关系"""
        dependency_findings = []
        
        # 分析强连通组件
        strongly_connected = list(nx.strongly_connected_components(self.parent.graph))
        
        for component in strongly_connected:
            if len(component) > 1:
                dependency_findings.append({
                    'type': 'circular_dependency',
                    'entities': list(component),
                    'description': f'发现循环依赖: {", ".join(component)}',
                    'severity': 'high'
                })
        
        # 分析拓扑排序
        try:
            topo_order = list(nx.topological_sort(self.parent.graph))
            dependency_findings.append({
                'type': 'dependency_order',
                'order': topo_order,
                'description': '实体依赖顺序分析',
                'severity': 'info'
            })
        except nx.NetworkXError:
            dependency_findings.append({
                'type': 'no_topological_order',
                'description': '图中存在环路，无法进行拓扑排序',
                'severity': 'warning'
            })
        
        return dependency_findings
    
    def _detect_missing_logical_relations(self) -> List[Dict[str, Any]]:
        """检测缺失的逻辑关系"""
        missing_relations = []
        
        # 基于传递性检测缺失关系
        entities = list(self.parent.entities.keys())
        
        for entity1 in entities:
            for entity2 in entities:
                if entity1 != entity2:
                    # 检查是否存在传递关系但缺少直接关系
                    if nx.has_path(self.parent.graph, entity1, entity2):
                        shortest_path = nx.shortest_path(self.parent.graph, entity1, entity2)
                        
                        if len(shortest_path) > 2:  # 存在间接路径
                            missing_relations.append({
                                'type': 'missing_direct_relation',
                                'source': entity1,
                                'target': entity2,
                                'relation_type': 'logical_dependency',
                                'confidence': 0.6,
                                'path_length': len(shortest_path),
                                'intermediate_nodes': shortest_path[1:-1],
                                'severity': 'low'
                            })
        
        return missing_relations[:5]  # 限制返回数量


def main():
    """主函数 - 使用示例"""
    # 创建全局分析器
    analyzer = GlobalAnalyzer()
    
    # 示例知识图谱数据
    sample_kg = {
        'entities': [
            {
                'name': '用户登录',
                'type': '流程',
                'attributes': {'描述': '用户输入用户名和密码进行登录'},
                'relations': ['验证', '授权']
            },
            {
                'name': '身份验证',
                'type': '服务',
                'attributes': {'描述': '验证用户身份的服务'},
                'relations': ['检查', '确认']
            },
            {
                'name': '用户数据库',
                'type': '数据源',
                'attributes': {'描述': '存储用户信息的数据库'},
                'relations': ['查询', '更新']
            }
        ],
        'relations': [
            {
                'name': '调用',
                'source': '用户登录',
                'target': '身份验证',
                'type': '功能调用',
                'attributes': {}
            },
            {
                'name': '查询',
                'source': '身份验证',
                'target': '用户数据库',
                'type': '数据访问',
                'attributes': {}
            }
        ]
    }
    
    # 加载知识图谱
    analyzer.load_knowledge_graph(sample_kg)
    
    # 执行全局分析
    results = analyzer.analyze_all_modules()
    
    # 输出结果
    for module_name, result in results.items():
        print(f"\n=== {result.module_name} ===")
        print(f"置信度: {result.confidence_score:.2f}")
        
        print("\n发现的问题:")
        for finding in result.findings:
            print(f"- {finding}")
        
        print("\n推荐的改进:")
        for recommendation in result.recommendations:
            print(f"- {recommendation}")


if __name__ == "__main__":
    main()
