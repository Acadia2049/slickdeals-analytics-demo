"""Bind parameters to already compiled dbt analyses; all business SQL lives in dbt."""
import argparse
from datetime import date, datetime, time, timedelta, timezone
import json
from zoneinfo import ZoneInfo

import sys
sys.dont_write_bytecode = True

from bundle import resolve

OPTIONS = {
    "merchant_overview": {"combine_merchants": False}, "snapshot_share": {"combine_merchants": False},
    "first_fixed_price": {"offer_types": None}, "promotion_mix": {"offer_types": None},
    "vote_velocity": {}, "comment_velocity": {},
    "deal_observation_audit": {"include_legacy": False, "deal_id": None},
}


def local_day_bounds(first, last):
    if first > last:
        raise ValueError("The first local date must precede or equal the last")
    ny = ZoneInfo("America/New_York")
    return datetime.combine(first, time.min, ny), datetime.combine(last + timedelta(days=1), time.min, ny)


def execute_query(connection, sql, defaults, start, end, merchant_ids, options, result_fields=None):
    if options.keys() - defaults.keys():
        raise ValueError(f"Unsupported filters: {options.keys() - defaults.keys()}")
    if any(dt.utcoffset() is None for dt in (start, end)):
        raise ValueError("Timestamps must include an explicit offset")
    lo, hi = (dt.astimezone(timezone.utc).replace(tzinfo=None) for dt in (start, end))
    if lo >= hi:
        raise ValueError("Exclusive window end must follow start")
    params = dict(defaults, **options, start_utc=lo, end_utc=hi, merchant_ids=merchant_ids)
    cursor = connection.execute(sql, params)
    fields = [column[0] for column in cursor.description]
    if result_fields is not None and [(c[0], str(c[1])) for c in cursor.description] != [(c["name"], c["type"]) for c in result_fields]:
        raise ValueError("Result schema differs from release contract")
    return [dict(zip(fields, row)) for row in cursor.fetchall()]


def query(package, name, start, end, merchant_ids=None, **options):
    spec = package.contract["queries"][name]
    sql = (package.root / "sql" / (name + ".sql")).read_text()
    with package.connect() as con:
        return execute_query(con, sql, spec["defaults"], start, end, merchant_ids, options, spec["result"])


def main(fixed_analysis=None):
    parser = argparse.ArgumentParser()
    if fixed_analysis is None:
        parser.add_argument("analysis", choices=OPTIONS)
    parser.add_argument("--store", help="Local release store")
    parser.add_argument("--version", help="Explicit installed release ID")
    parser.add_argument("first_ny_date", type=date.fromisoformat)
    parser.add_argument("last_ny_date", type=date.fromisoformat)
    parser.add_argument("--merchants", nargs="*", help="IDs; omit for all, no values for empty selection")
    parser.add_argument("--combine-merchants", action="store_true", default=argparse.SUPPRESS)
    parser.add_argument("--offer-types", nargs="*", default=argparse.SUPPRESS)
    parser.add_argument("--deal-id", type=int, default=argparse.SUPPRESS)
    parser.add_argument("--include-legacy", action="store_true", default=argparse.SUPPRESS)
    args = vars(parser.parse_args())
    package = resolve(args.pop("store"), args.pop("version"))
    name, ids = args.pop("analysis", fixed_analysis), args.pop("merchants")
    start, end = local_day_bounds(args.pop("first_ny_date"), args.pop("last_ny_date"))
    print(json.dumps(query(package, name, start, end, ids, **args), indent=2, default=str))


if __name__ == "__main__":
    main()
