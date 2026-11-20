with snapshots as ({{ selected_snapshots(ref('mart_merchant_snapshot')) }})
select * from snapshots order by snapshot_sequence, selected_merchant_id
