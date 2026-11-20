from datetime import date, timezone
import logging
from html import escape
import re

import altair as alt
import pandas as pd
import streamlit as st

from release_data import NY, latest_window, load_current, report_rows

st.set_page_config(page_title="Slickdeals Analytics", page_icon="📈", layout="wide", initial_sidebar_state="auto")
st.markdown("""<style>
[data-testid="stHeader"] {background:transparent;height:2rem}
[data-testid="stToolbar"] {display:none}
[data-testid="stMainBlockContainer"] {width:100%;max-width:none;min-width:0;padding:2.5rem clamp(1.4rem,2.5vw,4rem) 3rem}
[data-testid="stSidebar"] {background:#edf1ed;border-right:1px solid #d7e0d9}
[data-testid="stSidebarUserContent"] {padding-top:2.2rem}
[data-testid="stSidebar"] [data-testid="stPageLink"] a {border-radius:6px}
h1 {font-family:Georgia,serif!important;letter-spacing:-.045em;font-weight:500!important;font-size:clamp(2.4rem,3.1vw,4.2rem)!important}
h3 {font-size:clamp(1.25rem,1.45vw,1.85rem)!important;letter-spacing:-.02em}
.brand {display:flex;align-items:center;gap:10px;margin-bottom:20px;font-weight:750;font-size:23px;letter-spacing:-1px}
.mark {background:#116759;color:white;padding:1px 8px;transform:skew(-8deg);border-radius:4px;font-family:Georgia,serif}
.brand small {display:block;font:500 11px/1.3 sans-serif;color:#52675f;letter-spacing:1.1px}
.kpi {border:1px solid #d8e0da;background:#fff;border-radius:10px;padding:clamp(.9rem,1.1vw,1.5rem);min-height:7rem;margin-bottom:12px}
.kl {font-size:clamp(.95rem,1vw,1.35rem);font-weight:600;color:#38564c}.kv {font-size:clamp(2.15rem,2.7vw,3.8rem);line-height:1.35;letter-spacing:-1.4px;font-weight:650;font-variant-numeric:tabular-nums}
.ks,.status {font-size:.88rem;color:#52675f}.status {line-height:1.65}.status strong {color:#20463a}
.mix {display:grid;grid-template-columns:6.2rem 1fr 2.2rem;gap:10px;align-items:center;margin:13px 0;font-size:1rem}
.track {height:7px;background:#e9eeea;border-radius:5px}.fill {height:7px;background:#45917f;border-radius:5px}
[data-testid="stCaptionContainer"] p {font-size:.95rem}
.kv {white-space:nowrap}
@media(max-width:1100px){
  [data-testid="stHorizontalBlock"] {flex-wrap:wrap}
  [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {min-width:280px;flex:1 1 45%}
  [data-testid="stHorizontalBlock"]:has(.kpi) {flex-wrap:wrap}
  [data-testid="stHorizontalBlock"]:has(.kpi) > [data-testid="stColumn"] {min-width:200px;flex:1 1 40%}
}
@media(max-width:760px){
  [data-testid="stMainBlockContainer"]{padding:3.25rem 1rem 2rem}
  .kpi {min-height:0;margin-bottom:0}
}
</style>""", unsafe_allow_html=True)


PRICE_LABELS = {"fixed": "Fixed price", "starting_at": "Starting at", "upper_bound": "Up to",
                "percentage": "Percentage offer", "free": "Free", "other": "Other offers"}


def fmt(value, spec=","):
    return "—" if value is None else format(value, spec)


def card(label, value, sample):
    st.markdown(f'<div class="kpi"><div class="kl">{escape(label)}</div><div class="kv">{escape(value)}</div><div class="ks">{escape(sample)}</div></div>', unsafe_allow_html=True)


def header(title, subtitle):
    st.title(title)
    st.caption(subtitle)


def one(rows):
    return rows[0] if rows else {}


