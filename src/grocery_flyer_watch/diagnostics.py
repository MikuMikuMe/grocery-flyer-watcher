"""Opt-in, private, data-minimizing JSON diagnostics. Never an authorization ledger.

Arguments, return values, exception messages, paths and provider payloads are NOT
logged. Only finite source-controlled codes are exposed. Logging cannot change an
operation's result, exception or retry policy. Enable with FLYER_DIAGNOSTICS=1.
"""
from __future__ import annotations
from contextvars import ContextVar
from datetime import datetime, timezone
from functools import wraps
import json
import os
import sys
import subprocess
from time import monotonic
from uuid import uuid4

SAFE_CODES = frozenset({
    'action_schema',
    'actual_attempt_history_required',
    'actual_campaign_history_required',
    'actual_connector_reads_required',
    'actual_delivery_receipt_required',
    'actual_pinned_assessment_read_required',
    'actual_recipient_eligibility_evidence_required',
    'actual_sent_lookup_required',
    'alternate_sources_missing',
    'assessment_mismatch_or_unqualified',
    'assessment_publication_scope_mismatch',
    'assessment_read_hash_mismatch',
    'assessment_read_proof_schema',
    'assessment_read_stale',
    'assessment_timestamp_in_future',
    'attempt_history_status_required',
    'audit_schema',
    'authorization_required',
    'authorized_recipient_list_required',
    'authorized_roster_required',
    'baseline_content_hash_required',
    'baseline_coverage_missing',
    'baseline_missing',
    'baseline_offer_inventory_missing',
    'baseline_offer_schema',
    'baseline_reference_mismatch',
    'baseline_schema',
    'baseline_wrong_market_or_retailer',
    'baseline_wrong_source',
    'blocked_page_invented_content',
    'blocked_unit_not_explained',
    'body_differs_from_reviewed_selection',
    'both_connector_copy_and_proof_required',
    'bundle_changed_after_second_review',
    'bundle_schema',
    'bundle_version',
    'callable_schema_evidence_required',
    'campaign_history_check_stale',
    'candidate_id',
    'candidate_not_in_page_inventory',
    'candidate_priority',
    'candidate_schema',
    'candidate_source_unreviewed',
    'capability_schema',
    'capability_version',
    'cash_price_excerpt_missing',
    'cash_price_not_in_bound_excerpt',
    'cash_price_not_in_evidence',
    'change_evidence_missing',
    'change_schema',
    'change_trigger_ids',
    'changed_offer_has_no_useful_selected_purchase',
    'claim_differs_from_source_facts',
    'collection_period_label',
    'comparison_additional_attribute_mismatch',
    'comparison_attribute',
    'comparison_attribute_not_in_evidence',
    'comparison_dimensions_missing',
    'comparison_kind',
    'comparison_pack_mismatch',
    'comparison_period_not_equivalent',
    'comparison_price_not_in_evidence',
    'comparison_quote',
    'comparison_retailer',
    'comparison_schema',
    'comparison_unit_mismatch',
    'comparison_unit_not_in_evidence',
    'comparison_validity_evidence_missing',
    'comparison_window_missing',
    'complete_sent_lookup_required',
    'condition_not_in_evidence',
    'connector_artifact_hashes_required',
    'connector_copy_hash_mismatch',
    'connector_copy_missing',
    'connector_publication_proof_schema',
    'connector_publication_proof_stale',
    'connector_publication_scope_mismatch',
    'coverage_completeness_missing',
    'coverage_schema',
    'coverage_unit_schema',
    'critical_page_unavailable',
    'dated_flyer_item_dates_required',
    'delivery_uncertain_reconcile_sent_history_first',
    'department_leads_missing',
    'department_missing',
    'department_not_accounted_for',
    'departments_missing',
    'discovery_schema',
    'duplicate_baseline_offer',
    'duplicate_candidate',
    'duplicate_json_key',
    'duplicate_profile',
    'duplicate_provider',
    'duplicate_recipients',
    'duplicate_selection',
    'duplicate_source_unit',
    'edition_not_newer_than_baseline',
    'edition_schema',
    'empty_omission_audit',
    'exact_pack_missing',
    'existing_collection_history_required',
    'expired_item_promotion',
    'expired_or_stale_comparison',
    'fact_proof_schema',
    'factual_claim_in_unbound_assessment',
    'first_read_missing',
    'forbidden_phrases_schema',
    'front_or_back_not_accounted_for',
    'header_dates_do_not_match_edition',
    'ineligible_purchase_channel',
    'input_missing_or_too_large',
    'invalid_cash_price',
    'invalid_date',
    'invalid_delivery_outcome',
    'invalid_delivery_ticket',
    'invalid_item_window',
    'invalid_json',
    'invalid_observation_time',
    'invalid_or_expired_edition',
    'invalid_pack_quantity',
    'invalid_source_scope',
    'invalid_timestamp',
    'invented_collection_dates',
    'item_dates_outside_edition',
    'item_evidence_ref_missing',
    'item_terms_or_channel_evidence_missing',
    'journal_corrupt',
    'journal_schema_incompatible',
    'json_object_required',
    'local_purchase_claim_not_verified',
    'local_scope_not_assessed',
    'material_change_cannot_change_edition',
    'material_change_needs_known_triggers',
    'meat_comparison_needs_cut_and_bone',
    'missing_header',
    'new_edition_uses_period_not_shortlist_identity',
    'new_to_partial_coverage_is_not_new_offer',
    'no_candidates',
    'no_qualifying_change',
    'no_recipients',
    'no_source_content_change',
    'non_equivalent_comparison',
    'nonfinite_json',
    'not_uncertain_delivery',
    'observation_timezone_required',
    'outgoing_body_differs_from_reviewed_selection',
    'overlapping_workers_not_supported',
    'pack_not_in_evidence',
    'page_candidate_inventory_mismatch',
    'page_content_hash_required',
    'page_evidence_missing',
    'page_proof_mismatch',
    'page_proof_schema',
    'page_proofs_missing',
    'page_role',
    'partial_coverage_must_be_disclosed',
    'partial_exception_missing',
    'partial_exception_reason_missing',
    'pending_event_content_or_publication_changed',
    'price_and_unit_not_bound_together',
    'price_excerpt_not_in_source',
    'price_unit_not_in_evidence',
    'pricing_unit',
    'private_data_in_public_field',
    'private_data_in_public_output',
    'private_delivery_context_schema',
    'private_history_not_initialized_seed_before_delivery',
    'private_phrase_in_public_output',
    'private_receipt_schema',
    'private_state_must_be_outside_checkout',
    'private_state_symlink',
    'product_description_not_in_evidence',
    'profile_scope_mismatch',
    'prominence_not_assessed',
    'prominent_or_strong_offer_omitted_without_audit',
    'promotion_identity_missing',
    'provider_schema',
    'public_artifact_differs_from_reviewed_selection',
    'public_assessment_missing',
    'public_privacy_review_missing',
    'publication_must_be_content_addressed',
    'publication_not_verified',
    'publication_path',
    'publication_receipt_schema',
    'publication_redirect_refused',
    'publication_repository',
    'publication_requires_commit_not_branch',
    'publication_too_large',
    'published_artifact_mismatch',
    'purchase_channel',
    'purchase_condition',
    'recipient_not_in_private_configuration',
    'recipient_refused',
    'recipient_schema',
    'reconciliation_evidence_required',
    'reconciliation_lookup_stale',
    'reconciliation_schema',
    'rediscover_current_callable_schemas',
    'regular_or_saving_price_not_checkout',
    'reorder_restock_or_editorial_not_material',
    'retry_alternate_sources_before_partial',
    'review_changed_during_preflight',
    'review_plan_too_large',
    'review_schema',
    'review_version',
    'roundup_mostly_weak_or_unverified',
    'same_offer_counted_twice',
    'saving_amount_is_not_cash_price',
    'second_pass_coverage_gap',
    'second_pass_missing',
    'second_pass_reused_first_read',
    'second_source_read_missing',
    'seed_dates',
    'seed_profile_mismatch',
    'seed_scope_missing',
    'selected_fact_evidence_missing',
    'selected_offer_not_rechecked_today',
    'selected_source_mismatch',
    'selection_decisions_mismatch',
    'selection_reason_missing',
    'selection_section',
    'selection_size',
    'sent_lookup_result_required',
    'sent_lookup_schema',
    'sent_lookup_scope_mismatch',
    'sent_lookup_stale',
    'server_rejected_message',
    'shortfall_not_reviewed',
    'shortfall_schema',
    'shortfall_unexplained',
    'smtp_acceptance_unknown',
    'smtp_config_invalid',
    'smtp_not_started',
    'smtp_tls_required',
    'source_content_hash_required',
    'source_facts_schema',
    'source_inventory_missing',
    'source_kind',
    'source_page_proof_missing',
    'source_pages_missing',
    'source_product_missing',
    'source_quote_missing',
    'source_url',
    'spurious_partial_exception',
    'spurious_partial_note',
    'stale_source_evidence',
    'terms_schema',
    'timezone_required',
    'unassessed_department_lead',
    'unaudited_smtp_disabled_use_quality_send',
    'uncertain_attempt_requires_provider_reconciliation',
    'unclean_source_url',
    'undated_collection_not_new_edition',
    'unexpected_comparison_evidence',
    'unexpected_publication_resource',
    'unexpected_shortfall_override',
    'unit_candidates',
    'unknown_comparison_attribute',
    'unknown_local_eligibility_cannot_be_best_buy',
    'unknown_run_outcome',
    'unknown_state_backend',
    'unresolved_audit_findings',
    'unresolved_candidate',
    'unreviewed_source_unit',
    'useful_candidates_excluded_from_short_digest',
})

