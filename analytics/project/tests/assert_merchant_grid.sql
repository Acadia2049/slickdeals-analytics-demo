with snapshots as (
    select * from {{ ref('int_snapshot_context') }} where is_business_cohort
), merchants as (
    select distinct merchant_id from {{ ref('fct_deal_observation') }} where is_business_cohort
), grid as (
    select s.run_key, m.merchant_id, s.observation_rows from snapshots s cross join merchants m
), actual as (
    select *, count(*) over (partition by merchant_id, run_key) as multiplicity,
        sum(merchant_deals) over (partition by run_key) as all_merchants
    from {{ ref('mart_merchant_snapshot') }}
)
select coalesce(g.run_key, a.run_key) as run_key, coalesce(g.merchant_id, a.merchant_id) as merchant_id
from grid g full join actual a using (run_key, merchant_id)
where g.run_key is null or a.run_key is null or multiplicity <> 1
   or full_snapshot_deals is distinct from g.observation_rows or all_merchants is distinct from full_snapshot_deals
   or merchant_share is distinct from merchant_deals::double / nullif(full_snapshot_deals, 0)
   or (pair_eligible and (previous_memberships is null or retained_memberships is null or transferred_out is null
       or retained_memberships + transferred_out > previous_memberships))
   or (not pair_eligible and (previous_memberships is not null or retained_memberships is not null or transferred_out is not null))
