"""Standalone existing public-mirror renderer; no private platform imports.

Reviewed data-only snapshots may be fetched through PUBLIC_STATUS_URL. This is
read-only reporting, with no broker, credentials, operational controls or LLM.
Development follows docs/AUTOMATED_ENGINEERING.md; deployment remains separate.
"""
import argparse
import ipaddress
import json
import math
import os
import re
import shutil
import time
from datetime import UTC, datetime
from decimal import Decimal
from http.client import HTTPException
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

MAX_BYTES = 65536
FETCH_TIMEOUT_SECONDS = 5
MAX_FEED_REQUESTS = 2
STATUS_RAW_BASE = 'https://raw.githubusercontent.com/FussballSug/blitzwerk-quant-site/refs/heads/status-data/'
STATUS_URL_TEMPLATE = STATUS_RAW_BASE + 'slots/{utc_slot}.json'
STATUS_LATEST_URL = STATUS_RAW_BASE + 'latest.json'
PUBLIC_KEYS = {"schema_version", "snapshot_at", "freshness", "mode", "desk_state",
               "traders", "stages", "employees", "workflows", "incidents", "improvements", "reporting"}
CATALOG = {'sug': {'employee_id': 'sug', 'legacy_role_id': 'alexandar', 'name': 'Sug', 'manager': 'owner', 'owner': 'owner', 'purpose': 'Coordinate priorities, incidents and verified owner reporting.', 'responsibilities': ['operations_coordinator'], 'allowed_tools': ['sanitized_evidence', 'assigned_bounded_task'], 'authority': ['read_sanitized_evidence', 'propose_bounded_work'], 'execution_authority': 'none', 'approved_universe': None, 'strategy': None, 'strategy_version': None, 'risk_limits': None, 'resource_budget': {'worker_concurrency': 1, 'model_tokens': 0, 'api_calls': 0}, 'escalation_destination': 'owner'}, 'reinhardt': {'employee_id': 'reinhardt', 'legacy_role_id': 'reinhardt', 'name': 'Klaus Reinhardt', 'manager': 'sug', 'owner': 'owner', 'purpose': 'Own trader mandates, task queues, evaluation and blockers.', 'responsibilities': ['trading_director'], 'allowed_tools': ['sanitized_evidence', 'assigned_bounded_task'], 'authority': ['read_sanitized_evidence', 'propose_bounded_work'], 'execution_authority': 'none', 'approved_universe': None, 'strategy': None, 'strategy_version': None, 'risk_limits': None, 'resource_budget': {'worker_concurrency': 1, 'model_tokens': 0, 'api_calls': 0}, 'escalation_destination': 'sug'}, 'hoffmann': {'employee_id': 'hoffmann', 'legacy_role_id': 'hoffmann', 'name': 'Stefan Hoffmann', 'manager': 'sug', 'owner': 'owner', 'purpose': 'Own reliability, tooling, diagnosis, validated repair and recovery coordination.', 'responsibilities': ['engineering_lead', 'incident_commander'], 'allowed_tools': ['sanitized_evidence', 'assigned_bounded_task'], 'authority': ['read_sanitized_evidence', 'propose_bounded_work'], 'execution_authority': 'none', 'approved_universe': None, 'strategy': None, 'strategy_version': None, 'risk_limits': None, 'resource_budget': {'worker_concurrency': 1, 'model_tokens': 0, 'api_calls': 0}, 'escalation_destination': 'sug'}, 'weber': {'employee_id': 'weber', 'legacy_role_id': 'weber', 'name': 'Friedrich Weber', 'manager': 'owner', 'owner': 'owner', 'purpose': 'Independently veto or suspend activity through existing deterministic controls.', 'responsibilities': ['independent_risk'], 'allowed_tools': ['sanitized_evidence', 'assigned_bounded_task'], 'authority': ['independent_risk_veto', 'suspend_via_existing_risk_control'], 'execution_authority': 'none', 'approved_universe': None, 'strategy': None, 'strategy_version': None, 'risk_limits': None, 'resource_budget': {'worker_concurrency': 1, 'model_tokens': 0, 'api_calls': 0}, 'escalation_destination': 'owner'}, 'schneider': {'employee_id': 'schneider', 'legacy_role_id': 'schneider', 'name': 'Dr. Anna Schneider', 'manager': 'owner', 'owner': 'owner', 'purpose': "Validate another worker's strategy or engineering evidence; no self approval.", 'responsibilities': ['independent_validation'], 'allowed_tools': ['sanitized_evidence', 'assigned_bounded_task'], 'authority': ['independent_review', 'reject_candidate'], 'execution_authority': 'none', 'approved_universe': None, 'strategy': None, 'strategy_version': None, 'risk_limits': None, 'resource_budget': {'worker_concurrency': 1, 'model_tokens': 0, 'api_calls': 0}, 'escalation_destination': 'owner'}, 'vogel': {'employee_id': 'vogel', 'legacy_role_id': 'vogel', 'name': 'Matthias Vogel', 'manager': 'sug', 'owner': 'owner', 'purpose': 'Reconcile accounting evidence and publish sanitized verified reporting snapshots.', 'responsibilities': ['accounting', 'website_reporting'], 'allowed_tools': ['sanitized_evidence', 'assigned_bounded_task'], 'authority': ['read_sanitized_evidence', 'propose_bounded_work'], 'execution_authority': 'none', 'approved_universe': None, 'strategy': None, 'strategy_version': None, 'risk_limits': None, 'resource_budget': {'worker_concurrency': 1, 'model_tokens': 0, 'api_calls': 0}, 'escalation_destination': 'sug'}, 'fischer': {'employee_id': 'fischer', 'legacy_role_id': 'fischer', 'name': 'Dr. Lukas Fischer', 'manager': 'reinhardt', 'owner': 'owner', 'purpose': 'Produce reproducible, cost-aware, leakage-resistant experiments.', 'responsibilities': ['research'], 'allowed_tools': ['sanitized_evidence', 'assigned_bounded_task'], 'authority': ['read_sanitized_evidence', 'propose_bounded_work'], 'execution_authority': 'none', 'approved_universe': None, 'strategy': None, 'strategy_version': None, 'risk_limits': None, 'resource_budget': {'worker_concurrency': 1, 'model_tokens': 0, 'api_calls': 0}, 'escalation_destination': 'reinhardt'}, 'johanna': {'employee_id': 'johanna', 'legacy_role_id': 'johanna', 'name': 'Johanna Becker', 'manager': 'reinhardt', 'owner': 'owner', 'purpose': 'Provide cited fresh observations and identify missing source coverage.', 'responsibilities': ['market_intelligence'], 'allowed_tools': ['sanitized_evidence', 'assigned_bounded_task'], 'authority': ['read_sanitized_evidence', 'propose_bounded_work'], 'execution_authority': 'none', 'approved_universe': None, 'strategy': None, 'strategy_version': None, 'risk_limits': None, 'resource_budget': {'worker_concurrency': 1, 'model_tokens': 0, 'api_calls': 0}, 'escalation_destination': 'reinhardt'}, 'braun': {'employee_id': 'braun', 'legacy_role_id': 'braun', 'name': 'Maximilian Braun', 'manager': 'reinhardt', 'owner': 'owner', 'purpose': 'Evaluate the existing trend strategy within its approved paper mandate.', 'responsibilities': ['trader'], 'allowed_tools': ['sanitized_evidence', 'assigned_bounded_task'], 'authority': ['read_sanitized_evidence', 'propose_bounded_work'], 'execution_authority': 'paper_only_existing_scope', 'approved_universe': 'existing_approved_us_stock_screen', 'strategy': 'trend', 'strategy_version': None, 'risk_limits': 'existing_paper_risk_policy', 'resource_budget': {'worker_concurrency': 1, 'model_tokens': 0, 'api_calls': 0}, 'escalation_destination': 'reinhardt'}, 'hartmann': {'employee_id': 'hartmann', 'legacy_role_id': 'hartmann', 'name': 'Felix Hartmann', 'manager': 'reinhardt', 'owner': 'owner', 'purpose': 'Evaluate the existing momentum strategy within its approved paper mandate.', 'responsibilities': ['trader'], 'allowed_tools': ['sanitized_evidence', 'assigned_bounded_task'], 'authority': ['read_sanitized_evidence', 'propose_bounded_work'], 'execution_authority': 'paper_only_existing_scope', 'approved_universe': 'existing_approved_us_stock_screen', 'strategy': 'momentum', 'strategy_version': None, 'risk_limits': 'existing_paper_risk_policy', 'resource_budget': {'worker_concurrency': 1, 'model_tokens': 0, 'api_calls': 0}, 'escalation_destination': 'reinhardt'}, 'krueger': {'employee_id': 'krueger', 'legacy_role_id': 'krueger', 'name': 'Tobias Krüger', 'manager': 'reinhardt', 'owner': 'owner', 'purpose': 'Evaluate the existing mean-reversion strategy within its approved paper mandate.', 'responsibilities': ['trader'], 'allowed_tools': ['sanitized_evidence', 'assigned_bounded_task'], 'authority': ['read_sanitized_evidence', 'propose_bounded_work'], 'execution_authority': 'paper_only_existing_scope', 'approved_universe': 'existing_approved_us_stock_screen', 'strategy': 'mean_reversion', 'strategy_version': None, 'risk_limits': 'existing_paper_risk_policy', 'resource_budget': {'worker_concurrency': 1, 'model_tokens': 0, 'api_calls': 0}, 'escalation_destination': 'reinhardt'}, 'mueller': {'employee_id': 'mueller', 'legacy_role_id': 'mueller', 'name': 'Dr. Katharina Müller', 'manager': 'sug', 'owner': 'owner', 'purpose': 'Track bounded resource use and useful outcomes without expanding budgets.', 'responsibilities': ['resource_governance'], 'allowed_tools': ['sanitized_evidence', 'assigned_bounded_task'], 'authority': ['read_sanitized_evidence', 'propose_bounded_work'], 'execution_authority': 'none', 'approved_universe': None, 'strategy': None, 'strategy_version': None, 'risk_limits': None, 'resource_budget': {'worker_concurrency': 1, 'model_tokens': 0, 'api_calls': 0}, 'escalation_destination': 'sug'}, 'adler': {'employee_id': 'adler', 'legacy_role_id': 'adler', 'name': 'Dr. Markus Adler', 'manager': 'sug', 'owner': 'owner', 'purpose': 'Route documented compliance uncertainties to qualified professional review.', 'responsibilities': ['compliance'], 'allowed_tools': ['sanitized_evidence', 'assigned_bounded_task'], 'authority': ['read_sanitized_evidence', 'propose_bounded_work'], 'execution_authority': 'none', 'approved_universe': None, 'strategy': None, 'strategy_version': None, 'risk_limits': None, 'resource_budget': {'worker_concurrency': 1, 'model_tokens': 0, 'api_calls': 0}, 'escalation_destination': 'sug'}, 'richter': {'employee_id': 'richter', 'legacy_role_id': 'richter', 'name': 'Sabine Richter', 'manager': 'adler', 'owner': 'owner', 'purpose': 'Document securities and data-source compliance evidence.', 'responsibilities': ['securities_compliance'], 'allowed_tools': ['sanitized_evidence', 'assigned_bounded_task'], 'authority': ['read_sanitized_evidence', 'propose_bounded_work'], 'execution_authority': 'none', 'approved_universe': None, 'strategy': None, 'strategy_version': None, 'risk_limits': None, 'resource_budget': {'worker_concurrency': 1, 'model_tokens': 0, 'api_calls': 0}, 'escalation_destination': 'adler'}, 'bergmann': {'employee_id': 'bergmann', 'legacy_role_id': 'bergmann', 'name': 'Thomas Bergmann', 'manager': 'adler', 'owner': 'owner', 'purpose': 'Document corporate and tax recordkeeping questions.', 'responsibilities': ['corporate_tax_compliance'], 'allowed_tools': ['sanitized_evidence', 'assigned_bounded_task'], 'authority': ['read_sanitized_evidence', 'propose_bounded_work'], 'execution_authority': 'none', 'approved_universe': None, 'strategy': None, 'strategy_version': None, 'risk_limits': None, 'resource_budget': {'worker_concurrency': 1, 'model_tokens': 0, 'api_calls': 0}, 'escalation_destination': 'adler'}}
STATES = {'stopped', 'blocked', 'planned', 'stale', 'running', 'waiting'}
TRIGGERS = {'hourly', 'daily', 'manager_review', 'broker_event', 'startup', 'health_check', 'incident', 'approved_task', 'owner_decision', 'market_bar'}
BLOCKERS = {'independent_validation_required', 'missing_data', 'stale_data', 'approval_required', 'delivery_unconnected', 'risk_halt', 'budget_exhausted', 'dependency', 'authority_expired', 'service_stopped', 'reconciliation_required'}
GRAPHS = {'trading': ('fresh_data', 'mandate_check', 'strategy_evaluation', 'independent_risk', 'paper_submission', 'broker_reconciliation', 'performance_assessment'), 'improvement': ('observed_weakness', 'hypothesis', 'experiment', 'evaluation', 'independent_validation', 'authorized_promotion', 'paper_canary', 'measured_review'), 'incident': ('detect', 'contain', 'capture_evidence', 'diagnose', 'repair_or_recovery', 'validate', 'authorized_deployment', 'reconcile', 'resume_eligible', 'sustained_health', 'regression_coverage'), 'publishing': ('hourly_trigger', 'collect_reconciled', 'validate_sanitize', 'immutable_snapshot', 'publish_atomically', 'verify_public', 'record_success')}


