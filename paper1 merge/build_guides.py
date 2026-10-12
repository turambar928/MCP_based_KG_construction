#!/usr/bin/env python3
"""Build selected reader-document PDFs within this merged paper folder."""

import argparse
import json
import math
from pathlib import Path
import shutil
import subprocess
import unicodedata

HERE = Path(__file__).resolve().parent


def display_length(value):
    if isinstance(value, dict):
        if value.get("t") == "Str":
            return sum(2 if unicodedata.east_asian_width(c) in "WF" else 1
                       for c in value["c"])
        if value.get("t") in ("Code", "Math"):
            return len(value["c"][1])
        return display_length(value.get("c", []))
    if isinstance(value, list):
        return sum(map(display_length, value))
    return 0


def format_ast(value):
    if isinstance(value, dict):
        if value.get("t") == "Table":
            _, _, columns, head, bodies, foot = value["c"]
            rows = head[1] + [row for body in bodies for row in body[2] + body[3]] + foot[1]
            weights = []
            for i in range(len(columns)):
                lengths = sorted(display_length(row[1][i][-1]) for row in rows)
                typical = lengths[min(len(lengths) - 1, math.floor(len(lengths) * 0.8))]
                weights.append(max(8, typical) ** 0.7)
            total = sum(weights)
            value["c"][2] = [[col[0], {"t": "ColWidth", "c": w / total}]
                              for col, w in zip(columns, weights)]
        elif value.get("t") == "Code":
            code = value["c"][1]
            if not any(c in code for c in "{}\\\n"):
                return {"t": "RawInline", "c": ["latex", "\\nolinkurl{" + code + "}"]}
        return {k: format_ast(v) for k, v in value.items()}
    if isinstance(value, list):
        return [format_ast(v) for v in value]
    return value


def run(args, **kwargs):
    return subprocess.run(args, check=True, text=True, capture_output=True, **kwargs)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    bundled_pandoc = Path("/tmp/papers-markdown-tools/pypandoc/files/pandoc")
    parser.add_argument("--pandoc", default=shutil.which("pandoc") or
                        (str(bundled_pandoc) if bundled_pandoc.is_file() else None))
    parser.add_argument("--tectonic", default=shutil.which("tectonic"))
    parser.add_argument("--names", nargs="+",
                        choices=("MATHEMATICS", "EXPERIMENTS", "VERSION_COMPARISON_AND_MERGE"),
                        default=("MATHEMATICS", "EXPERIMENTS"))
    args = parser.parse_args()
    if not args.pandoc or not args.tectonic:
        parser.error("Pandoc and Tectonic are required; provide their executable paths.")
    build = HERE / ".build" / "guides"
    build.mkdir(parents=True, exist_ok=True)
    for name in args.names:
        source = HERE / (name + ".md")
        ast = json.loads(run([args.pandoc, str(source), "-f", "markdown", "-t", "json"]).stdout)
        title = source.read_text().splitlines()[0].lstrip("# ")
        latex = run([args.pandoc, "-f", "json", "-t", "latex", "--standalone",
                     "--template", str(HERE / "guide_pdf.latex"), "-M", "title=" + title],
                    input=json.dumps(format_ast(ast))).stdout
        tex = build / (name + ".tex")
        tex.write_text(latex)
        result = subprocess.run([args.tectonic, "-X", "compile", str(tex),
                                 "--only-cached", "--keep-logs"],
                                cwd=build, text=True, capture_output=True)
        log = result.stdout + result.stderr
        (HERE / (name + "_COMPILE_2026-10-12.log")).write_text(log)
        if result.returncode:
            raise RuntimeError(log)
        shutil.copy2(build / (name + ".pdf"), HERE / (name + ".pdf"))
        print(source.with_suffix(".pdf"))


if __name__ == "__main__":
    main()
