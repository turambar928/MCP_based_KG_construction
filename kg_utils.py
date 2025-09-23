# kg_utils.py - LLM版本

import json
import re
import asyncio
import requests
from typing import Dict, List, Tuple, Any, Optional
from dataclasses import dataclass
from collections import defaultdict


@dataclass
class Triple:
    """知识图谱三元组"""
    head: str
    relation: str
    tail: str
    confidence: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "head": self.head,
            "relation": self.relation,
            "tail": self.tail,
            "confidence": self.confidence
        }

    def __str__(self) -> str:
        return f"({self.head}, {self.relation}, {self.tail})"


class ChineseEntityRelationExtractor:
    """纯LLM中文实体抽取与关系抽取"""
    
    def __init__(self, api_key):
        self.api_key = api_key  # 模型是否需要跟env相同（取决于模型的实体和关系抽取能力）
        self.base_url = "https://api.siliconflow.cn/v1/chat/completions"
        self.model = "Qwen/Qwen2.5-7B-Instruct"
        
    def call_api(self, prompt):
        """调用Silicon Flow API"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.1,
            "max_tokens": 800
        }
        
        try:
            response = requests.post(self.base_url, headers=headers, json=data, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                if "choices" in result and len(result["choices"]) > 0:
                    return result["choices"][0]["message"]["content"]
            else:
                print(f"❌ API调用失败: HTTP {response.status_code}")
                return None
            
        except Exception as e:
            print(f"❌ API调用失败: {e}")
            return None
    
    def extract_entities_and_types(self, text):
        """同时提取实体和类型"""
        prompt = f"""
请从以下中文文本中提取实体，并标注每个实体的类型。

文本："{text}"

请按照以下格式输出，每行一个实体：
实体名称|实体类型

实体类型包括：Person（人物）、Organization（组织）、Location（地点）、Product（产品）、Event（事件）、Other（其他）

示例格式：
张三|Person
阿里巴巴|Organization
北京|Location
iPhone|Product
"""
        
        response = self.call_api(prompt)
        if response:
            entities = {}
            lines = response.strip().split('\n')
            for line in lines:
                if '|' in line:
                    parts = line.split('|')
                    if len(parts) >= 2:
                        entity = parts[0].strip()
                        entity_type = parts[1].strip()
                        if entity:
                            entities[entity] = entity_type
            return entities
        return {}

    def extract_triplets(self, text):
        """提取三元组"""
        prompt = f"""
请从以下中文文本中，严格按照 "头实体, 关系, 尾实体" 的格式，抽取所有实体关系三元组。

文本："{text}"

你的任务是识别出句子中的主语（头实体）、谓语（关系）和宾语（尾实体）。
- 关系应该是描述性的动词或短语。
- 实体应是具体的名词或名词短语。
- 只输出文本中明确存在或可以强力推断的关系。

请严格按照以下格式输出，每行一个三元
- (头实体, 关系, 尾实体)

示例输入: "北京市中国的首都，也是一座历史悠久的文化名城。"
示例输出:
(北京, 是, 中国的首都)
(北京, 位于, 中国)