def _resolve_employee(value):
    value = {'alexandar': 'sug', 'alexander': 'sug'}.get(value, value)
    if value not in CATALOG:
        raise ValueError('Unknown employee')
    return value


TRADERS = (
    {"employee_id": "braun", "name": "Maximilian Braun", "strategy": "Trend"},
    {"employee_id": "hartmann", "name": "Felix Hartmann", "strategy": "Momentum"},
    {"employee_id": "krueger", "name": "Tobias Krüger", "strategy": "Mean reversion"},
)
PUBLIC_KEYS = {"schema_version", "snapshot_at", "freshness", "mode", "desk_state",
               "traders", "stages", "employees", "workflows", "incidents", "improvements", "reporting"}
GRAPH_STATES = {"running", "completed", "held", "waiting", "failed", "rolled_back", "timed_out", "cancelled"}
OUTCOMES = {"passed", "rejected", "waiting", "failed", "rollback", "resumed", "uncertain"}
TOKEN = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:@/-]{0,159}\Z")
DIGEST = re.compile(r"[a-f0-9]{64}\Z")
HEALTHY_STATES = {'no_entry_signal', 'ready_disabled', 'daily_entry_limit', 'entry_pending',
                  'entry_submitted', 'exit_pending', 'exit_submitted', 'position_protected',
                  'canceling_stale_entry', 'canceling_for_exit', 'awaiting_protection'}