LEGACY_CODES = {
    'Unknown config fields; credentials belong in environment variables':
        'config_unknown_fields',
    'Configure at least two source URLs':
        'config_sources_missing',
    'Configure multiple source hosts':
        'config_source_diversity_missing',
    'collector must be an argv array, not a shell string':
        'config_collector_argv_invalid',
    'Private state must be outside the public output directory':
        'private_state_inside_public_output',
    'Unsupported publication or notification adapter':
        'config_adapter_unsupported',
    'No live collector configured; use --input for verified JSON':
        'collector_not_configured',
    'Collector failed; its private output was not logged':
        'collector_nonzero_exit',
    'Collector output too large':
        'collector_output_too_large',
    'Collector could not verify current sources':
        'source_verification_unavailable',
    'Expected a bounded snapshot list':
        'collector_snapshot_list_invalid',
    'Collector returned a different market or retailer':
        'snapshot_scope_mismatch',
    'Expired flyer; refusing to send it as a new offer':
        'snapshot_expired',
    'Preview is outside the 14-day horizon':
        'snapshot_preview_too_far',
    'Unconfigured source host':
        'source_host_unconfigured',
    'Preview needs corroborating sources':
        'preview_corroboration_missing',
    'Another run or stale lock exists':
        'state_lock_busy',
    'Unsupported private state':
        'state_schema_unsupported',
    'Unsafe archive path':
        'publication_path_unsafe',
    'Git output must be <repo>/public and state must be outside repo':
        'publication_state_path_unsafe',
    'Refusing to commit an existing staged change':
        'publication_staged_changes_present',
    'Seed does not match profile':
        'seed_scope_mismatch',
}

