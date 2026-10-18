#!/usr/bin/env python3
"""Check the Chinese reading PDF against the complete English source."""

from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import subprocess

HERE = Path(__file__).resolve().parents[1]
SOURCE = HERE.parent
VALIDATION = HERE / "validation"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def clean(text):
    return re.sub(r"(?<!\\)%[^\n]*", "", text)


def normalized_math(text):
    text = re.sub(r"\\text\{[^{}]*\}", r"\\text{LABEL}", text)
    return re.sub(r"\s+", "", text)


def tokens(text, command):
    return Counter(re.findall(r"\\" + command + r"\{([^}]+)\}", clean(text)))


def page_count(path):
    info = subprocess.check_output(["pdfinfo", str(path)], text=True)
    return int(re.search(r"^Pages:\s+(\d+)", info, re.M)[1])


def verify():
    manifest = json.loads((VALIDATION / "SOURCE_MANIFEST.json").read_text())
    assert sha(SOURCE / "main.pdf") == manifest["source_pdf_sha256"]
    for name, digest in manifest["source_files_sha256"].items():
        assert sha(SOURCE / name) == digest, "English source changed: " + name
    display = re.compile(r"\\begin\{(equation\*?|align\*?)\}.*?\\end\{\1\}|\\\[.*?\\\]", re.S)
    inline = re.compile(r"(?<!\\)\$(?:\\.|[^$])*?\$")
    table = re.compile(r"\\begin\{(tabular\*?|tabularx)\}.*?\\end\{\1\}", re.S)
    all_source, all_zh = [], []
    records = {}
    counts = Counter()
    for source in sorted((SOURCE / "sections").glob("*.tex")):
        target = HERE / "sections" / source.name
        old, new = clean(source.read_text()), clean(target.read_text())
        all_source.append(old)
        all_zh.append(new)
        old_display = [normalized_math(m.group()) for m in display.finditer(old)]
        new_display = [normalized_math(m.group()) for m in display.finditer(new)]
        assert old_display == new_display, (source.name, "display equations")
        old_inline = Counter(normalized_math(m.group()) for m in inline.finditer(old))
        new_inline = Counter(normalized_math(m.group()) for m in inline.finditer(new))
        assert old_inline == new_inline, (source.name, "inline math", old_inline-new_inline, new_inline-old_inline)
        old_tables, new_tables = list(table.finditer(old)), list(table.finditer(new))
        assert len(old_tables) == len(new_tables)
        for i, (left, right) in enumerate(zip(old_tables, new_tables)):
            numbers = lambda s: re.findall(r"[-+]?\d+(?:\.\d+)?", s)
            assert numbers(left.group()) == numbers(right.group()), (source.name, "table numbers", i)
        for command in ["label", "ref", "citep", "citet", "cite", "includegraphics"]:
            if command == "includegraphics":
                pattern = r"\\includegraphics(?:\[[^]]*\])?\{([^}]+)\}"
                assert Counter(re.findall(pattern, old)) == Counter(re.findall(pattern, new))
            else:
                assert tokens(old, command) == tokens(new, command), (source.name, command)
        structure = r"\\(section|subsection|subsubsection|paragraph)\*?\{"
        assert Counter(re.findall(structure, old)) == Counter(re.findall(structure, new))
        environments = r"\\begin\{(figure\*?|table\*?|algorithm)\}"
        assert Counter(re.findall(environments, old)) == Counter(re.findall(environments, new))
        records[source.name] = {"source_sha256": sha(source), "translation_sha256": sha(target),
                                "display_equations": len(old_display), "inline_expressions": sum(old_inline.values()),
                                "tables": len(old_tables), "formulas_and_table_values_preserved": True,
                                "headings_labels_citations_and_figures_preserved": True}
        counts.update({"display_equations": len(old_display), "inline_expressions": sum(old_inline.values()), "tables": len(old_tables)})
    assert (HERE / "references.bib").read_bytes() == (SOURCE / "references.bib").read_bytes()
    source_text, zh_text = "\n".join(all_source), "\n".join(all_zh)
    counts["figures"] = len(re.findall(r"\\includegraphics", source_text))
    counts["algorithms"] = len(re.findall(r"\\begin\{algorithm\}", source_text))
    labels = set(re.findall(r"\\label\{([^}]+)\}", zh_text))
    legend = (HERE / "figure_text_zh.tex").read_text()
    legend_refs = re.findall(r"\\ref\{([^}]+)\}", legend)
    assert len(legend_refs) == counts["figures"] and set(legend_refs) <= labels
    pdf = SOURCE / "main_zh.pdf"
    text = subprocess.check_output(["pdftotext", "-layout", str(pdf), "-"], text=True)
    assert "??" not in text
    for heading in ["摘要", "引言", "相关工作", "任务与方法", "实现", "实验评价", "结论", "声明", "参考文献", "补充实验", "图中文字对照"]:
        assert heading in text, heading
    assert "利用源文本与字段检查修复文档知识图谱" in text.split("\f")[0]
    assert not any(not re.sub(r"[\s\d]", "", page) for page in text.split("\f") if page.strip())
    build = SOURCE / ".build/translation_zh/manuscript"
    engine_log = (build / "main.log").read_text()
    critical = [line for line in engine_log.splitlines() if re.search(
        r"^!|Overfull|Missing character|(?:Reference|Citation).*undefined|There were undefined|multiply defined|Label\(s\) may have changed", line)]
    assert not critical, critical
    bbl = (build / "main.bbl").read_text()
    bibitems = lambda s: re.findall(r"\\bibitem\[.*?\]\{([^}]+)\}", s, re.S)
    assert bibitems(bbl) == manifest["bibliography_keys_in_source_order"]
    counts["references"] = len(bibitems(bbl))
    visual_path = VALIDATION / "VISUAL_REVIEW.json"
    visual = json.loads(visual_path.read_text()) if visual_path.exists() else {"status": "pending"}
    if visual.get("status") == "passed":
        assert visual["pdf_sha256"] == sha(pdf), "Visual review is stale"
    report = {"status": "passed", "source_pdf_sha256": manifest["source_pdf_sha256"],
              "source_pdf_pages": manifest["source_pages"], "translation_pdf_sha256": sha(pdf),
              "translation_pdf_pages": page_count(pdf), "content_counts": dict(counts),
              "sections": records, "figure_text_translations": len(legend_refs),
              "bibliographic_metadata_preserved": True, "english_sources_unchanged": True,
              "critical_compile_messages": critical,
              "visual_review": visual,
              "method": "Source-unit review; exact formula, table-number, label, citation and figure checks; cached XeTeX compilation",
              "new_api_calls": 0, "new_experiments": 0}
    (VALIDATION / "VALIDATION.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"status": report["status"], "pages": report["translation_pdf_pages"], "content_counts": dict(counts)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    verify()
