"""Losslessly archive complete optimizer traces with deterministic gzip metadata."""
import gzip,hashlib,json
from pathlib import Path
HERE=Path(__file__).resolve().parent
raw=(HERE/'optimizer_traces.jsonl').read_bytes();assert len(raw.splitlines())==5850
z=HERE/'optimizer_traces.jsonl.gz'
with z.open('wb') as f:
    with gzip.GzipFile(fileobj=f,mode='wb',filename='',mtime=0) as g:g.write(raw)
assert gzip.decompress(z.read_bytes())==raw
(HERE/'trace_archive.json').write_text(json.dumps({'archive':z.name,'compression':'gzip, mtime=0','rows':len(raw.splitlines()),'uncompressed_sha256':hashlib.sha256(raw).hexdigest(),'compressed_sha256':hashlib.sha256(z.read_bytes()).hexdigest()},indent=2)+'\n')
print('Archived 5850 traces; uncompressed hash recorded.')
