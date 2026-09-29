"""Create reviewable source/PDF packages with explicit, unfilled release gates.

Packages are review drafts until author metadata, journal requirements and
scientific gaps are resolved. Never archive the repository credentials file.
"""
import hashlib
import json
import re
import zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent


def build(paper):
    folder=ROOT/paper
    status={
        'paper':paper,'target':'DMKD' if paper=='paper1' else 'TKDE',
        'status':'review_draft_not_cleared_for_submission',
        'outstanding':(['Contract test collection remains incomplete (216/224 outcomes); no primary test result has been scored.',
                        'Independent human review of actual edits remains pending.',
                        'Confirm authors, affiliations, funding, conflicts and contributions.',
                        'Finalize scientific conclusions and main/supplement length after review.']
                       if paper=='paper1' else [
                        'Generated-rule learned scheduling remains unvalidated: no repair effects in the development pilot.',
                        'Independent rule/edit human verification has been deferred.',
                        'Confirm actual authors; current manuscript says Anonymous Authors.',
                        'Verify current TKDE page limit, anonymity and template requirements.',
                        'Resolve current template font fallback and compiler rerun warnings.']),
        'reproduce_pdf':'tectonic -X compile main.tex --only-cached --keep-logs',
        'environment':'Tectonic with a populated TeX resource cache; Times New Roman installed. Fonts are not redistributed.',
        'code_and_results':'https://github.com/turambar928/MCP_based_KG_construction',
        'scope':'Source and PDF manuscript review package. Experiment code and provenance are in the repository; this ZIP does not redistribute raw DocRED text.'}
    # Only manuscript source and assets. Exclude auxiliary output, historical
    # compiled drafts, credentials, hidden files and unrelated repository files.
    allowed={'.tex','.bib','.cls','.bst','.sty','.pdf','.svg','.png','.jpg','.jpeg','.eps','.csv','.dat'}
    files=[]
    for p in folder.rglob('*'):
        rel=p.relative_to(folder)
        if not p.is_file() or any(x.startswith('.') for x in rel.parts):continue
        if p.suffix.lower() not in allowed:continue
        if p.suffix=='.pdf' and len(rel.parts)==1 and p.name!='main.pdf':continue
        files.append(p)
    assert folder/'main.pdf' in files
    status['file_sha256']={str(p.relative_to(folder)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(files)}
    dest=HERE/'packages';dest.mkdir(exist_ok=True)
    target=dest/(paper+'_review_sources.zip')
    with zipfile.ZipFile(target,'w',compression=zipfile.ZIP_DEFLATED) as z:
        for p in sorted(files):z.write(p,str(p.relative_to(folder)))
        for name in [paper+'_cover_letter_draft.md','submission_author_checks_2026-09-29.md','journal_submission_audit_2026-09-29.md']:
            z.write(ROOT/'docs'/name,'submission_notes/'+name)
        z.writestr('REVIEW_STATUS.json',json.dumps(status,indent=2)+'\n')
        z.writestr('README.txt','REVIEW DRAFT — not yet cleared for submission.\nRead REVIEW_STATUS.json before use.\nCompile main.tex from this directory. See repository experiment READMEs for data and results.\n')
    (dest/(paper+'_status.json')).write_text(json.dumps(status,indent=2)+'\n')
    return dict(paper=paper,zip=str(target.relative_to(ROOT)),bytes=target.stat().st_size,
                sha256=hashlib.sha256(target.read_bytes()).hexdigest(),files=len(files),status=status['status'])


if __name__=='__main__':
    result=[build(p) for p in ['paper1','paper2']]
    (HERE/'packages/manifest.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
