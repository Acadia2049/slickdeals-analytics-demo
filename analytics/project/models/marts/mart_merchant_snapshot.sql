with snapshots as (
    select * from {{ ref('int_snapshot_context') }} where is_business_cohort
), observations as (
    select deal_id, run_key, merchant_id, merchant_name
    from {{ ref('fct_deal_observation') }} where is_business_cohort
), merchants as (
    select distinct merchant_id, merchant_name from observations
), appearances as (
    select run_key, merchant_id, count(*) as merchant_deals
    from observations group by run_key, merchant_id
), entries as (
    select first_run_key as run_key, first_merchant_id as merchant_id,
        count(*) filter (where is_newly_observed) as newly_observed,
        count(*) filter (where is_newly_observed and seen_in_legacy) as newly_seen_in_legacy,
        count(*) filter (where is_baseline_deal) as baseline_deals
    from {{ ref('mart_deal_first_observed') }} group by first_run_key, first_merchant_id
), membership as (
    select s.run_key, prev.merchant_id, count(*) as previous_memberships,
        count(*) filter (where cur.merchant_id = prev.merchant_id) as retained_memberships,
        count(*) filter (where cur.merchant_id <> prev.merchant_id) as transferred_out
    from snapshots as s
    join observations as prev on prev.run_key = s.previous_global_run_key
    left join observations as cur on cur.run_key = s.run_key and cur.deal_id = prev.deal_id
    where s.pair_eligible group by s.run_key, prev.merchant_id
)
select m.merchant_id, m.merchant_name, s.run_key, s.snapshot_timestamp, s.snapshot_sequence,
    s.previous_global_run_key, s.pair_eligible, s.observation_rows as full_snapshot_deals,
    coalesce(a.merchant_deals, 0) as merchant_deals,
    coalesce(a.merchant_deals, 0)::double / nullif(s.observation_rows, 0) as merchant_share,
    coalesce(e.newly_observed, 0) as newly_observed, coalesce(e.baseline_deals, 0) as baseline_deals,
    coalesce(e.newly_seen_in_legacy, 0) as newly_seen_in_legacy,
    case when s.pair_eligible then coalesce(k.previous_memberships, 0) end as previous_memberships,
    case when s.pair_eligible then coalesce(k.retained_memberships, 0) end as retained_memberships,
    case when s.pair_eligible then coalesce(k.transferred_out, 0) end as transferred_out
from snapshots as s cross join merchants as m
left join appearances as a on a.run_key = s.run_key and a.merchant_id = m.merchant_id
left join entries as e on e.run_key = s.run_key and e.merchant_id = m.merchant_id
left join membership as k on k.run_key = s.run_key and k.merchant_id = m.merchant_id
