# Trace a dashboard number: comment velocity

**Question:** How quickly did the displayed comment counters change for observed Amazon Deals during November 10–16, 2026, using New York calendar dates?

**Answer in release `sd-20261117T022306Z-r4`: 0.205042 comments per eligible observation hour, averaged equally across Deals.** This is a descriptive counter-change statistic, not a measure of writing quality, individual participation or causal impact.

## 1. Define the sample before calculating

An observation is one Deal in one captured snapshot. A comparison uses two original adjacent snapshots, both in the complete Frontpage v2 scope, with matching parser and a 1.5–2.5 hour gap. The Deal must be present in both. Merchant-level comparisons additionally require a stable merchant across the observed v2 history. A later merchant change can therefore change eligibility when history is extended; the release ID matters.

The date filter applies to the **end of the interval**. November 10–16 NY corresponds to `[2026-11-10 05:00:00Z, 2026-11-17 05:00:00Z)`. The first interval's start may fall before that window.

Code: [snapshot eligibility](../../analytics/project/models/intermediate/int_snapshot_context.sql), [observation history](../../analytics/project/models/intermediate/int_observation_history.sql), [counter-specific hours](../../analytics/project/models/marts/fct_deal_observation.sql).

## 2. Compute per Deal, then average

For each eligible Deal:

```text
Deal rate = sum(signed comment deltas) / sum(hours for non-missing comment deltas)
Merchant rate = mean(non-null Deal rates)
```

The actual r4 window contains:

| Quantity | Value |
|---|---:|
| Deals with a measured rate | 674 |
| Measured intervals | 6,659 |
| Eligible observation hours | 13,317.855 |
| Signed net change | 2,383 |
| Negative intervals retained | 14 |
| Missing comment deltas within this eligible sample | 0 |
| Equal-Deal-weighted rate | 0.20504239091806797 |

Dividing 2,383 by 13,317.855 would weight Deals by their observed hours and answer a different question. An independent Python regrouping of the Fact rows produced `0.20504239091806814`, agreeing within floating-point tolerance.

Code: [report entry](../../analytics/project/analyses/comment_velocity.sql), [shared aggregation macro](../../analytics/project/macros/business_queries.sql), [recorded result](metric-trace.json).

## 3. Inspect a negative observation

Deal **20255670**, November 10 UTC:

| Field | Earlier observation | Later observation |
|---|---|---|
| Timestamp | 04:31:40 | 06:31:45 |
| Displayed comments | 17 | 16 |

The delta is **−1 over 2.001388889 hours**. The source counter decreased; the pipeline preserves that observation. It does not infer whether comments were deleted, moderated, recounted, or displayed differently.

The later row's Raw SHA-256 is `883777d498d4eee1f3ddad22d8e7747388bdae414eb9013a9093ca4bf80c8e04`. The audit row identifies the run and independent verification status; an authorized operator can follow that key to the retained JSON and HTML. [Run key and record hash](metric-trace.json). Private source files are not required to run the synthetic demo and are not included in the public repository.

## 4. Test the interpretation

Missing counters are not zeros. Each counter uses only its own non-null measured intervals in its denominator. This real window has no missing comment deltas in the eligible sample, so the missing-value behavior is demonstrated by a separate hand-calculated synthetic fixture—not claimed as a finding in this window.

That fixture expects comment velocity **−0.75**, six eligible comment hours, and eight eligible vote hours. It also checks merchant transfers, full-snapshot denominators, exact price medians, empty selections, and 23/25-hour New York DST days. [Executable tests](../../analytics/tests/test_business_queries.py).

## Why this engineering transfers to research

The relevant habit is keeping the unit of observation, event identity, sample exclusions and denominator explicit. In a consented writing experiment, analogous checks would link `suggestion_shown`, `accepted`, `edited` and submitted-text events while preserving treatment assignment and missing events. That is a proposed application of these engineering practices; this repository does not itself implement a browser experiment or causal estimator.
