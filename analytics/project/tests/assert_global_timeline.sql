with expected as (
    select run_key, snapshot_timestamp, row_number() over w as seq,
        lag(run_key) over w as prev
    from {{ ref('stg_collection_run') }}
    window w as (order by snapshot_timestamp)
)
select coalesce(e.run_key, c.run_key) as run_key
from expected as e full outer join {{ ref('int_snapshot_context') }} as c using (run_key)
where e.run_key is null or c.run_key is null or e.seq is distinct from c.snapshot_sequence
   or e.prev is distinct from c.previous_global_run_key or c.observation_rows <> c.declared_rows
