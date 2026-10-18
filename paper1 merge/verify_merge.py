#!/usr/bin/env python3
"""Verify the merge and optionally compile the extracted Overleaf ZIP."""

import argparse
import ast
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import zipfile

from build_overleaf import ARCHIVE_NAME, dependencies, uncomment

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DATE = "2026-10-12"
SECTIONS = {"abstract.tex", "introduction.tex", "related_work.tex", "methodology.tex",
            "experiments.tex", "conclusion.tex", "declarations.tex", "appendix.tex"}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def pdf_text(path):
    return subprocess.check_output(["pdftotext", "-layout", str(path), "-"], text=True)


def pdf_pages(path):
    info = subprocess.check_output(["pdfinfo", str(path)], text=True)
    return int(re.search(r"^Pages:\s+(\d+)", info, re.M)[1])


def log_check(engine_log):
    source = engine_log.read_text()
    critical = [line for line in source.splitlines()
                if re.search(r"^!|Overfull|Missing character|(?:Reference|Citation) .* undefined|"
                             r"There were undefined|multiply defined|Label\(s\) may have changed", line)]
    check(not critical, f"Unresolved compile messages in {engine_log}: {critical}")
    return {"critical_messages": critical, "log_sha256": sha(engine_log)}


def protected_sources():
    manifest = json.loads((HERE / f"SOURCE_MANIFEST_{DATE}.json").read_text())
    result = {}
    for group, expected in manifest["protected_file_sha256"].items():
        current = {p.relative_to(ROOT).as_posix(): sha(p)
                   for p in (ROOT / group).rglob("*") if p.is_file()}
        missing = sorted(expected.keys() - current.keys())
        added = sorted(current.keys() - expected.keys())
        changed = sorted(p for p in current.keys() & expected.keys() if current[p] != expected[p])
        check(not missing and not added and not changed, f"Protected directory changed: {group}")
        result[group] = {"files": len(current), "missing": missing, "added": added,
                         "changed": changed, "unchanged": True}
    return result


def source_checks():
    baseline = ROOT / "paper1" / "overleaf"
    unchanged = ["main.tex", "sn-jnl.cls", "sn-basic.bst", "references.bib", "latexmkrc",
                 "sections/experiments.tex", "sections/appendix.tex", "sections/declarations.tex"]
    unchanged += [p.relative_to(baseline).as_posix()
                  for p in (baseline / "figure").rglob("*") if p.is_file()]
    for name in unchanged:
        check((HERE / name).read_bytes() == (baseline / name).read_bytes(), f"Changed baseline file: {name}")
    number_re = r"(?<![A-Za-z_])[-+]?\d+(?:\.\d+)?(?![A-Za-z_])"
    numbers = {}
    for name in ("abstract.tex", "conclusion.tex"):
        new = re.findall(number_re, uncomment((HERE / "sections" / name).read_text()))
        old = re.findall(number_re, uncomment((baseline / "sections" / name).read_text()))
        check(new == old, f"Numeric tokens changed: {name}")
        numbers[name] = new
    actual = {p.name for p in (HERE / "sections").glob("*.tex")}
    check(actual == SECTIONS, "The chapter file set differs from the agreed 8 files")
    main = uncomment((HERE / "main.tex").read_text())
    inputs = re.findall(r"\\input\{sections/([^}]+)\}", main)
    check({n + ".tex" for n in inputs} == SECTIONS and len(inputs) == 8, "Main chapter inputs differ")
    chapter_sources = {p.name: uncomment(p.read_text()) for p in (HERE / "sections").glob("*.tex")}
    for name, source in chapter_sources.items():
        check(not re.search(r"\\(?:input|include)\s*\{", source), f"Nested chapter inputs in {name}")
    text = main + "\n" + "\n".join(chapter_sources.values())
    labels = re.findall(r"\\label\{([^}]+)\}", text)
    repeated = sorted(k for k, n in Counter(labels).items() if n > 1)
    refs = set(re.findall(r"\\(?:ref|eqref|autoref|pageref)\*?\{([^}]+)\}", text))
    check(not repeated, f"Duplicate labels: {repeated}")
    check(not refs - set(labels), f"Undefined labels: {refs - set(labels)}")
    bib = set(re.findall(r"@\w+\s*\{\s*([^,]+),", (HERE / "references.bib").read_text()))
    citations = {k.strip() for g in re.findall(r"\\cite\w*\*?(?:\[[^]]*\])*\{([^}]+)\}", text)
                 for k in g.split(",")}
    check(not citations - bib, f"Undefined citations: {citations - bib}")
    methodology = chapter_sources["methodology.tex"]
    headings = re.findall(r"\\section\{([^}]+)\}", methodology)
    check(headings == ["Task and Method", "Implementation"], "Method chapters differ")
    check("neural decision" not in text.lower(), "Old generic routing name remains")
    return {"unchanged_baseline_sha256": {n: sha(HERE / n) for n in unchanged},
            "abstract_conclusion_numeric_tokens": numbers, "section_files": sorted(actual),
            "unique_labels": len(labels), "defined_reference_targets": len(refs),
            "defined_citation_keys": len(citations), "nested_inputs": 0}, set(labels)


