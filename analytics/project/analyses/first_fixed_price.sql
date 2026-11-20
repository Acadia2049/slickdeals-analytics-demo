with deals as ({{ first_price_population(ref('mart_deal_first_observed')) }})
select first_merchant_id as merchant_id, first_merchant_name as merchant_name, count(*) as first_observed_deals,
    count(*) filter (where fixed_price_eligible) as fixed_price_deals,
    quantile_cont(first_price_amount, 0.25) filter (where fixed_price_eligible) as fixed_price_p25,
    median(first_price_amount) filter (where fixed_price_eligible) as fixed_price_median,
    quantile_cont(first_price_amount, 0.75) filter (where fixed_price_eligible) as fixed_price_p75
from deals group by first_merchant_id, first_merchant_name order by merchant_id