def overview():
    header("Merchant Overview", f"{release.merchants[merchant]}  ·  {period}  ·  New York dates")
    overview_row = one(report_rows(release, "merchant_overview", dates, merchant))
    price = one(report_rows(release, "first_fixed_price", dates, merchant, offer_types=offer_types))
    cols = st.columns(4)
    with cols[0]:
        card("Average Frontpage share", fmt(overview_row.get("mean_snapshot_share"), ".2%"), f'{overview_row.get("snapshots_with_share", 0)} Frontpage captures')
    with cols[1]:
        card("Newly observed deals", fmt(overview_row.get("newly_observed")), f'{overview_row.get("observed_snapshots", 0)} Frontpage captures')
    with cols[2]:
        card("Observed continuity", fmt(overview_row.get("observed_continuity"), ".2%"), f'{fmt(overview_row.get("retained_memberships"))} / {fmt(overview_row.get("previous_memberships"))} prior appearances')
    with cols[3]:
        amount = price.get("fixed_price_median")
        card("Median first fixed price", "—" if amount is None else f"${amount:,.2f}", f'{price.get("fixed_price_deals", 0)} fixed-price deals')
    left, right = st.columns([1.8, 1])
    timeline = report_rows(release, "snapshot_share", dates, merchant)
    with left, st.container(border=True):
        st.subheader("Share timeline")
        st.caption("Share of all Frontpage deals at each Frontpage capture")
        if timeline:
            series = pd.DataFrame(timeline)[["snapshot_timestamp", "snapshot_share", "merchant_deals", "full_snapshot_deals"]]
            series["snapshot_timestamp"] = pd.to_datetime(series["snapshot_timestamp"],utc=True)
            line = alt.Chart(series).encode(
                x=alt.X("snapshot_timestamp:T",scale=alt.Scale(type="utc"),title="Captured · UTC",axis=alt.Axis(format="%b %d",tickCount=6)),
                y=alt.Y("snapshot_share:Q",title=None,axis=alt.Axis(format=".0%",tickCount=4),scale=alt.Scale(zero=True)),
                tooltip=[alt.Tooltip("snapshot_timestamp:T",title="UTC",format="%b %d %H:%M"),
                         alt.Tooltip("snapshot_share:Q",title="Share",format=".2%"),alt.Tooltip("merchant_deals:Q",title="Merchant deals"),alt.Tooltip("full_snapshot_deals:Q",title="All Frontpage deals")])
            chart = (line.mark_area(color="#83baac",opacity=.23) + line.mark_line(color="#087565",strokeWidth=2.5,point=len(timeline)<3)).properties(height=280).configure_axis(labelFontSize=14,titleFontSize=15,labelPadding=6)
            st.altair_chart(chart,use_container_width=True)
        else:
            st.info("No snapshots in this date range.")
    with right, st.container(border=True):
        st.subheader("Promotion mix")
        mix = report_rows(release, "promotion_mix", dates, merchant, offer_types=offer_types)
        st.caption(f'{price.get("first_observed_deals", 0)} first observations · {price_label}')
        if mix:
            peak = max(r["deals"] for r in mix)
            for row in sorted(mix,key=lambda r:-r["deals"]):
                label = PRICE_LABELS.get(row["first_price_type"], "Other offers")
                st.markdown(f'<div class="mix"><span>{escape(label)}</span><div class="track"><div class="fill" style="width:{100*row["deals"]/peak:.1f}%"></div></div><b>{row["deals"]}</b></div>',unsafe_allow_html=True)
        else:
            st.info("No matching first observations.")
    st.subheader("Engagement velocity")
    st.caption("Each deal has equal weight · net change per eligible observation hour")
    metrics = []
    for counter in ("vote","comment"):
        data = one(report_rows(release,counter+"_velocity",dates,merchant))
        metrics.append({"Counter":counter.title()+"s", "Rate / hour":fmt(data.get(counter+"_velocity_per_hour"),".6f"),
                        "Deals measured":data.get("deals_with_"+counter+"_rate",0),
                        "Measured intervals":data.get("intervals_with_"+counter+"s",0),
                        "Observation hours":fmt(data.get(counter+"_hours"),",.2f"),"Net change":fmt(data.get(counter+"_net_growth"))})
    st.dataframe(metrics,hide_index=True,width="stretch",row_height=44)
    with st.expander("How to read these measures"):
        st.markdown("""
- **Frontpage share** averages the merchant's share across Frontpage captures, with equal weight per capture.
- **Newly observed deals** counts first appearances after the initial observation; it does not mean newly published deals.
- **Observed continuity** is the proportion of prior deal appearances still present at the same merchant in the next comparable observation.
- **Median first fixed price** uses each deal's first observed fixed-price quote, not its later prices.
- **Engagement velocity** first calculates a rate for each deal, then averages those rates equally. Missing counters are excluded from their own observation hours; negative changes are retained.

An em dash (—) means unavailable or not comparable. Zero is an observed zero. These measures describe observed content and counters, not sales or causal effects.
""")


