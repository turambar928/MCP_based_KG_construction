"""Validate isolated exports with the cached XeTeX-based Tectonic engine."""
import concurrent.futures
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
TECTONIC = shutil.which('tectonic') or str(Path.home() / '.local/bin/tectonic')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def plain(pdf):
    text = subprocess.check_output(['pdftotext', '-layout', str(pdf), '-'], text=True)
    return re.sub(r'\s+', ' ', text).strip()


def validate(case):
    paper, fallback = case
    name = paper + ('_fallback' if fallback else '')
    archive = HERE / f'{paper}_overleaf.zip'
    with tempfile.TemporaryDirectory(prefix=name + '-overleaf-') as tmp:
        dest = Path(tmp)
        with zipfile.ZipFile(archive) as z:
            assert len(z.namelist()) == len(set(z.namelist()))
            assert all(not Path(n).is_absolute() and '..' not in Path(n).parts for n in z.namelist())
            z.extractall(dest)
        manifest = json.loads((dest / 'EXPORT_MANIFEST.json').read_text())
        expected_files = set(manifest['export_file_sha256']) | {'EXPORT_MANIFEST.json'}
        assert expected_files == {p.relative_to(dest).as_posix() for p in dest.rglob('*') if p.is_file()}
        for filename, digest in manifest['export_file_sha256'].items():
            assert sha((dest / filename).read_bytes()) == digest, filename
        for filename, digest in manifest['original_source_sha256'].items():
            original = (ROOT / paper / filename).read_bytes()
            assert sha(original) == digest, f'Original changed: {filename}'
            expected = original
            if paper == 'paper2' and filename == 'main.tex':
                expected = original.replace(b'\\setmainfont{Times New Roman}', b'\\input{overleaf-fonts}')
            assert (dest / filename).read_bytes() == expected, f'Export content changed: {filename}'
        if fallback:
            main = dest / 'main.tex'
            main.write_text(main.read_text().replace(r'\input{overleaf-fonts}',
                                                     r'\def\OverleafForceFallback{1}\input{overleaf-fonts}'))
        run = subprocess.run([TECTONIC, '-X', 'compile', 'main.tex', '--only-cached', '--keep-logs'],
                             cwd=dest, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                             text=True, timeout=240)
        output = '\n'.join(line.rstrip() for line in run.stdout.splitlines()) + '\n'
        (HERE / f'{name}_compile.log').write_text(output.replace(tmp, '<isolated-export>'))
        assert run.returncode == 0, output[-3000:]
        faults = [line for line in output.splitlines()
                  if re.search(r'Overfull|undefined references|Citation .* undefined|Reference .* undefined|^error:|Missing character', line, re.I)]
        assert not faults, faults
        pdf = dest / 'main.pdf'
        actual = plain(pdf)
        if not fallback:
            assert actual == plain(ROOT / paper / 'main.pdf'), 'Export text differs from existing manuscript PDF'
        fonts = subprocess.check_output(['pdffonts', str(pdf)], text=True)
        if fallback:
            assert 'TeXGyreTermes' in fonts, 'Fallback font not used'
        (HERE / f'{name}_fonts.txt').write_text(fonts)
        # Preserve local preview PDFs outside the import ZIPs.
        shutil.copy2(pdf, HERE / f'{name}_preview.pdf')
        info = subprocess.check_output(['pdfinfo', str(pdf)], text=True)
        return {
            'case': name, 'success': True,
            'pages': int(re.search(r'Pages:\s+(\d+)', info).group(1)),
            'zip_sha256': sha(archive.read_bytes()),
            'source_hashes_and_export_changes_verified': True,
            'matches_existing_pdf_text': True if not fallback else None,
            'forced_fallback_font_verified': fallback,
            'missing_references_citations_characters_or_overfull': 0,
            'warnings': sorted(set(line for line in output.splitlines() if line.startswith('warning:'))),
        }


if __name__ == '__main__':
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(validate, [('paper1', False), ('paper2', False), ('paper2', True)]))
    report = {
        'scope': 'Isolated local Tectonic/XeTeX compilation, not hosted Overleaf testing or journal compliance review.',
        'engine': subprocess.check_output([TECTONIC, '--version'], text=True).strip(),
        'results': results,
    }
    (HERE / 'validation.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
