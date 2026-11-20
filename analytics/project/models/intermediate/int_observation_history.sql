{{ config(materialized='view') }}

with observations as (
    select o.*,
        s.run_key,
        s.run_id,
        s.snapshot_sequence,
        s.previous_global_run_key,
        s.previous_global_snapshot_timestamp,
        s.global_gap_hours,
        s.pair_status,
        s.pair_eligible,
        s.is_business_cohort,
        s.raw_uri,
        s.raw_sha256,
        s.verification_status,
        s.verified_at,
        s.evidence_path,
        s.volume_status
    from {{ ref('stg_clean_observation') }} as o
    join {{ ref('int_snapshot_context') }} as s using (snapshot_timestamp)
), history as (
    select *,
        lag(run_key) over deal_history as previous_run_key,
        lag(snapshot_timestamp) over deal_history as previous_snapshot_timestamp,
        lag(snapshot_sequence) over deal_history as previous_snapshot_sequence,
        lag(store_normalized) over deal_history as previous_store_normalized,
        lag(title) over deal_history as previous_title,
        lag(title_link) over deal_history as previous_title_link,
        lag(deal_finder) over deal_history as previous_deal_finder,
        lag(comment_count) over deal_history as previous_comment_count,
        lag(vote_count) over deal_history as previous_vote_count,
        lag(views) over deal_history as previous_views,
        lag(deal_price_raw) over deal_history as previous_deal_price_raw,
        lag(deal_price_amount) over deal_history as previous_deal_price_amount,
        lag(deal_price_type) over deal_history as previous_deal_price_type,
        lag(price_parse_success) over deal_history as previous_price_parse_success,
        lag(record_hash) over deal_history as previous_record_hash,
        count(distinct store_normalized) filter (where is_business_cohort)
            over (partition by deal_id) > 1 as merchant_changed_in_v2,
        md5(store_normalized) as merchant_id,
        min(store) over (partition by store_normalized) as merchant_name
    from observations
    window deal_history as (partition by deal_id order by snapshot_sequence)
), distances as (
    select *, snapshot_sequence - previous_snapshot_sequence as snapshot_steps,
        epoch(snapshot_timestamp - previous_snapshot_timestamp) / 3600.0 as observation_gap_hours,
        store_normalized <> previous_store_normalized as merchant_changed_since_observation
    from history
)
select *, case
        when previous_run_key is null then 'first_observation'
        when snapshot_steps = 1 then 'consecutive_snapshot'
        else 'reappeared_after_gap' end as observation_context,
    case when snapshot_steps = 1 then comment_count::bigint - previous_comment_count end as audit_comment_delta,
    case when snapshot_steps = 1 then vote_count::bigint - previous_vote_count end as audit_vote_delta,
    case when snapshot_steps = 1 then views - previous_views end as audit_views_delta
from distances