def explorer():
    header("Deal Explorer", f'{release.audit_merchants.get(merchant,"All merchants")}  ·  {period}  ·  New York dates')
    raw_id=st.text_input("Deal ID",placeholder="Search by deal ID, or leave blank for all deals",key="deal_id").strip()
    if raw_id and (not re.fullmatch(r"[0-9]{1,19}",raw_id) or int(raw_id)>9223372036854775807):
        st.warning("Enter a valid numeric deal ID.")
        return
    rows=report_rows(release,"deal_observation_audit",dates,merchant,deal_id=int(raw_id) if raw_id else None)
    st.subheader("Observation history")
    if not rows:
        st.info("0 observations match these filters.")
        return
    pages=(len(rows)+49)//50
    col,select=st.columns([3,1])
    with select:
        page=st.selectbox("Page",range(1,pages+1),format_func=lambda x:f"{x} of {pages}",key="audit_page")
    start=(page-1)*50
    group=rows[::-1][start:start+50]
    with col:
        st.caption(f"{len(rows):,} observations · newest first · showing {start+1}–{start+len(group)}")
    display=[{"Snapshot · UTC":str(r["snapshot_timestamp"]), "Deal":str(r["deal_id"]), "Merchant":r["store"],
              "Title":r["title"], "Votes":fmt(r["vote_count"]), "Vote Δ":fmt(r["vote_delta"]),
              "Comments":fmt(r["comment_count"]), "Comment Δ":fmt(r["comment_delta"]),
              "Comparable change": "Yes" if r["interval_eligible"] else "No"} for r in group]
    st.dataframe(display,width="stretch",hide_index=True,row_height=44,height=min(402,48+len(group)*44))
    st.subheader("Observation detail")
    idx=st.selectbox("Inspect observation",range(len(group)),format_func=lambda i:f'{group[i]["snapshot_timestamp"]} UTC  ·  {group[i]["deal_id"]}  ·  {group[i]["title"]}')
    row=group[idx]
    facts, quality=st.columns([1,1])
    with facts, st.container(border=True):
        st.markdown("**Votes & comments**")
        st.caption("Changes between comparable observations")
        st.table([{"Measure":label,"Current":fmt(row[cur]),"Previous":fmt(row[prev]),"Change":fmt(row[delta])}
                  for label,cur,prev,delta in [
                      ("Votes","vote_count","previous_vote_count","vote_delta"),
                      ("Comments","comment_count","previous_comment_count","comment_delta")]])
        st.caption("— means missing or not comparable. Zero is an observed zero.")
        if any(row[k] is not None and row[k] < 0 for k in ("vote_delta", "comment_delta")):
            st.caption("A displayed counter decreased. The decrease is preserved; its cause is not known.")
    with quality, st.container(border=True):
        st.markdown("**Observation quality**")
        synthetic=release.package.manifest.get("purpose")=="synthetic-demo"
        check_label="Example consistency checks" if synthetic else "Source checks"
        check_status="Passed" if row["verification_status"]=="success" else "Not confirmed"
        st.markdown(f"**{check_label}:** {check_status}")
        if row["interval_eligible"]:
            explanation="This deal appears in consecutive, comparable observations. Changes use the actual time between them."
        elif row["observation_context"]=="first_observation":
            explanation="This is the deal's first observation. There is no earlier observation to compare."
        elif row["observation_context"]=="reappeared_after_gap":
            explanation="This deal reappeared after a gap. No change is inferred across its absence."
        elif row["pair_status"]=="elapsed_time":
            explanation="The time between observations is outside the comparison window."
        else:
            explanation="These observations do not meet the same collection and completeness requirements for comparison."
        st.write(explanation)
        if row["interval_eligible"] and not row["merchant_comparison_eligible"]:
            st.caption("Excluded from merchant-level rates because the merchant changed during the observed history.")
        if not synthetic:
            st.caption("Saved source records and checksums support this observation. See the repository's metric walkthrough for the technical trace.")


