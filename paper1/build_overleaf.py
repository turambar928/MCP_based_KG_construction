"""Build this paper's clean Overleaf folder and ZIP using local source files."""

import hashlib
import json
from pathlib import Path
import re
import shutil
import zipfile


HERE = Path(__file__).resolve().parent


def uncomment(source):
    return re.sub(r"(?<!\\)%[^\n]*", "", source)


def dependencies():
    found = set()

    def add(name, suffix="", required=True):
        path = Path(name)
        if not path.suffix and suffix:
            path = path.with_suffix(suffix)
        target = (HERE / path).resolve()
        if not target.is_relative_to(HERE):
            raise ValueError(f"Dependency outside the paper: {name}")
        if not target.is_file():
            if required:
                raise FileNotFoundError(target)
            return
        if path in found:
            return
        found.add(path)
        if path.suffix != ".tex":
            return
        source = uncomment(target.read_text())
        for name in re.findall(r"\\(?:input|include)\s*\{([^}]+)\}", source):
            add(name, ".tex")
        for name in re.findall(r"\\includegraphics\*?(?:\[[^]]*\])?\s*\{([^}]+)\}", source):
            candidates = [Path(name), Path("figure") / name]
            if not Path(name).suffix:
                candidates = [p.with_suffix(s) for p in candidates for s in (".pdf", ".png", ".jpg")]
            match = next((p for p in candidates if (HERE / p).is_file()), None)
            if match is None:
                raise FileNotFoundError(f"Missing figure: {name}")
            add(match)
        for names in re.findall(r"\\bibliography\s*\{([^}]+)\}", source):
            for name in names.split(","):
                add(name.strip(), ".bib")
        for command, suffix in (("documentclass", ".cls"), ("usepackage", ".sty"),
                                ("bibliographystyle", ".bst")):
            for names in re.findall(r"\\" + command + r"(?:\[[^]]*\])?\s*\{([^}]+)\}", source):
                for name in names.split(","):
                    add(name.strip(), suffix, required=False)

    add("main.tex")
    if (HERE / "sn-jnl.cls").is_file():
        add("sn-basic.bst")
    for name in ("main.pdf", "latexmkrc"):
        add(name)
    if (HERE / "fonts").is_dir():
        for font in (HERE / "fonts").iterdir():
            if font.is_file():
                add(font.relative_to(HERE))
    return sorted(found)


def build():
    dest = HERE / "overleaf"
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir()
    for path in dependencies():
        target = dest / path
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(HERE / path, target)
    shutil.copy2(HERE / "OVERLEAF_README.md", dest / "README.md")
    files = sorted(p for p in dest.rglob("*") if p.is_file())
    archive = HERE / f"{HERE.name}_overleaf.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as output:
        for path in files:
            name = path.relative_to(dest).as_posix()
            info = zipfile.ZipInfo(name, date_time=(2026, 10, 10, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            output.writestr(info, path.read_bytes())
    report = {
        "paper": HERE.name,
        "folder": "overleaf/",
        "zip": archive.name,
        "main_document": "main.tex",
        "compiler": "XeLaTeX",
        "section_files": sorted(p.name for p in (dest / "sections").glob("*.tex")),
        "file_sha256": {
            p.relative_to(dest).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in files
        },
        "zip_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
    }
    (HERE / "OVERLEAF_MANIFEST.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"folder": str(dest), "zip": str(archive), "files": len(files)}, indent=2))


if __name__ == "__main__":
    build()
