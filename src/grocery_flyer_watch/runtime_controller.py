"""Offline journal controller. Never retrieves sources, publishes, or sends mail."""
import argparse
from datetime import datetime
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


def timestamp(value):
    require(isinstance(value, str), 'missing native timestamp')
    t = datetime.fromisoformat(value.replace('Z', '+00:00'))
    require(t.tzinfo is not None, 'native timestamp must include offset')
    return t


def recover_empty(s, event, n):
    require(s['status'] == 'RUN_STARTED' and s.get('operation') is None and s.get('result') is None, 'only empty run may be recovered')
    require(event['checkpoint_sequence'] == s['checkpoint_sequence'], 'checkpoint changed')
    for key in ('verified_checkpoint', 'verified_no_unresolved_delivery', 'verified_no_other_writer'):
        require(event.get(key) is True, 'missing ' + key)
    last = event.get('latest_run')
    require(isinstance(last, dict) and last.get('recorded_status') in {'completed', 'failed', 'no_update'}, 'terminal native evidence required')
    require(isinstance(last.get('id'), str) and last['id'].strip(), 'missing native invocation ID')
    ended = timestamp(last.get('completed_at'))
    scheduled = timestamp(last.get('scheduled_for'))
    old_id, old_schedule = s.get('native_run_id'), s.get('scheduled_for')
    observed = s.get('observed_started_at')
    same = bool(old_id) and last['id'] == old_id
    if same:
        require(old_schedule is None or scheduled == timestamp(old_schedule), 'native schedule mismatch')
        require(observed is None or ended >= timestamp(observed), 'terminal evidence precedes observed start')
    elif old_id and old_schedule:
        require(scheduled > timestamp(old_schedule) and ended >= timestamp(old_schedule), 'native evidence does not establish supersession')
    else:
        require(observed is not None, 'missing abandoned invocation observation')
        started = timestamp(last.get('started_at'))
        require(ended >= started > timestamp(observed), 'native evidence does not establish supersession')
    n.update(status='RUN_FINISHED', operation=None, result=None,
             recovery=dict(run_key=s['run_key'], native_run_id=old_id, scheduled_for=old_schedule, basis='terminal' if same else 'superseded', evidence_run_id=last['id'], historical_outcome='unknown'),
             next_action='Resume canonical planner; no retailer advancement inferred.')
    if event['action'] == 'recover_start':
        key = event.get('run_key')
        require(isinstance(key, str) and key.strip() and key not in {s['run_key'], last['id']}, 'new invocation key required')
        native = event.get('native_run_id')
        new_time = event.get('scheduled_for')
        new_observed = event.get('observed_started_at')
        if native is not None:
            require(isinstance(native, str) and native.strip() and native not in {last['id'], old_id}, 'new native invocation required')
        if new_time is not None:
            require(timestamp(new_time) > scheduled, 'new invocation must follow terminal evidence')
        if new_observed is not None:
            require(timestamp(new_observed) >= ended, 'new observation precedes terminal evidence')
        require((native is not None and new_time is not None) or new_observed is not None, 'new invocation needs observed start when native identity/schedule unavailable')
        n.update(status='RUN_STARTED', run_key=key, native_run_id=native, scheduled_for=new_time, observed_started_at=new_observed)
    return validate(n)


def transition(s, event):
    validate(s)
    require(event.get('expected_revision') == s['revision'], 'stale revision')
    action = event.get('action')
    status = s['status']
    n = dict(s, revision=s['revision'] + 1)
    seq = event.get('checkpoint_sequence')
    require(type(seq) is int and seq >= s['checkpoint_sequence'], 'checkpoint regression')
    if action in {'recover_abandoned', 'recover_start'}:
        return recover_empty(s, event, n)
    if action == 'start':
        require(status in {'IDLE', 'RUN_FINISHED'}, 'unfinished run')
        key = event.get('run_key')
        require(isinstance(key, str) and key.strip() and key != s.get('run_key'), 'invalid run key')
        if event.get('observed_started_at') is not None:
            timestamp(event['observed_started_at'])
        n.update(status='RUN_STARTED', run_key=key, native_run_id=event.get('native_run_id'), scheduled_for=event.get('scheduled_for'), checkpoint_sequence=seq, operation=None, result=None, observed_started_at=event.get('observed_started_at'))
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


def recovery_bundle(s, event, history):
    action = event.get('action')
    require(action in {'start', 'recover_abandoned', 'recover_start'}, 'startup/recovery action required')
    if action == 'start':
        require(event.get('verified_checkpoint') is True and event.get('verified_no_other_writer') is True, 'verified checkpoint and single writer required')
        require(event.get('checkpoint_sequence') == s['checkpoint_sequence'], 'checkpoint changed')
        native, schedule, observed = (event.get(k) for k in ('native_run_id', 'scheduled_for', 'observed_started_at'))
        require((isinstance(native, str) and native.strip() and schedule is not None) or observed is not None, 'new invocation needs observed start when native identity/schedule unavailable')
        if schedule is not None:
            timestamp(schedule)
    n = transition(s, event)
    old = n['recovery'] if action != 'start' else None
    recovery_lines = ''
    if old:
        body = (f"## Recovered empty invocation — {old['run_key']}\n"
                f"- Native invocation: {old['native_run_id']}\n"
                f"- Scheduled: {old['scheduled_for']}\n"
                f"- Checkpoint sequence: {n['checkpoint_sequence']} (unchanged)\n"
                "- Empty RUN_STARTED closed using verified terminal or later native evidence. Historical workflow outcome unknown; no research progress inferred.")
        history = append_entry(history, old['run_key'] + ':RECOVERED_EMPTY', body)
        recovery_lines = (f"- Recovered run: {old['run_key']}\n"
                          f"- Terminal evidence invocation: {old['evidence_run_id']} ({old['basis']})\n")
    if n['status'] == 'RUN_STARTED':
        history = append_entry(history, n['run_key'] + ':START',
                               f"## Invocation START — {n['run_key']}\n- Checkpoint sequence: {n['checkpoint_sequence']}\n- Initialized; no retailer progress yet.")
    handoff = ("# Grocery Flyer Watcher — latest handoff\n\n"
               f"- Journal status: {n['status']}\n- Journal revision: {n['revision']}\n"
               f"- Run key: {n['run_key']}\n" + recovery_lines +
               f"- Native checkpoint: {n['checkpoint_sequence']} (unchanged)\n"
               "- No pending operation or result; no retailer progress inferred.\n"
               "- Next: execute the canonical planner and persist a real bounded operation.\n").encode()
    return render(n), history, handoff


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('command', choices=['inspect', 'transition', 'append', 'verify', 'recover'])
    p.add_argument('input', type=Path)
    p.add_argument('--request', type=Path)
    p.add_argument('--output', type=Path)
    p.add_argument('--history', type=Path)
    p.add_argument('--history-output', type=Path)
    p.add_argument('--handoff-output', type=Path)
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
            elif a.command == 'recover':
                paths = (a.output, a.history_output, a.handoff_output)
                require(a.history is not None and all(paths), 'recovery paths required')
                require(len({x.resolve() for x in (*paths, a.input, a.history, a.request)}) == 6, 'recovery paths must be distinct')
                require(not any(x.exists() for x in paths), 'recovery output already exists')
                bundle = recovery_bundle(parse(raw), request, a.history.read_bytes())
                for path, data in zip(paths, bundle):
                    with path.open('xb') as stream:
                        stream.write(data)
                out = {'status': parse(bundle[0])['status'], 'revision': parse(bundle[0])['revision'], 'sha256': [digest(x) for x in bundle], 'delivery_authorized': False}
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
