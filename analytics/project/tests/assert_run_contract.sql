select run_key from {{ ref('stg_collection_run') }}
where declared_rows is null or declared_rows <= 0
    or candidate_records is null or candidate_records < declared_rows
    or omitted_count is distinct from candidate_records - declared_rows
    or is_truncated is distinct from (candidate_records > declared_rows)
    or raw_schema_version is null or raw_schema_version not in (1, 2)
    or (manifest_schema_version = 1 and (raw_schema_version <> 1 or parser_version is not null or data_scope is not null))
    or (manifest_schema_version = 2 and (raw_schema_version <> 2 or declared_raw_schema_version is null
        or parser_version is null or data_scope is null or is_truncated))
    or manifest_schema_version is null or manifest_schema_version not in (1, 2)
