with facts as (
    select * from {{ ref('fct_deal_observation') }}
), baseline as (
    select min(snapshot_sequence) as sequence
    from {{ ref('int_snapshot_context') }} where is_business_cohort
), first_observation as (
    select * from facts where is_business_cohort
    qualify row_number() over (partition by deal_id order by snapshot_sequence) = 1
), first_quotes as (
    select f.deal_id, f.run_key as first_run_key, f.snapshot_sequence as first_sequence,
        f.snapshot_timestamp as first_observed_at, f.merchant_id as first_merchant_id,
        f.merchant_name as first_merchant_name, f.store as first_observed_store,
        f.title as first_title, f.title_link as first_link, f.deal_price_raw as first_price_raw,
        f.deal_price_type as first_price_type, f.deal_price_amount as first_price_amount,
        f.price_parse_success, coalesce(regexp_matches(f.deal_price_raw, '\$[0-9]+,[0-9]{2}([^0-9]|$)'), false)
            as ambiguous_comma_price,
        f.snapshot_sequence = b.sequence as is_baseline_deal, f.merchant_changed_in_v2,
        exists (select 1 from facts as legacy where legacy.raw_schema_version = 1
                and legacy.deal_id = f.deal_id) as seen_in_legacy,
        f.raw_uri, f.raw_sha256, f.record_hash
    from first_observation as f cross join baseline as b
)
select *, not is_baseline_deal as is_newly_observed,
    coalesce(first_price_type = 'fixed' and first_price_amount >= 0
        and price_parse_success and not ambiguous_comma_price, false) as fixed_price_eligible
from first_quotes
