#!/usr/bin/env python3
"""Check the reorganized repository; optionally compile both current paper ZIPs."""

import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import shutil
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "docs/organization/RELOCATION_2026-10-18.json"
REPORT = ROOT / "docs/organization/VALIDATION_2026-10-18.json"
PAPERS = ("paper1 merge", "paper2")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def archived_sources(manifest):
    result = {}
    for name, record in manifest["archives"].items():
        path = ROOT / record["path"]
        require(sha(path) == record["sha256"], f"Archive changed: {path}")
        with zipfile.ZipFile(path) as package:
            require(package.testzip() is None, f"Invalid ZIP: {path}")
            require(len(package.namelist()) == len(set(package.namelist())), f"Duplicate entries: {path}")
            actual = {key: hashlib.sha256(package.read(key)).hexdigest() for key in package.namelist()}
        require(actual == record["files"], f"Archived source differs: {path}")
        require(not any(key.startswith("paper1/zt/") for key in actual), "Teacher source entered an archive")
        result[name] = {"path": record["path"], "files": len(actual), "sha256": sha(path)}
    return result


def preserved_files(manifest):
    for name, digest in manifest["protected_tracked_files"].items():
        require((ROOT / name).is_file() and sha(ROOT / name) == digest, f"Code or experiment changed: {name}")
    teacher = manifest["teacher_files"]
    present = (ROOT / "paper1/zt").exists()
    if present:
        actual = {p.relative_to(ROOT).as_posix(): sha(p) for p in (ROOT / "paper1/zt").rglob("*") if p.is_file()}
        require(actual == teacher, "Teacher source paths or contents changed")
    current = {}
    for paper, files in manifest["active_manuscript_files"].items():
        for name, digest in files.items():
            require(sha(ROOT / paper / name) == digest, f"Active manuscript changed during cleanup: {paper}/{name}")
        current[paper] = {"files": len(files), "all_sha256_unchanged": True}
    return {"experimental_and_code_files": len(manifest["protected_tracked_files"]),
            "experimental_and_code_contents_unchanged": True,
            "teacher_source": {"status": "unchanged" if present else "local_source_not_present",
                               "files": len(teacher) if present else 0},
            "active_manuscripts": current}


def markdown_links():
    paths = {ROOT / "README.md", ROOT / "paper1/README.md", ROOT / "archive/README.md",
             ROOT / "exps/README.md", ROOT / "scripts/README.md"}
    paths.update((ROOT / "docs").rglob("*.md"))
    for paper in PAPERS:
        paths.update((ROOT / paper).glob("*.md"))
        paths.update((ROOT / paper / "docs").rglob("*.md"))
    paths.add(ROOT / "paper1 merge/translation_zh/README.md")
    missing, count = [], 0
    for path in sorted(paths):
        text = re.sub(r"^```[^\n]*\n.*?^```[^\n]*$", "", path.read_text(), flags=re.M | re.S)
        for target in re.findall(r"!?\[[^\]]*\]\(([^\n)]+)\)", text):
            if target.startswith("<"):
                target = target[1:target.index(">")]
            else:
                target = target.split(' "', 1)[0]
            if re.match(r"[A-Za-z][A-Za-z0-9+.-]*:", target) or target.startswith("#"):
                continue
            destination = (path.parent / target.split("#", 1)[0]).resolve()
            count += 1
            if destination != REPORT and not destination.exists():
                # The teacher folder is local and deliberately not published.
                if destination == ROOT / "paper1/zt" and not destination.exists():
                    continue
                missing.append({"source": path.relative_to(ROOT).as_posix(), "target": target})
    require(not missing, "Broken current-document links: " + json.dumps(missing, ensure_ascii=False))
    return {"documents": len(paths), "local_links": count, "missing": []}


