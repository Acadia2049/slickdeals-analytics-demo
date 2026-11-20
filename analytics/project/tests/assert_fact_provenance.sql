select f.deal_id, f.run_key
from {{ ref('fct_deal_observation') }} f
left join {{ ref('stg_run_verification') }} v on f.run_key = v.run_key
where v.run_key is null or f.run_id is distinct from v.run_id
   or f.raw_uri is distinct from v.raw_uri or f.raw_sha256 is distinct from v.raw_sha256
   or f.evidence_path is distinct from v.evidence_path or f.snapshot_timestamp is distinct from v.observed_at