pages=[st.Page(overview,title="Merchant Overview",default=True,icon=":material/monitoring:"),
       st.Page(explorer,title="Deal Explorer",url_path="deals",icon=":material/manage_search:")]
page=st.navigation(pages,position="hidden")


@st.fragment(run_every=60)
def detect():
    previous=st.session_state.get("active_release")
    try:
        updated=load_current(previous)
    except Exception:
        logging.getLogger(__name__).exception("Dashboard data verification failed")
        st.error("The latest data could not be verified. " +
                 ("Showing the last verified dataset." if previous else "No verified dataset is available yet."))
        return
    if updated is not previous:
        st.session_state.active_release=updated
        st.rerun()


detect()
release=st.session_state.get("active_release")
if release is None:
    st.stop()

with st.sidebar:
    st.markdown('<div class="brand"><span class="mark">s</span><div>Slickdeals<small>ANALYTICS</small></div></div>',unsafe_allow_html=True)
    for item in pages:
        st.page_link(item)
    st.divider()
    st.subheader("Filters")
    is_overview=page.title=="Merchant Overview"
    names=release.merchants
    ids=list(names) if is_overview else [None,*names]
    default=next((k for k,v in names.items() if v in ("Amazon", "Demo Market")),ids[0]) if is_overview else None
    merchant_key="overview_merchant" if is_overview else "explorer_merchant"
    if merchant_key in st.session_state and st.session_state[merchant_key] not in ids:
        del st.session_state[merchant_key]
    merchant=st.selectbox("Merchant",ids,index=ids.index(default),format_func=lambda k:names.get(k,"All merchants"),
                          key=merchant_key)
    mode=st.radio("Date range",["Latest available","Fixed dates"],key="date_mode")
    dates=latest_window(release)
    if mode=="Fixed dates":
        if "fixed_dates" not in st.session_state:
            st.session_state.fixed_dates=st.session_state.get("saved_dates",dates)
        selected=st.date_input("Fixed range · New York",value=[],
                               min_value=date(1970,1,1),max_value=date(2100,12,31),key="fixed_dates")
        if len(selected)!=2:
            st.info("Choose the end date.")
            st.stop()
        dates=tuple(selected)
        st.session_state.saved_dates=dates
    else:
        st.caption("Latest 7 days of available observations")
    period=f'{dates[0]:%b %d, %Y} – {dates[1]:%b %d, %Y}'
    price_label="All price types"
    offer_types=None
    if is_overview:
        offer=st.selectbox("First observed price type",[None,*release.types],format_func=lambda x:PRICE_LABELS.get(x, "All price types"),key="offer")
        if offer:
            offer_types=(offer,)
            price_label=PRICE_LABELS.get(offer, "Other offers")
        st.caption("Applies to first price and promotion mix.")
    st.divider()
    st.markdown("**Data coverage**")
    first,last=release.cohort_dates
    latest=release.coverage[1].replace(tzinfo=timezone.utc).astimezone(NY)
    st.caption(f"{first:%b %d, %Y} – {last:%b %d, %Y}")
    st.caption(f"Latest observation: {latest:%b %d, %Y · %I:%M %p} New York")
    st.caption("Public Frontpage observations. Dates in filters use New York time; observation timestamps use UTC.")

if release.package.manifest.get("purpose") == "synthetic-demo":
    st.info("Synthetic demonstration — fictional observations, not collected data or research findings.")

page.run()
