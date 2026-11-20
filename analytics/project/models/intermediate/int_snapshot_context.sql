{{ config(materialized='table') }}

with counts as (
    select snapshot_timestamp, count(*) as observation_rows
    from {{ ref('stg_clean_observation') }}
    group by snapshot_timestamp
), verified as (
    select r.*, v.verified_at, v.verified_rows, v.verification_status, v.evidence_path,
        coalesce(c.observation_rows, 0) as observation_rows
    from {{ ref('stg_collection_run') }} as r
    join {{ ref('stg_run_verification') }} as v
      on v.run_key = r.run_key and v.run_id = r.run_id
     and v.raw_sha256 = r.raw_sha256 and v.observed_at = r.snapshot_timestamp
     and v.raw_uri = r.raw_uri and v.verified_rows = r.declared_rows
    left join counts as c on c.snapshot_timestamp = r.snapshot_timestamp
    where v.verification_status = 'success' and r.validation_status = 'passed'
      and r.raw_sha256 = r.download_sha256
), sequenced as (
    select *, row_number() over timeline as snapshot_sequence,
        lag(run_key) over timeline as previous_global_run_key,
        lag(snapshot_timestamp) over timeline as previous_global_snapshot_timestamp,
        lag(raw_schema_version) over timeline as previous_global_version,
        lag(parser_version) over timeline as previous_global_parser,
        lag(data_scope) over timeline as previous_global_scope,
        lag(is_truncated) over timeline as previous_global_truncated
    from verified
    window timeline as (order by snapshot_timestamp)
), intervals as (
    select *,
        epoch(snapshot_timestamp - previous_global_snapshot_timestamp) / 3600.0 as global_gap_hours,
        coalesce(raw_schema_version = 2 and parser_version = 'frontpage-v2'
            and data_scope = 'server_html_frontpage_slickdeals', false) as is_business_cohort
    from sequenced
), classified as (
    select *, case
        when previous_global_run_key is null then 'first_snapshot'
        when raw_schema_version is distinct from 2 or raw_schema_version is distinct from previous_global_version
            or data_scope is distinct from 'server_html_frontpage_slickdeals'
            or data_scope is distinct from previous_global_scope then 'version_or_scope'
        when not is_business_cohort or parser_version is distinct from previous_global_parser then 'parser_boundary'
        when is_truncated is distinct from false or previous_global_truncated is distinct from false
            then 'truncation_or_unknown'
        when global_gap_hours not between 1.5 and 2.5 then 'elapsed_time'
        else 'eligible' end as pair_status
    from intervals
)
select *, pair_status = 'eligible' as pair_eligible
from classified
