select
    run_key, run_id, raw_uri, raw_sha256, row_count as verified_rows,
    observed_at at time zone 'UTC' as observed_at,
    verified_at at time zone 'UTC' as verified_at,
    status as verification_status,
    regexp_extract(filename, '/run_id=([^/]+)/verification[.]json$', 1) as directory_run_key,
    regexp_extract(filename, '(source/evidence/.+/verification[.]json)$', 1) as evidence_path
from {{ source('frozen_batch', 'run_verifications') }}