def teacher_and_guides(labels):
    teacher = ROOT / "paper1" / "zt" / "method.tex"
    lines = [i for i, s in enumerate(teacher.read_text().splitlines(), 1) if s.lstrip().startswith("%")]
    mapping = (HERE / f"TEACHER_MERGE_{DATE}.md").read_text()
    mapped = [int(n) for n in re.findall(r"^\| (\d+) \|", mapping, re.M)]
    check(sorted(lines) == sorted(mapped), "Teacher comment coverage differs")
    for name in ("MATHEMATICS.md", "EXPERIMENTS.md", f"TEACHER_MERGE_{DATE}.md"):
        source = (HERE / name).read_text()
        anchors = set(re.findall(r"`((?:sec|eq|alg|tab|fig|app):[^`]+)`", source))
        check(not anchors - labels, f"Stale anchors in {name}: {anchors - labels}")
        for link in re.findall(r"\]\(([^)]+)\)", source):
            if re.match(r"[A-Za-z][A-Za-z0-9+.-]*:", link):
                continue
            target = HERE / link.split("#")[0]
            if target == HERE / f"MERGE_VALIDATION_{DATE}.json":
                continue  # This invocation produces the linked report.
            check(target.exists(), f"Missing guide link in {name}: {link}")
    return {"source": str(teacher.relative_to(ROOT)), "comment_lines": lines,
            "mapped_comment_count": len(mapped), "all_comments_mapped": True,
            "guide_and_mapping_anchors_defined": True, "local_links_exist": True}


def code_checks():
    optimizer_path = ROOT / "content_enhancement" / "constraint_optimizer_v2.py"
    tree = ast.parse(optimizer_path.read_text())
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "MultiScaleConstraintOptimizer")
    init = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == "__init__")
    defaults = dict(zip([a.arg for a in init.args.args][-len(init.args.defaults):],
                        [ast.literal_eval(v) for v in init.args.defaults]))
    expected = {"tau_repair": 0.05, "tau_dup": 0.92, "beta": 0.35, "eta": 0.05,
                "hard_reward": 0.20, "confidence_weight": 0.02, "max_iterations": 12}
    check(all(defaults[k] == v for k, v in expected.items()), "Optimizer defaults differ from method text")
    costs_node = next(n.value for n in init.body if isinstance(n, ast.Assign) and
                      any(isinstance(t, ast.Attribute) and t.attr == "costs" for t in n.targets))
    costs = ast.literal_eval(costs_node)
    check((costs["delete"], costs["retype"], costs["add"]) == (0.30, 0.16, 0.06), "Edit costs differ")
    train_path = ROOT / "exps" / "math_revision_20260925" / "paper1" / "router" / "train.py"
    train_tree = ast.parse(train_path.read_text())
    constants = {}
    for node in train_tree.body:
        if isinstance(node, ast.Assign):
            try:
                value = ast.literal_eval(node.value)
            except (ValueError, TypeError):
                continue
            for target in node.targets:
                if isinstance(target, ast.Name):
                    constants[target.id] = value
                elif isinstance(target, ast.Tuple):
                    constants.update(zip((item.id for item in target.elts), value))
    d, h1, h2, scopes = len(constants["FEATURES"]), constants["H1"], constants["H2"], len(constants["SCALES"])
    params = d * h1 + h1 + h1 * h2 + h2 + h2 + 1 + h2 * scopes + scopes
    check((d, h1, h2, scopes, params, constants["LAMBDA"]) == (8, 32, 16, 3, 884, 1.0), "Router shape or loss weight differs")
    files = [optimizer_path, train_path,
             ROOT / "exps/math_revision_20260925/paper1/study.py",
             ROOT / "exps/decision_network/build_from_repair_benchmark.py",
             ROOT / "exps/paper1_mechanism_audit/replay_optimizer.py"]
    return {"optimizer_defaults": expected, "edit_costs": {k: costs[k] for k in ("delete", "retype", "add")},
            "network_dimensions": [d, h1, h2], "network_parameters": params,
            "training_loss_weight": constants["LAMBDA"],
            "reviewed_code_sha256": {p.relative_to(ROOT).as_posix(): sha(p) for p in files},
            "verification": "Static source checks and prose review; no experiment or training runs"}


