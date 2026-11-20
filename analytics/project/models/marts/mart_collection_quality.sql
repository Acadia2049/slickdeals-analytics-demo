select run_key, run_id, snapshot_timestamp, snapshot_sequence, raw_schema_version, parser_version, data_scope,
    declared_rows, verified_rows, observation_rows, candidate_records, omitted_count, is_truncated,
    volume_status, volume_reason, selector_failures, required_field_completeness,
    validation_status, verification_status, verified_at, evidence_path, raw_uri, raw_sha256, download_sha256,
    previous_global_run_key, global_gap_hours, pair_status, pair_eligible,
    case when is_truncated then 'truncated' when not is_truncated then 'complete'
        else 'unknown' end as truncation_state,
    coalesce(volume_status, 'unknown') as volume_state
from {{ ref('int_snapshot_context') }}
