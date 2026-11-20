"""Explicit engineering fixture paths; production consumers only open a verified package."""
import os
from pathlib import Path
from report_query import OPTIONS, execute_query, local_day_bounds
from bundle import verify

BUILD = Path(os.environ["SD_TEST_BUILD"]).resolve()
FIXTURE_DATABASE = BUILD / "analytics.duckdb"
PACKAGE = verify(Path(os.environ["SD_TEST_PACKAGE"])) if "SD_TEST_PACKAGE" in os.environ else None
DATABASE = PACKAGE.root / "analytics.duckdb" if PACKAGE else FIXTURE_DATABASE
ANALYSES = BUILD / "compile/target/compiled/slickdeals_analytics/analyses"


def query(connection, name, start, end, merchant_ids=None, **options):
    if PACKAGE:
        spec = PACKAGE.contract["queries"][name]
        return execute_query(connection, (PACKAGE.root / "sql" / (name + ".sql")).read_text(), spec["defaults"],
                             start, end, merchant_ids, options, spec["result"])
    return execute_query(connection, (ANALYSES / (name + ".sql")).read_text(), OPTIONS[name],
                         start, end, merchant_ids, options)


def comment_query(connection, start, end):
    return query(connection, "comment_velocity", start, end)
