import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
from datetime import datetime

# ─── Page Config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Kujawa Transport Solutions",
    page_icon="🚚",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    [data-testid="stSidebar"] { background-color: #1a1a2e; }
    [data-testid="stSidebar"] * { color: #e0e0e0 !important; }
    [data-testid="stSidebar"] .stRadio label { color: #ffffff !important; font-weight: 600; }
    .metric-card {
        background: linear-gradient(135deg, #1e3a5f 0%, #0d2137 100%);
        border-radius: 12px;
        padding: 20px;
        border-left: 4px solid #00b4d8;
        margin-bottom: 10px;
    }
    .metric-card h3 { color: #8ecae6; font-size: 0.85rem; margin: 0; text-transform: uppercase; letter-spacing: 1px; }
    .metric-card h1 { color: #ffffff; font-size: 2rem; margin: 5px 0 0 0; }
    .profit-card { border-left-color: #06d6a0; }
    .expense-card { border-left-color: #ef476f; }
    .revenue-card { border-left-color: #ffd166; }
    .section-header {
        font-size: 1.4rem;
        font-weight: 700;
        color: #023e8a;
        border-bottom: 3px solid #00b4d8;
        padding-bottom: 8px;
        margin-bottom: 20px;
    }
    .stPlotlyChart { border-radius: 10px; overflow: hidden; }
</style>
""", unsafe_allow_html=True)

# ─── Data Loading ───────────────────────────────────────────────────────────────
API_URL = "https://server.bookmetro.co.ke/api/v1.1/parcels/analytics/export"

@st.cache_data(ttl=300)
def load_data():
    try:
        resp = requests.get(API_URL, timeout=30)
        resp.raise_for_status()
        raw = resp.json()
        data = raw.get("data", {})

        # ── Revenue ──
        rev_df = pd.DataFrame(data.get("revenue", []))
        if not rev_df.empty:
            rev_df["amount"] = pd.to_numeric(rev_df["amount"], errors="coerce").fillna(0)
            rev_df["date"] = pd.to_datetime(rev_df.get("revenueDate", rev_df.get("date")), errors="coerce")
            rev_df["month"] = rev_df["date"].dt.to_period("M").astype(str)
            rev_df["day_of_week"] = rev_df["date"].dt.day_name()
            # Normalise source → channel label
            source_map = {
                "M-Pesa": "Phone (M-Pesa)",
                "Cash": "Cash",
                "Paybill": "Paybill",
                "business_number": "Phone (M-Pesa)",
            }
            rev_df["channel"] = rev_df["source"].map(source_map).fillna(rev_df["source"])

        # ── Expenses ──
        exp_df = pd.DataFrame(data.get("expenses", []))
        if not exp_df.empty:
            exp_df["amount"] = pd.to_numeric(exp_df.get("amount", 0), errors="coerce").fillna(0)
            exp_df["transactionCost"] = pd.to_numeric(exp_df.get("transactionCost", 0), errors="coerce").fillna(0)
            exp_df["total_expense"] = exp_df["amount"] + exp_df["transactionCost"]
            date_col = next((c for c in ["expenseDate", "date", "createdAt"] if c in exp_df.columns), None)
            if date_col:
                exp_df["date"] = pd.to_datetime(exp_df[date_col], errors="coerce")
            else:
                exp_df["date"] = pd.NaT
            exp_df["month"] = exp_df["date"].dt.to_period("M").astype(str)
            exp_df["day_of_week"] = exp_df["date"].dt.day_name()
            # Derive channel from source / channel column
            ch_col = next((c for c in ["channel", "source", "paymentMethod"] if c in exp_df.columns), None)
            if ch_col:
                exp_df["channel"] = exp_df[ch_col]
            else:
                exp_df["channel"] = "Unknown"

        # ── Parcels ──
        par_df = pd.DataFrame(data.get("parcels", []))
        if not par_df.empty:
            date_col = next((c for c in ["registeredDate", "createdAt", "date"] if c in par_df.columns), None)
            if date_col:
                par_df["date"] = pd.to_datetime(par_df[date_col], errors="coerce")
            else:
                par_df["date"] = pd.NaT
            par_df["month"] = par_df["date"].dt.to_period("M").astype(str)
            par_df["day_of_week"] = par_df["date"].dt.day_name()

            # Time columns → minutes
            def hms_to_minutes(col):
                if col not in par_df.columns:
                    return pd.Series([None] * len(par_df))
                def parse_hms(val):
                    if pd.isna(val) or val in ("", None):
                        return None
                    try:
                        parts = str(val).split(":")
                        if len(parts) == 3:
                            h, m, s = parts
                            return int(h) * 60 + int(m) + int(s) / 60
                        elif len(parts) == 2:
                            h, m = parts
                            return int(h) * 60 + int(m)
                        else:
                            return float(val) / 60  # assume seconds
                    except Exception:
                        return None
                return par_df[col].apply(parse_hms)

            par_df["registered_mins"] = hms_to_minutes("registeredtimehms")
            par_df["pending_mins"] = hms_to_minutes("pendingtimehms")
            par_df["intransit_mins"] = hms_to_minutes("intransittimehms")

            # Ensure route / town / area columns exist
            for col in ["route", "town", "area"]:
                if col not in par_df.columns:
                    # Try case-insensitive match
                    match = next((c for c in par_df.columns if c.lower() == col), None)
                    if match:
                        par_df[col] = par_df[match]
                    else:
                        par_df[col] = "Unknown"

        return rev_df, exp_df, par_df

    except Exception as e:
        st.error(f"Failed to load data: {e}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()


rev_df, exp_df, par_df = load_data()

# ─── Sidebar Navigation ─────────────────────────────────────────────────────────
with st.sidebar:
    st.image("https://i.imgur.com/fFQvAHi.png", width=60) if False else None
    st.markdown("## 🚚 Kujawa Transport")
    st.markdown("---")
    section = st.radio(
        "Navigate to:",
        ["📦 Parcel Analytics", "💰 Financials"],
        label_visibility="collapsed",
    )
    st.markdown("---")
    st.markdown("### ⚙️ Global Filters")
    if not rev_df.empty and "date" in rev_df.columns:
        all_dates = pd.concat(
            [df["date"].dropna() for df in [rev_df, exp_df, par_df] if not df.empty and "date" in df.columns]
        )
        min_d = all_dates.min().date()
        max_d = all_dates.max().date()
        date_range = st.date_input("Date range", value=(min_d, max_d), min_value=min_d, max_value=max_d)
    else:
        date_range = None
    st.markdown("---")
    st.caption("Data refreshes every 5 minutes")
    if st.button("🔄 Refresh Data"):
        st.cache_data.clear()
        st.rerun()

# Apply global date filter
def filter_by_date(df, date_range):
    if df.empty or date_range is None or "date" not in df.columns:
        return df
    if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
        start, end = date_range
        mask = (df["date"].dt.date >= start) & (df["date"].dt.date <= end)
        return df[mask]
    return df

rev_filt = filter_by_date(rev_df, date_range)
exp_filt = filter_by_date(exp_df, date_range)
par_filt = filter_by_date(par_df, date_range)

CHART_THEME = "plotly_white"
BAR_COLOR = "#00b4d8"
BAR_COLOR2 = "#0077b6"

def styled_bar(df, x, y, title, color=BAR_COLOR, height=320):
    fig = px.bar(df, x=x, y=y, title=title, template=CHART_THEME, height=height, color_discrete_sequence=[color])
    fig.update_layout(
        title_font_size=14,
        margin=dict(t=40, b=20, l=10, r=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(248,249,250,1)",
        showlegend=False,
    )
    fig.update_traces(marker_line_width=0)
    return fig

def kpi_card(label, value, cls=""):
    return f"""
    <div class="metric-card {cls}">
        <h3>{label}</h3>
        <h1>{value}</h1>
    </div>"""

DOW_ORDER = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

# ════════════════════════════════════════════════════════════════════════════════
#  PARCEL ANALYTICS
# ════════════════════════════════════════════════════════════════════════════════
if section == "📦 Parcel Analytics":
    st.markdown('<div class="section-header">📦 Parcel Analytics</div>', unsafe_allow_html=True)

    if par_filt.empty:
        st.warning("No parcel data available.")
    else:
        # ── Hierarchical Filters ──
        st.markdown("#### 🔍 Drill-down Filters")
        fcol1, fcol2, fcol3 = st.columns(3)
        routes = sorted(par_filt["route"].dropna().unique().tolist())
        sel_route = fcol1.selectbox("Route", ["All"] + routes)

        p_town = par_filt if sel_route == "All" else par_filt[par_filt["route"] == sel_route]
        towns = sorted(p_town["town"].dropna().unique().tolist())
        sel_town = fcol2.selectbox("Town", ["All"] + towns)

        p_area = p_town if sel_town == "All" else p_town[p_town["town"] == sel_town]
        areas = sorted(p_area["area"].dropna().unique().tolist())
        sel_area = fcol3.selectbox("Area", ["All"] + areas)

        # Apply drill-down
        pdata = par_filt.copy()
        if sel_route != "All":
            pdata = pdata[pdata["route"] == sel_route]
        if sel_town != "All":
            pdata = pdata[pdata["town"] == sel_town]
        if sel_area != "All":
            pdata = pdata[pdata["area"] == sel_area]

        # ── KPI ──
        st.markdown("#### 📊 Summary")
        kc1, kc2, kc3, kc4 = st.columns(4)
        kc1.markdown(kpi_card("Total Parcels", f"{len(pdata):,}"), unsafe_allow_html=True)
        kc2.markdown(kpi_card("Routes", pdata["route"].nunique()), unsafe_allow_html=True)
        kc3.markdown(kpi_card("Towns", pdata["town"].nunique()), unsafe_allow_html=True)
        kc4.markdown(kpi_card("Areas", pdata["area"].nunique()), unsafe_allow_html=True)

        st.markdown("---")

        # ── Bar Charts ──
        bc1, bc2, bc3 = st.columns(3)
        with bc1:
            route_counts = pdata["route"].value_counts().reset_index()
            route_counts.columns = ["Route", "Parcels"]
            st.plotly_chart(styled_bar(route_counts, "Route", "Parcels", "Parcels per Route"), use_container_width=True)
        with bc2:
            town_counts = pdata["town"].value_counts().reset_index()
            town_counts.columns = ["Town", "Parcels"]
            st.plotly_chart(styled_bar(town_counts, "Town", "Parcels", "Parcels per Town", BAR_COLOR2), use_container_width=True)
        with bc3:
            area_counts = pdata["area"].value_counts().reset_index()
            area_counts.columns = ["Area", "Parcels"]
            st.plotly_chart(styled_bar(area_counts, "Area", "Parcels", "Parcels per Area", "#0096c7"), use_container_width=True)

        st.markdown("---")

        # ── Time Series ──
        st.markdown("#### 📈 Time Series")
        ts_col1, ts_col2 = st.columns([1, 4])
        ts_group = ts_col1.radio("Group by:", ["All Dates", "Per Month", "Day of Week"], key="ts_grp")

        if ts_group == "All Dates":
            ts_data = pdata.groupby(pdata["date"].dt.date).size().reset_index(name="Parcels")
            ts_data.columns = ["Date", "Parcels"]
            fig_ts = px.bar(ts_data, x="Date", y="Parcels", title="Parcels Over Time",
                            template=CHART_THEME, height=340, color_discrete_sequence=[BAR_COLOR])
        elif ts_group == "Per Month":
            ts_data = pdata.groupby("month").size().reset_index(name="Parcels")
            ts_data.columns = ["Month", "Parcels"]
            fig_ts = px.bar(ts_data, x="Month", y="Parcels", title="Parcels per Month",
                            template=CHART_THEME, height=340, color_discrete_sequence=[BAR_COLOR])
        else:
            ts_data = pdata.groupby("day_of_week").size().reindex(DOW_ORDER).reset_index()
            ts_data.columns = ["Day", "Parcels"]
            fig_ts = px.bar(ts_data, x="Day", y="Parcels", title="Parcels by Day of Week",
                            template=CHART_THEME, height=340, color_discrete_sequence=[BAR_COLOR])

        fig_ts.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(248,249,250,1)",
            margin=dict(t=40, b=20, l=10, r=10),
        )
        ts_col2.plotly_chart(fig_ts, use_container_width=True)

        st.markdown("---")

        # ── Efficiency ──
        st.markdown("#### ⚡ Efficiency – Average Processing Times")
        ef_col1, ef_col2 = st.columns([1, 4])
        ef_filter = ef_col1.radio("Group by:", ["Overall", "By Route", "By Day of Week"], key="ef_grp")

        time_cols = {
            "Registered Time": "registered_mins",
            "Pending Time": "pending_mins",
            "In-Transit Time": "intransit_mins",
        }
        avail_time_cols = {k: v for k, v in time_cols.items() if v in pdata.columns}

        if avail_time_cols:
            if ef_filter == "Overall":
                avg_times = {label: pdata[col].dropna().mean() for label, col in avail_time_cols.items()}
                eff_df = pd.DataFrame(list(avg_times.items()), columns=["Stage", "Avg Minutes"])
                fig_eff = px.bar(eff_df, x="Stage", y="Avg Minutes",
                                 title="Average Time per Stage (mins)",
                                 template=CHART_THEME, height=340,
                                 color_discrete_sequence=["#48cae4", "#0077b6", "#03045e"])
            elif ef_filter == "By Route":
                rows = []
                for label, col in avail_time_cols.items():
                    grp = pdata.groupby("route")[col].mean().reset_index()
                    grp.columns = ["Route", "Avg Minutes"]
                    grp["Stage"] = label
                    rows.append(grp)
                eff_df = pd.concat(rows, ignore_index=True)
                fig_eff = px.bar(eff_df, x="Route", y="Avg Minutes", color="Stage", barmode="group",
                                 title="Avg Time per Stage by Route (mins)",
                                 template=CHART_THEME, height=340,
                                 color_discrete_sequence=["#48cae4", "#0077b6", "#03045e"])
            else:
                rows = []
                for label, col in avail_time_cols.items():
                    grp = pdata.groupby("day_of_week")[col].mean().reindex(DOW_ORDER).reset_index()
                    grp.columns = ["Day", "Avg Minutes"]
                    grp["Stage"] = label
                    rows.append(grp)
                eff_df = pd.concat(rows, ignore_index=True)
                fig_eff = px.bar(eff_df, x="Day", y="Avg Minutes", color="Stage", barmode="group",
                                 title="Avg Time per Stage by Day of Week (mins)",
                                 template=CHART_THEME, height=340,
                                 color_discrete_sequence=["#48cae4", "#0077b6", "#03045e"])

            fig_eff.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(248,249,250,1)",
                margin=dict(t=40, b=20, l=10, r=10),
            )
            ef_col2.plotly_chart(fig_eff, use_container_width=True)
        else:
            ef_col2.info("Timing data (registeredtimehms, pendingtimehms, intransittimehms) not found in parcel records.")


# ════════════════════════════════════════════════════════════════════════════════
#  FINANCIALS
# ════════════════════════════════════════════════════════════════════════════════
else:
    st.markdown('<div class="section-header">💰 Financials</div>', unsafe_allow_html=True)

    # ── KPI Calculations ──
    total_revenue = rev_filt["amount"].sum() if not rev_filt.empty else 0

    if not exp_filt.empty:
        total_expense_col = "total_expense" if "total_expense" in exp_filt.columns else "amount"
        total_expenses = exp_filt[total_expense_col].sum()
    else:
        total_expenses = 0

    net_profit = total_revenue - total_expenses
    profit_margin = (net_profit / total_revenue * 100) if total_revenue > 0 else 0

    # ── KPI Cards ──
    kf1, kf2, kf3, kf4 = st.columns(4)
    kf1.markdown(kpi_card("Total Revenue", f"KES {total_revenue:,.0f}", "revenue-card"), unsafe_allow_html=True)
    kf2.markdown(kpi_card("Total Expenses", f"KES {total_expenses:,.0f}", "expense-card"), unsafe_allow_html=True)
    kf3.markdown(kpi_card("Net Profit", f"KES {net_profit:,.0f}", "profit-card"), unsafe_allow_html=True)
    kf4.markdown(kpi_card("Profit Margin", f"{profit_margin:.1f}%", "profit-card"), unsafe_allow_html=True)

    st.markdown("---")

    # ══════ EXPENSES SECTION ══════
    st.markdown("#### 🔴 Expenses")

    if exp_filt.empty:
        st.info("No expense data available for the selected period.")
    else:
        exp_col1, exp_col2 = st.columns([1, 4])
        exp_grp = exp_col1.radio("Group expenses by:", ["By Channel", "By Month", "By Day of Week"], key="exp_grp")
        exp_amt = "total_expense" if "total_expense" in exp_filt.columns else "amount"

        if exp_grp == "By Channel":
            grp = exp_filt.groupby("channel")[exp_amt].sum().reset_index()
            grp.columns = ["Channel", "Amount (KES)"]
            fig_exp = px.bar(grp, x="Channel", y="Amount (KES)", title="Expenses by Channel",
                             template=CHART_THEME, height=340, color_discrete_sequence=["#ef476f"])
        elif exp_grp == "By Month":
            grp = exp_filt.groupby("month")[exp_amt].sum().reset_index()
            grp.columns = ["Month", "Amount (KES)"]
            fig_exp = px.bar(grp, x="Month", y="Amount (KES)", title="Expenses by Month",
                             template=CHART_THEME, height=340, color_discrete_sequence=["#ef476f"])
        else:
            grp = exp_filt.groupby("day_of_week")[exp_amt].sum().reindex(DOW_ORDER).reset_index()
            grp.columns = ["Day", "Amount (KES)"]
            fig_exp = px.bar(grp, x="Day", y="Amount (KES)", title="Expenses by Day of Week",
                             template=CHART_THEME, height=340, color_discrete_sequence=["#ef476f"])

        fig_exp.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(248,249,250,1)",
            margin=dict(t=40, b=20, l=10, r=10),
        )
        exp_col2.plotly_chart(fig_exp, use_container_width=True)

        # Breakdown note
        if "transactionCost" in exp_filt.columns:
            tc_total = pd.to_numeric(exp_filt["transactionCost"], errors="coerce").fillna(0).sum()
            base_total = pd.to_numeric(exp_filt["amount"], errors="coerce").fillna(0).sum()
            exp_col1.markdown(f"""
            **Breakdown:**
            - Base: **KES {base_total:,.0f}**
            - Transaction costs: **KES {tc_total:,.0f}**
            - **Total: KES {total_expenses:,.0f}**
            """)

    st.markdown("---")

    # ══════ REVENUE SECTION ══════
    st.markdown("#### 🟢 Revenue")

    if rev_filt.empty:
        st.info("No revenue data available for the selected period.")
    else:
        rev_col1, rev_col2 = st.columns([1, 4])
        rev_grp = rev_col1.radio(
            "Group revenue by:",
            ["By Month", "By Day of Week", "By Route", "By Town"],
            key="rev_grp",
        )

        if rev_grp == "By Month":
            grp = rev_filt.groupby("month")["amount"].sum().reset_index()
            grp.columns = ["Month", "Revenue (KES)"]
            fig_rev = px.bar(grp, x="Month", y="Revenue (KES)", title="Revenue by Month",
                             template=CHART_THEME, height=340, color_discrete_sequence=["#06d6a0"])
        elif rev_grp == "By Day of Week":
            grp = rev_filt.groupby("day_of_week")["amount"].sum().reindex(DOW_ORDER).reset_index()
            grp.columns = ["Day", "Revenue (KES)"]
            fig_rev = px.bar(grp, x="Day", y="Revenue (KES)", title="Revenue by Day of Week",
                             template=CHART_THEME, height=340, color_discrete_sequence=["#06d6a0"])
        elif rev_grp == "By Route":
            # Revenue doesn't have route directly; try to get from parcels via description matching
            # Fall back to channel breakdown
            grp = rev_filt.groupby("channel")["amount"].sum().reset_index()
            grp.columns = ["Channel", "Revenue (KES)"]
            fig_rev = px.bar(grp, x="Channel", y="Revenue (KES)",
                             title="Revenue by Channel (Route data not directly available in revenue dataset)",
                             template=CHART_THEME, height=340, color_discrete_sequence=["#06d6a0"])
            rev_col1.caption("ℹ️ Revenue records don't include route; showing by channel instead.")
        else:  # By Town
            grp = rev_filt.groupby("channel")["amount"].sum().reset_index()
            grp.columns = ["Channel", "Revenue (KES)"]
            fig_rev = px.bar(grp, x="Channel", y="Revenue (KES)",
                             title="Revenue by Channel (Town data not directly available in revenue dataset)",
                             template=CHART_THEME, height=340, color_discrete_sequence=["#06d6a0"])
            rev_col1.caption("ℹ️ Revenue records don't include town; showing by channel instead.")

        fig_rev.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(248,249,250,1)",
            margin=dict(t=40, b=20, l=10, r=10),
        )
        rev_col2.plotly_chart(fig_rev, use_container_width=True)

        # Revenue source summary
        rev_col1.markdown("**Revenue by source:**")
        src_grp = rev_filt.groupby("channel")["amount"].sum().reset_index()
        src_grp.columns = ["Source", "KES"]
        src_grp["KES"] = src_grp["KES"].apply(lambda x: f"KES {x:,.0f}")
        rev_col1.dataframe(src_grp, hide_index=True, use_container_width=True)

    st.markdown("---")

    # ── Revenue vs Expense Trend ──
    st.markdown("#### 📊 Revenue vs Expenses – Monthly Trend")
    if not rev_filt.empty and not exp_filt.empty:
        rev_monthly = rev_filt.groupby("month")["amount"].sum().reset_index()
        rev_monthly.columns = ["Month", "Amount"]
        rev_monthly["Type"] = "Revenue"

        exp_amt_col = "total_expense" if "total_expense" in exp_filt.columns else "amount"
        exp_monthly = exp_filt.groupby("month")[exp_amt_col].sum().reset_index()
        exp_monthly.columns = ["Month", "Amount"]
        exp_monthly["Type"] = "Expenses"

        combined = pd.concat([rev_monthly, exp_monthly], ignore_index=True)
        fig_trend = px.bar(combined, x="Month", y="Amount", color="Type", barmode="group",
                           title="Monthly Revenue vs Expenses",
                           template=CHART_THEME, height=380,
                           color_discrete_map={"Revenue": "#06d6a0", "Expenses": "#ef476f"})
        fig_trend.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(248,249,250,1)",
            margin=dict(t=40, b=20, l=10, r=10),
        )
        st.plotly_chart(fig_trend, use_container_width=True)
    else:
        st.info("Insufficient data for trend comparison.")
