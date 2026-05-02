import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import re

# ─────────────────────────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Kujawa Transport Solutions",
    page_icon="🚚",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────────
# CSS
# ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=Unbounded:wght@300;400;700&display=swap');

html, body, [class*="css"] {
    font-family: 'IBM Plex Mono', monospace;
}
[data-testid="stSidebar"] {
    background: #0b0f1a;
    border-right: 1px solid #1a2035;
}
[data-testid="stSidebar"] * { color: #8898b8 !important; }
[data-testid="stSidebar"] label {
    font-size: 9px !important;
    letter-spacing: 0.15em;
    text-transform: uppercase;
    color: #3d4f70 !important;
}
.main .block-container { padding: 1.5rem 2rem; max-width: 1600px; }

.page-header { margin-bottom: 1.5rem; padding-bottom: 1rem; border-bottom: 1px solid #1a2035; }
.page-title { font-family: 'Unbounded', sans-serif; font-size: 22px; font-weight: 700; color: #e2eaf8; letter-spacing: -0.02em; margin: 0; }
.page-subtitle { font-size: 11px; color: #3d4f70; letter-spacing: 0.06em; margin-top: 4px; }

.kpi-card {
    background: #0b0f1a; border: 1px solid #1a2035; border-radius: 10px;
    padding: 1.1rem 1.3rem; position: relative; overflow: hidden;
}
.kpi-card::after {
    content: ''; position: absolute; bottom: 0; left: 0; right: 0; height: 1px;
}
.kpi-card.cyan::after  { background: linear-gradient(90deg,#00d4ff,transparent); }
.kpi-card.green::after { background: linear-gradient(90deg,#00ff94,transparent); }
.kpi-card.red::after   { background: linear-gradient(90deg,#ff4466,transparent); }
.kpi-card.amber::after { background: linear-gradient(90deg,#ffb800,transparent); }
.kpi-card.blue::after  { background: linear-gradient(90deg,#4488ff,transparent); }
.kpi-label { font-size: 9px; letter-spacing: 0.18em; text-transform: uppercase; color: #3d4f70; margin-bottom: 8px; }
.kpi-value { font-family: 'Unbounded', sans-serif; font-size: 20px; font-weight: 700; color: #e2eaf8; letter-spacing: -0.03em; line-height: 1; }
.kpi-sub { font-size: 10px; color: #2a3550; margin-top: 6px; }

.section-heading {
    font-size: 9px; letter-spacing: 0.2em; text-transform: uppercase; color: #2a3550;
    margin: 1.8rem 0 0.8rem; padding-bottom: 6px; border-bottom: 1px solid #1a2035;
    display: flex; align-items: center; gap: 8px;
}
.section-heading::before {
    content: ''; display: inline-block; width: 3px; height: 12px;
    background: #00d4ff; border-radius: 2px;
}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────
# CHART DEFAULTS
# ─────────────────────────────────────────────────────────────────
BG    = "#0b0f1a"
GRID  = "#1a2035"
FONT  = dict(family="IBM Plex Mono, monospace", color="#5a6e90", size=11)
COLORS = ["#00d4ff","#00ff94","#4488ff","#ffb800","#ff4466","#aa66ff","#ff8844"]
DOW   = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]

def BL(**kw):
    d = dict(
        plot_bgcolor=BG, paper_bgcolor=BG, font=FONT,
        margin=dict(l=0, r=0, t=30, b=0),
        xaxis=dict(gridcolor=GRID, linecolor=GRID, tickfont=dict(size=10)),
        yaxis=dict(gridcolor=GRID, linecolor=GRID, tickfont=dict(size=10)),
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(size=10), orientation="h", y=1.1),
        hovermode="x unified",
    )
    d.update(kw)
    return d

# ─────────────────────────────────────────────────────────────────
# DATA FETCH
# ─────────────────────────────────────────────────────────────────
API_URL = "https://server.bookmetro.co.ke/api/v1.1/parcels/analytics/export"

@st.cache_data(ttl=300, show_spinner=False)
def fetch():
    try:
        r = requests.get(API_URL, timeout=25)
        r.raise_for_status()
        return r.json(), None
    except Exception as e:
        return None, str(e)

with st.spinner("Loading Kujawa data..."):
    raw, fetch_err = fetch()

if fetch_err or not raw:
    st.error(f"API error: {fetch_err}")
    st.stop()

# ─────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────
def hms_to_min(s):
    if not s or not isinstance(s, str): return None
    try:
        h = int(re.search(r'(\d+)h', s).group(1)) if re.search(r'(\d+)h', s) else 0
        m = int(re.search(r'(\d+)m', s).group(1)) if re.search(r'(\d+)m', s) else 0
        sec = int(re.search(r'(\d+)s', s).group(1)) if re.search(r'(\d+)s', s) else 0
        return round(h*60 + m + sec/60, 2)
    except: return None

def add_time_cols(df, date_col):
    df["date"]        = pd.to_datetime(df[date_col]).dt.normalize()
    df["month"]       = df["date"].dt.strftime("%Y-%m")
    df["month_label"] = df["date"].dt.strftime("%b %Y")
    df["day_name"]    = df["date"].dt.day_name()
    return df

def kpi_card(col, label, value, sub, color):
    with col:
        st.markdown(
            f'<div class="kpi-card {color}">'
            f'<div class="kpi-label">{label}</div>'
            f'<div class="kpi-value">{value}</div>'
            f'<div class="kpi-sub">{sub}</div></div>',
            unsafe_allow_html=True,
        )

def section(title):
    st.markdown(f'<div class="section-heading">{title}</div>', unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────
# PARSE
# ─────────────────────────────────────────────────────────────────

# Parcels
par_raw = raw["data"].get("parcels", [])
par_df  = pd.DataFrame(par_raw) if par_raw else pd.DataFrame()
if not par_df.empty:
    par_df = add_time_cols(par_df, "createdAt")
    par_df["reg_min"]     = par_df["registeredTimeHms"].apply(hms_to_min)
    par_df["pending_min"] = par_df["pendingTimeHms"].apply(hms_to_min)
    par_df["transit_min"] = par_df["inTransitTimeHms"].apply(hms_to_min)
    for c in ["routeName","townName","areaName"]:
        if c in par_df.columns:
            par_df[c] = par_df[c].fillna("Unknown").str.strip().str.title()

# Revenue
rev_raw = raw["data"].get("revenue", [])
rev_df  = pd.DataFrame(rev_raw) if rev_raw else pd.DataFrame()
if not rev_df.empty:
    rev_df["amount"] = pd.to_numeric(rev_df["amount"], errors="coerce").fillna(0)
    rev_df = add_time_cols(rev_df, "revenueDate")
    # Link revenue to route/town via parcelCode in description
    if not par_df.empty and "parcelCode" in par_df.columns:
        pmap = (par_df.drop_duplicates("parcelCode")
                .set_index("parcelCode")[["routeName","townName"]]
                .to_dict("index"))
        def get_code(desc):
            if not isinstance(desc, str): return None
            m = re.search(r'([A-Z]{2}\d{4}-\d+)', desc)
            return m.group(1) if m else None
        rev_df["_code"] = rev_df["description"].apply(get_code)
        rev_df["routeName"] = rev_df["_code"].map(lambda x: pmap.get(x, {}).get("routeName", "Unknown") if x else "Unknown")
        rev_df["townName"]  = rev_df["_code"].map(lambda x: pmap.get(x, {}).get("townName",  "Unknown") if x else "Unknown")
    else:
        rev_df["routeName"] = "Unknown"
        rev_df["townName"]  = "Unknown"

# Expenses — 3 source models
exp_raw = raw["data"].get("expenses", [])
exp_df  = pd.DataFrame(exp_raw) if exp_raw else pd.DataFrame()
if not exp_df.empty:
    exp_df["amount"]          = pd.to_numeric(exp_df["amount"], errors="coerce").fillna(0)
    exp_df["transactionCost"] = pd.to_numeric(exp_df.get("transactionCost", pd.Series(dtype=float)), errors="coerce").fillna(0)
    exp_df["total_cost"]      = exp_df["amount"] + exp_df["transactionCost"]
    exp_df = add_time_cols(exp_df, "date")
    # Unified channel label
    def channel_label(row):
        ch = str(row.get("expenseChannel","")).lower()
        if ch == "bank":  return "Bank"
        if ch == "phone": return "Phone (M-Pesa)"
        src = str(row.get("source","")).lower()
        if src == "cash": return "Cash"
        return "Other"
    exp_df["channel"] = exp_df.apply(channel_label, axis=1)

# Summary
total_revenue  = rev_df["amount"].sum()       if not rev_df.empty else 0
total_expenses = exp_df["total_cost"].sum()   if not exp_df.empty else 0
net_profit     = total_revenue - total_expenses
margin_pct     = (net_profit / total_revenue * 100) if total_revenue > 0 else 0

# ─────────────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="padding:20px 18px 14px;border-bottom:1px solid #1a2035;">
        <div style="font-family:'Unbounded',sans-serif;font-size:14px;font-weight:700;color:#e2eaf8;letter-spacing:.03em;">KUJAWA</div>
        <div style="font-size:9px;color:#2a3550;letter-spacing:.15em;text-transform:uppercase;margin-top:2px;">Transport Solutions</div>
    </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    section_choice = st.radio(
        "Navigation",
        ["📦  Parcel Analytics", "💰  Financials"],
        label_visibility="collapsed",
    )

    st.markdown("---")
    if st.button("⟳  Refresh", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    st.markdown(
        f'<p style="font-size:9px;color:#1a2035;line-height:1.9;padding-top:4px;">'
        f'UPDATED<br>{datetime.now().strftime("%d %b %Y · %H:%M")}</p>',
        unsafe_allow_html=True,
    )


# ═════════════════════════════════════════════════════════════════
# PARCEL ANALYTICS
# ═════════════════════════════════════════════════════════════════
if "Parcel" in section_choice:

    st.markdown("""
    <div class="page-header">
        <div class="page-title">Parcel Analytics</div>
        <div class="page-subtitle">Volume · Distribution · Efficiency</div>
    </div>""", unsafe_allow_html=True)

    if par_df.empty:
        st.info("No parcel data.")
        st.stop()

    # ── Hierarchical route → town → area filters ──
    all_routes = sorted(par_df["routeName"].dropna().unique()) if "routeName" in par_df.columns else []
    fc1, fc2, fc3 = st.columns(3)

    with fc1:
        sel_route = st.selectbox("Filter by route", ["All routes"] + all_routes, key="par_route")

    par_r = par_df if sel_route == "All routes" else par_df[par_df["routeName"] == sel_route]
    all_towns = sorted(par_r["townName"].dropna().unique()) if "townName" in par_r.columns else []

    with fc2:
        sel_town = st.selectbox("Filter by town", ["All towns"] + all_towns, key="par_town")

    par_rt = par_r if sel_town == "All towns" else par_r[par_r["townName"] == sel_town]
    all_areas = sorted(par_rt["areaName"].dropna().unique()) if "areaName" in par_rt.columns else []

    with fc3:
        sel_area = st.selectbox("Filter by area", ["All areas"] + all_areas, key="par_area")

    pv = par_rt if sel_area == "All areas" else par_rt[par_rt["areaName"] == sel_area]

    # ── KPI ──
    section("Overview")
    k1, k2, k3, k4 = st.columns(4)
    delivered  = int((pv["parcelStatus"] == "delivered").sum())  if "parcelStatus" in pv.columns else 0
    in_transit = int((pv["parcelStatus"] == "in-transit").sum()) if "parcelStatus" in pv.columns else 0
    pending    = int((pv["parcelStatus"] == "pending").sum())    if "parcelStatus" in pv.columns else 0
    kpi_card(k1, "Total Parcels", f"{len(pv):,}",     "in current filter",  "cyan")
    kpi_card(k2, "Delivered",     f"{delivered:,}",    "completed",          "green")
    kpi_card(k3, "In Transit",    f"{in_transit:,}",   "currently moving",   "amber")
    kpi_card(k4, "Pending",       f"{pending:,}",      "awaiting dispatch",  "blue")

    # ── Distribution bar charts ──
    section("Distribution")

    def hbar(df, col, title, ci=0):
        if col not in df.columns or df.empty:
            return go.Figure().update_layout(**BL(height=250))
        cnt = df.groupby(col).size().reset_index(name="n").sort_values("n", ascending=True)
        fig = go.Figure(go.Bar(
            x=cnt["n"], y=cnt[col].astype(str), orientation="h",
            marker_color=COLORS[ci], marker_opacity=0.85,
            text=cnt["n"], textposition="outside",
            textfont=dict(size=10, color="#5a6e90"),
            hovertemplate="%{y}: %{x}<extra></extra>",
        ))
        fig.update_layout(**BL(
            title=dict(text=title, font=dict(size=12, color="#8898b8")),
            margin=dict(l=0, r=50, t=30, b=0),
            height=max(260, len(cnt)*38+60),
            xaxis=dict(gridcolor=GRID), yaxis=dict(gridcolor=GRID),
            hovermode="y unified",
        ))
        return fig

    d1, d2, d3 = st.columns(3)
    with d1: st.plotly_chart(hbar(pv, "routeName", "Parcels per Route", 0), use_container_width=True)
    with d2: st.plotly_chart(hbar(pv, "townName",  "Parcels per Town",  1), use_container_width=True)
    with d3: st.plotly_chart(hbar(pv, "areaName",  "Parcels per Area",  2), use_container_width=True)

    # ── Time Series ──
    section("Time Series")

    ts_c1, ts_c2 = st.columns([1, 4])
    with ts_c1:
        ts_group = st.radio("Group parcels by", ["All dates","By month","By day of week"], key="ts")

    with ts_c2:
        if ts_group == "All dates":
            ts = pv.groupby("date").size().reset_index(name="n")
            ts["lbl"] = ts["date"].dt.strftime("%d %b %Y")
            xv, yv, ci, ang = ts["lbl"], ts["n"], 0, -45
        elif ts_group == "By month":
            ts = pv.groupby(["month","month_label"]).size().reset_index(name="n").sort_values("month")
            xv, yv, ci, ang = ts["month_label"], ts["n"], 3, -30
        else:
            ts = pv.groupby("day_name").size().reset_index(name="n")
            ts["day_name"] = pd.Categorical(ts["day_name"], categories=DOW, ordered=True)
            ts = ts.sort_values("day_name")
            xv, yv, ci, ang = ts["day_name"], ts["n"], 1, 0

        fig_ts = go.Figure(go.Bar(
            x=xv, y=yv, marker_color=COLORS[ci], marker_opacity=0.82,
            hovertemplate="%{x}: %{y} parcels<extra></extra>",
        ))
        fig_ts.update_layout(**BL(
            yaxis_title="Parcels", height=320,
            xaxis=dict(gridcolor=GRID, tickangle=ang),
        ))
        st.plotly_chart(fig_ts, use_container_width=True)

    # ── Efficiency ──
    section("Delivery Efficiency — Average Time per Stage (minutes)")

    eff_c1, eff_c2 = st.columns([1, 4])
    with eff_c1:
        eff_by = st.radio("Break down by", ["Overall","By route","By day of week"], key="eff")

    with eff_c2:
        edf = pv[["routeName","day_name","reg_min","pending_min","transit_min"]].copy()
        edf = edf[edf[["reg_min","pending_min","transit_min"]].notna().any(axis=1)]

        if edf.empty:
            st.info("No timing data for this filter.")
        else:
            stages = {
                "Registration": ("reg_min",     COLORS[0]),
                "Pending":      ("pending_min",  COLORS[3]),
                "In Transit":   ("transit_min",  COLORS[1]),
            }

            if eff_by == "Overall":
                fig_e = go.Figure()
                for label, (col, color) in stages.items():
                    avg = edf[col].mean()
                    if pd.notna(avg):
                        fig_e.add_trace(go.Bar(
                            x=[label], y=[round(avg,1)], name=label,
                            marker_color=color, marker_opacity=0.85,
                            text=[f"{avg:.1f}m"], textposition="outside",
                            textfont=dict(size=11, color=color),
                        ))
                fig_e.update_layout(**BL(barmode="group", height=300, showlegend=False,
                    yaxis_title="Average minutes"))

            elif eff_by == "By route":
                grp = edf.groupby("routeName")[["reg_min","pending_min","transit_min"]].mean().round(1).reset_index()
                fig_e = go.Figure()
                for label, (col, color) in stages.items():
                    fig_e.add_trace(go.Bar(x=grp["routeName"], y=grp[col], name=label,
                        marker_color=color, marker_opacity=0.82))
                fig_e.update_layout(**BL(barmode="group", height=340,
                    xaxis=dict(gridcolor=GRID, tickangle=-30),
                    yaxis_title="Average minutes"))

            else:
                grp = edf.groupby("day_name")[["reg_min","pending_min","transit_min"]].mean().round(1).reset_index()
                grp["day_name"] = pd.Categorical(grp["day_name"], categories=DOW, ordered=True)
                grp = grp.sort_values("day_name")
                fig_e = go.Figure()
                for label, (col, color) in stages.items():
                    fig_e.add_trace(go.Bar(x=grp["day_name"], y=grp[col], name=label,
                        marker_color=color, marker_opacity=0.82))
                fig_e.update_layout(**BL(barmode="group", height=340,
                    yaxis_title="Average minutes"))

            st.plotly_chart(fig_e, use_container_width=True)


# ═════════════════════════════════════════════════════════════════
# FINANCIALS
# ═════════════════════════════════════════════════════════════════
else:

    st.markdown("""
    <div class="page-header">
        <div class="page-title">Financials</div>
        <div class="page-subtitle">Revenue · Expenses · Profit</div>
    </div>""", unsafe_allow_html=True)

    # ── KPI ──
    section("Overview")
    k1, k2, k3, k4 = st.columns(4)
    kpi_card(k1, "Total Revenue",  f"KES {total_revenue:,.0f}",  f"{len(rev_df)} txns",      "green")
    kpi_card(k2, "Total Expenses", f"KES {total_expenses:,.0f}", "incl. transaction costs",  "red")
    kpi_card(k3, "Net Profit",     f"KES {net_profit:,.0f}",     "revenue minus expenses",   "cyan")
    kpi_card(k4, "Profit Margin",  f"{margin_pct:.1f}%",          "net ÷ revenue",            "amber")

    # ══════════════════════════════════
    # EXPENSES
    # ══════════════════════════════════
    section("Expenses")

    if exp_df.empty:
        st.info("No expense data.")
    else:
        ef1, ef2, ef3 = st.columns([1.2, 1.2, 1])
        with ef1:
            ch_opts = ["All channels"] + sorted(exp_df["channel"].unique().tolist())
            sel_ch = st.selectbox("Filter by channel", ch_opts, key="exp_ch")
        with ef2:
            exp_grp = st.radio("Group by", ["By month","By day of week"], key="exp_grp", horizontal=True)
        with ef3:
            st.markdown("<br>", unsafe_allow_html=True)
            show_split = st.checkbox("Split transaction costs", value=False)

        ev = exp_df if sel_ch == "All channels" else exp_df[exp_df["channel"] == sel_ch]

        if exp_grp == "By month":
            grp = ev.groupby(["month","month_label"]).agg(
                amt=("amount","sum"), txc=("transactionCost","sum"), tot=("total_cost","sum")
            ).reset_index().sort_values("month")
            xv = grp["month_label"]; ang = -30
        else:
            grp = ev.groupby("day_name").agg(
                amt=("amount","sum"), txc=("transactionCost","sum"), tot=("total_cost","sum")
            ).reset_index()
            grp["day_name"] = pd.Categorical(grp["day_name"], categories=DOW, ordered=True)
            grp = grp.sort_values("day_name")
            xv = grp["day_name"]; ang = 0

        fig_exp = go.Figure()
        if show_split:
            fig_exp.add_trace(go.Bar(x=xv, y=grp["amt"], name="Expense",
                marker_color=COLORS[4], marker_opacity=0.85))
            fig_exp.add_trace(go.Bar(x=xv, y=grp["txc"], name="Txn cost",
                marker_color=COLORS[3], marker_opacity=0.75))
            fig_exp.update_layout(**BL(barmode="stack"))
        else:
            fig_exp.add_trace(go.Bar(x=xv, y=grp["tot"], name="Total expense",
                marker_color=COLORS[4], marker_opacity=0.85,
                hovertemplate="%{x}<br>KES %{y:,.0f}<extra></extra>"))
            fig_exp.update_layout(**BL())

        fig_exp.update_layout(
            yaxis=dict(gridcolor=GRID, tickprefix="KES "),
            xaxis=dict(gridcolor=GRID, tickangle=ang),
            height=340,
        )
        st.plotly_chart(fig_exp, use_container_width=True)

        # Channel breakdown + top descriptions
        ec1, ec2 = st.columns(2)

        with ec1:
            by_ch = exp_df.groupby("channel")["total_cost"].sum().reset_index()
            fig_ch = go.Figure(go.Pie(
                labels=by_ch["channel"], values=by_ch["total_cost"],
                hole=0.55, marker=dict(colors=COLORS[:len(by_ch)]),
                textfont=dict(family="IBM Plex Mono", size=11),
                hovertemplate="%{label}: KES %{value:,.0f}<extra></extra>",
            ))
            fig_ch.add_annotation(text="by\nchannel", x=0.5, y=0.5, showarrow=False,
                font=dict(size=10, color="#3d4f70", family="IBM Plex Mono"), align="center")
            fig_ch.update_layout(**BL(showlegend=True, height=280, margin=dict(l=0,r=0,t=20,b=0)))
            st.plotly_chart(fig_ch, use_container_width=True)

        with ec2:
            top = (exp_df.groupby("description")["total_cost"].sum()
                   .reset_index().sort_values("total_cost", ascending=True).tail(10))
            top["description"] = top["description"].fillna("(no description)").str.strip().str[:40]
            fig_top = go.Figure(go.Bar(
                x=top["total_cost"], y=top["description"], orientation="h",
                marker_color=COLORS[2], marker_opacity=0.82,
                text=top["total_cost"].map(lambda v: f"KES {v:,.0f}"),
                textposition="outside", textfont=dict(size=9, color="#5a6e90"),
                hovertemplate="%{y}<br>KES %{x:,.0f}<extra></extra>",
            ))
            fig_top.update_layout(**BL(
                margin=dict(l=0,r=90,t=30,b=0), height=280, hovermode="y unified",
                title=dict(text="Top expense descriptions", font=dict(size=11,color="#5a6e90")),
                xaxis=dict(gridcolor=GRID, tickprefix="KES "),
                yaxis=dict(gridcolor=GRID),
            ))
            st.plotly_chart(fig_top, use_container_width=True)

    # ══════════════════════════════════
    # REVENUE
    # ══════════════════════════════════
    section("Revenue")

    if rev_df.empty:
        st.info("No revenue data.")
    else:
        rf1, rf2 = st.columns([2, 1])
        with rf1:
            rev_grp = st.radio(
                "Group by",
                ["By month","By day of week","By route","By town"],
                key="rev_grp", horizontal=True,
            )
        with rf2:
            src_opts = ["All sources"] + sorted(rev_df["source"].dropna().unique().tolist()) if "source" in rev_df.columns else ["All sources"]
            sel_src = st.selectbox("Payment source", src_opts, key="rev_src")

        rv = rev_df if sel_src == "All sources" else rev_df[rev_df["source"] == sel_src]

        if rev_grp == "By month":
            grp = rv.groupby(["month","month_label"])["amount"].sum().reset_index().sort_values("month")
            xv, yv, ci, ang = grp["month_label"], grp["amount"], 1, -30
        elif rev_grp == "By day of week":
            grp = rv.groupby("day_name")["amount"].sum().reset_index()
            grp["day_name"] = pd.Categorical(grp["day_name"], categories=DOW, ordered=True)
            grp = grp.sort_values("day_name")
            xv, yv, ci, ang = grp["day_name"], grp["amount"], 0, 0
        elif rev_grp == "By route":
            grp = rv.groupby("routeName")["amount"].sum().reset_index().sort_values("amount", ascending=False)
            xv, yv, ci, ang = grp["routeName"], grp["amount"], 3, -30
        else:
            grp = rv.groupby("townName")["amount"].sum().reset_index().sort_values("amount", ascending=False)
            xv, yv, ci, ang = grp["townName"], grp["amount"], 2, -30

        fig_rev = go.Figure(go.Bar(
            x=xv, y=yv, marker_color=COLORS[ci], marker_opacity=0.85,
            hovertemplate="%{x}<br>KES %{y:,.0f}<extra></extra>",
        ))
if rev_grp in ["By month","By day of week"]:
    fig_rev.add_trace(go.Scatter(
        x=xv, y=yv, mode="lines+markers",
        line=dict(color="rgba(255,255,255,0.27)", width=1.5, dash="dot"),
        marker=dict(size=5, color="rgba(255,255,255,0.53)"), name="Trend",
        hovertemplate="%{x}<br>KES %{y:,.0f}<extra></extra>",
    ))
        fig_rev.update_layout(**BL(
            yaxis=dict(gridcolor=GRID, tickprefix="KES "),
            xaxis=dict(gridcolor=GRID, tickangle=ang),
            height=360, showlegend=False,
        ))
        st.plotly_chart(fig_rev, use_container_width=True)

        # Source donut + monthly net profit
        rc1, rc2 = st.columns(2)

        with rc1:
            if "source" in rev_df.columns:
                by_src = rev_df.groupby("source")["amount"].sum().reset_index()
                fig_src = go.Figure(go.Pie(
                    labels=by_src["source"], values=by_src["amount"],
                    hole=0.55, marker=dict(colors=COLORS[:len(by_src)]),
                    textfont=dict(family="IBM Plex Mono", size=11),
                    hovertemplate="%{label}: KES %{value:,.0f}<extra></extra>",
                ))
                fig_src.add_annotation(text="by\nsource", x=0.5, y=0.5, showarrow=False,
                    font=dict(size=10, color="#3d4f70", family="IBM Plex Mono"), align="center")
                fig_src.update_layout(**BL(showlegend=True, height=280, margin=dict(l=0,r=0,t=20,b=0)))
                st.plotly_chart(fig_src, use_container_width=True)

        with rc2:
            if not exp_df.empty:
                mr = rev_df.groupby("month_label")["amount"].sum().reset_index().rename(columns={"amount":"rev"})
                me = exp_df.groupby("month_label")["total_cost"].sum().reset_index().rename(columns={"total_cost":"exp"})
                mn = mr.merge(me, on="month_label", how="outer").fillna(0)
                mn["net"] = mn["rev"] - mn["exp"]
                colors_net = [COLORS[1] if v >= 0 else COLORS[4] for v in mn["net"]]
                fig_net = go.Figure(go.Bar(
                    x=mn["month_label"], y=mn["net"],
                    marker_color=colors_net, marker_opacity=0.85,
                    hovertemplate="%{x}<br>Net: KES %{y:,.0f}<extra></extra>",
                ))
                fig_net.update_layout(**BL(
                    title=dict(text="Monthly net profit", font=dict(size=11, color="#5a6e90")),
                    yaxis=dict(gridcolor=GRID, tickprefix="KES "),
                    xaxis=dict(gridcolor=GRID, tickangle=-30),
                    height=280, margin=dict(l=0,r=0,t=30,b=0), showlegend=False,
                ))
                st.plotly_chart(fig_net, use_container_width=True)

    # ── Raw data ──
    with st.expander("📄 Revenue transactions"):
        cols = [c for c in ["date","amount","source","description","mpesaCode","routeName","townName"] if c in rev_df.columns]
        st.dataframe(rev_df[cols].sort_values("date", ascending=False), use_container_width=True)

    with st.expander("📄 Expense transactions"):
        cols = [c for c in ["date","channel","sourceModel","amount","transactionCost","total_cost","description","phone"] if c in exp_df.columns]
        st.dataframe(exp_df[cols].sort_values("date", ascending=False), use_container_width=True)
