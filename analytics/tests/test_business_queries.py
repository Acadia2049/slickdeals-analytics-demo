"""Hand-calculated examples going through the real compiled business models and analyses."""
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import hashlib
from pathlib import Path
import sys
import unittest

import duckdb

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from build_query import ANALYSES, FIXTURE_DATABASE, local_day_bounds, query

UTC = timezone.utc
START = datetime(2026, 11, 4, 1, tzinfo=UTC)  # November 3 at 20:00 in New York.
END = START + timedelta(hours=10)
A, B, C = [hashlib.md5(x.encode()).hexdigest() for x in ("a","b","c")]


def fixture(db):
    db.execute("attach ':memory:' as analytics")
    for schema in ("staging","intermediate","marts"):
        db.execute(f"create schema analytics.analytics_{schema}")
    with duckdb.connect(str(FIXTURE_DATABASE),read_only=True) as types:
        # dbt enforces the public contract's column order when materializing tables.
        public_schemas = {model: types.execute(f"describe analytics_marts.{model}").fetchall()
                          for model in ("fct_deal_observation","mart_deal_first_observed","mart_merchant_snapshot")}
        for name in ("analytics_staging.stg_clean_observation","analytics_intermediate.int_snapshot_context"):
            schema = types.execute(f"describe {name}").fetchall()
            columns = ", ".join(f'"{col}" {typ}' for col,typ,*_ in schema)
            db.execute(f"create table analytics.{name} ({columns})")

    # (Deal, merchant, displayed vote, displayed comment, price type, amount)
    events = [
        [(1,"a",0,10,"fixed",1),(2,"a",10,10,"starting_at",5),(3,"a",0,0,"fixed",100),
         (4,"a",1,0,"fixed",101),(8,"a",0,0,"fixed",102),(7,"c",0,0,"other",None)],
        [(1,"a",2,10,"fixed",1),(2,"a",20,6,"fixed",50),(3,"b",100,100,"fixed",90)],
        [(1,"a",5,12,"fixed",1),(5,"a",0,0,"fixed",200)],
        [(1,"a",9,None,"fixed",1)], [(1,"a",None,30,"fixed",1)]]
    for i, rows in enumerate(events):
        ts = (START + timedelta(hours=2*i)).replace(tzinfo=None)
        db.execute("""insert into analytics.analytics_intermediate.int_snapshot_context
            (run_key,snapshot_sequence,snapshot_timestamp,previous_global_run_key,global_gap_hours,
             is_business_cohort,pair_eligible,observation_rows) values (?,?,?,?,?,?,?,?)""",
            [str(i),i+1,ts,str(i-1) if i else None,2 if i else None,True,i>0,len(rows)])
        for deal,shop,votes,comments,kind,amount in rows:
            db.execute("""insert into analytics.analytics_staging.stg_clean_observation
                (deal_id,snapshot_timestamp,store_normalized,store,vote_count,comment_count,deal_price_type,
                 deal_price_amount,deal_price_raw,price_parse_success,title,title_link,raw_schema_version)
                 values (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                [deal,ts,shop,shop.upper(),votes,comments,kind,amount,str(amount),kind!="other",
                 f"title {deal}-{i}",f"/{deal}-{i}",2])
    for schema,model in [("intermediate","int_observation_history"),("marts","fct_deal_observation"),
                         ("marts","mart_deal_first_observed"),("marts","mart_merchant_snapshot")]:
        sql = (ANALYSES.parent / "models" / schema / (model+".sql")).read_text()
        relation = f"analytics.analytics_{schema}.{model}"
        if model in public_schemas:
            declared = [(c,t) for c,t,*_ in public_schemas[model]]
            computed = [(c,t) for c,t,*_ in db.execute("describe "+sql).fetchall()]
            if sorted(computed) != sorted(declared):
                raise ValueError(f"Fixture SQL schema disagrees with dbt contract: {model}")
            columns = ", ".join(f'"{c}" {t}' for c,t in declared)
            db.execute(f"create table {relation} ({columns})")
            db.execute(f"insert into {relation} by name "+sql)
        else:
            db.execute(f"create table {relation} as "+sql)


class BusinessQueries(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db = duckdb.connect()
        cls.addClassCleanup(cls.db.close)
        fixture(cls.db)

    def report(self,name,merchants=None,bounds=(START,END),**options):
        return query(self.db,name,*bounds,merchant_ids=merchants,**options)

    def test_complete_denominator_and_combined_merchants(self):
        rows = self.report("snapshot_share",[A])
        self.assertEqual([(r["merchant_deals"],r["full_snapshot_deals"]) for r in rows],
                         [(5,6),(2,3),(2,2),(1,1),(1,1)])
        scoped, = self.report("merchant_overview",[A,B],combine_merchants=True)
        self.assertAlmostEqual(scoped["mean_snapshot_share"],(5/6+1+1+1+1)/5)
        all_shops, = self.report("merchant_overview",combine_merchants=True)
        self.assertEqual(all_shops["mean_snapshot_share"],1)
        self.assertEqual(len(self.report("merchant_overview",[A,B,A])),2)

    def test_weighted_continuity_and_transfers(self):
        a, = self.report("merchant_overview",[A])
        self.assertEqual((a["previous_memberships"],a["retained_memberships"],a["transferred_out"]),(10,5,1))
        self.assertEqual(a["observed_continuity"],0.5)
        b, = self.report("merchant_overview",[B])
        self.assertEqual((b["previous_memberships"],b["retained_memberships"],b["newly_observed"]),(1,0,0))
        first, = self.report("merchant_overview",[B],(START,START+timedelta(hours=1)))
        self.assertIsNone(first["previous_memberships"])
        self.assertIsNone(first["observed_continuity"])
        zero, = self.report("merchant_overview",[B],(START+timedelta(hours=2),START+timedelta(hours=3)))
        self.assertEqual(zero["previous_memberships"],0)
        self.assertIsNone(zero["observed_continuity"])

    def test_frozen_quote_and_exact_period_median(self):
        full, = self.report("first_fixed_price",[A])
        self.assertEqual((full["first_observed_deals"],full["fixed_price_deals"],full["fixed_price_median"]),(6,5,101))
        medians = [self.report("first_fixed_price",[A],local_day_bounds(day,day))[0]["fixed_price_median"]
                   for day in (date(2026,11,3),date(2026,11,4))]
        self.assertEqual(medians,[Decimal("100.50"),Decimal("200")])
        self.assertNotEqual(sum(medians)/2,full["fixed_price_median"])
        start_only, = self.report("first_fixed_price",[A],offer_types=["starting_at"])
        self.assertEqual((start_only["first_observed_deals"],start_only["fixed_price_deals"],start_only["fixed_price_median"]),
                         (1,0,None))
        self.assertEqual(self.report("promotion_mix",[A],offer_types=["starting_at"])[0]["deals"],1)
        mid = (START+timedelta(minutes=30),START+timedelta(hours=3))
        self.assertEqual(self.report("first_fixed_price",[A],mid),[])
        self.assertEqual(self.report("first_fixed_price",[B]),[])  # transferred Deal belongs to A at its first quote

    def test_unequal_deal_weights_and_counter_specific_exposure(self):
        c, = self.report("comment_velocity",[A])
        v, = self.report("vote_velocity",[A])
        self.assertEqual((c["eligible_deals"],c["eligible_intervals"],c["intervals_with_comments"],
                          c["comment_hours"],c["comment_net_growth"],c["comment_velocity_per_hour"]),(2,5,3,6,-2,-0.75))
        self.assertEqual((v["intervals_with_votes"],v["vote_hours"],v["vote_net_growth"],v["vote_velocity_per_hour"]),
                         (4,8,19,3.25))
        self.assertEqual(self.report("vote_velocity",[B,C]),[])
        row, = self.report("deal_observation_audit",[B],deal_id=3)
        self.assertEqual((row["vote_delta"],row["comment_delta"],row["merchant_comparison_eligible"]),(100,100,False))
        self.assertEqual(self.report("vote_velocity",[A],(START,START+timedelta(hours=2))),[])
        ends, = self.report("vote_velocity",[A],(START+timedelta(hours=2),START+timedelta(hours=2,minutes=30)))
        self.assertEqual(ends["vote_velocity_per_hour"],3)  # (2/2 + 10/2) / 2

    def test_empty_window_and_empty_selection(self):
        for name in ("merchant_overview","snapshot_share","first_fixed_price","promotion_mix","vote_velocity",
                     "comment_velocity","deal_observation_audit"):
            with self.subTest(name=name):
                self.assertEqual(self.report(name,[]),[])
                self.assertEqual(self.report(name,bounds=(END,END+timedelta(seconds=1))),[])
        self.assertEqual(self.report("merchant_overview",[],combine_merchants=True),[])
        self.assertEqual(self.report("promotion_mix",offer_types=[]),[])

    def test_dst_local_day_boundaries_with_real_query(self):
        for day,utc_hours in [(date(2026,3,8),23),(date(2026,11,1),25)]:
            lo,hi = local_day_bounds(day,day)
            low = lo.astimezone(UTC).replace(tzinfo=None)
            high = hi.astimezone(UTC).replace(tzinfo=None)
            self.assertEqual(high-low,timedelta(hours=utc_hours))
            self.db.execute("begin")
            try:
                for t in [low-timedelta(microseconds=1),low,high-timedelta(microseconds=1),high]:
                    self.db.execute("""insert into analytics.analytics_marts.mart_deal_first_observed
                        (first_merchant_id,first_price_type,first_observed_at) values ('dst','fixed',?)""",[t])
                item, = self.report("promotion_mix",["dst"],(lo,hi))
                self.assertEqual(item["deals"],2)
            finally:
                self.db.execute("rollback")


if __name__ == "__main__":
    unittest.main(verbosity=2)
