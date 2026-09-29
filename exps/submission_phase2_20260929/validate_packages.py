"""Extract each draft source archive and compile without workspace dependencies."""
import concurrent.futures,hashlib,json,re,subprocess,tempfile,zipfile
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]

def validate(paper):
    archive=HERE/'packages'/f'{paper}_review_sources.zip'
    with tempfile.TemporaryDirectory(prefix=paper+'-phase2-') as tmp:
        dest=Path(tmp)
        with zipfile.ZipFile(archive) as z:
            assert all(not Path(n).is_absolute() and '..' not in Path(n).parts for n in z.namelist());z.extractall(dest)
        run=subprocess.run(['tectonic','-X','compile','main.tex','--only-cached','--keep-logs'],cwd=dest,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=180)
        log=run.stdout;(HERE/(paper+'_isolated_compile.log')).write_text('\n'.join(line.rstrip() for line in log.splitlines())+'\n')
        assert run.returncode==0,log[-1000:]
        faults=[line for line in log.splitlines() if re.search(r'Overfull|undefined references|Citation .* undefined|Reference .* undefined|^error:',line,re.I)]
        assert not faults,faults
        def plain(path):
            text=subprocess.check_output(['pdftotext','-layout',str(path),'-'],text=True);return re.sub(r'\s+',' ',text).strip()
        expected=plain(ROOT/paper/'main.pdf');actual=plain(dest/'main.pdf');assert expected==actual,'Independent PDF text differs'
        info=subprocess.check_output(['pdfinfo',str(dest/'main.pdf')],text=True)
        return dict(paper=paper,success=True,pages=int(re.search(r'Pages:\s+(\d+)',info).group(1)),text_sha256=hashlib.sha256(actual.encode()).hexdigest(),zip_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),missing_references_or_overfull=0,scope='Source-package compilation and text equality, not scientific or journal approval.')

if __name__=='__main__':
    with concurrent.futures.ThreadPoolExecutor(2) as pool:results=list(pool.map(validate,['paper1','paper2']))
    (HERE/'package_validation.json').write_text(json.dumps(results,indent=2)+'\n');print(json.dumps(results,indent=2))
