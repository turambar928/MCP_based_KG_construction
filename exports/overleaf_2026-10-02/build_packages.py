"""Export the two current manuscripts without changing their working sources.

Run from any directory: python3 exports/overleaf_2026-10-02/build_packages.py
Only Python's standard library is required. No API or network access is used.
"""
import hashlib
import json
from pathlib import Path
import re
import subprocess
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
FONT_CONFIG = r"""% Export-only compatibility settings; select XeLaTeX in Overleaf.
\newcommand{\OverleafTermesFont}{%
  \setmainfont{texgyretermes}[
    Path=fonts/,
    Extension=.otf,
    UprightFont=*-regular,
    BoldFont=*-bold,
    ItalicFont=*-italic,
    BoldItalicFont=*-bolditalic]
}
% The override is used only by the isolated fallback compilation test.
\ifdefined\OverleafForceFallback
  \OverleafTermesFont
\else
  \IfFontExistsTF{Times New Roman}{%
    \setmainfont{Times New Roman}%
  }{%
    \OverleafTermesFont
  }
\fi
"""


def uncomment(text):
    return re.sub(r"(?<!\\)%[^\n]*", "", text)


def dependencies(base):
    """Follow this repository's literal TeX inputs and PDF graphics."""
    found = set()
    graphic_dirs = [Path('.'), Path('figure')]

    def add(name, extension='', required=True):
        relative = Path(name)
        if not relative.suffix and extension:
            relative = relative.with_suffix(extension)
        path = (base / relative).resolve()
        if not path.is_relative_to(base.resolve()):
            raise ValueError(f'External dependency: {relative}')
        if not path.is_file():
            if required:
                raise FileNotFoundError(path)
            return
        if relative in found:
            return
        found.add(relative)
        if relative.suffix != '.tex':
            return
        source = uncomment(path.read_text())
        for target in re.findall(r'\\(?:input|include)\s*\{([^}]+)\}', source):
            add(target, '.tex')
        for target in re.findall(r'\\includegraphics\*?(?:\[[^]]*\])?\s*\{([^}]+)\}', source):
            candidates = [d / target for d in graphic_dirs]
            if not Path(target).suffix:
                candidates = [p.with_suffix('.pdf') for p in candidates]
            match = next((p for p in candidates if (base / p).is_file()), None)
            if match is None:
                raise FileNotFoundError(target)
            add(str(match))
        for targets in re.findall(r'\\bibliography\s*\{([^}]+)\}', source):
            for target in targets.split(','):
                add(target.strip(), '.bib')
        for command, extension in [('documentclass', '.cls'), ('usepackage', '.sty'),
                                   ('bibliographystyle', '.bst')]:
            for targets in re.findall(r'\\' + command + r'(?:\[[^]]*\])?\s*\{([^}]+)\}', source):
                for target in targets.split(','):
                    add(target.strip(), extension, required=False)

    add('main.tex')
    # sn-jnl selects this bibliography style through its sn-basic class option.
    if (base / 'sn-jnl.cls').exists():
        add('sn-basic.bst')
    return sorted(found)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def build(paper):
    base = ROOT / paper
    files = {p.as_posix(): (base / p).read_bytes() for p in dependencies(base)}
    sources = {name: digest(data) for name, data in files.items()}
    if paper == 'paper2':
        old = b'\\setmainfont{Times New Roman}'
        assert files['main.tex'].count(old) == 1
        files['main.tex'] = files['main.tex'].replace(old, b'\\input{overleaf-fonts}')
        files['overleaf-fonts.tex'] = FONT_CONFIG.encode()
        for path in sorted((HERE / 'fonts').iterdir()):
            files['fonts/' + path.name] = path.read_bytes()
    files['latexmkrc'] = b"# XeLaTeX + BibTeX; also select XeLaTeX in Overleaf settings.\n$pdf_mode = 5;\n"
    files['README_Overleaf.md'] = (HERE / 'README.md').read_bytes()
    # Inspect text only and never print any matching credential.
    for name, data in files.items():
        if Path(name).suffix in {'.tex', '.bib', '.md', '.txt', '.cls', '.bst'}:
            if re.search(rb'sk-[A-Za-z0-9_-]{24,}', data):
                raise ValueError(f'Possible credential in {name}; export aborted')
    manifest = {
        'paper': paper,
        'source_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'compiler': 'XeLaTeX',
        'main_document': 'main.tex',
        'original_source_sha256': sources,
        'export_file_sha256': {name: digest(data) for name, data in sorted(files.items())},
        'export_only_changes': (['main.tex: replace fixed body font with overleaf-fonts.tex',
                                 'Prefer Times New Roman; otherwise use bundled TeX Gyre Termes']
                                if paper == 'paper2' else []),
    }
    files['EXPORT_MANIFEST.json'] = (json.dumps(manifest, indent=2) + '\n').encode()
    archive = HERE / f'{paper}_overleaf.zip'
    with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for name, data in sorted(files.items()):
            info = zipfile.ZipInfo(name, date_time=(2026, 10, 2, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            z.writestr(info, data)
    return {'paper': paper, 'archive': archive.name, 'files': len(files),
            'bytes': archive.stat().st_size, 'sha256': digest(archive.read_bytes())}


if __name__ == '__main__':
    print(json.dumps([build(p) for p in ['paper1', 'paper2']], indent=2))