REASONS = BLOCKERS | {"uncertain_side_effect", "attempt_budget_exhausted", "resource_budget_exhausted",
                     "evidence_private", "process_failed", "heartbeat_stale", "overdue_task",
                     "scheduler_stale", "publishing_failed", "missed_hourly_slot", "invariant_failed"}


def _token(value):
    return value if isinstance(value, str) and TOKEN.fullmatch(value) else None


def _member(value, choices):
    return isinstance(value, str) and value in choices


def _epoch(value):
    return value if type(value) in (int, float) and math.isfinite(value) and value >= 0 else None


def _rows(value, limit=200):
    return value[:limit] if isinstance(value, list) else []








# BEGIN canonical public evidence helpers
METRICS=('realized_pnl','unrealized_pnl','drawdown','exposure','fees','sample_size')

LEGACY_TRADER_KEYS = frozenset({'employee_id','name','strategy','state','strategy_version',
                               'approved_universe','performance'})

OBSERVATION_MODE = 'source_receipt_observation'

RECOVERY_MODE = 'finite_stopped_startup_recovery'

CANARY_MODE = 'finite_closed_session_canary'

OBSERVATION_GRAPHS = {
    'trading': GRAPHS['trading'],
    'publishing': ('hourly_trigger', 'collect_status_receipts', 'validate_sanitize', 'immutable_snapshot',
                   'publish_atomically', 'verify_public', 'record_success'),
    'incident': ('detect', 'capture_evidence', 'diagnose', 'repair_or_recovery'),
}

