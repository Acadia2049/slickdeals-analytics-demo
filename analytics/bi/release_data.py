"""One validated release per render; all business reports use the published query API."""
from dataclasses import dataclass
from datetime import timedelta, timezone
from pathlib import Path
import os
import re
import sys
from zoneinfo import ZoneInfo

import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from bundle import QUERIES, Package, load_json, valid_id, verify
from report_query import local_day_bounds, query

STORE = Path(os.environ.get("SLICKDEALS_BI_STORE", ROOT / "demo/local")).resolve()
NY = ZoneInfo("America/New_York")


@dataclass
class Release:
    package: Package
    fingerprint: str
    coverage: tuple
    cohort_dates: tuple
    merchants: dict
    audit_merchants: dict
    types: tuple


def ny_date(utc):
    return utc.replace(tzinfo=timezone.utc).astimezone(NY).date()


def latest_window(release):
    first, last = release.cohort_dates
    return max(first, last - timedelta(days=6)), last


def load_current(previous=None, store=STORE):
    pointer = load_json(store / "current")
    name, fingerprint = valid_id(pointer["release_id"]), pointer["manifest_sha256"]
    if not isinstance(fingerprint, str) or not re.fullmatch("[a-f0-9]{64}", fingerprint):
        raise ValueError("Invalid manifest fingerprint")
    if previous and previous.package.root.name == name:
        if previous.fingerprint != fingerprint:
            raise ValueError("The published version ID was reused with a different manifest")
        return previous
    pkg = verify(store / "versions" / name, fingerprint)
    with pkg.connect() as db:
        coverage = db.execute("select min(snapshot_timestamp), max(snapshot_timestamp) from analytics_marts.mart_collection_quality").fetchone()
        span = db.execute("select min(snapshot_timestamp), max(snapshot_timestamp) from analytics_marts.mart_merchant_snapshot").fetchone()
        merchants = dict(db.execute("select distinct merchant_id, merchant_name from analytics_marts.mart_merchant_snapshot order by merchant_name, merchant_id").fetchall())
        audit_merchants = dict(db.execute("select distinct merchant_id, merchant_name from analytics_marts.fct_deal_observation order by merchant_name, merchant_id").fetchall())
        types = tuple(row[0] for row in db.execute("select distinct first_price_type from analytics_marts.mart_deal_first_observed order by 1").fetchall())
    if not merchants or None in span or None in coverage:
        raise ValueError("Release has no verified business coverage")
    # Check every report's bound SQL and ordered output contract before adopting the new package.
    bounds = local_day_bounds(ny_date(span[1]), ny_date(span[1]))
    for report in QUERIES:
        query(pkg, report, *bounds, [])
    return Release(pkg, fingerprint, coverage, tuple(map(ny_date, span)), merchants, audit_merchants, types)


@st.cache_data(show_spinner=False, max_entries=96)
def _rows(root, version, fingerprint, report, first, last, merchant, offer_types, deal_id, legacy, _pkg):
    opts = {}
    if report in ("first_fixed_price", "promotion_mix"):
        opts["offer_types"] = None if offer_types is None else list(offer_types)
    if report == "deal_observation_audit":
        opts.update(deal_id=deal_id, include_legacy=legacy)
    return query(_pkg, report, *local_day_bounds(first, last), None if merchant is None else [merchant], **opts)


def report_rows(release, name, dates, merchant, *, offer_types=None, deal_id=None, legacy=False):
    return _rows(str(release.package.root), release.package.root.name, release.fingerprint,
                 name, *dates, merchant, offer_types, deal_id, legacy, _pkg=release.package)
