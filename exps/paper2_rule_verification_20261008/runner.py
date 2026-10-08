"""Explicit collect command only; durable request accounting and Qwen-only transport."""
import argparse
import datetime
import fcntl
import json
import os
from pathlib import Path
import re
import sys
import time
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from exps.paper2_rule_verification_20261008.common import HERE, MODEL, PROTOCOL, read, digest, read_events, append_event
from exps.paper2_rule_verification_20261008.prepare import freeze, verify


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def credentials():
    key, url = os.getenv('PAPER2_API_KEY'), os.getenv('PAPER2_BASE_URL')
    if not key and not url:
        text = (ROOT / 'apis').read_text()
        keys = set(re.findall(r'sk-[A-Za-z0-9_-]+', text))
        urls = set(re.findall(r'https?://[^\s\x27\x22<>]+', text))
        if len(keys) != 1 or len(urls) != 1:
            raise ValueError('Ambiguous API configuration; set PAPER2_API_KEY and PAPER2_BASE_URL explicitly')
        key, url = next(iter(keys)), next(iter(urls))
    if not key or not url:
        raise ValueError('Both API environment variables are required')
    url = url.rstrip('/')
    parsed = urlsplit(url)
    if parsed.scheme not in ('http', 'https') or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path not in ('', '/v1'):
        raise ValueError('Expected API origin or /v1 base URL, without credentials or query string')
    return key, url if url.endswith('/v1') else url + '/v1'


def transport(payload, auth, client):
    if payload.get('model') != MODEL:
        raise ValueError('Only the frozen Qwen model may be requested; no model fallback')
    key, url = auth
    start = time.perf_counter()
    result = dict(status='transport_error', retryable=False, http_status=None, returned_model=None,
                  finish_reason=None, usage=None, raw_response='')
    try:
        response = client.post(url + '/chat/completions', headers={'Authorization': 'Bearer ' + key}, json=payload)
        result['http_status'] = response.status_code
        if response.status_code != 200:
            result['retryable'] = response.status_code in PROTOCOL['retry_http']
        else:
            body = response.json()
            result['returned_model'] = body.get('model')
            result['usage'] = body.get('usage')
            if result['returned_model'] != MODEL:
                result['status'] = 'model_mismatch'
            else:
                choice = body['choices'][0]
                result['finish_reason'] = choice.get('finish_reason')
                content = choice.get('message', {}).get('content')
                result['raw_response'] = content if isinstance(content, str) else ''
                if result['finish_reason'] != 'stop':
                    result['status'] = 'incomplete_output'
                elif not result['raw_response'].strip():
                    result['status'] = 'empty_output'
                else:
                    result['status'] = 'ok'
    except Exception as err:
        # Never write exception messages, request headers, endpoints, or keys.
        import httpx
        result['status'] = 'transport_error' if isinstance(err, httpx.TransportError) else 'response_protocol_error'
        result['retryable'] = isinstance(err, httpx.TransportError)
        result['error_type'] = type(err).__name__
    result['latency_seconds'] = time.perf_counter() - start
    return result


def states(events, tasks):
    expected = {t['task_id']: digest(t['request']) for t in tasks}
    if len(expected) != len(tasks):
        raise ValueError('Duplicate tasks')
    rows = {}
    for event in events:
        tid = event.get('task_id')
        if tid not in expected or event.get('request_sha256') != expected[tid]:
            raise ValueError('Unexpected task or request hash in journal')
        row = rows.setdefault(tid, dict(started=[], finished=[], outcome=None))
        if row['outcome'] is not None:
            raise ValueError('Journal changed after final outcome')
        kind = event.get('kind')
        if kind == 'attempt_started':
            if len(row['started']) != len(row['finished']) or event['attempt'] != len(row['started']) + 1 or event['attempt'] > 2:
                raise ValueError('Invalid or duplicate request attempt')
            row['started'].append(event)
        elif kind == 'attempt_finished':
            if len(row['started']) != len(row['finished']) + 1 or event['attempt'] != len(row['started']):
                raise ValueError('Unmatched request completion')
            row['finished'].append(event)
        elif kind == 'outcome':
            if not row['started']:
                raise ValueError('Outcome without dispatched attempt')
            expected_outcome = finalize(tid, expected[tid], row, interrupted=event.get('status') == 'interrupted')
            if event != expected_outcome:
                raise ValueError('Outcome disagrees with journal')
            row['outcome'] = event
        else:
            raise ValueError('Unknown journal event')
    if sum(len(x['started']) for x in rows.values()) > PROTOCOL['maximum_dispatch_intents']:
        raise ValueError('Request budget exceeded')
    return rows