RUNTIME_BASES={'future_clock','recorded_heartbeat_not_worker_attestation','controller_result_invalid',
    'controller_heartbeat_overdue','scheduled_task_overdue','controller_handled_responsibility',
    'expected_heartbeat_overdue','responsibility_record_only'}

def unknown():
    return {'strategy_version':None,'configured_strategy_version':None,'executed_strategy_version':None,
        'configured_source_revision':None,'executed_source_revision':None,'manifest_sha256':None,
        'strategy_evidence_state':'missing_data','strategy_evidence_as_of':None,'strategy_evidence_reference':None,
        'execution_basis':None,'worker_connection_verified':False,'mandate_reference':None,
        'approved_universe_reference':None,'risk_policy_reference':None,
        'performance':dict.fromkeys(METRICS),'performance_basis':None,'performance_as_of':None,
        'performance_reference':None,'assumed_costs':None,'fees_basis':'unknown'}

def _number(value,*,nonnegative=False):
    if value is None:return None
    if type(value) is not str or not 1<=len(value)<=64:raise ValueError('Bounded metric amount required.')
    result=Decimal(value)
    if not result.is_finite() or abs(result.adjusted())>12 or nonnegative and result<0:raise ValueError('Invalid metric amount.')
    return str(result)

def _digest(value,size=64):
    return value if type(value) is str and re.fullmatch('[a-f0-9]{'+str(size)+'}',value) else None

def _employee_evidence(row,now):
    """Shape/expiry allowlist for the authoritative employee producer projection."""
    result=unknown();at=_epoch(row.get('strategy_evidence_as_of'))
    state=row.get('strategy_evidence_state')
    if _member(state,{'stale','missing_data'}):result['strategy_evidence_state']=state
    if at is not None and now is not None and at<=now and now-at>60:
        result['strategy_evidence_state']='stale'
    if (state!='current' or at is None or now is not None and not 0<=now-at<=60
            or row.get('worker_connection_verified') is not False
            or row.get('execution_basis')!='recorded_evaluation_receipt'):
        return result
    versions={key:_digest(row.get(key)) for key in ('strategy_version','configured_strategy_version',
        'executed_strategy_version','manifest_sha256','strategy_evidence_reference','mandate_reference')}
    sources={key:_digest(row.get(key),40) for key in ('configured_source_revision','executed_source_revision')}
    if (any(v is None for v in (*versions.values(),*sources.values()))
            or versions['strategy_version']!=versions['executed_strategy_version']):return result
    result.update(versions);result.update(sources)
    result.update(strategy_evidence_state='current',strategy_evidence_as_of=at,
        execution_basis='recorded_evaluation_receipt',worker_connection_verified=False)
    for key in ('approved_universe_reference','risk_policy_reference'):result[key]=_digest(row.get(key))
    performance_at=_epoch(row.get('performance_as_of'));basis=row.get('performance_basis')
    reference=_digest(row.get('performance_reference'));values=row.get('performance')
    if (performance_at is None or now is not None and not 0<=now-performance_at<=60
            or not _member(basis,{'paper_local_virtual_cost_v1','broker_reported_accounting'})
            or reference is None or type(values) is not dict or set(values)!=set(METRICS)):
        return result
    metrics={}
    for key in METRICS:
        value=values[key]
        try:
            metrics[key]=(value if type(value) is int and 0<=value<=1000000 else None) if key=='sample_size' else _number(value,nonnegative=key in {'drawdown','exposure','fees'})
        except (ValueError,TypeError,ArithmeticError):metrics[key]=None
    fees_basis=row.get('fees_basis') if _member(row.get('fees_basis'),{'unknown','broker_observed','assumed_virtual_friction'}) else 'unknown'
    if basis!='broker_reported_accounting' or fees_basis!='broker_observed':metrics['fees']=None
    try:costs=_number(row.get('assumed_costs'),nonnegative=True)
    except (ValueError,TypeError,ArithmeticError):costs=None
    result.update(performance=metrics,performance_basis=basis,performance_as_of=performance_at,
        performance_reference=reference,assumed_costs=costs,fees_basis=fees_basis)
    return result

