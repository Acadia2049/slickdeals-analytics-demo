select
    run_key, run_id,
    scheduled_at at time zone 'UTC' as scheduled_at,
    observed_at at time zone 'UTC' as observed_at,
    completed_at at time zone 'UTC' as completed_at,
    snapshot_timestamp at time zone 'UTC' as snapshot_timestamp,
    schema_version as manifest_schema_version,
    raw_schema_version as declared_raw_schema_version,
    case when schema_version = 1 and raw_schema_version is null then 1
         else raw_schema_version end as raw_schema_version,
    parser_version, data_scope, row_count as declared_rows,
    candidate_records, omitted_count, is_truncated, validation_status,
    raw_location as raw_uri, raw_sha256, verified_sha256 as download_sha256,
    selector_failures, required_field_completeness,
    volume_assessment.status as volume_status, volume_assessment.reason as volume_reason
from {{ source('frozen_batch', 'collection_runs') }}
