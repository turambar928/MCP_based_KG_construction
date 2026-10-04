"""Paths, immutable artifacts and the independent development protocol."""
import hashlib
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
OLD = ROOT / 'exps/paper2_docred'
MODEL = 'google/gemma-4-26B-A4B-it'
ARMS = ('deletion', 'augmentation')
POLICIES = ('stop', 'acquire_then_repair', 'repair_asap', 'augmentation_first',
            'augmentation_first_asap', 'deletion_only', 'augmentation_only', 'uniform_feasible')
PROTOCOL = dict(
    version='independent-rule-feasibility-20261004-v1', model=MODEL,
    scope='New development feasibility study, controlled reference recovery; not a third round of the closed v2 protocol, not a natural-error or held-out policy test.',
    selection='First ten existing dev pairs in their frozen order with no document in any earlier DocRED pilot membership or response log; no replacement based on content or outcomes.',
    documents=20, episodes=10, nominal_responses=40, maximum_attempts_per_task=2,
    maximum_dispatch_intents=80, workers=1, request_spacing_seconds=3,
    connect_timeout_seconds=15, read_timeout_seconds=150,
    retry_http=[429, 500, 502, 503, 504], retry_wait_seconds=5,
    temperature=0, max_tokens=4000, max_rules=20, max_clauses=3,
    parser='One JSON object, optionally enclosed in a single complete json/markdown fence; duplicate keys and nonfinite numbers rejected. Entire object must satisfy schema. Valid-schema candidates additionally pass original vocabulary/quote compiler. No output-repair retries.',
    finish_reason='Only stop is accepted. Length, filter, unexpected model and malformed envelopes retain failed outcomes.',
    interruption='Persist dispatch intent before network I/O; unresolved intents become interrupted outcomes on resume and are never automatically resent. Unknown request delivery is reported separately.',
    outage='Stop after two consecutive transport/protocol failures; finalized outcomes are never rerun. Resume only untouched tasks.',
    construction='Existing v2 deterministic construction, seed v2:<document_id>; first document clean, second adds ceil(0.2*reference size) substitutions. Not natural error truth.',
    actions=['acquire_deletion', 'acquire_augmentation', 'repair', 'stop'], response_budget=4, horizon=10, discount=.95,
    environment='Unchanged paper2_docred_v2_round2.SourceRuleEnvironment; no trained checkpoints.',
    policies=list(POLICIES), random_policy_seed=20261004,
    gates=dict(min_valid_responses=36, min_source_repair_episodes=2,
               min_mean_preservation=.99, min_unique_injected_per_strategy=1,
               max_single_bank_correct_losses=0, min_oracle_headroom_pp=.5,
               min_mean_oracle_acquisition_saving=1., min_cost_saving_episodes=2),
    gate_logic='All outputs finalized, >=36 valid-schema outputs, and ONE same deterministic fixed schedule improves mean F1, preserves >=99% reference facts and has source-necessary injected removals in >=2 episodes (same pre-edit state without source contradiction rules no longer flags these records). Each strategy must uniquely remove >=1 injected item under single-bank replay with no reference loss. Finally either safe oracle F1 headroom >=0.5pp above best deterministic schedule, or same-quality per-episode safe oracle mean saving >=1 packet in >=2 episodes.',
    oracle='Scorer-only post-hoc bound; labels never guide generation or deployed policies. Oracle cost savings are not demonstrated achievable savings.',
    uncertainty='Ten document-pair units, descriptive paired bootstrap with seed 20261004 and 10000 draws for every fixed-schedule difference from stop; no confirmatory superiority claim or outcome-driven arm selection.',
    failure_branch='Retain the single batch and all failures. No sample substitution, prompt retuning, third-round relabeling, automatic formal training or calls to old formal runner.',
    success_branch='Feasibility for a separately frozen formal protocol only; independent semantic review remains pending, not inferred from quotes or reference matching.',
    deferred_formal_design='DDQN/DQN from scratch versus fixed and budget-matched adaptive controls; jointly report F1, preservation, acquired packets and seed variation. Training sources/budgets and primary tests must be frozen separately before formal work.',
)


def read(path):
    return json.loads(Path(path).read_text())


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def write_once(path, value):
    path = Path(path)
    data = (json.dumps(value, indent=2, ensure_ascii=False) + '\n').encode()
    if path.exists():
        if path.read_bytes() != data:
            raise ValueError('Frozen artifact differs: ' + str(path))
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('xb') as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())


def read_events(path):
    path = Path(path)
    if not path.exists():
        return []
    try:
        return [json.loads(line) for line in path.read_text().splitlines()]
    except (ValueError, UnicodeError) as err:
        raise ValueError('Journal incomplete/corrupt; preserve it for manual recovery, do not resend tasks') from err


def append_event(path, event):
    with Path(path).open('a') as f:
        f.write(json.dumps(event, ensure_ascii=False) + '\n')
        f.flush()
        os.fsync(f.fileno())
