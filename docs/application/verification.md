# Verification record — November 20, 2026

This is a dated report, not a live monitoring service. Three distinct artifacts are kept separate:

| Artifact | Version / scope | Evidence checked |
|---|---|---|
| Production collection | Two-hour MWAA Serverless schedule, ECS collector/verifier | Latest 50 executions: 50 SUCCESS. Last checked execution finished Nov 20, 15:34:04 NY. |
| Latest downloaded original warehouse | Nov 20, 15:31:43 NY cutoff | 399 snapshots, 79,356 rows, 6,759 distinct Deals; 12 models + 81 data tests passed. |
| Approved dashboard release | `sd-20261117T022306Z-r4`, through Nov 16, 19:31:34 NY | 353 snapshots, 66,833 rows; stored build receipt records 9 models, 38 data tests + 6 unit tests. |

The AWS end date was extended to `2026-12-06T04:59:59Z` (December 5, 23:59:59 NY). A readback confirmed `READY`, `scheduled`, and the unchanged cron `30 */2 * * *`; the only workflow-definition change was `end_date`. The final scheduled slot is December 5 at 23:30 NY. The production definition and account details remain private.

## Checks performed for this public showcase

- **Clean environment:** created a new Python 3.10 virtual environment and installed the demo requirements. Corrected an actual dependency conflict: the prior UI environment pinned python-dateutil 3.0, while dbt requires a version below 3.0. The unified environment uses 2.9.0.post0 and passes `pip check`.
- **Relocated source:** built the demo in the new standalone directory, without importing the private platform or sibling analytics source. Synthetic inputs are generated locally; no AWS login or production input files are used.
- **Actual model execution:** 9 models built; 38 data tests and 6 dbt unit tests passed; reports compiled. Six hand-calculated Python/SQL business tests passed.
- **UI/SQL regression:** three dashboard test methods passed against both the synthetic demo and actual r4. They compare cards, chart series, rates, filters, empty windows and observation outputs to compiled SQL. Release IDs no longer cause the entire suite to skip.
- **Actual browser:** Merchant Overview rendered r4's Amazon 43.49% share, 591 newly observed Deals, 91.56% continuity, $15.00 median first fixed price, and 0.205042 comment velocity. Deal Explorer filtered Deal 20255670 and displayed the November 10 negative delta with verification `success`. No browser error logs were captured. Narrow and desktop layouts were inspected; narrow cards were adjusted to wrap without splitting values.
- **Source check:** reopened both downloaded raw JSON files for the 17→16 comment example, recomputed their SHA-256 values, and matched the independent verification records. The exact hashes are in [the trace record](metric-trace.json).

## Reproduce the metric comparison

With an authorized r4 store:

```sh
analytics/.venv/bin/python -B analytics/tools/trace_comment_velocity.py \
  --store /path/to/local --merchant Amazon 2026-11-10 2026-11-16
```

For the self-contained synthetic example:

```sh
analytics/.venv/bin/python -B analytics/tools/trace_comment_velocity.py \
  --store analytics/demo/local --merchant 'Demo Market' 2026-11-03 2026-11-04
```

The latter should report a rate of −0.75 and two missing eligible comment deltas. Its numbers are intentionally different from the production example.

## Limits

The private r4 input batch was not rebuilt during this showcase task; its stored dbt receipt was inspected and its package/UI/SQL were tested again. The freshly downloaded original warehouse is not silently substituted for r4. The public CI workflow builds the synthetic demo; it does not deploy AWS infrastructure, access private S3 objects, or publish a production release. Synthetic verification checks fixture consistency and is not independent evidence of a web observation.
