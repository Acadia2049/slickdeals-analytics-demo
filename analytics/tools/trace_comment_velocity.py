"""Independently regroup Fact intervals and compare them with the published report."""
import argparse
from datetime import date, timezone
import json
import math

from bundle import digest, resolve
from report_query import local_day_bounds, query


def trace(store, merchant, first, last):
    package = resolve(store)
    start, end = local_day_bounds(first, last)
    lo, hi = [t.astimezone(timezone.utc).replace(tzinfo=None) for t in (start, end)]
    with package.connect() as db:
        matches = db.execute('select distinct merchant_id from analytics_marts.mart_merchant_snapshot where merchant_name=?', [merchant]).fetchall()
        if len(matches) != 1:
            raise ValueError('Select a merchant name with exactly one identity in this release')
        identity = matches[0][0]
        report = query(package, 'comment_velocity', start, end, [identity])
        rows = db.execute('''select deal_id, comment_delta, eligible_comment_hours
            from analytics_marts.fct_deal_observation
            where merchant_comparison_eligible and merchant_id=?
              and snapshot_timestamp>=? and snapshot_timestamp<?
            order by deal_id,snapshot_timestamp''', [identity, lo, hi]).fetchall()
    totals = {}
    for deal, delta, hours in rows:
        if delta is not None:
            assert hours is not None and hours > 0
            net, measured = totals.get(deal, (0, 0.0))
            totals[deal] = net + delta, measured + hours
    rates = [net/hours for net,hours in totals.values()]
    independent = sum(rates)/len(rates) if rates else None
    published = report[0]['comment_velocity_per_hour'] if report else None
    if independent is None or published is None:
        assert independent is published
    else:
        assert math.isclose(independent, published, rel_tol=1e-10, abs_tol=1e-12)
    return dict(release_id=package.root.name, manifest_sha256=digest(package.root/'manifest.json'),
                merchant=merchant,ny_date_range=[str(first),str(last)],published=report,
                independent_rate=independent,negative_intervals=sum(d is not None and d<0 for _,d,_ in rows),
                missing_intervals=sum(d is None for _,d,_ in rows),status='matched')


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--store',required=True)
    parser.add_argument('--merchant',required=True)
    parser.add_argument('first',type=date.fromisoformat)
    parser.add_argument('last',type=date.fromisoformat)
    args=parser.parse_args()
    print(json.dumps(trace(args.store,args.merchant,args.first,args.last),indent=2))
