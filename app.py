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

def parse_date(series):
    """
    Normalize timestamps to UTC and strip timezone
    so all dates are comparable.
    """
    return pd.to_datetime(series, errors="coerce", utc=True).dt.tz_localize(None)

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
            rev_df["date"] = parse_date(
                rev_df.get("revenueDate", rev_df.get("date"))
            )
            rev_df["month"] = rev_df["date"].dt.to_period("M").astype(str)
            rev_df["day_of_week"] = rev_df["date"].dt.day_name()
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
                exp_df["date"] = parse_date(
                    exp_df[date_col]
                )
            else:
                exp_df["date"] = pd.NaT
            exp_df["month"] = exp_df["date"].dt.to_period("M").astype(str)
            exp_df["day_of_week"] = exp_df["date"].dt.day_name()
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
                par_df["date"] = parse_date(
                    par_df[date_col]
                )
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
                            return float(val) / 60
                    except Exception:
                        return None
                return par_df[col].apply(parse_hms)

            par_df["registered_mins"] = hms_to_minutes("registeredtimehms")
            par_df["pending_mins"] = hms_to_minutes("pendingtimehms")
            par_df["intransit_mins"] = hms_to_minutes("intransittimehms")

            for col in ["route", "town", "area"]:
                if col not in par_df.columns:
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
        date_series = [
            df["date"].dropna()
            for df in [rev_df, exp_df, par_df]
            if not df.empty and "date" in df.columns
        ]

        if date_series:
            all_dates = pd.concat(date_series, ignore_index=True)

            if not all_dates.empty:
                min_d = all_dates.min().date()
                max_d = all_dates.max().date()

                date_range = st.date_input(
                    "Date range",
                    value=(min_d, max_d),
                    min_value=min_d,
                    max_value=max_d
                )
            else:
                date_range = None
        else:
            date_range = None
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

# Rest of your original dashboard logic continues unchanged...
