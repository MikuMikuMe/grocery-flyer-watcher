"""Offline journal controller. Never retrieves sources, publishes, or sends mail."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

SCHEMA = 'flyer-operation-journal-v1'
STATES = {'IDLE', 'RUN_STARTED', 'PENDING', 'IN_PROGRESS', 'RESULT_SAVED', 'COMMITTED', 'RUN_FINISHED'}
KINDS = {'read_only', 'immutable_write', 'delivery_reconcile'}
ACTIVE = {'PENDING', 'IN_PROGRESS', 'RESULT_SAVED'}
ID = re.compile(r'[0-9a-f]{64}\Z')
FENCE = re.compile(r'(?m)^```json\n([\s\S]*?)\n```\s*\Z')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(',', ':'), allow_nan=False).encode()


def operation_id(identity):
    require(isinstance(identity, dict) and set(identity) == {'retailer', 'edition', 'stage', 'unit', 'source', 'kind'}, 'invalid operation identity')
    require(all(isinstance(v, str) and v.strip() for v in identity.values()), 'empty operation identity')
    require(identity['kind'] in KINDS, 'invalid operation kind')
    return digest(canonical(identity))


def validate(s):
    require(isinstance(s, dict) and s.get('schema') == SCHEMA, 'invalid schema')
    require(type(s.get('revision')) is int and s['revision'] >= 0, 'invalid revision')
    require(s.get('status') in STATES, 'invalid status')
    require(type(s.get('checkpoint_sequence')) is int and s['checkpoint_sequence'] >= 0, 'invalid checkpoint sequence')
    status, op, result = s['status'], s.get('operation'), s.get('result')
    if status != 'IDLE':
        require(isinstance(s.get('run_key'), str) and s['run_key'].strip(), 'missing run key')
    if status in ACTIVE | {'COMMITTED'}:
        require(isinstance(op, dict) and op.get('id') == operation_id(op.get('identity')), 'invalid operation')
        require(type(op.get('start_sequence')) is int and 0 <= op['start_sequence'] <= s['checkpoint_sequence'], 'invalid operation sequence')
    else:
        require(op is None and result is None, 'unexpected operation')
    if status in {'PENDING', 'IN_PROGRESS'}:
        require(result is None, 'pending operation has result')
    if status in {'RESULT_SAVED', 'COMMITTED'}:
        require(isinstance(result, dict) and result.get('disposition') in {'advance', 'no_progress', 'uncertain'}, 'invalid result')
        require(isinstance(result.get('evidence'), str) and result['evidence'].strip(), 'missing result evidence')
        if result['disposition'] == 'advance':
            require(bool(result.get('artifact') or result.get('units')), 'missing result payload')
        if status == 'COMMITTED':
            require(result['disposition'] != 'uncertain', 'uncertain result cannot commit')
            require(s['checkpoint_sequence'] > op['start_sequence'] if result['disposition'] == 'advance' else s['checkpoint_sequence'] == op['start_sequence'], 'invalid committed sequence')
    return s


def parse(raw):
    match = FENCE.search(raw.decode('utf-8'))
    require(match is not None, 'missing journal JSON fence')
    return validate(json.loads(match.group(1)))


def render(s):
    validate(s)
    return ('# Private operation journal\n\nNative checkpoint remains authoritative. Never interpret intent as evidence.\n\n```json\n' + json.dumps(s, indent=2, sort_keys=True, ensure_ascii=True, allow_nan=False) + '\n```\n').encode()


def transition(s, event):
    validate(s)
    require(event.get('expected_revision') == s['revision'], 'stale revision')
    action = event.get('action')
    status = s['status']
    n = dict(s, revision=s['revision'] + 1)
    seq = event.get('checkpoint_sequence')
    require(type(seq) is int and seq >= s['checkpoint_sequence'], 'checkpoint regression')
    if action == 'start':
        require(status in {'IDLE', 'RUN_FINISHED'}, 'unfinished run')
        key = event.get('run_key')
        require(isinstance(key, str) and key.strip() and key != s.get('run_key'), 'invalid run key')
        n.update(status='RUN_STARTED', run_key=key, native_run_id=event.get('native_run_id'), scheduled_for=event.get('scheduled_for'), checkpoint_sequence=seq, operation=None, result=None)
    elif action == 'pending':
        require(status in {'RUN_STARTED', 'COMMITTED'}, 'unresolved operation')
        require(seq == s['checkpoint_sequence'], 'checkpoint changed before intent')
        identity = event.get('identity')
        n.update(status='PENDING', operation={'id': operation_id(identity), 'identity': identity, 'start_sequence': seq}, result=None)
    elif action == 'begin':
        require(status == 'PENDING' and seq == s['checkpoint_sequence'], 'invalid begin')
        n['status'] = 'IN_PROGRESS'
    elif action == 'result':
        require(status in {'PENDING', 'IN_PROGRESS'} and seq == s['checkpoint_sequence'], 'invalid result transition')
        require(status == 'IN_PROGRESS' or s['operation']['identity']['kind'] == 'read_only', 'external operation must begin first')
        n.update(status='RESULT_SAVED', result=event.get('result'))
    elif action == 'reconcile':
        require(status == 'RESULT_SAVED' and s['result']['disposition'] == 'uncertain', 'no uncertain result')
        require(seq == s['checkpoint_sequence'], 'checkpoint changed; inspect before reconciliation')
        n['result'] = event.get('result')
    elif action == 'commit':
        require(status == 'RESULT_SAVED', 'result not saved')
        require(event.get('verified_checkpoint') is True and event.get('verified_secondary_records') is True, 'independent readback required')
        n.update(status='COMMITTED', checkpoint_sequence=seq)
    elif action == 'finish':
        require(status in {'RUN_STARTED', 'COMMITTED'} and seq == s['checkpoint_sequence'], 'unfinished operation or changed checkpoint')
        require(event.get('verified_secondary_records') is True, 'final history/handoff readback required')
        n.update(status='RUN_FINISHED', operation=None, result=None)
    else:
        raise ValueError('unknown action')
    if 'next_action' in event:
        n['next_action'] = event['next_action']
    return validate(n)


def inspect(s, seq, last_run_id=None, handoff_run_id=None):
    validate(s)
    require(type(seq) is int and seq >= 0, 'invalid observed sequence')
    status = s['status']
    if seq < s['checkpoint_sequence']:
        action = 'checkpoint_conflict'
    elif status in {'PENDING', 'IN_PROGRESS'}:
        kind = s['operation']['identity']['kind']
        action = {'read_only': 'verify_then_retry_read_only', 'immutable_write': 'reconcile_immutable_artifact', 'delivery_reconcile': 'reconcile_native_uncertainty_and_sent'}[kind]
        if seq != s['checkpoint_sequence']:
            action = 'checkpoint_conflict'
    elif status == 'RESULT_SAVED':
        action = 'reconcile_uncertainty' if s['result']['disposition'] == 'uncertain' else 'verify_result_and_missing_delta' if seq == s['checkpoint_sequence'] else 'verify_advanced_checkpoint_repair_secondary'
    elif seq > s['checkpoint_sequence']:
        action = 'checkpoint_conflict'
    elif status == 'COMMITTED':
        action = 'verify_secondary_records_then_continue'
    elif status == 'RUN_STARTED':
        action = 'recover_interrupted_run'
    else:
        action = 'start_run'
    return {'action': action, 'status': status, 'revision': s['revision'], 'operation_id': (s.get('operation') or {}).get('id'), 'handoff_stale': last_run_id is not None and last_run_id != handoff_run_id, 'delivery_authorized': False}


def append_entry(raw, key, body):
    require(isinstance(key, str) and key.strip(), 'missing entry key')
    require(isinstance(body, str) and body.strip(), 'missing entry body')
    tag = digest(key.encode())
    start = ('<!-- journal-entry:' + tag + ' -->\n').encode()
    end = ('\n<!-- /journal-entry:' + tag + ' -->\n').encode()
    payload = body.encode()
    require(b'<!-- journal-entry:' not in payload and b'<!-- /journal-entry:' not in payload, 'reserved entry marker')
    entry = start + payload + end
    if start in raw:
        require(raw.count(start) == 1 and raw.count(end) == 1 and entry in raw, 'entry key conflict')
        return raw
    require(end not in raw, 'orphan entry marker')
    return raw + (b'\n' if raw.endswith(b'\n') else b'\n\n') + entry


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('command', choices=['inspect', 'transition', 'append', 'verify'])
    p.add_argument('input', type=Path)
    p.add_argument('--request', type=Path)
    p.add_argument('--output', type=Path)
    a = p.parse_args()
    try:
        raw = a.input.read_bytes()
        require(a.request is not None, 'request required')
        if a.command == 'verify':
            require(raw == a.request.read_bytes(), 'readback mismatch')
            out = {'sha256': digest(raw), 'verified': True}
        else:
            request = json.loads(a.request.read_bytes())
            if a.command == 'inspect':
                out = inspect(parse(raw), **request)
            else:
                new = render(transition(parse(raw), request)) if a.command == 'transition' else append_entry(raw, **request)
                require(a.output is not None, 'output required')
                require(a.output.resolve() != a.input.resolve(), 'must write separate output')
                with a.output.open('xb') as stream:
                    stream.write(new)
                out = {'sha256': digest(new), 'bytes': len(new), 'delivery_authorized': False}
        print(json.dumps(out, sort_keys=True))
        return 0
    except (ValueError, TypeError, KeyError, OSError) as exc:
        print(json.dumps({'error': str(exc), 'delivery_authorized': False}), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
