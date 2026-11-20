with deals as ({{ first_price_population(ref('mart_deal_first_observed')) }})
select first_merchant_id as merchant_id, first_price_type, count(*) as deals
from deals group by first_merchant_id, first_price_type order by merchant_id, first_price_type
