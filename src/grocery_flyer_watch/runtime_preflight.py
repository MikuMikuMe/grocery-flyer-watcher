"""Read-only operational diagnosis from CURRENT callable schemas and private state.

Permission approval, provider authentication, exposed tool schemas and a successful
provider mutation are different facts. This module must never claim one proves another.
It does not invent tool availability, contact a provider or weaken the delivery gate.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import re
import sqlite3
import sys

ROUTES = {
    'gmail_search': ({'Gmail.search_emails'}, {'Gmail.search_email_ids'}),
    'gmail_read': ({'Gmail.read_email'}, {'Gmail.batch_read_email'}),
    'gmail_send': ({'Gmail.send_email'}, {'Gmail.create_draft', 'Gmail.send_draft'}),
    'github_read': ({'GitHub.fetch_file'}, {'GitHub_Auto_Project_Connector.read_repository_file'}),
    'github_publish': ({'GitHub_Auto_Project_Connector.commit_repository_files'}, {'GitHub.create_file'}),
    'task_update': ({'Automations.update'},),
}
PROVIDERS = {
    'gmail_search': {'Gmail'}, 'gmail_read': {'Gmail'}, 'gmail_send': {'Gmail'},
    'github_read': {'GitHub','GitHub_Auto_Project_Connector'},
    'github_publish': {'GitHub','GitHub_Auto_Project_Connector'}, 'task_update': {'Automations'},
}
TABLES = {
    'scopes': {'id'}, 'recipients': {'address'}, 'handled_editions': {'id'},
    'events': {'id','scope','edition','selection','publication','body_hash','triggers','audience'},
    'deliveries': {'event','recipient','status','ticket','reserved_at','receipt'},
    'delivered_offers': {'recipient','fingerprint'},
}

class PreflightError(ValueError):
    pass

def require(ok: bool, code: str) -> None:
    if not ok:
        raise PreflightError(code)

def parse_time(value: str) -> datetime:
    require(isinstance(value,str), 'invalid_observation_time')
    try:
        stamp=datetime.fromisoformat(value.replace('Z','+00:00'))
    except ValueError:
        raise PreflightError('invalid_observation_time') from None
    require(stamp.tzinfo is not None, 'observation_timezone_required')
    return stamp

def capabilities(data: dict, *, now: datetime | None = None) -> dict:
    now=now or datetime.now(timezone.utc)
    require(isinstance(data,dict) and set(data)=={'format','observed_at','discovery'}, 'capability_schema')
    require(data['format']=='callable-actions-v1', 'capability_version')
    require(timedelta(0) <= now-parse_time(data['observed_at']) <= timedelta(minutes=15),
            'rediscover_current_callable_schemas')
    require(isinstance(data['discovery'],list), 'discovery_schema')
    observed={}
    for item in data['discovery']:
        require(isinstance(item,dict) and set(item)=={'provider','complete','evidence_ref','actions'},
                'discovery_schema')
        provider=item['provider']
        require(provider in {'Gmail','GitHub','GitHub_Auto_Project_Connector','Automations'}, 'provider_schema')
        require(provider not in observed, 'duplicate_provider')
        require(type(item['complete']) is bool and isinstance(item['evidence_ref'],str)
                and bool(item['evidence_ref'].strip()), 'callable_schema_evidence_required')
        require(isinstance(item['actions'],list) and all(isinstance(x,str) and
                re.fullmatch(re.escape(provider)+r'\.[A-Za-z_][A-Za-z0-9_]*',x)
                for x in item['actions']) and len(item['actions'])==len(set(item['actions'])), 'action_schema')
        observed[provider]=item
    actions={a for d in observed.values() for a in d['actions']}
    result={}
    for operation,routes in ROUTES.items():
        present=next((sorted(r) for r in routes if r <= actions),None)
        complete=all(p in observed and observed[p]['complete'] for p in PROVIDERS[operation])
        result[operation]={'status':'exposed_not_execution_tested' if present else
                           ('not_exposed' if complete else 'unknown'), 'route':present}
    # No unsupported inference about OAuth scopes, write approval or provider outcome.
    return result

def journal_health(path: Path | None, *, persistence: dict | None = None) -> dict:
    if path is None:
        return {'status':'journal_not_configured','action':'restore_existing_authorized_private_store'}
    path=path.absolute()
    if any(p.is_symlink() for p in [path,*path.parents]) or any((p/'.git').exists() for p in path.parents):
        return {'status':'unsafe_journal_location','action':'use_private_location_outside_checkout'}
    if not path.is_file():
        return {'status':'journal_not_restored','action':'restore_existing_history_do_not_create_empty_state'}
    try:
        # mode=ro never creates a missing database or initializes history.
        db=sqlite3.connect(path.as_uri()+'?mode=ro', uri=True, timeout=3)
        try:
            good=db.execute('PRAGMA quick_check').fetchall()==[('ok',)]
            require(good, 'journal_corrupt')
            for table,required in TABLES.items():
                columns={row[1] for row in db.execute(f'PRAGMA table_info({table})')}
                require(required <= columns,'journal_schema_incompatible')
            seeded=db.execute('SELECT 1 FROM scopes LIMIT 1').fetchone() is not None
        finally:
            db.close()
    except (sqlite3.Error, PreflightError):
        return {'status':'journal_unreadable_or_incompatible','action':'restore_verified_backup_without_reset'}
    if not seeded:
        return {'status':'history_not_initialized','action':'import_actual_handled_history_without_backfill'}
    # A local file's existence cannot prove it survives another scheduled execution.
    if not isinstance(persistence,dict) or set(persistence)!={'kind','restore_ref','checkpoint_ref'} or \
            persistence.get('kind') not in {'durable_mount','existing_private_store'} or \
            not all(isinstance(persistence.get(k),str) and persistence[k].strip()
                    for k in ('restore_ref','checkpoint_ref')):
        return {'status':'durability_unverified','action':'verify_restore_and_checkpoint_in_existing_private_store'}
    return {'status':'history_present_durability_attested','action':'continue_scope_and_recipient_checks'}

def diagnose(data: dict, journal: Path | None = None, persistence: dict | None = None,
             *, now: datetime | None = None) -> dict:
    ops=capabilities(data,now=now)
    state=journal_health(journal,persistence=persistence)
    missing=[k for k in ('gmail_search','gmail_read','gmail_send','github_read','github_publish')
             if ops[k]['status']!='exposed_not_execution_tested']
    blockers=[('action_not_exposed:' if ops[k]['status']=='not_exposed' else 'action_discovery_incomplete:')+k for k in missing]
    if state['status']!='history_present_durability_attested':
        blockers.append(state['status'])
    return {'status':'operational_prerequisites_present' if not blockers else 'operationally_blocked',
            'operations':ops,'private_state':state,'blockers':blockers,
            'continue_independent_source_checks':True,'delivery_authorized':False,
            'provider_authentication':'not_inferred','provider_mutation_result':'not_attempted'}

def main(argv: list[str] | None = None) -> int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('capabilities',type=Path)
    p.add_argument('--journal',type=Path)
    p.add_argument('--persistence-proof',type=Path)
    a=p.parse_args(argv)
    try:
        proof=json.loads(a.persistence_proof.read_text()) if a.persistence_proof else None
        result=diagnose(json.loads(a.capabilities.read_text()),a.journal,proof)
        print(json.dumps(result,indent=2))
        return 0 if result['status']=='operational_prerequisites_present' else 2
    except Exception as exc:
        print(json.dumps({'status':'operationally_blocked','code':str(exc) if isinstance(exc,PreflightError)
                          else type(exc).__name__,'delivery_authorized':False}),file=sys.stderr)
        return 2

if __name__=='__main__':
    raise SystemExit(main())
