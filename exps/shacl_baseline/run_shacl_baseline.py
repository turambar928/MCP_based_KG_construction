# -*- coding: utf-8 -*-
"""
External baseline for paper1: SHACL-based validation-and-repair (Exp9).

Pipeline (per domain, on the SAME degraded KG that feeds Exp2):
  1. Serialize the KG to RDF (rdflib) — this collapses exact-duplicate triples (RDF set semantics).
  2. Type nodes and attach administrative/geographic hierarchy levels (keyword-based), so shapes apply.
  3. Validate against a SHACL shapes graph (pyshacl) that encodes our constraint families as
     SHACL-SPARQL constraints: relation-validity + admin/geo hierarchy non-reversal.
  4. Remove the triples flagged by the constraints (SHACL-repair semantics).
  5. Re-evaluate the repaired graph with the SAME deterministic checkers used for Exp1-8
     (isolation / redundancy / logical-consistency); S_sem is held at the Exp2 value because
     SHACL has no semantic-repair capability. Report Q = 0.25*(S_iso+S_red+S_log+S_sem).

Output: exps/shacl_baseline/shacl_results.json
"""
import os, sys, json, importlib.util
from urllib.parse import quote
import pandas as pd
from rdflib import Graph, URIRef, Namespace, Literal
from rdflib.namespace import RDF
import pyshacl

HERE = os.path.dirname(os.path.abspath(__file__))
EXPS = os.path.dirname(HERE)
EX = Namespace("http://ex.org/kg#")
LEVEL_GOV = URIRef("http://ex.org/kg#govLevel")
LEVEL_GEO = URIRef("http://ex.org/kg#geoLevel")
NODE = URIRef("http://ex.org/kg#Node")

GOV_LEVELS = [("国务院",1),("中央",1),("省",2),("自治区",2),("直辖市",2),("市",3),
              ("地级市",3),("州",3),("县",4),("区",4),("县级市",4),("乡",5),("镇",5),("街道",5)]
GEO_LEVELS = [("国家",1),("中国",1),("省",2),("自治区",2),("直辖市",2),("市",3),("地级市",3),
              ("州",3),("县",4),("区",4),("县级市",4),("乡",5),("镇",5),("街道",5),("村",6),("社区",6)]
INVALID_REL = {"NONE", "", "未知关系"}
# hierarchy conflict rules (from the evaluators' _check_*_hierarchy_conflicts)
GOV_DESC = {"管理", "领导"}     # conflict if subjLevel > objLevel
GOV_ASC  = {"隶属于"}           # conflict if subjLevel < objLevel
GEO_DESC = {"管辖", "包含"}     # conflict if subjLevel > objLevel
GEO_ASC  = {"位于", "属于"}     # conflict if subjLevel < objLevel

DOMAINS = [
    ("Government", "pol_evaluate",     "政务_低质量_nodes.csv", "政务_低质量_relationships.csv", "qa_gover_2"),
    ("Finance",    "finance_evaluate", "金融_低质量_nodes.csv", "金融_低质量_relationships.csv", "qa_finance_2"),
    ("Environment","env_evaluate",     "环境_低质量_nodes.csv", "环境_低质量_relationships.csv", "qa_environment_2"),
]


def load_module(name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(EXPS, name + ".py"))
    m = importlib.util.module_from_spec(spec); sys.modules[name] = m
    spec.loader.exec_module(m); return m


def level(name, table):
    for kw, lv in table:
        if kw in str(name):
            return lv
    return None


def node_uri(i): return EX[f"n{i}"]
def rel_uri(r): return EX[quote(str(r), safe="")]


SHAPES_TTL = """
@prefix sh: <http://www.w3.org/ns/shacl#> .
@prefix ex: <http://ex.org/kg#> .

ex:HierShape a sh:NodeShape ;
  sh:targetClass ex:Node ;
  sh:sparql [ a sh:SPARQLConstraint ;
    sh:message "hierarchy reversal" ;
    sh:prefixes ex: ;
    sh:select \"\"\"
      PREFIX ex: <http://ex.org/kg#>
      SELECT $this ?path ?value WHERE {
        $this ?path ?value .
        { $this ex:govLevel ?l1 . ?value ex:govLevel ?l2 .
          FILTER( (?path IN (ex:%s) && ?l1 > ?l2) || (?path IN (ex:%s) && ?l1 < ?l2) ) }
        UNION
        { $this ex:geoLevel ?l1 . ?value ex:geoLevel ?l2 .
          FILTER( (?path IN (ex:%s) && ?l1 > ?l2) || (?path IN (ex:%s) && ?l1 < ?l2) ) }
      } \"\"\" ] .
"""


def build_shapes():
    g = lambda S: ", ex:".join(quote(x, safe="") for x in S)
    ttl = SHAPES_TTL % (g(GOV_DESC), g(GOV_ASC), g(GEO_DESC), g(GEO_ASC))
    sg = Graph(); sg.parse(data=ttl, format="turtle"); return sg


