select * from {{ ref('fct_deal_observation') }}
where {{ selected_window('snapshot_timestamp') }} and {{ selected_merchants('merchant_id') }}
  and (is_business_cohort or $include_legacy)
  and (cast($deal_id as bigint) is null or deal_id = $deal_id)
order by snapshot_sequence, deal_id
