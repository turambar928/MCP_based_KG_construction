#!/usr/bin/env python3
"""Compile the merged manuscript in its own build directory with cached Tectonic."""

import argparse
from pathlib import Path
import shutil
import subprocess

from build_overleaf import dependencies

HERE = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tectonic", default=shutil.which("tectonic"))
    parser.add_argument("--log-date", default="2026-10-12",
                        help="Date suffix for the compile log (YYYY-MM-DD).")
    args = parser.parse_args()
    if not args.tectonic:
        parser.error("Tectonic is required; provide its executable path.")
    build = HERE / ".build" / "manuscript"
    if build.exists():
        shutil.rmtree(build)
    build.mkdir(parents=True)
    for rel in dependencies():
        if rel.name == "main.pdf":
            continue
        target = build / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(HERE / rel, target)
    result = subprocess.run([args.tectonic, "-X", "compile", "main.tex",
                             "--only-cached", "--keep-logs", "--keep-intermediates",
                             "--reruns", "4"], cwd=build, text=True, capture_output=True)
    log = result.stdout + result.stderr
    (HERE / f"MANUSCRIPT_COMPILE_{args.log_date}.log").write_text(log)
    if result.returncode:
        raise RuntimeError(log)
    shutil.copy2(build / "main.pdf", HERE / "main.pdf")
    print(HERE / "main.pdf")


if __name__ == "__main__":
    main()
