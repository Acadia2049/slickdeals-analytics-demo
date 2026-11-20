with fact as (
    select * from {{ ref('fct_deal_observation') }} where is_business_cohort
), expected as (
    select deal_id, min(snapshot_sequence) as seq from fact group by deal_id
)
select coalesce(e.deal_id, d.deal_id) as deal_id
from expected as e full join {{ ref('mart_deal_first_observed') }} as d using (deal_id)
left join fact as f on f.deal_id = d.deal_id and f.snapshot_sequence = e.seq
where e.seq is distinct from d.first_sequence or f.run_key is distinct from d.first_run_key
   or (f.snapshot_timestamp, f.merchant_id, f.title, f.title_link, f.deal_price_raw,
       f.deal_price_type, f.deal_price_amount, f.price_parse_success, f.record_hash)
      is distinct from (d.first_observed_at, d.first_merchant_id, d.first_title, d.first_link, d.first_price_raw,
       d.first_price_type, d.first_price_amount, d.price_parse_success, d.record_hash)
   or d.is_baseline_deal is distinct from (e.seq = (select min(snapshot_sequence) from fact))
   or d.is_newly_observed is distinct from not d.is_baseline_deal
