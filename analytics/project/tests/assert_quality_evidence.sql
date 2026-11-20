select coalesce(v.run_key, q.run_key) as run_key
from {{ ref('stg_run_verification') }} as v
full join {{ ref('mart_collection_quality') }} as q using (run_key)
where v.run_key is null or q.run_key is null
   or (v.run_id, v.verified_at, v.raw_uri, v.raw_sha256, v.evidence_path, v.verified_rows)
      is distinct from (q.run_id, q.verified_at, q.raw_uri, q.raw_sha256, q.evidence_path, q.observation_rows)
   or q.verified_rows is distinct from q.declared_rows or q.download_sha256 is distinct from q.raw_sha256