_context: ContextVar = ContextVar("flyer_diagnostics", default=None)


def safe_code(exc: BaseException) -> str:
    """Reject arbitrary strings even from an accidentally misused gate exception."""
    cls = type(exc)
    if cls.__module__ in {
        "grocery_flyer_watch.review", "grocery_flyer_watch.runtime_preflight",
        "grocery_flyer_watch.reviewed_delivery", "__main__",
    } and cls.__name__ in {"ReviewError", "PreflightError", "KnownDeliveryFailure", "AmbiguousDelivery"}:
        if len(exc.args) == 1 and type(exc.args[0]) is str and exc.args[0] in SAFE_CODES:
            return exc.args[0]
    if type(exc) in {ValueError, RuntimeError} and len(exc.args) == 1 and type(exc.args[0]) is str:
        if exc.args[0] in LEGACY_CODES:
            return LEGACY_CODES[exc.args[0]]
    if isinstance(exc, subprocess.TimeoutExpired):
        return "subprocess_timeout"
    if isinstance(exc, subprocess.CalledProcessError):
        return "subprocess_nonzero_exit"
    if isinstance(exc, KeyboardInterrupt):
        return "operation_interrupted"
    if isinstance(exc, TimeoutError):
        return "operation_timeout"
    if isinstance(exc, PermissionError):
        return "filesystem_permission_denied"
    if isinstance(exc, FileNotFoundError):
        return "input_or_executable_missing"
    if isinstance(exc, json.JSONDecodeError):
        return "invalid_json"
    return "unexpected_error"


