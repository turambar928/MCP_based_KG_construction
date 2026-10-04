"""Build template-preserving updates with recursive literal TeX inputs."""
from pathlib import Path
import hashlib
import json
import re
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
BASE = ROOT / 'paper2'
SECTIONS = ('abstract', 'introduction', 'methodology', 'experiments', 'conclusion', 'appendix')


def content_dependencies():
    found = set()
    def visit(name):
        path = Path(name)
        if not path.suffix:
            path = path.with_suffix('.tex')
        absolute = (BASE / path).resolve()
        if not absolute.is_relative_to(BASE.resolve()) or path.suffix != '.tex' or path == Path('main.tex'):
            raise ValueError(f'Unexpected content dependency: {name}')
        if path in found:
            return
        source = absolute.read_text()
        found.add(path)
        source = re.sub(r'(?<!\\)%[^\n]*', '', source)
        for child in re.findall(r'\\(?:input|include)\s*\{([^}]+)\}', source):
            visit(child)
    for section in SECTIONS:
        visit(f'sections/{section}.tex')
    return sorted(found)


def write_zip(name, files):
    with zipfile.ZipFile(HERE / name, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for path, data in sorted(files.items()):
            info = zipfile.ZipInfo(path, date_time=(2026, 10, 4, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, data)


def main():
    files = {str(p): (BASE / p).read_bytes() for p in content_dependencies()}
    hashes = {p: hashlib.sha256(data).hexdigest() for p, data in files.items()}
    files['README.md'] = (HERE / 'README.md').read_bytes()
    files['content_changes.patch'] = (HERE / 'content_changes.patch').read_bytes()
    files['CONTENT_MANIFEST.json'] = (json.dumps(dict(
        scope='Six revised sections and recursive TeX inputs; existing template, bibliography and figures required.',
        tex_sha256=hashes), indent=2) + '\n').encode()
    write_zip('paper2_sections_update.zip', files)
    table = 'tables/offline_loop_ceiling.tex'
    write_zip('paper2_missing_table_fix.zip', {table: files[table], 'README.md': (
        '# Overleaf 最小修复\n\n'
        '只需把 tables/offline_loop_ceiling.tex 上传到项目根目录的 tables 文件夹，保持文件名不变。'
        '然后选择 Recompile from scratch。无需更改 main.tex、编译器或模板。\n\n'
        '这是前一更新包漏带的表格；原章节内容不需要再次替换。'
        '若完整编译后引用仍未定义，再检查 references.bib 与文献命令。Underfull 是排版警告。\n'
    ).encode()})
    print(json.dumps({'tex_files': len(hashes), 'contains_required_table': table in hashes}, indent=2))


if __name__ == '__main__':
    main()