def _employee_runtime(item,row,now):
    basis=row.get('runtime_basis') if _member(row.get('runtime_basis'),RUNTIME_BASES) else 'responsibility_record_only'
    freshness=row.get('runtime_freshness') if _member(row.get('runtime_freshness'),{'current','stale','unverified'}) else 'unverified'
    at=_epoch(row.get('runtime_evidence_as_of'));due=_epoch(row.get('runtime_due_at'))
    task=_token(row.get('last_task_reference'))
    if now is not None and any(value is not None and value>now for value in (item['heartbeat'],item['updated_at'],at)):
        item['state']='stale';freshness='unverified';basis='future_clock'
    elif item['state']=='running':
        freshness='unverified';basis='recorded_heartbeat_not_worker_attestation'
        if now is not None and item['heartbeat'] is not None and now-item['heartbeat']>60:item['state']='stale'
    elif basis=='controller_handled_responsibility' and freshness=='current':
        if at is None or task is None:freshness='unverified'
        elif now is not None and due is not None and now>=due:
            item['state']='stale';freshness='stale';basis='scheduled_task_overdue'
        elif now is not None and now-at>45:
            item['state']='stale';freshness='stale';basis='controller_heartbeat_overdue'
    elif (now is not None and item['heartbeat'] is not None and now-item['heartbeat']>60
            and item['next_trigger'] in {'health_check','startup'}):
        item['state']='stale';freshness='stale';basis='expected_heartbeat_overdue'
    elif freshness=='current':freshness='unverified'
    item.update(runtime_freshness=freshness,runtime_basis=basis,runtime_evidence_as_of=at,
        runtime_due_at=due,last_task_reference=task)

def _compatible_public_projection(snapshot, normalized):
    """Retain exact old feed bytes while allowing readers to add unknown fields."""
    traders=snapshot.get('traders')
    legacy=(type(traders) is list and len(traders)==len(TRADERS)
            and all(type(row) is dict and set(row)==LEGACY_TRADER_KEYS for row in traders))
    if not legacy:return normalized,_traders(snapshot['employees'])
    added=(set(unknown())-{'strategy_version','performance'})|{
        'runtime_freshness','runtime_basis','runtime_evidence_as_of','runtime_due_at','last_task_reference'}
    if any(type(row) is not dict or set(row)&added for row in snapshot['employees']):
        raise ValueError('Mixed legacy and current employee schema')
    expected=[{key:value for key,value in row.items() if key in LEGACY_TRADER_KEYS}
              for row in _traders(normalized['employees'])]
    normalized=json.loads(json.dumps(normalized))
    for row in normalized['employees']:
        for key in added:row.pop(key,None)
    return normalized,expected
# END canonical public evidence helpers


def sanitize_operations(operations, *, now=None):
    """Allowlist public evidence. Never forward logs, inputs, messages or broker records."""
    operations = operations if isinstance(operations, dict) else {}
    result = {key: [] for key in ('employees', 'workflows', 'incidents', 'improvements')}
    seen = set()
    for row in _rows(operations.get('employees'), 15):
        if not isinstance(row, dict):
            continue
        try:
            employee_id = _resolve_employee(row.get('employee_id'))
        except (ValueError, TypeError):
            continue
        if employee_id in seen:
            continue
        seen.add(employee_id)
        item = json.loads(json.dumps(CATALOG[employee_id]))
        state = row.get('state') if _member(row.get('state'), STATES | {'unverified'}) else 'planned'
        heartbeat = _epoch(row.get('heartbeat'))
        task = _token(row.get('current_task'))
        if state == 'running' and (heartbeat is None or task is None):
            state = 'unverified'
        digest = row.get('last_useful_result')
        item.update(state=state, current_task=task,
                    last_useful_result=digest if isinstance(digest, str) and DIGEST.fullmatch(digest) else None,
                    next_trigger=row.get('next_trigger') if _member(row.get('next_trigger'), TRIGGERS) else None,
                    heartbeat=heartbeat, blocker=row.get('blocker') if _member(row.get('blocker'), BLOCKERS) else None,
                    updated_at=_epoch(row.get('updated_at')))
        item.update(_employee_evidence(row,now));_employee_runtime(item,row,now)
        result['employees'].append(item)
    for row in _rows(operations.get('workflows')):
        if not isinstance(row, dict) or not _member(row.get('kind'), GRAPHS):
            continue
        kind = row['kind']
        observer = (type(row.get('version')) is int and row['version'] == 2
                    and row.get('mode') == OBSERVATION_MODE and row.get('execution_authorized') is False
                    and kind in OBSERVATION_GRAPHS)
        recovery = (type(row.get('version')) is int and row['version'] == 3
                    and kind == 'incident' and row.get('mode') == RECOVERY_MODE
                    and row.get('execution_authorized') is False)
        canary = (type(row.get('version')) is int and row['version'] == 3
                  and kind == 'improvement' and row.get('mode') == CANARY_MODE
                  and row.get('execution_authorized') is False)
        nodes = OBSERVATION_GRAPHS[kind] if observer else GRAPHS[kind]
        if (not _token(row.get('run_id')) or not _member(row.get('node'), nodes)
                or not _member(row.get('status'), GRAPH_STATES) or type(row.get('version')) is not int
                or not (row['version'] == 1 or observer or recovery or canary)):
            continue
        history = []
        for event in _rows(row.get('history'), 100):
            if (isinstance(event, dict) and _member(event.get('node'), nodes)
                    and _member(event.get('outcome'), OUTCOMES) and _epoch(event.get('at')) is not None):
                history.append({key: event[key] for key in ('node', 'outcome', 'at')})
        artifacts = [d for d in _rows(row.get('artifact_digests'), 100)
                     if isinstance(d, str) and DIGEST.fullmatch(d)]
        item = {key: row[key] for key in ('run_id', 'kind', 'version', 'status', 'node')}
        item.update(updated_at=_epoch(row.get('updated_at')), deadline_at=_epoch(row.get('deadline_at')),
                    artifact_digests=artifacts, history=history)
        if observer:
            evidence = _epoch(row.get('evidence_as_of'))
            state = row.get('current_evidence') if _member(row.get('current_evidence'), {'current', 'stale', 'unverified'}) else 'unverified'
            if evidence is None or now is not None and evidence > now:
                evidence = None
                state = 'unverified'
            elif now is not None:
                state = 'stale' if now-evidence > (60 if kind == 'trading' else 600) else 'current'
            item.update(mode=OBSERVATION_MODE, execution_authorized=False,
                        evidence_as_of=evidence, current_evidence=state)
        elif recovery:
            item.update(mode=RECOVERY_MODE, execution_authorized=False)
        elif canary:
            item.update(mode=CANARY_MODE, execution_authorized=False)
        result['workflows'].append(item)
    result['improvements'] = [dict(row) for row in result['workflows'] if row['kind'] == 'improvement']
    for row in _rows(operations.get('incidents')):
        if not isinstance(row, dict) or not _token(row.get('incident_id')):
            continue
        if not _member(row.get('state'), {'open', 'resolved'}):
            continue
        owner = row.get('owner')
        owner = 'sug' if _member(owner, {'alexandar', 'alexander'}) else owner
        result['incidents'].append({'incident_id': row['incident_id'], 'state': row['state'],
            'owner': owner if _member(owner, CATALOG) else None,
            'first_seen': _epoch(row.get('first_seen')), 'last_seen': _epoch(row.get('last_seen')),
            'reason': row.get('reason') if _member(row.get('reason'), REASONS) else 'evidence_private'})
    return result


