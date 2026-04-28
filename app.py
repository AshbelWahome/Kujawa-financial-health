import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

# ─────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="BookMetro Dashboard",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────
# CUSTOM CSS
# ─────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Sora:wght@300;400;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Sora', sans-serif; }
[data-testid="stSidebar"] { background: #0f1117; border-right: 1px solid #1e2130; }
[data-testid="stSidebar"] * { color: #e2e8f0 !important; }
.main .block-container { padding: 2rem 2.5rem; max-width: 1400px; }
.kpi-card {
    background: linear-gradient(135deg, #1a1f2e 0%, #161b28 100%);
    border: 1px solid #1e2130; border-radius: 16px;
    padding: 1.4rem 1.6rem; position: relative; overflow: hidden;
}
.kpi-card::before {
    content:''; position:absolute; top:0; left:0; right:0;
    height:2px; border-radius:16px 16px 0 0;
}
.kpi-card.green::before  { background: #22c55e; }
.kpi-card.red::before    { background: #ef4444; }
.kpi-card.blue::before   { background: #3b82f6; }
.kpi-card.amber::before  { background: #f59e0b; }
.kpi-card.purple::before { background: #8b5cf6; }
.kpi-label { font-size:10px; letter-spacing:0.12em; text-transform:uppercase; color:#64748b; margin-bottom:6px; font-family:'DM Mono',monospace; }
.kpi-value { font-size:24px; font-weight:700; color:#f1f5f9; font-family:'DM Mono',monospace; letter-spacing:-0.02em; }
.kpi-sub   { font-size:11px; color:#475569; margin-top:4px; font-family:'DM Mono',monospace; }
.section-header { font-size:11px; letter-spacing:0.14em; text-transform:uppercase; color:#475569; font-family:'DM Mono',monospace; margin:2rem 0 1rem; padding-bottom:8px; border-bottom:1px solid #1e2130; }
.bs-table { width:100%; border-collapse:collapse; font-family:'DM Mono',monospace; font-size:13px; }
.bs-table th { padding:10px 16px; text-align:left; font-size:10px; letter-spacing:0.1em; text-transform:uppercase; color:#475569; border-bottom:1px solid #1e2130; }
.bs-table td { padding:9px 16px; color:#cbd5e1; border-bottom:1px solid #0f1117; }
.bs-table tr:hover td { background:#1a1f2e; }
.bs-table .total-row td { color:#f1f5f9; font-weight:600; border-top:1px solid #2d3550; border-bottom:2px solid #2d3550; }
.bs-table .section-row td { color:#94a3b8; font-size:10px; letter-spacing:0.1em; text-transform:uppercase; padding-top:16px; background:transparent; }
.positive { color:#22c55e !important; }
.negative { color:#ef4444 !important; }
</style>
""", unsafe_allow_html=True)

CHART_LAYOUT = dict(
    plot_bgcolor="#13161f", paper_bgcolor="#13161f",
    font=dict(family="DM Mono", color="#94a3b8", size=11),
    margin=dict(l=0, r=0, t=30, b=0),
    xaxis=dict(gridcolor="#1e2130"),
    yaxis=dict(gridcolor="#1e2130"),
    hovermode="x unified",
)

# ─────────────────────────────────────────────
# DATA FETCH
# ─────────────────────────────────────────────
API_URL = "https://server.bookmetro.co.ke/api/v1.1/parcels/analytics/export"

@st.cache_data(ttl=300, show_spinner=False)
def fetch_all():
    try:
        r = requests.get(API_URL, timeout=20)
        r.raise_for_status()
        return r.json(), None
    except Exception as e:
        return None, str(e)

with st.spinner("Fetching BookMetro data..."):
    raw, fetch_err = fetch_all()

if fetch_err or not raw:
    st.error(f"Could not reach API: {fetch_err}")
    st.stop()

# ─────────────────────────────────────────────
# PARSE
# ─────────────────────────────────────────────
def to_df(records, date_field):
    if not records:
        return pd.DataFrame()
    df = pd.DataFrame(records)
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0)
    df["date"]   = pd.to_datetime(df[date_field]).dt.normalize()
    df["month"]  = df["date"].dt.to_period("M").astype(str)
    df["month_name"] = df["date"].dt.strftime("%B %Y")
    df["day_name"]   = df["date"].dt.day_name()
    return df

rev_df = to_df(raw["data"].get("revenue", []),  "revenueDate")
exp_df = to_df(raw["data"].get("expenses", []), "expenseDate")

# Parcels
par_raw = raw["data"].get("parcels", [])
par_df  = pd.DataFrame(par_raw) if par_raw else pd.DataFrame()
if not par_df.empty:
    # find best date column
    for dc in ["parcelDate","createdAt","date","updatedAt"]:
        if dc in par_df.columns:
            par_df["date"] = pd.to_datetime(par_df[dc]).dt.normalize()
            break
    par_df["month"]      = par_df["date"].dt.to_period("M").astype(str)
    par_df["month_name"] = par_df["date"].dt.strftime("%B %Y")
    par_df["day_name"]   = par_df["date"].dt.day_name()

    # detect route column
    route_col = next((c for c in ["route","routeName","route_name","routeId","from","origin","destination"] if c in par_df.columns), None)

# ─────────────────────────────────────────────
# GLOBAL METRICS
# ─────────────────────────────────────────────
total_revenue  = rev_df["amount"].sum() if not rev_df.empty else 0
total_expenses = exp_df["amount"].sum() if not exp_df.empty else 0
net_profit     = total_revenue - total_expenses
margin_pct     = (net_profit / total_revenue * 100) if total_revenue > 0 else 0

# ─────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 📦 BookMetro")
    st.markdown("---")

    all_months = ["All"] + sorted(rev_df["month_name"].unique().tolist()) if not rev_df.empty else ["All"]
    sel_month  = st.selectbox("Filter by month", all_months)

    all_routes = []
    if not par_df.empty and route_col:
        all_routes = sorted(par_df[route_col].dropna().astype(str).unique().tolist())
    sel_route = st.selectbox("Filter parcels by route", ["All routes"] + all_routes) if all_routes else None

    st.markdown("---")
    if st.button("🔄 Refresh", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    st.markdown(
        f'<p style="font-size:10px;color:#334155;font-family:DM Mono,monospace;">'
        f'Last fetched<br>{datetime.now().strftime("%d %b %Y %H:%M")}</p>',
        unsafe_allow_html=True,
    )

# filtered slices
def mfilter(df):
    if sel_month == "All" or df.empty:
        return df
    return df[df["month_name"] == sel_month]

rev_f = mfilter(rev_df)
exp_f = mfilter(exp_df)
par_f = mfilter(par_df) if not par_df.empty else par_df

# ─────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────
st.markdown("## 📦 BookMetro Financial Dashboard")
if sel_month != "All":
    st.caption(f"Showing: {sel_month}")

# ─────────────────────────────────────────────
# KPI CARDS
# ─────────────────────────────────────────────
st.markdown('<p class="section-header">Overview</p>', unsafe_allow_html=True)
c1, c2, c3, c4, c5 = st.columns(5)
def kpi(col, label, value, sub, color):
    with col:
        st.markdown(f'<div class="kpi-card {color}"><div class="kpi-label">{label}</div>'
                    f'<div class="kpi-value">{value}</div><div class="kpi-sub">{sub}</div></div>',
                    unsafe_allow_html=True)

kpi(c1, "Total Revenue",  f"KES {total_revenue:,.0f}",  f"{len(rev_df)} txns",   "green")
kpi(c2, "Total Expenses", f"KES {total_expenses:,.0f}", f"{len(exp_df)} txns",   "red")
kpi(c3, "Net Profit",     f"KES {net_profit:,.0f}",     "Revenue − expenses",    "blue")
kpi(c4, "Profit Margin",  f"{margin_pct:.1f}%",          "Overall margin",        "amber")
kpi(c5, "Total Parcels",  f"{len(par_df):,}",            "All records",           "purple")

# ─────────────────────────────────────────────
# DAILY PARCELS
# ─────────────────────────────────────────────
st.markdown('<p class="section-header">Daily parcels</p>', unsafe_allow_html=True)

if not par_f.empty:
    view_col, chart_col = st.columns([1, 4])
    with view_col:
        parcel_view = st.radio("Group by", ["All dates", "By month", "By day of week"])

    with chart_col:
        DOW_ORDER = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]

        if parcel_view == "All dates":
            daily = par_f.groupby("date").size().reset_index(name="count")
            daily["label"] = daily["date"].dt.strftime("%d %b %Y")
            fig = go.Figure(go.Bar(x=daily["label"], y=daily["count"], marker_color="#3b82f6", marker_opacity=0.85))
            fig.update_layout(**CHART_LAYOUT, xaxis_tickangle=-45, yaxis_title="Parcels")

        elif parcel_view == "By month":
            monthly = par_f.groupby("month_name").size().reset_index(name="count")
            fig = go.Figure(go.Bar(x=monthly["month_name"], y=monthly["count"], marker_color="#8b5cf6", marker_opacity=0.85))
            fig.update_layout(**CHART_LAYOUT, yaxis_title="Parcels")

        else:
            dow = par_f.groupby("day_name").size().reset_index(name="count")
            dow["day_name"] = pd.Categorical(dow["day_name"], categories=DOW_ORDER, ordered=True)
            dow = dow.sort_values("day_name")
            fig = go.Figure(go.Bar(x=dow["day_name"], y=dow["count"], marker_color="#22c55e", marker_opacity=0.85))
            fig.update_layout(**CHART_LAYOUT, yaxis_title="Parcels")

        st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No parcel data available.")

# ─────────────────────────────────────────────
# PARCELS PER ROUTE
# ─────────────────────────────────────────────
st.markdown('<p class="section-header">Parcels per route</p>', unsafe_allow_html=True)

if not par_df.empty and route_col:
    route_data = par_df if (sel_route is None or sel_route == "All routes") else par_df[par_df[route_col].astype(str) == sel_route]
    route_counts = (route_data.groupby(route_col).size()
                    .reset_index(name="count")
                    .sort_values("count", ascending=True))
    fig_r = go.Figure(go.Bar(
        x=route_counts["count"], y=route_counts[route_col].astype(str),
        orientation="h", marker_color="#f59e0b", marker_opacity=0.85,
        text=route_counts["count"], textposition="outside",
        textfont=dict(family="DM Mono", size=11, color="#94a3b8"),
    ))
    fig_r.update_layout(
        **{**CHART_LAYOUT, "margin": dict(l=0, r=60, t=10, b=0)},
        xaxis_title="Parcels", yaxis_title="",
        height=max(300, len(route_counts) * 40),
    )
    st.plotly_chart(fig_r, use_container_width=True)
elif not par_df.empty:
    st.info("No route field detected in the parcel data. Showing raw records below.")
    st.dataframe(par_df.head(30), use_container_width=True)
else:
    st.info("No parcel data.")

# ─────────────────────────────────────────────
# DAILY REVENUE & EXPENSES
# ─────────────────────────────────────────────
st.markdown('<p class="section-header">Daily revenue & expenses</p>', unsafe_allow_html=True)

fig_daily = go.Figure()
if not rev_f.empty:
    dr = rev_f.groupby("date")["amount"].sum().reset_index()
    dr["label"] = dr["date"].dt.strftime("%d %b")
    fig_daily.add_trace(go.Bar(x=dr["label"], y=dr["amount"], name="Revenue",
                               marker_color="#3b82f6", marker_opacity=0.85))
if not exp_f.empty:
    de = exp_f.groupby("date")["amount"].sum().reset_index()
    de["label"] = de["date"].dt.strftime("%d %b")
    fig_daily.add_trace(go.Bar(x=de["label"], y=de["amount"], name="Expenses",
                               marker_color="#ef4444", marker_opacity=0.75))
fig_daily.update_layout(
    **CHART_LAYOUT, barmode="group",
    legend=dict(orientation="h", y=1.1, bgcolor="rgba(0,0,0,0)"),
    xaxis_tickangle=-45,
    yaxis=dict(gridcolor="#1e2130", tickprefix="KES "),
)
st.plotly_chart(fig_daily, use_container_width=True)

# ─────────────────────────────────────────────
# REVENUE vs EXPENSES TREND
# ─────────────────────────────────────────────
st.markdown('<p class="section-header">Monthly revenue vs expenses</p>', unsafe_allow_html=True)

fig_trend = go.Figure()
if not rev_df.empty:
    mr = rev_df.groupby("month")["amount"].sum().reset_index().rename(columns={"amount":"revenue"})
    fig_trend.add_trace(go.Scatter(x=mr["month"], y=mr["revenue"], name="Revenue",
        mode="lines+markers", line=dict(color="#3b82f6", width=2.5), marker=dict(size=6),
        fill="tozeroy", fillcolor="rgba(59,130,246,0.08)"))

    if not exp_df.empty:
        me = exp_df.groupby("month")["amount"].sum().reset_index().rename(columns={"amount":"expenses"})
        fig_trend.add_trace(go.Scatter(x=me["month"], y=me["expenses"], name="Expenses",
            mode="lines+markers", line=dict(color="#ef4444", width=2), marker=dict(size=6)))
        mg = mr.merge(me, on="month", how="left").fillna(0)
        mg["net"] = mg["revenue"] - mg["expenses"]
        fig_trend.add_trace(go.Scatter(x=mg["month"], y=mg["net"], name="Net profit",
            mode="lines+markers", line=dict(color="#22c55e", width=2, dash="dot"), marker=dict(size=5)))

fig_trend.update_layout(
    **CHART_LAYOUT,
    legend=dict(orientation="h", y=1.1, bgcolor="rgba(0,0,0,0)"),
    yaxis=dict(gridcolor="#1e2130", tickprefix="KES "),
)
st.plotly_chart(fig_trend, use_container_width=True)

# ─────────────────────────────────────────────
# BALANCE SHEET
# ─────────────────────────────────────────────
st.markdown('<p class="section-header">Balance sheet</p>', unsafe_allow_html=True)

rev_by_source = rev_df.groupby("source")["amount"].sum().to_dict() if not rev_df.empty else {}
mpesa_rev = rev_by_source.get("M-Pesa", 0)
biz_rev   = rev_by_source.get("business_number", 0)
other_rev = sum(v for k, v in rev_by_source.items() if k not in ["M-Pesa","business_number"])

def bs_section(title, items, total_label):
    rows = f'<tr class="section-row"><td colspan="2">{title}</td></tr>'
    total = 0
    for name, val in items.items():
        cls = "positive" if val >= 0 else "negative"
        rows += f'<tr><td>{name}</td><td class="{cls}" style="text-align:right">KES {val:,.0f}</td></tr>'
        total += val
    rows += f'<tr class="total-row"><td>{total_label}</td><td style="text-align:right">KES {total:,.0f}</td></tr>'
    return rows, total

a_html, a_tot = bs_section("Assets", {
    "M-Pesa collections":       mpesa_rev,
    "Business number receipts": biz_rev,
    "Other revenue":            other_rev,
}, "Total assets")

l_html, l_tot = bs_section("Liabilities", {
    "Operating expenses": total_expenses,
}, "Total liabilities")

e_html, e_tot = bs_section("Equity", {
    "Retained earnings (net profit)": net_profit,
}, "Total equity")

bs1, bs2 = st.columns(2)
with bs1:
    st.markdown(f'<table class="bs-table"><thead><tr><th>Item</th><th style="text-align:right">Amount</th></tr></thead><tbody>{a_html}</tbody></table>', unsafe_allow_html=True)
with bs2:
    le = l_tot + e_tot
    chk_cls  = "positive" if abs(le - a_tot) < 1 else "negative"
    chk_text = "✓ Balanced" if abs(le - a_tot) < 1 else "✗ Check figures"
    st.markdown(f'''<table class="bs-table">
        <thead><tr><th>Item</th><th style="text-align:right">Amount</th></tr></thead>
        <tbody>
            {l_html}{e_html}
            <tr class="total-row">
                <td>Liabilities + Equity</td>
                <td class="{chk_cls}" style="text-align:right">KES {le:,.0f}&nbsp;<span style="font-size:11px">{chk_text}</span></td>
            </tr>
        </tbody>
    </table>''', unsafe_allow_html=True)

# ─────────────────────────────────────────────
# PROFIT MARGIN TREND
# ─────────────────────────────────────────────
if not rev_df.empty and not exp_df.empty:
    st.markdown('<p class="section-header">Profit margin trend</p>', unsafe_allow_html=True)
    mr2 = rev_df.groupby("month")["amount"].sum().reset_index().rename(columns={"amount":"revenue"})
    me2 = exp_df.groupby("month")["amount"].sum().reset_index().rename(columns={"amount":"expenses"})
    mg2 = mr2.merge(me2, on="month", how="left").fillna(0)
    mg2 = mg2[mg2["revenue"] > 0].copy()
    mg2["margin"] = ((mg2["revenue"] - mg2["expenses"]) / mg2["revenue"] * 100).round(1)

    fig_mg = go.Figure(go.Scatter(
        x=mg2["month"], y=mg2["margin"],
        fill="tozeroy", mode="lines+markers",
        line=dict(color="#8b5cf6", width=2.5),
        fillcolor="rgba(139,92,246,0.10)",
        marker=dict(size=7, color="#8b5cf6"),
        text=[f"{v:.1f}%" for v in mg2["margin"]],
        textposition="top center",
        textfont=dict(family="DM Mono", size=10, color="#8b5cf6"),
        hovertemplate="<b>%{x}</b><br>Margin: %{y:.1f}%<extra></extra>",
    ))
    avg = mg2["margin"].mean()
    fig_mg.add_hline(y=avg, line_dash="dot", line_color="#475569", line_width=1,
                     annotation_text=f"avg {avg:.1f}%",
                     annotation_font=dict(family="DM Mono", size=10, color="#475569"))
    fig_mg.update_layout(
        **CHART_LAYOUT, showlegend=False,
        yaxis=dict(gridcolor="#1e2130", ticksuffix="%"),
    )
    st.plotly_chart(fig_mg, use_container_width=True)

# ─────────────────────────────────────────────
# RAW DATA
# ─────────────────────────────────────────────
with st.expander("📄 Revenue transactions"):
    cols = [c for c in ["date","amount","source","description","mpesaCode"] if c in rev_df.columns]
    st.dataframe(rev_df[cols].sort_values("date", ascending=False), use_container_width=True)

if not exp_df.empty:
    with st.expander("📄 Expense transactions"):
        st.dataframe(exp_df.sort_values("date", ascending=False), use_container_width=True)

if not par_df.empty:
    with st.expander("📄 Parcel records"):
        st.dataframe(par_df.sort_values("date", ascending=False), use_container_width=True)
