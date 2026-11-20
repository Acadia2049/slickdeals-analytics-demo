with snapshots as ({{ selected_snapshots(ref('mart_merchant_snapshot')) }})
select selected_merchant_id as merchant_id, selected_merchant_name as merchant_name,
    count(*) as observed_snapshots, count(snapshot_share) as snapshots_with_share,
    avg(snapshot_share) as mean_snapshot_share,
    sum(newly_observed)::bigint as newly_observed, sum(baseline_deals)::bigint as baseline_deals,
    sum(newly_seen_in_legacy)::bigint as newly_seen_in_legacy,
    count(*) filter (where pair_eligible) as eligible_pairs,
    sum(previous_memberships)::bigint as previous_memberships,
    sum(retained_memberships)::bigint as retained_memberships, sum(transferred_out)::bigint as transferred_out,
    sum(retained_memberships)::double / nullif(sum(previous_memberships), 0) as observed_continuity
from snapshots group by selected_merchant_id, selected_merchant_name order by merchant_id