def safe_error_type(exc: BaseException) -> str:
    # Class names can be supplied by plugins too. Never copy arbitrary identifiers.
    known = {"ValueError", "TypeError", "KeyError", "OSError", "FileNotFoundError",
             "PermissionError", "TimeoutError", "JSONDecodeError", "RuntimeError",
             "CalledProcessError", "TimeoutExpired", "ReviewError", "PreflightError",
             "KnownDeliveryFailure", "AmbiguousDelivery", "KeyboardInterrupt", "SystemExit"}
    return type(exc).__name__ if type(exc).__name__ in known else "Exception"


def emit(stage: str, outcome: str, *, exc: BaseException | None = None,
         duration_ms: float | None = None, code: str | None = None) -> None:
    """Emit only allowed vocabulary; this function accepts no arbitrary metadata."""
    if os.environ.get("FLYER_DIAGNOSTICS") != "1":
        return
    try:
        context = _context.get()
        if context is None:
            context = {"run_id": uuid4().hex, "sequence": 0}
        context["sequence"] += 1
        record = {"schema": "flyer-diagnostic-v1", "run_id": context["run_id"],
                  "sequence": context["sequence"],
                  "timestamp": datetime.now(timezone.utc).isoformat(),
                  "stage": stage if stage in STAGES else "operation",
                  "outcome": outcome if outcome in OUTCOMES else "unknown"}
        if duration_ms is not None:
            record["duration_ms"] = max(0, round(duration_ms, 3))
        if exc is not None:
            record.update(code=safe_code(exc), error_type=safe_error_type(exc))
        elif code in SAFE_CODES or code in EVENT_CODES:
            record["code"] = code
        sys.stderr.write(json.dumps(record, sort_keys=True, allow_nan=False) + "\n")
        sys.stderr.flush()
    except Exception:
        # Diagnostic sink failure must not fail or retry a completed side effect.
        pass


def _duration(started):
    try:
        return (monotonic() - started) * 1000
    except Exception:
        return None


def traced(stage: str):
    """Trace synchronous phase boundaries without inspecting data or changing errors."""
    def decorate(function):
        @wraps(function)
        def wrapper(*args, **kwargs):
            if os.environ.get("FLYER_DIAGNOSTICS") != "1":
                return function(*args, **kwargs)
            token = None
            try:
                started = monotonic()
                if _context.get() is None:
                    token = _context.set({"run_id": uuid4().hex, "sequence": 0})
            except Exception:
                return function(*args, **kwargs)
            emit(stage, "started")
            try:
                result = function(*args, **kwargs)
            except BaseException as exc:
                emit(stage, "interrupted" if isinstance(exc, (KeyboardInterrupt, SystemExit)) else "failed",
                     exc=exc, duration_ms=_duration(started))
                raise
            else:
                # Completed means returned, NOT approved, published or sent.
                emit(stage, "completed", duration_ms=_duration(started))
                return result
            finally:
                if token is not None:
                    _context.reset(token)
        return wrapper
    return decorate

STAGES = frozenset({
    'artifacts.generate',
    'artifacts.verify',
    'artifacts.write',
    'assessment.generate',
    'body.verify',
    'cli',
    'collector.read',
    'config.load',
    'delivery.authorize',
    'delivery.outcome',
    'delivery.preflight',
    'delivery.send',
    'delivery.transport',
    'input.read',
    'operation',
    'private_path.validate',
    'profile',
    'profiles.run',
    'publication.bridge',
    'publication.fetch',
    'publication.urls',
    'publication.verify',
    'publication.write',
    'quality.check',
    'quality.cli',
    'report.render',
    'repository.authorize',
    'repository.cli',
    'review.cli',
    'review.project',
    'review.render',
    'review.validate',
    'run',
    'runtime.capabilities',
    'runtime.cli',
    'runtime.preflight',
    'runtime.state',
    'snapshot.compare',
    'snapshot.read',
    'snapshot.scope',
    'snapshot.validate',
    'state.finish',
    'state.lock',
    'state.read',
    'state.reconcile',
    'state.reserve',
    'state.seed',
    'state.write',
})
OUTCOMES = frozenset(("started", "completed", "failed", "interrupted", "blocked", "uncertain", "accepted", "skipped", "unknown"))
EVENT_CODES = frozenset(("already_handled", "profile_disabled", "profile_failed", "transport_accepted", "acceptance_unknown", "delivery_blocked", "delivery_failed", "state_ack_failed", "cli_failed"))
