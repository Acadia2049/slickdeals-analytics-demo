{% macro selected_merchants(column) -%}
    (cast($merchant_ids as varchar[]) is null or list_contains(cast($merchant_ids as varchar[]), {{ column }}))
{%- endmacro %}

{% macro selected_window(column) -%}
    {{ column }} >= cast($start_utc as timestamp) and {{ column }} < cast($end_utc as timestamp)
{%- endmacro %}

{% macro first_price_population(relation) -%}
    select * from {{ relation }}
    where {{ selected_window('first_observed_at') }} and {{ selected_merchants('first_merchant_id') }}
      and (cast($offer_types as varchar[]) is null or list_contains(cast($offer_types as varchar[]), first_price_type))
{%- endmacro %}

{% macro selected_snapshots(relation) -%}
    select case when not $combine_merchants then merchant_id end as selected_merchant_id,
        case when not $combine_merchants then merchant_name end as selected_merchant_name,
        run_key, snapshot_timestamp, snapshot_sequence, pair_eligible,
        sum(merchant_deals)::bigint as merchant_deals, max(full_snapshot_deals) as full_snapshot_deals,
        sum(merchant_deals)::double / nullif(max(full_snapshot_deals), 0) as snapshot_share,
        sum(newly_observed)::bigint as newly_observed, sum(baseline_deals)::bigint as baseline_deals,
        sum(newly_seen_in_legacy)::bigint as newly_seen_in_legacy,
        sum(previous_memberships)::bigint as previous_memberships,
        sum(retained_memberships)::bigint as retained_memberships,
        sum(transferred_out)::bigint as transferred_out
    from {{ relation }}
    where {{ selected_window('snapshot_timestamp') }} and {{ selected_merchants('merchant_id') }}
    group by all
{%- endmacro %}

{% macro merchant_velocity(relation, counter) -%}
with deal_rates as (
    select merchant_id, merchant_name, deal_id, count(*) as eligible_intervals,
        count({{ counter }}_delta) as measured_intervals,
        sum({{ counter }}_delta) as net_growth, sum(eligible_{{ counter }}_hours) as measured_hours,
        sum({{ counter }}_delta) / nullif(sum(eligible_{{ counter }}_hours), 0) as deal_rate
    from {{ relation }}
    where merchant_comparison_eligible and {{ selected_window('snapshot_timestamp') }}
      and {{ selected_merchants('merchant_id') }}
    group by merchant_id, merchant_name, deal_id
)
select merchant_id, merchant_name, count(*) as eligible_deals,
    sum(eligible_intervals)::bigint as eligible_intervals, count(deal_rate) as deals_with_{{ counter }}_rate,
    sum(measured_intervals)::bigint as intervals_with_{{ counter }}s,
    sum(measured_hours) as {{ counter }}_hours, sum(net_growth) as {{ counter }}_net_growth,
    avg(deal_rate) as {{ counter }}_velocity_per_hour
from deal_rates group by merchant_id, merchant_name order by merchant_id
{%- endmacro %}
