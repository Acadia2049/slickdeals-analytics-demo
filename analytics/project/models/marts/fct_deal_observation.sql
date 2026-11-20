with intervals as (
    select *, coalesce(pair_eligible and snapshot_steps = 1 and observation_gap_hours > 0, false)
        as interval_eligible
    from {{ ref('int_observation_history') }}
)
select *,
    interval_eligible and not merchant_changed_in_v2 as merchant_comparison_eligible,
    case when interval_eligible then audit_comment_delta end as comment_delta,
    case when interval_eligible and audit_comment_delta is not null
        then observation_gap_hours end as eligible_comment_hours,
    case when interval_eligible then audit_vote_delta end as vote_delta,
    case when interval_eligible and audit_vote_delta is not null
        then observation_gap_hours end as eligible_vote_hours,
    case when interval_eligible then audit_views_delta end as views_delta
from intervals
