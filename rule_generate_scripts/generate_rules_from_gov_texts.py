'''
创新点：基于LLM的知识图谱质量评估规则自动生成方案ß
'''


import os
import json
import time
import random
import argparse
import re
from typing import List, Dict, Any, Tuple


class ZhuqueAIClient:
    def __init__(self, api_key: str, base_url: str = "http://api.cipsup.cn/v1", model: str = "Qwen3-32B", temperature: float = 0.2):
        self.model = model
        self.temperature = temperature
        self.client = None
        try:
            from openai import OpenAI
            self.client = OpenAI(
                api_key=api_key,
                base_url=base_url
            )
        except Exception as exc:
            raise RuntimeError(
                "未安装或无法初始化 openai SDK，请先执行: pip install openai"
            ) from exc

    def chat(self, prompt: str) -> Dict[str, Any]:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=self.temperature,
        )
        content = response.choices[0].message.content.strip()
        return self._parse_ai_response(content)

    def _parse_ai_response(self, content: str) -> Dict[str, Any]:
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass

        cleaned = content
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass

        try:
            normalized = cleaned.replace('""', '"')
            return json.loads(normalized)
        except Exception:
            pass

        match = re.search(r"\{[\s\S]*\}", cleaned)
        if match:
            try:
                return json.loads(match.group())
            except Exception:
                pass

        try:
            score_match = re.search(r'"score":\s*([0-9.]+)', content)
            reason_match = re.search(r'"reason":\s*"([^"]+)"', content)
            score = float(score_match.group(1)) if score_match else 0
            reason = reason_match.group(1) if reason_match else "无法解析响应"
            return {"score": score, "reason": reason}
        except Exception:
            return {"raw": content}


def read_jsonl(path: str, limit: int = None) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as f:
        for idx, line in enumerate(f):
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except Exception:
                continue
            if limit is not None and len(records) >= limit:
                break
    return records


