"""Check recursive update contents and reproduce the reported missing-table repair."""
from pathlib import Path
import hashlib
import importlib.util
import json
import re
import shutil
import subprocess
import tempfile
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
BASE = ROOT / 'paper2'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def main():
    spec = importlib.util.spec_from_file_location('full_export', ROOT / 'exports/overleaf_2026-10-02/build_packages.py')
    exporter = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(exporter)
    with zipfile.ZipFile(HERE / 'paper2_sections_update.zip') as archive:
        contents = {n: archive.read(n) for n in archive.namelist()}
    manifest = json.loads(contents['CONTENT_MANIFEST.json'])['tex_sha256']
    assert 'main.tex' not in contents
    assert all(n.startswith(('sections/', 'tables/')) for n in manifest)
    for name, expected in manifest.items():
        assert digest(contents[name]) == expected
        assert contents[name] == (BASE / name).read_bytes()
    with tempfile.TemporaryDirectory(prefix='paper2-dependency-repair-') as tmp:
        dest = Path(tmp)
        # Supply only the existing project resources not carried by the update.
        for relative in exporter.dependencies(BASE):
            if relative.as_posix() in manifest:
                continue
            (dest / relative).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(BASE / relative, dest / relative)
        for name in manifest:
            (dest / name).parent.mkdir(parents=True, exist_ok=True)
            (dest / name).write_bytes(contents[name])
        missing = dest / 'tables/offline_loop_ceiling.tex'
        missing.unlink()
        try:
            exporter.dependencies(dest)
        except FileNotFoundError as err:
            assert 'offline_loop_ceiling' in str(err)
        else:
            raise AssertionError('Missing dependency was not detected')
        with zipfile.ZipFile(HERE / 'paper2_missing_table_fix.zip') as archive:
            assert set(archive.namelist()) == {'tables/offline_loop_ceiling.tex', 'README.md'}
            missing.write_bytes(archive.read('tables/offline_loop_ceiling.tex'))
        assert exporter.dependencies(dest) == exporter.dependencies(BASE)
        assert (dest / 'main.tex').read_bytes() == (BASE / 'main.tex').read_bytes()
        engine = shutil.which('tectonic') or str(Path.home() / '.local/bin/tectonic')
        run = subprocess.run([engine, '-X', 'compile', 'main.tex', '--only-cached', '--keep-logs'],
                             cwd=dest, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=240)
        log = '\n'.join(line.rstrip() for line in run.stdout.splitlines()) + '\n'
        (HERE / 'dependency_compile.log').write_text(log.replace(tmp, '<isolated-content-repair>'))
        assert run.returncode == 0, log[-2500:]
        problems = [line for line in log.splitlines() if re.search(
            r'Overfull|undefined references|Citation .* undefined|Reference .* undefined|Missing character|^error:', line, re.I)]
        assert not problems, problems
        info = subprocess.check_output(['pdfinfo', str(dest / 'main.pdf')], text=True)
        report = dict(scope='Updated ZIP content dependency check and isolated local compilation; user Overleaf template not accessed.',
                      tex_files_checked=len(manifest), main_tex_excluded_from_updates=True,
                      missing_table_detected_before_repair=True, minimal_fix_restores_dependency=True,
                      all_dependencies_resolve=True, compile_success=True,
                      undefined_references_citations_or_overfull=0,
                      local_original_template_pages=int(re.search(r'Pages:\s+(\d+)', info)[1]),
                      model_api_requests=0,
                      zip_sha256={n: digest((HERE / n).read_bytes()) for n in
                                  ['paper2_sections_update.zip', 'paper2_missing_table_fix.zip']})
    (HERE / 'dependency_validation.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
