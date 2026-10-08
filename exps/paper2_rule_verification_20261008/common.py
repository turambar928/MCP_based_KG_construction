"""Single frozen automatic-review study; no training or independent human labels."""
from pathlib import Path
from exps.paper2_rule_feasibility_20261004.common import (
    ROOT, read, sha, digest, write_once, read_events, append_event, POLICIES,
    PROTOCOL as BASE_PROTOCOL)
HERE = Path(__file__).resolve().parent
STUDY = ROOT / 'exps/paper2_rule_feasibility_20261004'
MODEL = 'Qwen3.8-27B-no-thinking'
VERSION = 'episode-scoped-automatic-review-20261008-v1'
MODES = ('grounded', 'independent_empty', 'schema', 'automatic', 'combined')
PROTOCOL = dict(BASE_PROTOCOL, version=VERSION, model=MODEL, max_tokens=6000,
    scope='Post-hoc development-cache automatic rule review, not independent human validation or held-out evaluation.',
    selection='All 407 compiled occurrences in the frozen 20-document cache; one request per nonempty packet, no outcome-based sampling.',
    nominal_responses=38, maximum_dispatch_intents=80, modes=list(MODES),
    parser='Strict per-candidate, per-record automatic review JSON; exact target-document quotes; no duplicate keys, missing or extra records; whole output rejects on failure.',
    schema_policy='Use traceable hard constraints only with sound DocRED type mapping and exceptions accounted for; otherwise uncertain. Names alone never authorize a rule.',
    automatic_policy='Review every candidate and all initial matching records in its immutable document pair; all checks must approve with exact source evidence. No-match, insufficient evidence, malformed output or conflict abstains.',
    combination='Any rejection vetoes; otherwise schema approval or automatic approval admits; uncertainty alone is not a rejection.',
    interpretation='Type compatibility is not factual support; source absence is not contradiction. Initial episode records only shrink under the unchanged executor.',
    output_failure='Reject entire output on schema/cardinality/quote failure; no model repair calls.',
    outage='Persist stop latch after two consecutive final transport/protocol failures or any model mismatch. No automatic resume after outage.',
    failure_branch='One batch only; no prompt retuning, replacement documents, extra models or automatic training.',
    schema_gate_note='Report 38-task review schema success separately; the old >=36/40 generation gate remains a historical generation check, not a new review threshold.',
    random_policy_seed=20261004)