def write_jsonl(path: str, rows: List[Dict[str, Any]]):
    with open(path, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def extract_text_fields(record: Dict[str, Any]) -> Tuple[str, Dict[str, str]]:
    text_fields = {}
    for key in ["实施依据", "责任事项", "服务事项", "权力类型", "行驶主体", "承办机构"]:
        if key in record and isinstance(record[key], str) and record[key].strip():
            text_fields[key] = record[key]
    concatenated = "\n".join([f"{k}: {v}" for k, v in text_fields.items()])
    return concatenated, text_fields


def random_delete_spans(text: str, max_spans: int = 5, max_span_len: int = 6) -> Tuple[str, List[str]]:
    if not text:
        return text, []
    spans_removed: List[str] = []
    text_len = len(text)
    if text_len == 0:
        return text, spans_removed

    num_spans = min(max_spans, max(1, text_len // 200))
    indices = list(range(text_len))
    random.shuffle(indices)
    cut_points = sorted(indices[: num_spans])

    result_chars: List[str] = []
    last = 0
    for cp in cut_points:
        span_length = random.randint(1, max_span_len)
        start = cp
        end = min(text_len, cp + span_length)
        if start > last:
            result_chars.append(text[last:start])
        removed = text[start:end]
        if removed.strip():
            spans_removed.append(removed)
        result_chars.append("[缺失]")
        last = end
    if last < text_len:
        result_chars.append(text[last:])

    return "".join(result_chars), spans_removed


def build_deletion_prompt(service_item: str, original_text: str, masked_text: str, removed_fragments: List[str]) -> str:
    schema = {
        "strategy": "deletion",
        "service_item": "...",
        "analysis": "...",
        "removed_fragments": ["..."],
        "missing_rule_candidates": ["..."],
        "proposed_rules": {
            "entity_types": ["..."],
            "relationship_types": ["..."],
            "type_conflict_rules_forbidden": [["下级机构", "管理", "上级机构"]],
            "type_conflict_rules_allowed": [["政府机构", "发布", "政策"]],
            "hierarchy_rules": ["..."],
            "geo_hierarchy_rules": [["省", "管辖", "市"], ["市", "管辖", "区县"]],
            "procedural_rules": ["..."]
        }
    }
    return (
        "你是政务知识图谱规则抽取专家。我们从政务事项文本中随机删除了一些短语，导致规则性信息缺失。\n"
        "请阅读原文与缺失版，基于上下文与政务常识，推断缺失了哪些规则，并将其抽象为可用于知识图谱校验的规则。\n"
        "强制只输出JSON，严格遵循以下Schema，不要输出额外文本或代码块标记。\n"
        f"Schema示例: {json.dumps(schema, ensure_ascii=False)}\n\n"
        f"服务事项: {service_item}\n"
        "原文: \n" + original_text + "\n\n"
        "缺失版: \n" + masked_text + "\n\n"
        f"被删除片段: {json.dumps(removed_fragments, ensure_ascii=False)}\n"
        "请在proposed_rules中尽量给出可泛化的类型与关系，而不是仅具体实体名。"
    )


def build_augmentation_prompt(service_item: str, original_text: str, max_additions: int = 3) -> str:
    schema = {
        "strategy": "augmentation",
        "service_item": "...",
        "analysis": "...",
        "added_clauses": ["..."],
        "proposed_rules": {
            "entity_types": ["..."],
            "relationship_types": ["..."],
            "type_conflict_rules_forbidden": [["被监管对象", "监管", "监管机构"]],
            "type_conflict_rules_allowed": [["政府机构", "适用于", "地区"]],
            "hierarchy_rules": ["..."],
            "geo_hierarchy_rules": [["国家", "管辖", "省"], ["省", "管辖", "市"]],
            "procedural_rules": ["..."]
        }
    }
    return (
        "你是政务知识图谱规则抽取专家。请在保持真实合规的前提下，为给定政务事项文本拟造不超过"
        f"{max_additions}条合理的补充条款（added_clauses），并基于这些新增内容，抽象出可用于知识图谱校验的规则。\n"
        "强制只输出JSON，严格遵循以下Schema，不要输出额外文本或代码块标记。\n"
        f"Schema示例: {json.dumps(schema, ensure_ascii=False)}\n\n"
        f"服务事项: {service_item}\n"
        "原文: \n" + original_text + "\n\n"
        "请确保proposed_rules尽量通用，避免只出现具体实体名称。"
    )


def aggregate_rules(per_item_results: List[Dict[str, Any]]) -> Dict[str, Any]:
    entity_types = set()
    relationship_types = set()
    forbidden = set()
    allowed = set()
    hierarchy_rules = set()
    geo_rules = set()
    procedural_rules = set()

    def tuple3(x):
        if isinstance(x, (list, tuple)) and len(x) == 3:
            return tuple(x)
        return None

    for item in per_item_results:
        pr = item.get("proposed_rules") or {}
        for et in pr.get("entity_types", []) or []:
            entity_types.add(str(et))
        for rt in pr.get("relationship_types", []) or []:
            relationship_types.add(str(rt))
        for rule in pr.get("type_conflict_rules_forbidden", []) or []:
            t = tuple3(rule)
            if t:
                forbidden.add(t)
        for rule in pr.get("type_conflict_rules_allowed", []) or []:
            t = tuple3(rule)
            if t:
                allowed.add(t)
        for hr in pr.get("hierarchy_rules", []) or []:
            hierarchy_rules.add(json.dumps(hr, ensure_ascii=False))
        for gr in pr.get("geo_hierarchy_rules", []) or []:
            hierarchy = tuple3(gr)
            if hierarchy:
                geo_rules.add(hierarchy)
            else:
                geo_rules.add(json.dumps(gr, ensure_ascii=False))
        for prule in pr.get("procedural_rules", []) or []:
            procedural_rules.add(str(prule))

    return {
        "entity_types": sorted(entity_types),
        "relationship_types": sorted(relationship_types),
        "type_conflict_rules_forbidden": [list(x) for x in sorted(list(forbidden))],
        "type_conflict_rules_allowed": [list(x) for x in sorted(list(allowed))],
        "hierarchy_rules": [json.loads(x) if x.startswith("{") or x.startswith("[") else x for x in sorted(hierarchy_rules)],
        "geo_hierarchy_rules": [list(x) if isinstance(x, tuple) else x for x in sorted(list(geo_rules), key=lambda v: json.dumps(v, ensure_ascii=False))],
        "procedural_rules": sorted(procedural_rules),
    }


def main():
    parser = argparse.ArgumentParser(description="使用大模型从政务文本生成规则（删除缺失+文本增补 双策略）")
    default_input = os.path.join("data", "政务_test.jsonl")
    parser.add_argument("--input", default=default_input, help="输入JSONL文件路径")
    parser.add_argument("--output-dir", default=os.path.join("data", "rule_suggestions"), help="输出目录")
    parser.add_argument("--api-key", default="sk-iNPt408ZjaLwZ8Vs4aPVaSmTmLAccBHNLxlWelnrgujyMfd1", help="朱雀AI API Key")
    parser.add_argument("--base-url", default="http://api.cipsup.cn/v1", help="朱雀API基础URL")
    parser.add_argument("--model", default="Qwen3-32B", help="模型名称")
    parser.add_argument("--temperature", type=float, default=0.2, help="采样温度")
    parser.add_argument("--strategy", choices=["deletion", "augmentation", "both"], default="both", help="生成策略")
    parser.add_argument("--limit", type=int, default=20, help="最多处理前N条，0表示全部")
    parser.add_argument("--sleep", type=float, default=1.5, help="调用间隔秒")
    parser.add_argument("--max-spans", type=int, default=5, help="删除策略中最多删除的片段数")
    parser.add_argument("--max-span-len", type=int, default=6, help="删除策略中单个片段最大长度（字符）")
    parser.add_argument("--max-additions", type=int, default=3, help="增补策略中最多生成的新增条款数")
    args = parser.parse_args()

    if not args.api_key:
        raise SystemExit("必须提供 --api-key")

    os.makedirs(args.output_dir, exist_ok=True)

    client = ZhuqueAIClient(api_key=args.api_key, base_url=args.base_url, model=args.model, temperature=args.temperature)

    records = read_jsonl(args.input, limit=None if args.limit == 0 else args.limit)
    per_item_outputs: List[Dict[str, Any]] = []
    per_call_rows: List[Dict[str, Any]] = []

    for record in records:
        unid = record.get("统一发布平台unid") or record.get("id") or record.get("unid") or "unknown"
        service_item = record.get("服务事项") or record.get("事项名称") or "未提供"
        original_text, fields = extract_text_fields(record)

        if not original_text.strip():
            continue

        if args.strategy in ("deletion", "both"):
            masked, removed = random_delete_spans(original_text, max_spans=args.max_spans, max_span_len=args.max_span_len)
            prompt = build_deletion_prompt(service_item, original_text, masked, removed)
            try:
                result = client.chat(prompt)
            except Exception as exc:
                result = {"error": str(exc)}
            row = {
                "unid": unid,
                "service_item": service_item,
                "strategy": "deletion",
                "removed_fragments": removed,
                "llm_result": result,
            }
            per_call_rows.append(row)
            if isinstance(result, dict):
                per_item_outputs.append(result)
            time.sleep(args.sleep)

        if args.strategy in ("augmentation", "both"):
            prompt = build_augmentation_prompt(service_item, original_text, max_additions=args.max_additions)
            try:
                result = client.chat(prompt)
            except Exception as exc:
                result = {"error": str(exc)}
            row = {
                "unid": unid,
                "service_item": service_item,
                "strategy": "augmentation",
                "llm_result": result,
            }
            per_call_rows.append(row)
            if isinstance(result, dict):
                per_item_outputs.append(result)
            time.sleep(args.sleep)

    per_call_path = os.path.join(args.output_dir, "per_item_rule_suggestions.jsonl")
    write_jsonl(per_call_path, per_call_rows)

    aggregated = aggregate_rules([
        x.get("llm_result", {}) if "llm_result" in x else x for x in per_call_rows
        if isinstance(x.get("llm_result", {}), dict)
    ])

    with open(os.path.join(args.output_dir, "aggregated_rules.json"), "w", encoding="utf-8") as f:
        json.dump(aggregated, f, ensure_ascii=False, indent=2)

    print("已生成：")
    print(per_call_path)
    print(os.path.join(args.output_dir, "aggregated_rules.json"))


if __name__ == "__main__":
    main()






# python generate_rules_from_gov_texts.py --input /Users/turambar928/Documents/GitHub/MCP_based_KG_construction/data/政务_test.jsonl --output-dir /Users/turambar928/Documents/GitHub/MCP_based_KG_construction/data/rule_suggestions --api-key sk-iNPt408ZjaLwZ8Vs4aPVaSmTmLAccBHNLxlWelnrgujyMfd1 --base-url http://api.cipsup.cn/v1 --model Qwen3-32B

'''
uv run generate_rules_from_gov_texts.py \
  --input ./exps/政务.jsonl \
  --output-dir ./exps/rule_suggestions \
  --api-key sk-iNPt408ZjaLwZ8Vs4aPVaSmTmLAccBHNLxlWelnrgujyMfd1 \
  --base-url http://api.cipsup.cn/v1 \
  --model Qwen3-32B \
  --strategy both \
  --limit 20           

'''