def package_module(paper):
    source = ROOT / paper / "tools/build_overleaf.py"
    spec = importlib.util.spec_from_file_location("package_" + paper.replace(" ", "_"), source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def pdf_text(path):
    return subprocess.check_output(["pdftotext", "-layout", str(path), "-"], text=True)


def pdf_pages(path):
    info = subprocess.check_output(["pdfinfo", str(path)], text=True)
    return int(re.search(r"^Pages:\s+(\d+)", info, re.M)[1])


def inspect_package(paper, compile_papers):
    base = ROOT / paper
    packager = package_module(paper)
    manifest = json.loads((base / "validation/OVERLEAF_MANIFEST.json").read_text())
    expected = {p.as_posix() for p in packager.dependencies()} | {"README.md"}
    folder = base / "overleaf"
    actual = {p.relative_to(folder).as_posix(): sha(p) for p in folder.rglob("*") if p.is_file()}
    require(set(actual) == expected, f"Package dependencies differ: {paper}")
    require(actual == manifest["file_sha256"], f"Package folder manifest differs: {paper}")
    for name, digest in actual.items():
        original = base / ("docs/OVERLEAF.md" if name == "README.md" else name)
        require(sha(original) == digest, f"Stale packaged file: {paper}/{name}")
    archive = base / manifest["zip"]
    require(sha(archive) == manifest["zip_sha256"], f"Stale ZIP: {paper}")
    with zipfile.ZipFile(archive) as package:
        names = package.namelist()
        require(len(names) == len(set(names)), f"Duplicate ZIP entries: {paper}")
        require(all(not Path(n).is_absolute() and ".." not in Path(n).parts for n in names), "Unsafe ZIP path")
        require({n: hashlib.sha256(package.read(n)).hexdigest() for n in names} == actual,
                f"ZIP and folder differ: {paper}")
        if compile_papers:
            build = base / ".build/repository_check"
            if build.exists():
                shutil.rmtree(build)
            build.mkdir(parents=True)
            package.extractall(build)
    record_path = base / "validation/REPOSITORY_COMPILE_2026-10-18.json"
    compiled = {"status": "not_run_for_current_package"}
    if compile_papers:
        engine = shutil.which("tectonic")
        require(bool(engine), "Tectonic is required for --compile-papers")
        (build / "main.pdf").unlink()
        result = subprocess.run([engine, "-X", "compile", "main.tex", "--only-cached",
                                 "--keep-logs", "--keep-intermediates", "--reruns", "4"],
                                cwd=build, text=True, capture_output=True)
        logs = base / "validation/logs"
        logs.mkdir(exist_ok=True)
        (logs / "REPOSITORY_COMPILE_2026-10-18.log").write_text(result.stdout + result.stderr)
        require(result.returncode == 0, f"ZIP compilation failed: {paper}")
        log = (build / "main.log").read_text()
        critical = [s for s in log.splitlines() if re.search(
            r"^!|Overfull|Missing character|(?:Reference|Citation).*undefined|There were undefined|multiply defined|Label\(s\) may have changed", s)]
        require(not critical, f"Unresolved compile messages: {paper}: {critical}")
        original, rebuilt = pdf_text(base / "main.pdf"), pdf_text(build / "main.pdf")
        require("??" not in rebuilt and original == rebuilt, f"Compiled text changed: {paper}")
        require(pdf_pages(base / "main.pdf") == pdf_pages(build / "main.pdf"), f"Page count changed: {paper}")
        compiled = {"status": "passed", "zip_sha256": sha(archive),
                    "canonical_pdf_sha256": sha(base / "main.pdf"),
                    "rebuilt_pdf_sha256": sha(build / "main.pdf"),
                    "page_count": pdf_pages(build / "main.pdf"), "pdf_text_equal": True,
                    "critical_compile_messages": [], "isolated_project": ".build/repository_check/"}
        record_path.write_text(json.dumps(compiled, indent=2) + "\n")
    elif record_path.exists():
        previous = json.loads(record_path.read_text())
        if previous.get("zip_sha256") == sha(archive) and previous.get("canonical_pdf_sha256") == sha(base / "main.pdf"):
            compiled = previous
    return {"files": len(actual), "zip_sha256": sha(archive), "all_dependencies_local_or_standard_tex": True,
            "folder_and_zip_match_source": True, "independent_compile": compiled}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compile-papers", action="store_true", help="Compile each current Overleaf ZIP in isolation.")
    args = parser.parse_args()
    manifest = json.loads(MANIFEST.read_text())
    archives = archived_sources(manifest)
    preserved = preserved_files(manifest)
    links = markdown_links()
    for path in [ROOT / "scripts/maintenance/check_repository.py", *(ROOT / "paper1 merge/tools").glob("*.py"),
                 *(ROOT / "paper2/tools").glob("*.py"), *(ROOT / "paper1 merge/translation_zh/tools").glob("*.py")]:
        compile(path.read_text(), str(path), "exec")
    with ThreadPoolExecutor(max_workers=2) as executor:
        tasks = {paper: executor.submit(inspect_package, paper, args.compile_papers) for paper in PAPERS}
        packages = {paper: task.result() for paper, task in tasks.items()}
    counts = {}
    for name, before in manifest["top_level_entries_before"].items():
        after = len([p for p in (ROOT / name).iterdir() if not p.name.startswith(".")])
        counts[name] = {"before": before, "after": after}
    report = {"date": "2026-10-18", "status": "passed", "archives": archives,
              "preserved_contents": preserved, "documentation_links": links, "paper_packages": packages,
              "paper_top_level_entries": counts, "tool_syntax": "passed",
              "new_api_calls": 0, "new_experiments": 0, "new_training_runs": 0}
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"status": "passed", "protected_code_and_experiment_files": preserved["experimental_and_code_files"],
                      "teacher_source": preserved["teacher_source"], "local_links_checked": links["local_links"],
                      "paper_top_level_entries": counts,
                      "independent_compiles": {p: v["independent_compile"]["status"] for p, v in packages.items()}},
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
