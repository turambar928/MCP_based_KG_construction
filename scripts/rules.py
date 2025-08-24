import json, re
from collections import Counter, defaultdict

PER_ITEM_PATH = "/Users/turambar928/Documents/GitHub/MCP_based_KG_construction/data/rule_suggestions/per_item_rule_suggestions.jsonl"

ENTITY_MAP = {
    "政府部门": "政府机构", "政府机关": "政府机构", "行政机关": "政府机构",
    "市政府": "政府机构", "省政府": "政府机构", "县政府": "政府机构",
    "企业单位": "企业", "公司": "企业",
    "群众": "公民", "个人": "公民",
    "地域": "地区", "行政区": "地区",
    "法律": "法规", "规章制度": "法规",
    "政令": "政策", "文件": "政策",
    "事项": "服务事项", "办理事项": "服务事项",
    "监管方": "监管机构", "被管对象": "被监管对象",
    "任何对象": "任何实体", "任意实体": "任何实体",
}

REL_MAP = {
    "领导": "管理", "主管": "管理",
    "下属": "隶属于",
    "覆盖": "管辖", "包含": "管辖",
    "适用": "适用于",
    "规定": "规范", "约束": "约束",
    "提供服务": "提供",
    "收费": "收费标准",
}

def norm_text(x: str) -> str:
    x = (x or "").strip()
    x = re.sub(r"\s+", "", x)
    return x

def norm_entity(x: str) -> str:
    x = norm_text(x)
    return ENTITY_MAP.get(x, x)

def norm_rel(x: str) -> str:
    x = norm_text(x)
    return REL_MAP.get(x, x)

cnt_forbidden = Counter()
cnt_allowed = Counter()

with open(PER_ITEM_PATH, "r", encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except Exception:
            continue
        pr = (row.get("llm_result") or {}).get("proposed_rules") or {}
        for kind, counter in [("type_conflict_rules_forbidden", cnt_forbidden),
                              ("type_conflict_rules_allowed", cnt_allowed)]:
            for triple in pr.get(kind, []) or []:
                if not (isinstance(triple, list) and len(triple) == 3):
                    continue
                s, r, t = norm_entity(triple[0]), norm_rel(triple[1]), norm_entity(triple[2])
                counter[(s, r, t)] += 1

# 频次阈值（可调）
THRESH = 2

rules = {}
all_keys = set(cnt_forbidden.keys()) | set(cnt_allowed.keys())
for k in all_keys:
    f = cnt_forbidden[k]
    a = cnt_allowed[k]
    if max(f, a) < THRESH:
        continue
    if f > a:
        rules[k] = "禁止"
    elif a > f:
        rules[k] = "允许"
    else:
        rules[k] = "禁止"  # 平手取保守

print("# 粘贴到 CONFIG['logical_rules']['类型冲突规则'] 中")
print("{")
for (s, r, t), v in sorted(rules.items()):
    print(f"    ({repr(s)}, {repr(r)}, {repr(t)}): {repr(v)},")
print("}")