def validate_public_snapshot(snapshot):
    """Fail closed before publication/rendering; return the validated original object."""
    if not isinstance(snapshot, dict) or set(snapshot) != PUBLIC_KEYS or (type(snapshot.get('schema_version')) is not int or snapshot.get('schema_version') != 2):
        raise ValueError('Unexpected public snapshot schema')
    if (not _member(snapshot.get('freshness'), {'current', 'stale', 'unverified'})
            or snapshot.get('mode') != 'paper research'
            or not _member(snapshot.get('desk_state'), {'status unavailable', 'status delayed', 'monitoring',
                'operational', 'attention', 'stopped for review', 'waiting'})):
        raise ValueError('Invalid public status')
    if snapshot['freshness'] != 'unverified' and snapshot['snapshot_at'] is None:
        raise ValueError('Verified freshness requires an observation timestamp')
    if snapshot['desk_state'] == 'operational' and snapshot['freshness'] != 'current':
        raise ValueError('Operational requires current observed evidence')
    if snapshot['snapshot_at'] is not None:
        _timestamp(snapshot['snapshot_at'])
    normalized,traders = _compatible_public_projection(snapshot,sanitize_operations(snapshot))
    if any(snapshot[key] != normalized[key] for key in normalized):
        raise ValueError('Unexpected public operations fields')
    if snapshot['stages'] != _stages():
        raise ValueError('Invalid static graph definition')
    if snapshot['traders'] != traders:
        raise ValueError('Unverified trader scorecard')
    if snapshot['reporting'] != {'coordinator': 'Sug', 'delivery_connection': 'unverified'}:
        raise ValueError('Unverified reporting connection')
    return snapshot


def _stages():
    return [{'name': name, 'state': 'not observed'} for name in
            ('Research', 'Independent validation', 'Deterministic risk', 'Paper execution')]


def _traders(employees):
    by_id = {row['employee_id']: row for row in employees}
    traders = []
    for row in TRADERS:
        employee = by_id.get(row['employee_id'], {})
        traders.append({**row, 'state': employee.get('state', 'unverified'),
                        'approved_universe': employee.get('approved_universe'),
                        **{key:employee.get(key,value) for key,value in unknown().items()}})
    return traders


def refresh_public_snapshot(snapshot, *, now=None):
    validate_public_snapshot(snapshot)
    now = (now or datetime.now(UTC)).astimezone(UTC)
    result = json.loads(json.dumps(snapshot))
    if result['snapshot_at'] is not None:
        age = (now - _timestamp(result['snapshot_at'])).total_seconds()
        if age < 0:
            result['freshness'] = 'unverified'
            result['desk_state'] = 'status unavailable'
        elif age > 600:
            result['freshness'] = 'stale'
            result['desk_state'] = 'status delayed'
    result.update(sanitize_operations(result, now=now.timestamp()))
    result['traders'] = _traders(result['employees'])
    return result


def _timestamp(value):
    if not isinstance(value, str):
        raise TypeError
    result = datetime.fromisoformat(value)
    if result.tzinfo is None or result.utcoffset() is None:
        raise ValueError
    return result.astimezone(UTC)


