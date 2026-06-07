# -*- coding: utf-8 -*-
"""
Build the training dataset for the neural repair decision network f_phi (paper1 §3.2 / §4.4.1).

Instance = a DOCUMENT (one jsonl record). Each administrative record is turned into a small
typed sub-graph from its structured fields; deterministic per-scale detectors then produce the
quality state vector and graph statistics, while the document's known injected-defect set
("引入问题", present only in the degraded corpora) supplies self-supervised labels — no manual
annotation (Eq. repair_label / scale_label in the methodology).

Per document we emit:
  state vector s = (S_iso, S_red, S_log, S_sem)  in [0,100]^4   (Eq. quality_state)
  graph stats   g = (|V|, |E|, density, n_violations)
  labels:
        y_repair = 1 if the doc carries injected defects (degraded corpus), else 0 (clean corpus)
        y_scale / scale_label = dominant scale among the injected defects, mapped:
            entity  <- 重复三元组制造, 冗余信息, 孤立节点制造, 字段缺失
            graph   <- 层级冲突制造, 逻辑矛盾, 关系错误, 实体类型错误
            context <- 术语错误, 信息不一致, 格式错误

S_iso/S_red/S_log are deterministic (no LLM). S_sem is filled later by score_semantics.py
(1 Qwen call/doc on a sample); until then it is imputed and flagged via sem_observed=0.

Output: exps/decision_network/dataset.csv  (+ per-doc triples cache triples_cache.jsonl)
"""
import os
import re
import json
import random
import collections
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
EXPS = os.path.dirname(HERE)
SEED = 42
random.seed(SEED)

# balanced sampling per (domain): (n_clean, n_dirty)
SAMPLE = {"government": (700, 700), "finance": (400, 400), "environment": (350, 350)}

SOURCES = {  # domain -> (clean_jsonl, dirty_jsonl, domain_kind)
    "government": ("政务.jsonl", "政务_低质量.jsonl", "gov"),
    "finance":    ("金融.jsonl", "金融_低质量.jsonl", "fin"),
    "environment":("环境.jsonl", "环境_低质量.jsonl", "env"),
}

DEFECT_SCALE = {
    "重复三元组制造": "entity", "冗余信息": "entity", "孤立节点制造": "entity", "字段缺失": "entity",
    "层级冲突制造": "graph", "逻辑矛盾": "graph", "关系错误": "graph", "实体类型错误": "graph",
    "术语错误": "context", "信息不一致": "context", "格式错误": "context",
}

# admin-hierarchy levels (from the evaluators' _get_gov_level); larger = lower in hierarchy
GOV_LEVELS = [("国务院", 1), ("中央", 1), ("省", 2), ("自治区", 2), ("直辖市", 2),
              ("市", 3), ("地级市", 3), ("州", 3), ("县", 4), ("区", 4), ("县级市", 4),
              ("乡", 5), ("镇", 5), ("街道", 5), ("村", 6), ("社区", 6)]
AUTHORITY_KW = ["局", "厅", "部", "委员会", "政府", "监管", "管理局", "管委会"]

ORG_FIELDS = ["行驶主体", "承办机构"]
SCALAR_FIELDS = ["服务事项", "权力类型", "行驶主体", "承办机构", "实施依据", "监管电话"]


def gov_level(name):
    name = str(name)
    for kw, lv in GOV_LEVELS:
        if kw in name:
            return lv
    return None


def parse_rm(rm):
    """责任事项 multiline 'k：v' -> dict."""
    out = {}
    for line in str(rm).splitlines():
        m = re.match(r"\s*([^：:]+)[：:]\s*(.*)", line)
        if m:
            out[m.group(1).strip()] = m.group(2).strip()
    return out


def doc_to_triples(doc):
    """Deterministic field -> typed triples. Returns (triples, node_types)."""
    si = str(doc.get("服务事项", "")).strip() or "服务事项"
    triples = []          # (subj, rel, obj)
    ntype = {}            # node name -> type

    def add(subj, rel, obj, st, ot):
        if obj is None or str(obj).strip() == "":
            return
        triples.append((subj, rel, str(obj).strip()))
        ntype.setdefault(subj, st)
        ntype.setdefault(str(obj).strip(), ot)

    add(si, "权力类型", doc.get("权力类型"), "服务事项", "权力类型")
    add(si, "行驶主体", doc.get("行驶主体"), "服务事项", "政府机构")
    add(si, "承办机构", doc.get("承办机构"), "服务事项", "政府机构")
    add(si, "实施依据", str(doc.get("实施依据", ""))[:60], "服务事项", "法规")
    add(si, "监管电话", doc.get("监管电话"), "服务事项", "电话")
    for k, v in parse_rm(doc.get("责任事项", "")).items():
        add(si, k, v, "服务事项", "责任要素")
    return triples, ntype


