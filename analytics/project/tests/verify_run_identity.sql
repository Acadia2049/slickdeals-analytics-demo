-- Full outer join exposes missing evidence as well as orphaned or conflicting copies.
select coalesce(r.run_key, v.run_key) as run_key
from {{ ref('stg_collection_run') }} as r
full outer join {{ ref('stg_run_verification') }} as v using (run_key)
where r.run_key is null or v.run_key is null
   or r.run_id is distinct from v.run_id
   or v.directory_run_key is distinct from v.run_key
   or v.evidence_path = '' or v.verified_at is null
   or v.verification_status is distinct from 'success'
   or r.validation_status is distinct from 'passed'
   or r.snapshot_timestamp is distinct from v.observed_at
   or r.snapshot_timestamp is distinct from r.observed_at
   or r.declared_rows is distinct from v.verified_rows
   or r.raw_uri is distinct from v.raw_uri or r.raw_uri is null
   or not coalesce(regexp_full_match(r.raw_sha256, '[0-9a-f]{64}'), false)
   or r.raw_sha256 is distinct from v.raw_sha256
   or r.raw_sha256 is distinct from r.download_sha256
