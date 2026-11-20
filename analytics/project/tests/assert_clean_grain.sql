select deal_id, snapshot_timestamp from {{ ref('stg_clean_observation') }}
group by all having count(*) <> 1
