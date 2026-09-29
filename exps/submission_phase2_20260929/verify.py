"""Verify preserved historical files and append-only experiment outcomes."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent

def verify():
    frozen=json.loads((HERE/'preservation.json').read_text());prefix=json.loads((HERE/'append_only.json').read_text())
    changed=[p for p,h in frozen.items() if not (ROOT/p).is_file() or hashlib.sha256((ROOT/p).read_bytes()).hexdigest()!=h]
    bad_prefix=[]
    for p,meta in prefix.items():
        data=(ROOT/p).read_bytes()
        if len(data)<meta['bytes'] or hashlib.sha256(data[:meta['bytes']]).hexdigest()!=meta['sha256']:bad_prefix.append(p)
    result=dict(protected_files=len(frozen),changed_protected_files=changed,append_only_files=len(prefix),changed_prefixes=bad_prefix)
    (HERE/'verification.json').write_text(json.dumps(result,indent=2)+'\n')
    assert not changed and not bad_prefix,result
    print(json.dumps(result,indent=2))

if __name__=='__main__':verify()