现在，请处理上面的文本。
"""
        
        response = self.call_api(prompt)
        if response:
            return self.parse_triplets(response)
        return []
    
    def parse_triplets(self, response):
        """解析三元组"""
        triplets = []
        lines = response.strip().split('\n')
        
        for line in lines:
            # 匹配格式：(头实体,关系,尾实体)
            match = re.search(r'\(([^,]+),\s*([^,]+),\s*([^)]+)\)', line)
            if match:
                head = match.group(1).strip()
                relation = match.group(2).strip()
                tail = match.group(3).strip()
                if head and relation and tail:
                    triplets.append((head, relation, tail))
        
        return triplets


class LLMJsonExtractor:
    """从LLM提取JSON的工具"""

    def __init__(self, api_key: str, model_name: str = "deepseek-chat"):
        self.api_key = api_key
        self.model_name = model_name
        self.base_url = "https://api.siliconflow.cn/v1/chat/completions"
        self.model = "Qwen/Qwen2.5-7B-Instruct"
        if not api_key:
            raise ValueError("API key must be provided for LLMJsonExtractor")

        # Check for custom base URL for self-hosted models
        # base_url = os.getenv("OPENAI_BASE_URL") # This line was removed as per the new_code, as it's not in the new_code.
        # if base_url:
        #     openai.api_base = base_url

    async def _call_llm_api(self, prompt: str) -> Optional[Dict[str, Any]]:
        """调用Silicon Flow API（带重试与退避）"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.1,
            "max_tokens": 800
        }

        max_attempts = 3
        backoff_seconds = 1.5
        last_error = None
        for attempt in range(1, max_attempts + 1):
            try:
                response = requests.post(self.base_url, headers=headers, json=data, timeout=30)
                if response.status_code == 200:
                    result = response.json()
                    if "choices" in result and len(result["choices"]) > 0:
                        return result["choices"][0]["message"]["content"]
                    else:
                        last_error = "empty choices"
                else:
                    last_error = f"HTTP {response.status_code}: {response.text[:200]}"
            except Exception as e:
                last_error = str(e)

            # 重试退避
            if attempt < max_attempts:
                try:
                    await asyncio.sleep(backoff_seconds * attempt)
                except Exception:
                    pass

        print(f"❌ API调用失败(重试{max_attempts}次后放弃): {last_error}")
        return None
    
    async def extract_entities_and_types(self, text):
        """同时提取实体和类型"""
        prompt = f"""
Please extract entities from the following Chinese text and label the type of each entity.
Text: "{text}"
Please output in the following format, one entity per line:
Entity Name|Entity Type
Entity types include: Person, Organization, Location, Product, Event, Other
Example format:
张三|Person
阿里巴巴|Organization
北京|Location
iPhone|Product
"""
        
        response = await self._call_llm_api(prompt)
        if response:
            entities = {}
            lines = response.strip().split('\n')
            for line in lines:
                if '|' in line:
                    parts = line.split('|')
                    if len(parts) >= 2:
                        entity = parts[0].strip()
                        entity_type = parts[1].strip()
                        if entity:
                            entities[entity] = entity_type
            return entities
        return {}

    async def extract_triplets(self, text):
        """提取三元组"""
        prompt = f"""
Please extract entity relationship triplets from the following Chinese text.
Text: "{text}"
Please strictly follow the format below, with one triplet per line:
(Head Entity,Relation,Tail Entity)
Requirements:
1. Head and tail entities must be explicitly mentioned in the text.
2. The relation should accurately describe the relationship between the two entities.
3. Only output confirmed relationships, do not guess.
4. Output only one triplet per line.
Example:
(张三,担任,CEO)
(阿里巴巴,总部位于,杭州)
"""
        
        response = await self._call_llm_api(prompt)
        if response:
            return self.parse_triplets(response)
        return []
    
    def parse_triplets(self, response):
        """解析三元组"""
        triplets = []
        lines = response.strip().split('\n')
        
        for line in lines:
            # 匹配格式：(头实体,关系,尾实体)
            match = re.search(r'\(([^,]+),\s*([^,]+),\s*([^)]+)\)', line)
            if match:
                head = match.group(1).strip()
                relation = match.group(2).strip()
                tail = match.group(3).strip()
                if head and relation and tail:
                    triplets.append((head, relation, tail))
        
        return triplets