def run_domain(name, modname, ncsv, rcsv, semdir):
    mod = load_module(modname)
    ndf = pd.read_csv(os.path.join(EXPS, ncsv), keep_default_na=False)
    rdf_in = pd.read_csv(os.path.join(EXPS, rcsv), keep_default_na=False)
    id2name = dict(zip(ndf["id"], ndf["name"]))

    # build RDF data graph (collapses exact-duplicate triples)
    dg = Graph()
    for nid, nm in id2name.items():
        u = node_uri(nid); dg.add((u, RDF.type, NODE))
        gl = level(nm, GOV_LEVELS); geol = level(nm, GEO_LEVELS)
        if gl is not None: dg.add((u, LEVEL_GOV, Literal(gl)))
        if geol is not None: dg.add((u, LEVEL_GEO, Literal(geol)))
    triple_key = {}   # (s_uri,p_uri,o_uri) -> (start_id, rel, end_id)
    for _, row in rdf_in.iterrows():
        s, p, o = node_uri(row["start_id"]), rel_uri(row["relation_type"]), node_uri(row["end_id"])
        dg.add((s, p, o))
        triple_key[(s, p, o)] = (row["start_id"], row["relation_type"], row["end_id"])

    n_rdf = len(triple_key)                       # unique triples after RDF dedup
    n_raw = len(rdf_in)

    # SHACL validation (pyshacl) — record conformance
    shapes = build_shapes()
    conforms, _, _ = pyshacl.validate(dg, shacl_graph=shapes, inference="none",
                                      advanced=True, abort_on_first=False)

    # identify violating triples via the SHACL-SPARQL constraint bodies (hierarchy)
    remove = set()
    q_hier = """PREFIX ex: <http://ex.org/kg#>
      SELECT ?s ?p ?o WHERE {
        ?s ?p ?o .
        {{ ?s ex:govLevel ?l1 . ?o ex:govLevel ?l2 .
           FILTER( (?p IN (ex:%s) && ?l1 > ?l2) || (?p IN (ex:%s) && ?l1 < ?l2) ) }}
        UNION
        {{ ?s ex:geoLevel ?l1 . ?o ex:geoLevel ?l2 .
           FILTER( (?p IN (ex:%s) && ?l1 > ?l2) || (?p IN (ex:%s) && ?l1 < ?l2) ) }}
      }""" % (", ex:".join(quote(x, safe="") for x in GOV_DESC),
              ", ex:".join(quote(x, safe="") for x in GOV_ASC),
              ", ex:".join(quote(x, safe="") for x in GEO_DESC),
              ", ex:".join(quote(x, safe="") for x in GEO_ASC))
    for s, p, o in dg.query(q_hier):
        if (s, p, o) in triple_key:
            remove.add((s, p, o))
    # relation-validity: predicate is an invalid relation type
    invalid_uris = {rel_uri(r) for r in INVALID_REL}
    for k in list(triple_key):
        if k[1] in invalid_uris:
            remove.add(k)

    # repaired triple set -> DataFrame for re-evaluation
    kept = [triple_key[k] for k in triple_key if k not in remove]
    rep = pd.DataFrame(kept, columns=["start_id", "relation_type", "end_id"])
    rep = rep[["start_id", "end_id", "relation_type"]]

    # re-evaluate with the SAME deterministic checkers
    ev = mod.KnowledgeGraphEvaluator({"output_dir": os.path.join(HERE, "_tmp"),
                                      "logical_rules": mod.CONFIG["logical_rules"]})
    ev.nodes = ndf.copy(); ev.relationships = rep.copy()
    iso, _ = ev.detect_isolated_nodes()
    red, _ = ev.detect_redundant_triples()
    log, _ = ev.check_logical_consistency()
    sem = json.load(open(os.path.join(EXPS, semdir, "quality_scores.json")))["semantic_score"]  # Exp2 S_sem (held)
    S = {"S_iso": round((1 - iso) * 100, 2), "S_red": round((1 - red) * 100, 2),
         "S_log": round((1 - log) * 100, 2), "S_sem": round(sem, 2)}
    Q = round(sum(S.values()) / 4, 2)
    out = {"domain": name, "n_raw": n_raw, "n_rdf_dedup": n_rdf, "n_removed_shacl": len(remove),
           "conforms": bool(conforms), **S, "Q_score": Q}
    print(out, flush=True)
    return out


def main():
    os.makedirs(os.path.join(HERE, "_tmp"), exist_ok=True)
    rows = [run_domain(*d) for d in DOMAINS]
    avg = round(sum(r["Q_score"] for r in rows) / len(rows), 2)
    res = {"rows": rows, "avg_Q": avg}
    json.dump(res, open(os.path.join(HERE, "shacl_results.json"), "w"), indent=2, ensure_ascii=False)
    print("\nSHACL-repair avg Q =", avg)


if __name__ == "__main__":
    main()
