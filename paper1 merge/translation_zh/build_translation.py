#!/usr/bin/env python3
"""Build the complete Chinese translation of the frozen merged Paper1."""

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent
BLOCK = re.compile(r"\S[^\n]*(?:\n(?!\s*\n)[^\n]*)*")
DISPLAY = re.compile(r"\\begin\{(equation\*?|align\*?)\}.*?\\end\{\1\}|\\\[.*?\\\]", re.S)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_tsv(name):
    return dict(line.split("\t", 1) for line in (HERE / name).read_text().splitlines() if line.strip())


def without_comments(text):
    return re.sub(r"(?<!\\)%[^\n]*", "", text)


def command_contents(text, names, translations):
    pattern = r"\\(?:" + "|".join(names) + r")\*?\{"
    changes = []
    for match in re.finditer(pattern, text):
        start = match.end()
        pos, depth = start, 1
        while depth:
            if text[pos] == "{" and text[pos - 1] != "\\":
                depth += 1
            elif text[pos] == "}" and text[pos - 1] != "\\":
                depth -= 1
            pos += 1
        content = text[start:pos - 1]
        key = re.sub(r"\s+", " ", content).strip()
        if re.search(r"[\u4e00-\u9fff]", content):
            continue
        if key not in translations:
            raise ValueError("Missing heading/caption translation: " + key)
        changes.append((start, pos - 1, translations[key]))
    for start, end, translated in reversed(changes):
        text = text[:start] + translated + text[end:]
    return text


def apply_terms(text, terms):
    saved = []
    def protect(match):
        saved.append(match.group())
        return f"@@@{len(saved)-1}@@@"
    # Keep symbols, identifiers, references and paths intact.
    protected = re.compile(DISPLAY.pattern + r"|(?<!\\)\$(?:\\.|[^$])*?\$|"
                           r"\\(?:label|ref|cite\w*|texttt|includegraphics|url)"
                           r"(?:\[[^]]*\])?\{[^{}]*\}", re.S)
    text = protected.sub(protect, text)
    pattern = re.compile(r"(?<![A-Za-z0-9_])(?:" + "|".join(
        re.escape(term) for term in sorted(terms, key=len, reverse=True)) + r")(?![A-Za-z0-9_])")
    text = pattern.sub(lambda match: terms[match.group()], text)
    return re.sub(r"@@@(\d+)@@@", lambda match: saved[int(match[1])], text)