def english_review():
    result = {}
    for name in ("abstract.tex", "introduction.tex", "related_work.tex", "methodology.tex", "conclusion.tex"):
        source = uncomment((HERE / "sections" / name).read_text())
        source = re.sub(r"\\begin\{(equation|figure|algorithm)\}.*?\\end\{\1\}", "", source, flags=re.S)
        source = re.sub(r"\\(?:cite\w*|label|ref)\*?(?:\[[^]]*\])*\{[^}]*\}", "", source)
        source = re.sub(r"\$[^$]*\$", " MATH ", source)
        source = re.sub(r"\\\w+\{([^{}]*)\}", r"\1", source)
        sentences = re.split(r"(?<=[.!?])\s+", re.sub(r"\s+", " ", source))
        counts = [len(re.findall(r"\b[A-Za-z]+(?:[-'][A-Za-z]+)*\b", s)) for s in sentences if s.strip()]
        result[name] = {"sentences": len(counts), "max_prose_words": max(counts),
                        "sentences_over_30_words": sum(n > 30 for n in counts)}
    return result


def package_checks(compile_zip, tectonic):
    manifest = json.loads((HERE / "OVERLEAF_MANIFEST.json").read_text())
    archive = HERE / ARCHIVE_NAME
    check(sha(archive) == manifest["zip_sha256"], "ZIP digest differs from manifest")
    expected = {p.as_posix() for p in dependencies()} | {"README.md"}
    folder = HERE / "overleaf"
    current = {p.relative_to(folder).as_posix(): sha(p) for p in folder.rglob("*") if p.is_file()}
    check(set(current) == expected, "Package file set differs from local dependency set")
    check(current == manifest["file_sha256"], "Folder hashes differ from package manifest")
    for name in current:
        original = HERE / ("OVERLEAF_README.md" if name == "README.md" else name)
        check(sha(original) == current[name], f"Stale packaged file: {name}")
    with zipfile.ZipFile(archive) as package:
        names = package.namelist()
        check(len(names) == len(set(names)), "Duplicate ZIP entries")
        zipped = {name: hashlib.sha256(package.read(name)).hexdigest() for name in names}
        check(zipped == current, "ZIP content differs from folder")
        check(all(not Path(n).is_absolute() and ".." not in Path(n).parts for n in names), "Unsafe ZIP path")
        if compile_zip:
            build = HERE / ".build" / "zip"
            if build.exists():
                shutil.rmtree(build)
            build.mkdir(parents=True)
            package.extractall(build)
    record_path = HERE / f"ZIP_REBUILD_CHECK_{DATE}.json"
    if compile_zip:
        check(bool(tectonic), "Tectonic is required for --compile-zip")
        (build / "main.pdf").unlink()
        completed = subprocess.run([tectonic, "-X", "compile", "main.tex", "--only-cached",
                                    "--keep-logs", "--keep-intermediates", "--reruns", "4"],
                                   cwd=build, capture_output=True, text=True)
        (HERE / f"ZIP_COMPILE_{DATE}.log").write_text(completed.stdout + completed.stderr)
        check(completed.returncode == 0, "Extracted ZIP compilation failed; see ZIP_COMPILE log")
        engine = log_check(build / "main.log")
        canonical = pdf_text(HERE / "main.pdf")
        rebuilt = pdf_text(build / "main.pdf")
        check(canonical == rebuilt, "Independent ZIP PDF text differs from canonical manuscript")
        check(pdf_pages(HERE / "main.pdf") == pdf_pages(build / "main.pdf"), "PDF page count differs")
        record = {"zip_sha256": sha(archive), "canonical_pdf_sha256": sha(HERE / "main.pdf"),
                  "rebuilt_pdf_sha256": sha(build / "main.pdf"), "page_count": pdf_pages(build / "main.pdf"),
                  "pdf_text_equal": True, "pdf_text_sha256": hashlib.sha256(rebuilt.encode()).hexdigest(),
                  "compiler": "Tectonic 0.15.0 (XeTeX engine), cached standard TeX packages",
                  "isolated_project": ".build/zip/", "engine_log_check": engine}
        write_json(record_path, record)
    record = json.loads(record_path.read_text())
    check(record["zip_sha256"] == sha(archive) and record["canonical_pdf_sha256"] == sha(HERE / "main.pdf"),
          "Independent compilation record is stale; rerun with --compile-zip")
    return {"files": len(current), "zip_sha256": sha(archive), "folder_matches_source": True,
            "zip_matches_folder": True, "all_dependencies_local_or_standard_tex": True,
            "independent_compile": record}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compile-zip", action="store_true")
    parser.add_argument("--report-date", default=DATE,
                        help="Date suffix of the visual review and output report (YYYY-MM-DD).")
    parser.add_argument("--tectonic", default=shutil.which("tectonic"))
    args = parser.parse_args()
    protected = protected_sources()
    sources, labels = source_checks()
    teacher = teacher_and_guides(labels)
    code = code_checks()
    package = package_checks(args.compile_zip, args.tectonic)
    compiled = {}
    for name, folder in (("main", "manuscript"), ("MATHEMATICS", "guides"), ("EXPERIMENTS", "guides")):
        path = HERE / (name + ".pdf")
        text = pdf_text(path)
        check("??" not in text, f"Unresolved reference marker in {name}.pdf")
        compiled[name] = {"sha256": sha(path), "pages": pdf_pages(path),
                          "final_engine_log": log_check(HERE / ".build" / folder / (name + ".log"))}
    visual_path = HERE / f"VISUAL_REVIEW_{args.report_date}.json"
    visual = json.loads(visual_path.read_text()) if visual_path.exists() else {"status": "pending"}
    if visual.get("status") == "passed":
        for name, digest in visual["reviewed_pdf_sha256"].items():
            check(sha(HERE / name) == digest, f"Visual check is stale: {name}")
    write_json(HERE / f"MERGE_VALIDATION_{args.report_date}.json", {
        "date": args.report_date, "merge_source_date": DATE,
        "status": "内容定稿待作者确认", "protected_sources": protected,
        "source_checks": sources, "teacher_comment_coverage": teacher, "method_code_checks": code,
        "edited_english_review": english_review(), "compiled_pdfs": compiled,
        "overleaf_package": package, "visual_review": visual,
        "new_api_calls": 0, "new_experiments": 0, "new_training_runs": 0, "new_annotations": 0,
    })
    print(json.dumps({"protected_files_unchanged": sum(v["files"] for v in protected.values()),
                      "teacher_comments": teacher["mapped_comment_count"],
                      "overleaf_files": package["files"], "independent_zip_compile": True,
                      "pdf_pages": {n: v["pages"] for n, v in compiled.items()},
                      "visual_review": visual["status"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