def build_public_snapshot(receipt, *, now=None, operations=None):
    """Return exact sanitized schema; missing or unreconciled metrics remain unknown."""
    now = (now or datetime.now(UTC)).astimezone(UTC)
    result = {
        'schema_version': 2, 'snapshot_at': None, 'freshness': 'unverified',
        'mode': 'paper research', 'desk_state': 'status unavailable', 'stages': _stages(),
        'reporting': {'coordinator': 'Sug', 'delivery_connection': 'unverified'},
        **sanitize_operations(operations, now=now.timestamp()),
    }
    result['traders'] = _traders(result['employees'])
    try:
        if not isinstance(receipt, dict):
            raise TypeError
        checked = _timestamp(receipt['checked_at'])
        age = (now - checked).total_seconds()
        if age < 0 or not isinstance(receipt.get('state'), str) or not _member(receipt.get('health'), {'ok', 'attention'}):
            raise ValueError
        result['snapshot_at'] = checked.isoformat()
        result['freshness'] = 'current' if age <= 600 else 'stale'
        if age > 600:
            result['desk_state'] = 'status delayed'
        elif receipt['state'] in {'stopped_for_review', 'stopped'}:
            result['desk_state'] = 'stopped for review'
        elif receipt['state'] in {'market_closed', 'outside_entry_window'}:
            result['desk_state'] = 'monitoring'
        elif receipt['state'] in {'waiting_for_data', 'entry_wait'}:
            result['desk_state'] = 'waiting'
        elif receipt['health'] == 'ok' and receipt['state'] in HEALTHY_STATES:
            result['desk_state'] = 'operational'
        else:
            result['desk_state'] = 'attention'
    except (KeyError, TypeError, ValueError, OverflowError):
        pass
    return result


validate_snapshot = validate_public_snapshot
ASSETS = Path(__file__).parent / 'assets'
PAGES = {'home', 'mission', 'processes', 'desk', 'team', 'principles'}


def _assets():
    return ASSETS if ASSETS.is_dir() else Path(__file__).parents[1] / 'owner-dashboard/dist'


def public_url(value):
    """Explicit credential-free HTTPS endpoint; redirects and private literals denied."""
    if not isinstance(value, str) or not 1 <= len(value) <= 2048:
        raise ValueError('Invalid public data URL')
    parts = urlsplit(value)
    if (parts.scheme != 'https' or not parts.hostname or parts.username is not None or parts.password is not None
            or parts.query or parts.fragment or parts.port not in (None, 443)):
        raise ValueError('Credential-free public HTTPS endpoint required')
    host = parts.hostname.lower().rstrip('.')
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        if ('.' not in host or host.endswith(('.local', '.localhost', '.internal'))
                or not re.fullmatch(r'[a-z0-9.-]+', host)):
            raise ValueError('Public host required') from None
    else:
        if not address.is_global:
            raise ValueError('Public host required')
    return value


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def fetch_public_snapshot(url, *, timeout=FETCH_TIMEOUT_SECONDS):
    if type(timeout) not in (int, float) or not 0 < timeout <= FETCH_TIMEOUT_SECONDS:
        raise ValueError('Bounded public request timeout required')
    request = Request(public_url(url), headers={'Accept': 'application/json',
                      'User-Agent': 'BlitzwerkPublicReporting/2'})
    with build_opener(_NoRedirect()).open(request, timeout=timeout) as response:
        data = response.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise ValueError('Snapshot exceeds public byte budget')
    return data


def _decode(data):
    if not isinstance(data, bytes) or len(data) > MAX_BYTES:
        raise ValueError('Bounded public snapshot bytes required')
    snapshot = json.loads(data)
    validate_snapshot(snapshot)
    return snapshot


def load_local_snapshot(path=None, *, now=None):
    path = Path(path) if path is not None else _assets() / 'snapshot.json'
    try:
        if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_BYTES:
            raise ValueError('Missing public snapshot')
        return refresh_public_snapshot(_decode(path.read_bytes()), now=now)
    except (OSError, ValueError, TypeError, RecursionError, OverflowError):
        return build_public_snapshot(None, now=now)


def _observed_time(snapshot, *, now):
    """Validate cached/remote observation time without treating receipt as health."""
    validate_snapshot(snapshot)
    observed = _timestamp(snapshot['snapshot_at']) if snapshot['snapshot_at'] is not None else None
    if observed is not None and observed > now:
        raise ValueError('Future public observation rejected')
    return observed


def current_slot_url(template, *, now):
    """Only the reviewed existing public repository/data branch is supported."""
    if template != STATUS_URL_TEMPLATE:
        raise ValueError('Exact approved data-only URL template required')
    if not isinstance(now, datetime) or now.tzinfo is None or now.utcoffset() is None:
        raise ValueError('Aware UTC slot clock required')
    return template.format(utc_slot=now.astimezone(UTC).strftime('%Y%m%dT%H00Z'))