def finalize(tid, request_hash, row, interrupted=False):
    last = row['finished'][-1] if row['finished'] else {}
    unresolved = len(row['started']) - len(row['finished'])
    if unresolved and not interrupted:
        raise ValueError('Unresolved dispatch must remain interrupted')
    return dict(kind='outcome', task_id=tid, request_sha256=request_hash,
                status='interrupted' if interrupted else last.get('status'),
                raw_response='' if interrupted else last.get('raw_response', ''),
                usage=None if interrupted else last.get('usage'),
                returned_model=None if interrupted else last.get('returned_model'),
                finish_reason=None if interrupted else last.get('finish_reason'),
                observed_request_attempts=len(row['finished']), uncertain_dispatches=unresolved,
                dispatch_intents=len(row['started']))


def recover(journal, tasks):
    rows = states(read_events(journal), tasks)
    for tid, row in rows.items():
        if row['outcome'] is not None:
            continue
        # An already finished nonretryable attempt can be finalized without I/O.
        last = row['finished'][-1] if row['finished'] else {}
        incomplete = len(row['started']) != len(row['finished']) or last.get('retryable', False)
        append_event(journal, finalize(tid, row['started'][0]['request_sha256'], row, interrupted=incomplete))
    return states(read_events(journal), tasks)


def collect_with(tasks, journal, send, sleep=time.sleep):
    latch = Path(journal).with_suffix(".stopped.json")
    if latch.exists():
        raise RuntimeError("Outage/model-mismatch latch is set; no automatic resume")
    rows = recover(journal, tasks)
    failures = 0
    for prior in rows.values():
        outcome = prior.get("outcome") or {}
        failures = failures + 1 if outcome.get("status") in ("transport_error", "response_protocol_error") else 0
        if outcome.get("status") == "model_mismatch" or failures >= 2:
            latch.write_text(json.dumps({"reason": "prior_outage_or_model_mismatch"}) + "\n")
            raise RuntimeError("Previous outage prohibits automatic resume")
    for task in tasks:
        tid, request_hash = task['task_id'], digest(task['request'])
        if tid in rows:
            continue  # Completed errors and interrupted tasks are never rerun.
        began = time.perf_counter()
        row = dict(started=[], finished=[], outcome=None)
        for attempt in range(1, PROTOCOL['maximum_attempts_per_task'] + 1):
            sleep(PROTOCOL['request_spacing_seconds'])
            event = dict(kind='attempt_started', task_id=tid, attempt=attempt, request_sha256=request_hash, started_utc=now())
            append_event(journal, event)
            row['started'].append(event)
            result = send(task['request'])
            finished = dict(result, kind='attempt_finished', task_id=tid, attempt=attempt, request_sha256=request_hash)
            append_event(journal, finished)
            row['finished'].append(finished)
            if not result['retryable']:
                break
            if attempt < PROTOCOL['maximum_attempts_per_task']:
                sleep(PROTOCOL['retry_wait_seconds'])
        outcome = finalize(tid, request_hash, row)
        append_event(journal, outcome)
        rows[tid] = dict(row, outcome=outcome)
        print(json.dumps(dict(completed=len(rows), total=len(tasks), status=outcome['status'], task_seconds=round(time.perf_counter()-began, 3))), flush=True)
        failures = failures + 1 if outcome['status'] in ('transport_error', 'response_protocol_error') else 0
        if outcome['status'] == 'model_mismatch' or failures >= 2:
            latch.write_text(json.dumps({'reason': outcome['status'], 'completed': len(rows)}) + '\n')
            raise RuntimeError('Collection stopped; keep finalized outcomes, resume only untouched tasks')
    return states(read_events(journal), tasks)


def collect():
    tasks = verify()  # Verify before reading credentials or making any request.
    journal = HERE / 'local/journal.jsonl'
    with (HERE / 'local/collection.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        rows = recover(journal, tasks)
        if len(rows) == len(tasks):
            print('All outcomes finalized; no API request made.')
            return
        import httpx
        auth = credentials()
        with httpx.Client(trust_env=False, follow_redirects=False, timeout=httpx.Timeout(150, connect=15)) as client:
            collect_with(tasks, journal, lambda p: transport(p, auth, client))


def status():
    tasks = verify()
    rows = states(read_events(HERE / 'local/journal.jsonl'), tasks)
    outcomes = [r['outcome'] for r in rows.values() if r['outcome'] is not None]
    return dict(outage_latched=(HERE / "local/journal.stopped.json").exists(), state='not_started' if not rows else ('complete' if len(outcomes)==len(tasks) else 'partial'),
                planned_outputs=len(tasks), finalized_outputs=len(outcomes),
                observed_request_attempts=sum(len(r['finished']) for r in rows.values()),
                uncertain_dispatches=sum(len(r['started'])-len(r['finished']) for r in rows.values()),
                policy_training='not_started; no training command in this protocol')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['freeze', 'verify', 'status', 'collect', 'analyze'])
    command = parser.parse_args().command
    if command == 'freeze':
        freeze()
        print(json.dumps(status(), indent=2))
    elif command == 'verify':
        print('Verified frozen tasks:', len(verify()))
    elif command == 'status':
        print(json.dumps(status(), indent=2))
    elif command == 'collect':
        collect()
    else:
        from exps.paper2_rule_verification_20261008.analyze import analyze
        analyze()


if __name__ == '__main__':
    main()