def prepare():
    manifest = json.loads((HERE / "SOURCE_MANIFEST.json").read_text())
    assert sha(SOURCE / "main.pdf") == manifest["source_pdf_sha256"]
    for name, digest in manifest["source_files_sha256"].items():
        assert sha(SOURCE / name) == digest, "Source changed: " + name
    translations = {}
    for path in sorted(HERE.glob("prose_*.txt")):
        parts = re.split(r"^@@ (\S+)\s*\n", path.read_text(), flags=re.M)
        for i in range(1, len(parts), 2):
            assert parts[i] not in translations
            translations[parts[i]] = parts[i + 1].strip()
    headings, captions, terms = (read_tsv(name) for name in ("headings.tsv", "captions.tsv", "terms.tsv"))
    used, counts = set(), {}
    (HERE / "sections").mkdir(exist_ok=True)
    for path in sorted((SOURCE / "sections").glob("*.tex")):
        source = path.read_text()
        def translate_block(match):
            number = translate_block.index
            translate_block.index += 1
            key = f"{path.stem}.{number:03d}"
            original = match.group()
            if key not in translations:
                first = original.splitlines()[0]
                assert first.startswith(("\\", "%", "}")) or "&" in original, "Missing prose: " + key
                return original
            used.add(key)
            translated = translations[key]
            equations = [m.group() for m in DISPLAY.finditer(original)]
            for i, equation in enumerate(equations):
                placeholder = f"[[EQ:{i}]]"
                assert translated.count(placeholder) == 1, key + " equation placeholder"
                translated = translated.replace(placeholder, equation)
            assert "[[EQ:" not in translated
            # Keep explicit numeric values; allow spelling a source number as digits.
            old = without_comments(original)
            new = without_comments(translated)
            old_numbers = set(re.findall(r"\d+(?:\.\d+)?", old))
            new_numbers = set(re.findall(r"\d+(?:\.\d+)?", new))
            words = "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen twenty".split()
            spelled = {str(i) for i, word in enumerate(words) if re.search(r"\b" + word + r"\b", old, re.I)}
            spelled |= {str(i) for word, i in {"thirty": 30, "forty": 40, "fifty": 50, "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90}.items() if re.search(r"\b" + word + r"\b", old, re.I)}
            assert old_numbers <= new_numbers and new_numbers <= old_numbers | spelled, (key, "numbers", old_numbers-new_numbers, new_numbers-old_numbers-spelled)
            old_math = re.findall(r"(?<!\\)\$(?:\\.|[^$])*?\$", old)
            new_math = re.findall(r"(?<!\\)\$(?:\\.|[^$])*?\$", new)
            assert Counter(old_math) == Counter(new_math), (key, "inline math")
            return translated
        translate_block.index = 0
        translated = BLOCK.sub(translate_block, source)
        translated = command_contents(translated, ["section", "subsection", "subsubsection", "paragraph"], headings)
        translated = command_contents(translated, ["caption"], captions)
        translated = apply_terms(translated, terms)
        for old, new in [(r"\text{ occurs in }", r"\text{ 出现在 }"),
                         (r"\text{delete}", r"\text{删除}"),
                         (r"\text{retype}", r"\text{改关系}"),
                         (r"\text{add}", r"\text{添加}"),
                         (r"\text{duplicate}", r"\text{重复}"),
                         (r"\text{failed check}", r"\text{未通过检查}")]:
            translated = translated.replace(old, new)
        (HERE / "sections" / path.name).write_text(translated)
        counts[path.name] = sum(key.startswith(path.stem + ".") for key in used)
    assert used == translations.keys(), "Unused translations: " + str(translations.keys() - used)
    for name in ["sn-jnl.cls", "sn-basic.bst", "references.bib"]:
        shutil.copy2(SOURCE / name, HERE / name)
    cls = HERE / "sn-jnl.cls"
    class_text = cls.read_text().replace("Corresponding author(s). E-mail(s):", "通讯作者及邮箱：")
    class_text = class_text.replace("Contributing authors:", "其他作者邮箱：")
    cls.write_text(class_text)
    for path in (SOURCE / "figure").rglob("*.pdf"):
        target = HERE / path.relative_to(SOURCE)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
    main = (SOURCE / "main.tex").read_text()
    main = main.replace("Repairing Document Knowledge Graphs with Source Text and Field Checks", "利用源文本与字段检查修复文档知识图谱")
    main = main.replace("These authors contributed equally to this work.", "以上作者对本文贡献相同。")
    main = main.replace("China Mobile System Integration Co. Ltd.", "中移系统集成有限公司")
    main = main.replace("Tongji University", "同济大学").replace("Xi'an Jiaotong University", "西安交通大学")
    main = main.replace(r"\country{China}", r"\country{中国}")
    fonts = r"""
\usepackage{fontspec}
\setmainfont{Noto Serif CJK SC}[SmallCapsFont={Noto Serif CJK SC},ItalicFont={Noto Serif CJK SC},ItalicFeatures={FakeSlant=0.15},BoldItalicFont={Noto Serif CJK SC Bold},BoldItalicFeatures={FakeSlant=0.15}]
\setsansfont{Noto Sans CJK SC}
\setmonofont{Noto Sans Mono CJK SC}[Scale=0.85]
\XeTeXlinebreaklocale "zh"
\XeTeXlinebreakskip=0pt plus 1pt
\setlength{\emergencystretch}{3em}
\setlength{\bibsep}{0.7em}
\renewcommand{\figurename}{图}
\renewcommand{\tablename}{表}
\renewcommand{\refname}{参考文献}
\renewcommand{\appendixname}{附录}
\renewcommand{\abstractname}{摘要}
\def\keywordname{关键词}
\floatname{algorithm}{算法}
\algrenewcommand{\algorithmicrequire}{输入：}
\algrenewcommand{\algorithmicensure}{输出：}
\algrenewcommand{\algorithmicfor}{对}
\algrenewcommand{\algorithmicdo}{执行}
\algrenewcommand{\algorithmicif}{若}
\algrenewcommand{\algorithmicthen}{则}
\algrenewcommand{\algorithmicelse}{否则}
\algrenewcommand{\algorithmicend}{结束}
\algrenewcommand{\algorithmicreturn}{返回}
"""
    main = main.replace(r"\usepackage{algpseudocode}", r"\usepackage{algpseudocode}" + "\n" + fonts)
    main = re.sub(r"(?m)^\\maketitle\s*$", lambda _: r"\maketitle" + "\n" + r"\begin{center}\footnotesize 中文完整译本，对应英文合并版。参考文献保留原始出版信息；模型标识与程序名称保留原文。图内英文标注的中文对照见译文附页。\end{center}", main)
    main = main.replace(r"\input{sections/appendix}", r"\input{sections/appendix}" + "\n" + r"\input{figure_text_zh}")
    (HERE / "main.tex").write_text(main)
    (HERE / "TRANSLATION_COVERAGE.json").write_text(json.dumps({
        "source_pdf_sha256": manifest["source_pdf_sha256"], "translated_units": len(used),
        "translated_units_by_file": counts, "all_prose_units_accounted_for": True,
        "unit_numbers_and_inline_math_preserved": True,
        "heading_translations": len(headings), "caption_translations": len(captions),
        "term_translations": len(terms)}, ensure_ascii=False, indent=2) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepare-only", action="store_true")
    args = parser.parse_args()
    prepare()
    if args.prepare_only:
        return
    engine = shutil.which("tectonic")
    if not engine:
        parser.error("Tectonic is required")
    build = SOURCE / ".build" / "translation_zh" / "manuscript"
    build.mkdir(parents=True, exist_ok=True)
    for path in HERE.rglob("*"):
        if path.is_file() and (path.suffix in (".tex", ".cls", ".bst", ".bib") or path.suffix == ".pdf" and "figure" in path.parts):
            target = build / path.relative_to(HERE)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)
    result = subprocess.run([engine, "-X", "compile", "main.tex", "--only-cached", "--keep-logs", "--keep-intermediates", "--reruns", "4"], cwd=build, capture_output=True, text=True)
    (HERE / "COMPILE.log").write_text(result.stdout + result.stderr)
    if result.returncode:
        raise RuntimeError(result.stdout + result.stderr)
    shutil.copy2(build / "main.pdf", SOURCE / "main_zh.pdf")
    print(SOURCE / "main_zh.pdf")


if __name__ == "__main__":
    main()