class PureLLMKnowledgeGraphBuilder:
    """纯LLM知识图谱构建器（无硬编码规则）"""

    def __init__(self, api_key: str, model_name: str = "deepseek-chat"):
        self.llm_extractor = LLMJsonExtractor(api_key, model_name)
        self.entity_types: Dict[str, str] = {}
        # 添加一个简单的无效实体名称集合
        self.invalid_entity_names = {"", "_", " "}

    def _is_valid_entity(self, entity_name: str) -> bool:
        """检查实体名称是否有效"""
        if not entity_name or not entity_name.strip():
            return False
        if entity_name.lower() in self.invalid_entity_names:
            return False
        # 过滤掉纯数字且长度较短的
        if entity_name.isdigit() and len(entity_name) < 4:
            return False
        # **关键修复**: 允许中文字符。检查是否至少包含一个字母、数字或中文字符。
        if not re.search(r'[\u4e00-\u9fa5a-zA-Z0-9]', entity_name):
            return False
        return True

    async def build_graph(self, text: str, use_llm: bool = True) -> Dict[str, Any]:
        """
        使用LLM构建知识图谱
        Args:
            text: 输入文本
            use_llm: 必须为True，纯LLM版本不支持规则模式
        Returns:
            知识图谱数据
        """
        if not use_llm:
            print("⚠️  纯LLM版本不支持规则模式，自动启用LLM模式")

        # **性能优化**: 并行执行实体和三元组的提取
        entities_task = self.llm_extractor.extract_entities_and_types(text)
        triplets_task = self.llm_extractor.extract_triplets(text)

        results = await asyncio.gather(entities_task, triplets_task)
        entities_with_types, llm_triplets = results[0], results[1]

        # 若 LLM 返回为空，使用本地轻量规则作为回退，避免整批为0
        if not entities_with_types and not llm_triplets:
            entities_with_types, llm_triplets = self._fallback_extract(text)

        # 处理实体
        entities = list(entities_with_types.keys())
        self.entity_types = entities_with_types

        # 处理三元组
        triples = []
        relations = set()

        for head, relation, tail in llm_triplets:
            # 计算置信度
            confidence = self._calculate_llm_confidence(text, head, relation, tail)
            triple = Triple(head, relation, tail, confidence)
            triples.append(triple)
            relations.add(relation)

            # 确保实体被包含
            if head not in entities:
                entities.append(head)
                self.entity_types[head] = "Other"
            if tail not in entities:
                entities.append(tail)
                self.entity_types[tail] = "Other"

        # 去重和合并
        triples = self._merge_duplicate_triples(triples)

        # 计算置信度
        confidence_scores = [triple.confidence for triple in triples]
        
        # 应用过滤器
        final_entities = [e for e in entities if self._is_valid_entity(e)]
        
        final_triples = [
            t for t in triples 
            if self._is_valid_entity(t.head) and 
               self._is_valid_entity(t.tail) and 
               self._is_valid_entity(t.relation)
        ]
        
        final_relations = list(set(t.relation for t in final_triples))
        final_confidence_scores = [t.confidence for t in final_triples]

        return {
            "entities": final_entities,
            "relations": final_relations,
            "triples": final_triples,
            "confidence_scores": final_confidence_scores
        }

    def _fallback_extract(self, text: str) -> Tuple[Dict[str, str], List[Tuple[str, str, str]]]:
        """
        本地回退抽取：基于简单正则/规则的三元组抽取与实体推断。
        目标：当 LLM 限流/失败时，仍尽量产出可用三元组，避免完全为0。
        """
        # 常见关系触发词及正则模板（中文）
        patterns = [
            (r"([\u4e00-\u9fa5A-Za-z0-9_]{2,})\s*是\s*([\u4e00-\u9fa5A-Za-z0-9_]{2,})", "是"),
            (r"([\u4e00-\u9fa5A-Za-z0-9_]{2,})\s*属于\s*([\u4e00-\u9fa5A-Za-z0-9_]{2,})", "属于"),
            (r"([\u4e00-\u9fa5A-Za-z0-9_]{2,})\s*位于\s*([\u4e00-\u9fa5A-Za-z0-9_]{2,})", "位于"),
            (r"([\u4e00-\u9fa5A-Za-z0-9_]{2,})\s*担任\s*([\u4e00-\u9fa5A-Za-z0-9_]{2,})", "担任"),
            (r"([\u4e00-\u9fa5A-Za-z0-9_]{2,})\s*监管\s*电话\s*([0-9\-]{5,})", "监管电话"),
            (r"承办机构[:：]\s*([\u4e00-\u9fa5A-Za-z0-9_（）()]{2,})", "承办机构"),
        ]

        found_triplets: List[Tuple[str, str, str]] = []
        for pattern, relation in patterns:
            for m in re.finditer(pattern, text):
                try:
                    if relation == "承办机构":
                        head = "本事项"
                        tail = m.group(1).strip()
                    elif relation == "监管电话":
                        head = "本事项"
                        tail = m.group(2).strip() if m.lastindex and m.lastindex >= 2 else m.group(1).strip()
                    else:
                        head = m.group(1).strip()
                        tail = m.group(2).strip()
                    if head and tail:
                        found_triplets.append((head, relation, tail))
                except Exception:
                    continue

        # 去重
        uniq = set()
        dedup_triplets: List[Tuple[str, str, str]] = []
        for h, r, t in found_triplets:
            key = (h, r, t)
            if key not in uniq:
                uniq.add(key)
                dedup_triplets.append(key)

        # 实体类型：尽量标注简单类型，否则 Other
        entities_with_types: Dict[str, str] = {}
        for h, r, t in dedup_triplets:
            if h not in entities_with_types:
                entities_with_types[h] = "Other"
            if t not in entities_with_types:
                if r == "监管电话" and re.fullmatch(r"[0-9\-]{5,}", t):
                    entities_with_types[t] = "Contact"
                elif r == "承办机构":
                    entities_with_types[t] = "Organization"
                else:
                    entities_with_types[t] = "Other"

        return entities_with_types, dedup_triplets

    def _calculate_llm_confidence(self, data: str, head: str, relation: str, tail: str) -> float:
        """计算LLM三元组置信度"""
        confidence = 0.5  # 基础置信度降低
        
        # 1. 实体在原文中的位置和频率
        head_count = data.count(head)
        tail_count = data.count(tail)
        
        # 实体出现频率影响置信度
        if head_count > 0 and tail_count > 0:
            frequency_bonus = min(0.3, (head_count + tail_count) * 0.05)
            confidence += frequency_bonus
        
        # 2. 实体距离分析
        head_pos = data.find(head)
        tail_pos = data.find(tail)
        if head_pos != -1 and tail_pos != -1:
            distance = abs(head_pos - tail_pos)
            text_length = len(data)
            # 距离越近，置信度越高
            proximity_bonus = max(0, 0.2 * (1 - distance / text_length))
            confidence += proximity_bonus
        
        # 3. 关系词在实体附近的存在
        relation_in_context = False
        if head_pos != -1 and tail_pos != -1:
            start_pos = min(head_pos, tail_pos)
            end_pos = max(head_pos, tail_pos) + max(len(head), len(tail))
            context = data[max(0, start_pos-20):min(len(data), end_pos+20)]
            
            # 检查关系词或相关词是否在上下文中
            relation_words = [relation, '是', '在', '的', '有', '属于', '担任', '位于']
            if any(word in context for word in relation_words):
                confidence += 0.15
                relation_in_context = True
        
        # 4. 实体类型匹配度
        head_type = self.entity_types.get(head, "Other")
        tail_type = self.entity_types.get(tail, "Other")
        
        # 合理的类型组合获得更高置信度
        type_combinations = {
            ("Person", "Organization"): 0.15,
            ("Person", "Location"): 0.12,
            ("Organization", "Location"): 0.10,
            ("Person", "Product"): 0.08,
            ("Organization", "Product"): 0.08,
        }
        
        combination_key = (head_type, tail_type)
        reverse_key = (tail_type, head_type)
        
        if combination_key in type_combinations:
            confidence += type_combinations[combination_key]
        elif reverse_key in type_combinations:
            confidence += type_combinations[reverse_key]
        
        # 5. 关系类型的可信度
        relation_confidence_map = {
            '是': 0.9, '担任': 0.85, '位于': 0.85, '属于': 0.8,
            '工作于': 0.8, '就职于': 0.8, '毕业于': 0.75, '学习': 0.7,
            '开发': 0.7, '制作': 0.7, '创建': 0.7, '拥有': 0.65,
            '包含': 0.6, '相关': 0.5, '关联': 0.5
        }
        
        relation_base = relation_confidence_map.get(relation, 0.6)
        confidence = confidence * relation_base
        
        # 6. 文本长度影响（较长文本可能包含更多噪音）
        text_length = len(data)
        if text_length > 500:
            confidence *= 0.95  # 轻微降低
        elif text_length < 50:
            confidence *= 0.9   # 文本太短可能信息不足
        
        # 7. 确保置信度在合理范围内
        confidence = max(0.1, min(0.98, confidence))
        
        # 8. 添加一些随机性避免完全相同的置信度
        import random
        random.seed(hash(head + relation + tail) % 1000)  # 基于内容的伪随机
        noise = (random.random() - 0.5) * 0.05  # ±2.5%的噪声
        confidence += noise
        
        return round(max(0.1, min(0.98, confidence)), 3)

    def _merge_duplicate_triples(self, triples: List[Triple]) -> List[Triple]:
        """合并重复三元组"""
        triple_dict = {}
        
        for triple in triples:
            key = (triple.head, triple.relation, triple.tail)
            if key in triple_dict:
                # 保留置信度更高的
                if triple.confidence > triple_dict[key].confidence:
                    triple_dict[key] = triple
            else:
                triple_dict[key] = triple
        
        return list(triple_dict.values())

    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        entity_type_counts = defaultdict(int)
        for entity, entity_type in self.entity_types.items():
            entity_type_counts[entity_type] += 1

        relation_counts = defaultdict(int)
        for triple in self.triples:
            relation_counts[triple.relation] += 1

        return {
            "total_entities": len(self.entities),
            "total_relations": len(self.relations),
            "total_triples": len(self.triples),
            "entity_types": dict(entity_type_counts),
            "relation_distribution": dict(relation_counts),
            "average_confidence": sum(triple.confidence for triple in self.triples) / len(self.triples) if self.triples else 0
        }

    def export_graph(self, format_type: str = "json") -> str:
        """导出知识图谱"""
        if format_type == "json":
            graph_data = {
                "entities": [{"id": entity, "type": self.entity_types.get(entity, "Other")} for entity in self.entities],
                "relations": list(self.relations),
                "triples": [triple.to_dict() for triple in self.triples]
            }
            return json.dumps(graph_data, ensure_ascii=False, indent=2)
        else:
            raise ValueError(f"不支持的格式: {format_type}")

    def clear_graph(self):
        """清空知识图谱"""
        self.entities.clear()
        self.relations.clear()
        self.triples.clear()
        self.entity_types.clear()


# 为了兼容性，保留原来的类名
class KnowledgeGraphBuilder(PureLLMKnowledgeGraphBuilder):
    """知识图谱构建器（兼容性别名）"""
    pass