def load_public_snapshot(url=None, *, url_template=None, cache=None, fetch=None, now=None, local_path=None):
    """Fetch current immutable slot, then latest only as explicit stale fallback.

    At most two requests share a five-second network-timeout/deadline budget.
    Future, regressing or missing observation times never replace newer cached
    evidence. Schema validity is not broker health, source authority or delivery.
    Apply docs/AUTOMATED_ENGINEERING.md to changes and acceptance evidence.
    """
    cache = cache if isinstance(cache, dict) else {}
    now = (now or datetime.now(UTC)).astimezone(UTC)
    if not url and not url_template:
        return load_local_snapshot(local_path, now=now), 'local_snapshot'
    retained, retained_at = cache.get('snapshot'), None
    try:
        retained_at = _observed_time(retained, now=now)
    except (ValueError, TypeError, RecursionError, OverflowError):
        retained = None
    endpoints = []
    try:
        if url_template:
            if url is not None and url != STATUS_LATEST_URL:
                raise ValueError('Fallback must use the same fixed data-only branch')
            endpoints = [(current_slot_url(url_template, now=now), False), (STATUS_LATEST_URL, True)]
        else:
            endpoints = [(public_url(url), False)]
    except (ValueError, TypeError, OverflowError):
        pass
    deadline = time.monotonic() + FETCH_TIMEOUT_SECONDS
    for endpoint, fallback in endpoints[:MAX_FEED_REQUESTS]:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        try:
            raw = fetch(endpoint) if fetch is not None else fetch_public_snapshot(endpoint, timeout=remaining)
            if time.monotonic() >= deadline:
                raise TimeoutError('Public feed deadline exceeded')
            snapshot = _decode(raw)
            observed = _observed_time(snapshot, now=now)
            if url_template and not fallback and observed is None:
                raise ValueError('Current slot has no verified observation')
            if retained_at is not None and (observed is None or observed < retained_at):
                raise ValueError('Public observation would regress cached evidence')
            result = refresh_public_snapshot(snapshot, now=now)
            cache['snapshot'] = json.loads(json.dumps(snapshot))
            if fallback:
                if result['snapshot_at'] is not None:
                    result['freshness'], result['desk_state'] = 'stale', 'status delayed'
                return result, 'remote_unavailable_last_verified'
            return result, 'verified_remote'
        except (OSError, HTTPException, ValueError, TypeError, RecursionError, OverflowError):
            continue
    snapshot = (refresh_public_snapshot(retained, now=now) if retained is not None
                else load_local_snapshot(local_path, now=now))
    if snapshot['snapshot_at'] is not None:
        try:
            _observed_time(snapshot, now=now)
        except (ValueError, TypeError, RecursionError, OverflowError):
            snapshot = build_public_snapshot(None, now=now)
        else:
            snapshot['freshness'], snapshot['desk_state'] = 'stale', 'status delayed'
    return snapshot, 'remote_unavailable_last_verified'


def render_document(snapshot, page='home', *, assets=None):
    validate_snapshot(snapshot)
    assets = Path(assets) if assets is not None else _assets()
    page = page if page in PAGES else 'home'
    html = (assets / 'index.html').read_text()
    css = (assets / 'styles.css').read_text()
    script = (assets / 'app.js').read_text()
    payload = json.dumps(snapshot, sort_keys=True).replace('</', r'<\/')
    html = html.replace('data-page="__PAGE__"', f'data-page="{page}"')
    html = html.replace('<link rel="stylesheet" href="styles.css">', f'<style>{css}</style>')
    return html.replace('<script src="app.js"></script>', f'<script>window.BLITZWERK_DATA={payload};</script><script>{script}</script>')


def export_package(directory):
    """Prepare the existing mirror layout locally, never push or deploy."""
    directory = Path(directory)
    if directory.is_symlink() or not directory.is_dir() or any(directory.iterdir()):
        raise ValueError('Empty existing package directory required')
    assets = directory / 'assets'
    assets.mkdir()
    for name in ('index.html', 'styles.css', 'app.js', 'snapshot.json'):
        shutil.copyfile(_assets() / name, assets / name)
    shutil.copyfile(__file__, directory / 'streamlit_app.py')
    source = Path(__file__).parents[1]
    shutil.copyfile(source / 'requirements.txt', directory / 'requirements.txt')
    shutil.copyfile(Path(__file__).with_name('README.md'), directory / 'README.md')
    # Freeze only a validated public snapshot. No runtime paths are discovered.
    _decode((assets / 'snapshot.json').read_bytes())
    return directory


def configured_public_feed(environment=None):
    """Default to the existing public feed only when both settings are absent."""
    environment = os.environ if environment is None else environment
    if 'PUBLIC_STATUS_URL' not in environment and 'PUBLIC_STATUS_URL_TEMPLATE' not in environment:
        return STATUS_LATEST_URL, STATUS_URL_TEMPLATE
    return environment.get('PUBLIC_STATUS_URL'), environment.get('PUBLIC_STATUS_URL_TEMPLATE')


def main():
    import streamlit as st

    st.set_page_config(page_title='Blitzwerk Kapital', page_icon='⚡', layout='wide', initial_sidebar_state='collapsed')
    st.markdown('<style>#MainMenu,header,footer{visibility:hidden}.block-container{padding:0;max-width:none}</style>', unsafe_allow_html=True)
    if 'public_snapshot_cache' not in st.session_state:
        st.session_state['public_snapshot_cache'] = {}

    @st.fragment(run_every='30s')
    def reporting_view():
        url, template = configured_public_feed()
        snapshot, status = load_public_snapshot(url, url_template=template,
                         cache=st.session_state['public_snapshot_cache'], now=datetime.now(UTC))
        if status == 'remote_unavailable_last_verified':
            st.warning('Reporting feed unavailable. Showing the last verified public snapshot; current engine state is unknown.')
        st.iframe(render_document(snapshot, page=st.query_params.get('page', 'home')),
                  height='content', alt='Blitzwerk PAPER operations and verified status')
    reporting_view()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Read-only public mirror')
    parser.add_argument('--export-directory')
    args, _unknown = parser.parse_known_args()
    if args.export_directory:
        export_package(args.export_directory)
    else:
        main()
