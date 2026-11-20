"""Compare any selected release with its compiled SQL; never skip a release."""
from datetime import date
import json
from pathlib import Path
import re
import sys
import unittest

import pyarrow as pa
from streamlit.testing.v1 import AppTest

BI=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(BI))
from release_data import load_current, latest_window, local_day_bounds, report_rows


class Dashboard(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r=load_current()
        cls.dates=latest_window(cls.r)
        cls.amazon=next(k for k,v in cls.r.merchants.items() if v in ("Amazon", "Demo Market"))

    def sql(self,name,dates,merchant,**opts):
        pkg=self.r.package
        lo,hi=local_day_bounds(*dates)
        from datetime import timezone
        params=dict(pkg.contract["queries"][name]["defaults"], start_utc=lo.astimezone(timezone.utc).replace(tzinfo=None),
                    end_utc=hi.astimezone(timezone.utc).replace(tzinfo=None),merchant_ids=[merchant] if merchant else None)
        params.update(opts)
        with pkg.connect() as db:
            cur=db.execute((pkg.root/"sql"/(name+".sql")).read_text(),params)
            fields=[c[0] for c in cur.description]
            return [dict(zip(fields,row)) for row in cur.fetchall()]

    def dashboard(self):
        return AppTest.from_file(str(BI/"app.py"),default_timeout=30).run()

    def cards(self,app):
        self.assertFalse(app.exception)
        return [re.search(r'class="kv">([^<]+)',item.value).group(1) for item in app.markdown if 'class="kv">' in item.value]

    def test_cards_chart_mix_rates_and_price_filter(self):
        app=self.dashboard()
        data=self.sql("merchant_overview",self.dates,self.amazon)[0]
        price=self.sql("first_fixed_price",self.dates,self.amazon)[0]
        cards=[f'{data["mean_snapshot_share"]:.2%}',f'{data["newly_observed"]:,}',f'{data["observed_continuity"]:.2%}',f'${price["fixed_price_median"]:,.2f}']
        self.assertEqual(self.cards(app),cards)
        chart=app.get("arrow_vega_lite_chart")[0].proto.datasets[0]
        series=pa.ipc.open_stream(chart.data.data).read_all().to_pylist()
        expected=self.sql("snapshot_share",self.dates,self.amazon)
        self.assertEqual([(r["snapshot_timestamp"].replace(tzinfo=None),r["snapshot_share"],r["full_snapshot_deals"]) for r in series],
                         [(r["snapshot_timestamp"],r["snapshot_share"],r["full_snapshot_deals"]) for r in expected])
        mix=self.sql("promotion_mix",self.dates,self.amazon)
        bars=[m.value for m in app.markdown if 'class="mix">' in m.value]
        self.assertEqual(len(bars),len(mix))
        labels={"fixed":"Fixed price","starting_at":"Starting at","upper_bound":"Up to",
                "percentage":"Percentage offer","free":"Free","other":"Other offers"}
        for row in mix:
            self.assertTrue(any(f'>{labels[row["first_price_type"]]}</span>' in b and f'>{row["deals"]}</b>' in b for b in bars))
        rates=app.dataframe[0].value
        for i,k in enumerate(("vote","comment")):
            rate=self.sql(k+"_velocity",self.dates,self.amazon)[0]
            self.assertEqual(rates.iloc[i]["Rate / hour"],f'{rate[k+"_velocity_per_hour"]:.6f}')
            self.assertEqual(rates.iloc[i]["Deals measured"],rate["deals_with_"+k+"_rate"])
        app.selectbox(key="offer").set_value("other").run()
        self.assertEqual(self.cards(app),cards[:3]+["—"])
        self.assertTrue(rates.equals(app.dataframe[0].value))
        expected_mix=self.sql("promotion_mix",self.dates,self.amazon,offer_types=["other"])
        self.assertEqual(len([m for m in app.markdown if 'class="mix">' in m.value]),len(expected_mix))
        other=self.sql("first_fixed_price",self.dates,self.amazon,offer_types=["other"])
        self.assertTrue(all(r["fixed_price_deals"]==0 and r["fixed_price_median"] is None for r in other))

    def test_merchant_empty_window_zero_and_null(self):
        app=self.dashboard()
        key=next(k for k in self.r.merchants if k != self.amazon)
        app.selectbox(key="overview_merchant").set_value(key).run()
        self.assertEqual(self.cards(app)[0],f'{self.sql("merchant_overview",self.dates,key)[0]["mean_snapshot_share"]:.2%}')
        app.radio(key="date_mode").set_value("Fixed dates").run()
        app.date_input(key="fixed_dates").set_value((date(2025,1,1),)*2).run()
        self.assertEqual(self.cards(app),["—"]*4)
        self.assertTrue(all(app.dataframe[0].value["Rate / hour"]=="—"))

    def test_observation_audit(self):
        expected=self.sql("deal_observation_audit",self.dates,self.amazon)
        self.assertTrue(expected)
        deal=expected[-1]["deal_id"]
        rows=report_rows(self.r,"deal_observation_audit",self.dates,self.amazon,deal_id=deal)
        self.assertEqual(rows,self.sql("deal_observation_audit",self.dates,self.amazon,deal_id=deal))
        self.assertTrue(all(r["verification_status"]=="success" for r in rows))
        self.assertTrue(all(len(r["raw_sha256"])==64 for r in rows))
        self.assertEqual(report_rows(self.r,"deal_observation_audit",(date(2025,1,1),)*2,None,deal_id=deal),[])


if __name__=="__main__":
    unittest.main(verbosity=2)