def compute_state(doc):
    """Deterministic S_iso/S_red/S_log + graph stats from the doc's field-graph."""
    triples, ntype = doc_to_triples(doc)
    nodes = set(ntype.keys())
    n_e = len(triples)
    n_v = len(nodes)
    if n_e == 0:
        return None

    # --- entity / connectivity: missing expected fields => isolated/missing ---
    expected = SCALAR_FIELDS + ["责任事项"]
    n_missing = sum(1 for f in expected if str(doc.get(f, "")).strip() == "")
    iso_rate = n_missing / len(expected)

    # --- entity / redundancy: duplicate triples/objects + repeated clauses in 责任事项 ---
    tc = collections.Counter(triples)
    dup_triples = sum(c - 1 for c in tc.values() if c > 1)
    obj_counts = collections.Counter(o for _, _, o in triples)
    dup_objs = sum(c - 1 for c in obj_counts.values() if c > 1)
    rm_text = str(doc.get("责任事项", ""))
    clauses = [c.strip() for c in re.split(r"[。；\n]", rm_text) if len(c.strip()) > 6]
    dup_clauses = len(clauses) - len(set(clauses))
    red_rate = min(1.0, (dup_triples + 0.5 * dup_objs + dup_clauses) / n_e)

    # --- graph / logical: reversed admin hierarchy + authority-as-offender + type errors ---
    conf = 0
    ab, ho = str(doc.get("行驶主体", "")), str(doc.get("承办机构", ""))
    la, lh = gov_level(ab), gov_level(ho)
    if la is not None and lh is not None and la > lh:   # acting body lower than handling org
        conf += 1
    rm = parse_rm(rm_text)
    offender = rm.get("违法主体", "")
    if offender and any(k in offender for k in AUTHORITY_KW):  # authority listed as offender
        conf += 1
    # entity-type mismatch: phone field without digits
    tel = str(doc.get("监管电话", ""))
    if tel and not re.search(r"\d", tel):
        conf += 1
    # placeholder / abolished org (信息不一致 / 实体类型错误)
    if any(k in ho for k in ["已撤销", "未知", "无"]) and ho.strip():
        conf += 1
    log_rate = min(1.0, conf / n_e)

    S_iso = (1 - iso_rate) * 100.0
    S_red = (1 - red_rate) * 100.0
    S_log = (1 - log_rate) * 100.0
    density = n_e / (n_v * (n_v - 1)) if n_v > 1 else 0.0
    n_viol = round(iso_rate * n_e + red_rate * n_e + conf)
    return {
        "n_v": n_v, "n_e": n_e, "density": round(density, 5),
        "S_iso": round(S_iso, 3), "S_red": round(S_red, 3), "S_log": round(S_log, 3),
        "n_missing": n_missing, "n_dup": dup_triples + dup_objs, "n_logconf": conf,
        "triples": triples,
    }


def scale_label_from_defects(defects):
    c = collections.Counter()
    for d in defects or []:
        sc = DEFECT_SCALE.get(d)
        if sc:
            c[sc] += 1
    if not c:
        return "none", (0.0, 0.0, 0.0)
    tot = sum(c.values())
    vec = (c.get("entity", 0) / tot, c.get("graph", 0) / tot, c.get("context", 0) / tot)
    return max(c, key=c.get), vec


def load_docs(path):
    with open(os.path.join(EXPS, path), encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def main():
    rows = []
    triple_cache = []
    for domain, (clean_f, dirty_f, kind) in SOURCES.items():
        n_clean, n_dirty = SAMPLE[domain]
        clean = load_docs(clean_f)
        dirty = load_docs(dirty_f)
        random.shuffle(clean)
        random.shuffle(dirty)

        for tag, docs, n, is_dirty in [("clean", clean, n_clean, 0), ("dirty", dirty, n_dirty, 1)]:
            taken = 0
            for doc in docs:
                if taken >= n:
                    break
                st = compute_state(doc)
                if st is None:
                    continue
                defects = doc.get("引入问题", []) if is_dirty else []
                slabel, svec = scale_label_from_defects(defects)
                uid = str(doc.get("统一发布平台unid", f"{domain}_{tag}_{taken}"))
                rows.append({
                    "uid": uid, "domain": domain, "variant": tag, "is_dirty": is_dirty,
                    "n_v": st["n_v"], "n_e": st["n_e"], "density": st["density"],
                    "S_iso": st["S_iso"], "S_red": st["S_red"], "S_log": st["S_log"],
                    "S_sem": float("nan"), "sem_observed": 0,
                    "n_missing": st["n_missing"], "n_dup": st["n_dup"], "n_logconf": st["n_logconf"],
                    "y_repair": is_dirty,
                    "scale_label": slabel,
                    "pi_entity": round(svec[0], 4), "pi_graph": round(svec[1], 4), "pi_context": round(svec[2], 4),
                    "defects": "|".join(defects),
                })
                triple_cache.append({"uid": uid, "domain": domain,
                                     "triples": [f"{s} --[{r}]-> {o}" for s, r, o in st["triples"]]})
                taken += 1
            print(f"[{domain}/{tag}] took {taken}")

    df = pd.DataFrame(rows)
    out = os.path.join(HERE, "dataset.csv")
    df.to_csv(out, index=False)
    with open(os.path.join(HERE, "triples_cache.jsonl"), "w", encoding="utf-8") as f:
        for r in triple_cache:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"\nSaved {len(df)} document instances -> {out}")
    print("\n== repair balance by domain ==")
    print(df.groupby(["domain", "variant"]).agg(n=("y_repair", "size")).to_string())
    print("\n== feature means by repair label ==")
    print(df.groupby("y_repair")[["S_iso", "S_red", "S_log", "n_missing", "n_dup", "n_logconf"]].mean().round(2).to_string())
    print("\n== scale_label (dirty only) ==")
    print(dict(df[df.is_dirty == 1]["scale_label"].value_counts()))


if __name__ == "__main__":
    main()
