select deal_id, run_key from {{ ref('fct_deal_observation') }}
where (interval_eligible and (not pair_eligible or previous_run_key is distinct from previous_global_run_key
           or observation_gap_hours is distinct from global_gap_hours))
   or merchant_comparison_eligible is distinct from (interval_eligible and not merchant_changed_in_v2)
   or comment_delta is distinct from (
        case when interval_eligible then comment_count::bigint - previous_comment_count end)
   or eligible_comment_hours is distinct from (
        case when comment_delta is not null then observation_gap_hours end)
   or vote_delta is distinct from (
        case when interval_eligible then vote_count::bigint - previous_vote_count end)
   or eligible_vote_hours is distinct from (
        case when vote_delta is not null then observation_gap_hours end)
   or (snapshot_steps is distinct from 1 and
        (audit_comment_delta is not null or audit_vote_delta is not null or audit_views_delta is not null))
