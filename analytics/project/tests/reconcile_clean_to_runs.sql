-- Check every row, including disagreements within one snapshot and missing parents.
with checks as (
    select coalesce(r.snapshot_timestamp, o.snapshot_timestamp) as snapshot_timestamp,
        r.run_key, r.declared_rows, count(o.snapshot_timestamp) as actual_rows,
        count(*) filter (where o.raw_schema_version is distinct from r.raw_schema_version
            or o.parser_version is distinct from r.parser_version
            or o.data_scope is distinct from r.data_scope
            or o.is_truncated is distinct from r.is_truncated
            or o.omitted_count is distinct from r.omitted_count
            or o.candidate_records is distinct from r.candidate_records) as mismatches
    from {{ ref('stg_collection_run') }} as r
    full outer join {{ ref('stg_clean_observation') }} as o using (snapshot_timestamp)
    group by all
)
select * from checks
where run_key is null or declared_rows is distinct from actual_rows or mismatches > 0
