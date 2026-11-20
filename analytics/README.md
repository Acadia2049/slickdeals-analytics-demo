# Reproducible analytics demo

This directory brings the dashboard's dbt models, report queries and Streamlit UI into a standalone public showcase repository. It supplies a small synthetic demo so a reviewer can run the actual analytics code without the owner's AWS account or local data.

## Run

From the repository root, with Python 3.10:

```sh
python3.10 -m venv analytics/.venv
analytics/.venv/bin/python -m pip install -r analytics/requirements.txt
analytics/.venv/bin/python -B analytics/tools/build_demo.py
analytics/.venv/bin/python -m streamlit run analytics/bi/app.py
```

Open the local URL printed by Streamlit. The synthetic-data banner should be visible. The default store is `analytics/demo/local`, separate from any approved production release. Re-running the builder verifies an existing demo rather than overwriting it. To rebuild after changing models, remove only the generated `analytics/demo/local` directory, then run the builder again. Build logs are retained under `analytics/demo/builds/`.

The demo deliberately contains a missing counter, a negative counter change, disappearance/reappearance, a merchant transfer, and a four-hour sampling gap. It uses fictional merchants and `example.com` links. Its evidence records are generated fixtures, **not independently collected AWS evidence**. Hashes validate fixture consistency, not the truth of real-world claims.

## Verify

```sh
analytics/.venv/bin/python -B analytics/bi/tests/test_dashboard.py
analytics/.venv/bin/python -B analytics/tools/report_query.py \
  --store analytics/demo/local comment_velocity 2026-11-03 2026-11-04
```

The builder runs dbt build (9 models, 38 data tests, 6 unit tests), compiles reports, and runs six hand-calculated business-query tests against the real compiled SQL. Those tests exercise merchant denominators, transfers, exact window medians, counter-specific hours, empty filters and DST boundaries. Dashboard tests compare cards, chart inputs, filters and observation outputs with SQL; they do not skip when the release ID changes.

`requirements.txt` records the combined environment tested from a clean virtual environment. `requirements-build.txt` and `bi/requirements.txt` retain the build and UI component pins; the dateutil pin is aligned with dbt. `requirements-build.lock` preserves the historical build environment for provenance.

## Inspect an authorized real release

If you already have an approved local release store, point the same UI at it:

```sh
SLICKDEALS_BI_STORE=/absolute/path/to/local \
  analytics/.venv/bin/python -m streamlit run analytics/bi/app.py
SLICKDEALS_BI_STORE=/absolute/path/to/local \
  analytics/.venv/bin/python -B analytics/bi/tests/test_dashboard.py
```

The store's `current` file identifies an immutable package by release ID and manifest hash. Package reads disable DuckDB external access. The application validates the package and query contracts before adopting a version; it keeps the last valid release when a new pointer is invalid. This repository update does not switch an operator's published release.

## Integration boundary

The public demo starts with the 38-column Clean contract. Production intake still uses the platform's scraper/PySpark code and the operator's separately maintained refresh/release workflow. Its frozen inputs, release receipts, historical regressions and local installation commands are not bundled here. Moving that entire operational workflow into this directory is a separate migration; copying local paths or release history would not make it reproducible.

The nine-model graph is distinct from the older `dbt/` warehouse. Use `analytics/project/` for dashboard metrics. All seven reports consume the same four materialized marts; no business metric is reimplemented in the UI.

## Presentation interface

The dashboard presents dates, sample sizes, metric definitions and observation quality. Internal release IDs, schema versions, storage locations and raw audit objects are kept in the technical tools and walkthrough rather than displayed in the interface. The explorer uses the same Frontpage population as the overview. Missing or incomparable values appear as an em dash with an explanation; synthetic data remains explicitly labeled.
