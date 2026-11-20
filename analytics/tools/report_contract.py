"""Describe the compiled reports using dbt lineage and the DuckDB result schema."""
import json
from bundle import QUERIES, MARTS, digest
from report_query import OPTIONS

CONTRACT_VERSION = "1.0.0"
PARAMETERS = {
    "start_utc": ["TIMESTAMP","必填；UTC 区间起点，含。"],
    "end_utc": ["TIMESTAMP","必填；UTC 区间终点，不含。纽约起止日期分别按当地午夜换算。"],
    "merchant_ids": ["VARCHAR[]","NULL 为全部商家，空列表为空选择。使用商家身份 ID。"],
    "combine_merchants": ["BOOLEAN","默认 false；true 按快照合并选中商家，期间份额仍对快照等权。"],
    "offer_types": ["VARCHAR[]","按首次报价类型过滤。NULL 为全部，空列表为空选择。"],
    "deal_id": ["BIGINT","可选精确 Deal ID；NULL 为全部。"],
    "include_legacy": ["BOOLEAN","默认 false 仅批准的 v2；true 可查完整审计历史。"],
}
MEANINGS = {
    "selected_merchant_id":"所选商家 ID；合并输出为 NULL。","selected_merchant_name":"所选商家名称；合并输出为 NULL。",
    "snapshot_share":"本快照所选商家的 Deal 观察数 / 完整快照的 Deal 观察数。","observed_snapshots":"窗口中真实快照数。",
    "snapshots_with_share":"份额非 NULL 的快照数。","mean_snapshot_share":"逐快照份额的算术平均。",
    "eligible_pairs":"窗口结束端属于合格相邻对的快照数。","observed_continuity":"留存成员之和 / 前端成员之和，零分母 NULL。",
    "first_observed_deals":"窗口内属于首商家和所选报价类型的首见 Deal 数，含基线。",
    "fixed_price_deals":"上述样本中首报价为合格固定价的 Deal 数。","fixed_price_p25":"合格首报价连续 25% 分位数。",
    "fixed_price_median":"合格首报价中位数。","fixed_price_p75":"合格首报价连续 75% 分位数。",
    "deals":"该首商家和首类型的 Deal 数。","eligible_deals":"窗口内有可比区间的稳定商家 Deal 数。",
    "eligible_intervals":"窗口内合格稳定商家 Deal 区间数。",
}


def write_json(path, data):
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True, default=str)+"\n")


def describe_queries(db, meta, sql_dir, release_id):
    specs = {}
    for name in QUERIES:
        node = meta["nodes"]["analysis.slickdeals_analytics."+name]
        parents = [meta["nodes"][key] for key in node["depends_on"]["nodes"]]
        if not parents or any(p["schema"]!="analytics_marts" or p["name"] not in MARTS for p in parents):
            raise ValueError(f"Nonpublic dependency: {name}")
        meanings = {k:v["description"] for p in parents for k,v in p["columns"].items()}
        if name != "deal_observation_audit":
            meanings.update(MEANINGS)
        for q,word in (("comment","评论"),("vote","票数")):
            meanings.update({f"{q}_hours":f"{word}两端非空的有效观察区间小时之和。",
                             f"{q}_net_growth":f"{word}有符号净变化之和。",
                             f"intervals_with_{q}s":f"{word}差值可用的区间数。",
                             f"deals_with_{q}_rate":f"{word}速率非空的 Deal 数。",
                             f"{q}_velocity_per_hour":f"先逐 Deal 求每有效观察区间小时的{word}净变化，再按 Deal 等权平均。"})
        if name in ("first_fixed_price","promotion_mix"):
            meanings.update(merchant_id="首观察商家 ID。",merchant_name="首观察商家展示名。")
        path = sql_dir / (name+".sql")
        params = dict(OPTIONS[name], start_utc="2026-11-03",end_utc="2026-11-08",merchant_ids=None)
        cur = db.execute("select * from ("+path.read_text().strip().rstrip(";")+") as report limit 0",params)
        fields = [{"name":c[0],"type":str(c[1]),"description":meanings[c[0]]} for c in cur.description]
        specs[name] = {"sql_sha256":digest(path),"marts":[p["name"] for p in parents],"defaults":OPTIONS[name],
                       "parameters":list(params),"result":fields}
    return {"version":CONTRACT_VERSION,"release_id":release_id,"parameters":PARAMETERS,"queries":specs,
            "time":"UTC [start,end)。Velocity 使用区间结束时间，Pricing/Mix 使用首观察时间。",
            "hours":"有效观察区间小时是两次合格观察之间的实测时间差；不代表用户曝光或连续在线时长。"}
