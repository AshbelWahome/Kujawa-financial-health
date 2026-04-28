import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
import json

# ─────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="Finance Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────
# CUSTOM CSS
# ─────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Sora:wght@300;400;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Sora', sans-serif;
}

/* Sidebar */
[data-testid="stSidebar"] {
    background: #0f1117;
    border-right: 1px solid #1e2130;
}
[data-testid="stSidebar"] * {
    color: #e2e8f0 !important;
}
[data-testid="stSidebar"] .stTextInput input,
[data-testid="stSidebar"] .stTextInput input:focus {
    background: #1a1f2e !important;
    border: 1px solid #2d3550 !important;
    color: #e2e8f0 !important;
    border-radius: 8px;
}
[data-testid="stSidebar"] label {
    font-size: 11px !important;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: #64748b !important;
}

/* Main background */
.main .block-container {
    padding: 2rem 2.5rem;
    max-width: 1400px;
}

/* KPI cards */
.kpi-card {
    background: linear-gradient(135deg, #1a1f2e 0%, #161b28 100%);
    border: 1px solid #1e2130;
    border-radius: 16px;
    padding: 1.4rem 1.6rem;
    position: relative;
    overflow: hidden;
}
.kpi-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 2px;
    border-radius: 16px 16px 0 0;
}
.kpi-card.green::before  { background: #22c55e; }
.kpi-card.red::before    { background: #ef4444; }
.kpi-card.blue::before   { background: #3b82f6; }
.kpi-card.amber::before  { background: #f59e0b; }

.kpi-label {
    font-size: 10px;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: #64748b;
    margin-bottom: 6px;
    font-family: 'DM Mono', monospace;
}
.kpi-value {
    font-size: 28px;
    font-weight: 700;
    color: #f1f5f9;
    font-family: 'DM Mono', monospace;
    letter-spacing: -0.02em;
}
.kpi-delta {
    font-size: 12px;
    margin-top: 6px;
    font-family: 'DM Mono', monospace;
}
.kpi-delta.up   { color: #22c55e; }
.kpi-delta.down { color: #ef4444; }
.kpi-delta.flat { color: #64748b; }

/* Section headers */
.section-header {
    font-size: 11px;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: #475569;
    font-family: 'DM Mono', monospace;
    margin: 2rem 0 1rem;
    padding-bottom: 8px;
    border-bottom: 1px solid #1e2130;
}

/* Chart container */
.chart-card {
    background: #13161f;
    border: 1px solid #1e2130;
    border-radius: 16px;
    padding: 1.2rem;
}

/* Balance sheet table */
.bs-table {
    width: 100%;
    border-collapse: collapse;
    font-family: 'DM Mono', monospace;
    font-size: 13px;
}
.bs-table th {
    padding: 10px 16px;
    text-align: left;
    font-size: 10px;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: #475569;
    border-bottom: 1px solid #1e2130;
}
.bs-table td {
    padding: 9px 16px;
    color: #cbd5e1;
    border-bottom: 1px solid #0f1117;
}
.bs-table tr:hover td { background: #1a1f2e; }
.bs-table .total-row td {
    color: #f1f5f9;
    font-weight: 600;
    border-top: 1px solid #2d3550;
    border-bottom: 2px solid #2d3550;
}
.bs-table .section-row td {
    color: #94a3b8;
    font-size: 10px;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    padding-top: 16px;
    background: transparent;
}
.positive { color: #22c55e !important; }
.negative { color: #ef4444 !important; }

/* Status badge */
.status-badge {
    display: inline-block;
    padding: 3px 10px;
    border-radius: 20px;
    font-size: 10px;
    font-family: 'DM Mono', monospace;
    letter-spacing: 0.08em;
}
.badge-ok  { background: #14532d; color: #4ade80; }
.badge-err { background: #7f1d1d; color: #fca5a5; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# SIDEBAR — CONFIG
# ─────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚙️ API Configuration")
    st.markdown("---")

    api_url      = st.text_input("API Base URL",      value="https://your-api.com", placeholder="https://api.example.com")
    username     = st.text_input("Username",          placeholder="your_username")
    password     = st.text_input("Password",          type="password", placeholder="••••••••")
    revenue_path = st.text_input("Revenue endpoint",  value="/revenue",   placeholder="/revenue")
    expenses_path= st.text_input("Expenses endpoint", value="/expenses",  placeholder="/expenses")
    cashflow_path= st.text_input("Cash flow endpoint",value="/cashflow",  placeholder="/cashflow")
    other_path   = st.text_input("Other endpoint",    value="/other",     placeholder="/other (optional)")

    st.markdown("---")
    use_demo = st.toggle("Use demo data", value=True, help="Toggle off to connect your real API")

    if st.button("🔄  Refresh data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    st.markdown("---")
    st.markdown(
        '<p style="font-size:10px;color:#334155;font-family:DM Mono,monospace;">'
        'FINANCE DASHBOARD v1.0<br>Last refreshed: ' + datetime.now().strftime("%H:%M:%S") + '</p>',
        unsafe_allow_html=True,
    )

# ─────────────────────────────────────────────
# DATA LAYER
# ─────────────────────────────────────────────
def get_session():
    """Authenticate and return a requests.Session with credentials."""
    session = requests.Session()
    session.auth = (username, password)
    return session


@st.cache_data(ttl=300, show_spinner=False)
def fetch_endpoint(base_url: str, path: str, uname: str, pwd: str):
    """Fetch one endpoint. Returns (data_dict_or_list, error_str_or_None)."""
    url = base_url.rstrip("/") + path
    try:
        resp = requests.get(url, auth=(uname, pwd), timeout=15)
        resp.raise_for_status()
        return resp.json(), None
    except requests.exceptions.ConnectionError:
        return None, f"Cannot reach {url}"
    except requests.exceptions.HTTPError as e:
        return None, f"HTTP {e.response.status_code}: {e}"
    except Exception as e:
        return None, str(e)


def demo_data():
    """Return realistic mock financial data."""
    months = ["Jan","Feb","Mar","Apr","May","Jun",
              "Jul","Aug","Sep","Oct","Nov","Dec"]
    revenue  = [420,455,438,510,490,560,530,590,610,575,640,700]
    expenses = [310,325,318,370,360,395,385,410,430,415,450,480]
    net      = [r - e for r, e in zip(revenue, expenses)]
    cashflow = [80,95,78,112,100,130,125,145,160,140,170,195]

    return {
        "summary": {
            "total_revenue":  sum(revenue),
            "total_expenses": sum(expenses),
            "net_profit":     sum(net),
            "total_cashflow": sum(cashflow),
            "revenue_growth": 8.4,
            "expense_growth": 5.1,
            "profit_margin":  24.7,
            "cashflow_growth":12.3,
        },
        "monthly": pd.DataFrame({
            "month": months,
            "revenue": revenue,
            "expenses": expenses,
            "net_profit": net,
            "cash_flow": cashflow,
        }),
        "balance_sheet": {
            "assets": {
                "Cash & Equivalents":      420_000,
                "Accounts Receivable":     185_000,
                "Inventory":               95_000,
                "Prepaid Expenses":        28_000,
                "Property & Equipment":    640_000,
                "Intangible Assets":       210_000,
            },
            "liabilities": {
                "Accounts Payable":        112_000,
                "Short-term Debt":         80_000,
                "Accrued Expenses":        45_000,
                "Long-term Debt":          380_000,
                "Deferred Revenue":        60_000,
            },
            "equity": {
                "Common Stock":            500_000,
                "Retained Earnings":       312_000,
                "Additional Paid-in Cap.": 89_000,
            },
        },
        "cashflow_breakdown": pd.DataFrame({
            "category": ["Operating","Investing","Financing","Other"],
            "inflow":  [1_850_000, 320_000, 540_000, 80_000],
            "outflow": [1_200_000, 480_000, 390_000, 55_000],
        }),
    }


# ─────────────────────────────────────────────
# LOAD DATA
# ─────────────────────────────────────────────
errors = []

if use_demo:
    data = demo_data()
    conn_status = "demo"
else:
    # Fetch all endpoints
    rev_raw, e1  = fetch_endpoint(api_url, revenue_path,  username, password)
    exp_raw, e2  = fetch_endpoint(api_url, expenses_path, username, password)
    cf_raw,  e3  = fetch_endpoint(api_url, cashflow_path, username, password)
    for e in [e1, e2, e3]:
        if e: errors.append(e)

    if errors:
        conn_status = "error"
        # Fall back to demo so the dashboard still renders
        data = demo_data()
        st.warning("⚠️  Could not reach one or more endpoints — showing demo data. Check sidebar config.")
        for err in errors:
            st.error(err)
    else:
        conn_status = "live"
        # ── Adapt this section to match your actual API response shape ──
        # Example assumes each endpoint returns a list of
        # {"month": "Jan", "value": 12345} objects.
        try:
            rev_df  = pd.DataFrame(rev_raw)
            exp_df  = pd.DataFrame(exp_raw)
            cf_df   = pd.DataFrame(cf_raw)

            monthly = rev_df.rename(columns={"value": "revenue"})
            monthly["expenses"]   = exp_df["value"].values
            monthly["net_profit"] = monthly["revenue"] - monthly["expenses"]
            monthly["cash_flow"]  = cf_df["value"].values

            summary = {
                "total_revenue":  monthly["revenue"].sum(),
                "total_expenses": monthly["expenses"].sum(),
                "net_profit":     monthly["net_profit"].sum(),
                "total_cashflow": monthly["cash_flow"].sum(),
                "revenue_growth": 0.0,   # calculate from your data
                "expense_growth": 0.0,
                "profit_margin":  round(monthly["net_profit"].sum() / monthly["revenue"].sum() * 100, 1),
                "cashflow_growth":0.0,
            }
            data = {**demo_data(), "monthly": monthly, "summary": summary}
        except Exception as ex:
            st.error(f"Data parsing error: {ex}\nCheck the adapter section in app.py.")
            data = demo_data()

# ─────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────
col_title, col_badge = st.columns([6, 1])
with col_title:
    st.markdown("## 📊 Finance Dashboard")
with col_badge:
    badge_html = {
        "demo": '<span class="status-badge badge-ok">DEMO DATA</span>',
        "live": '<span class="status-badge badge-ok">● LIVE</span>',
        "error":'<span class="status-badge badge-err">● ERROR</span>',
    }[conn_status]
    st.markdown("<br>" + badge_html, unsafe_allow_html=True)

# ─────────────────────────────────────────────
# KPI CARDS
# ─────────────────────────────────────────────
s = data["summary"]

def fmt(v): return f"${v:,.0f}"
def delta_class(v): return "up" if v >= 0 else "down"
def delta_arrow(v): return "▲" if v >= 0 else "▼"

kpis = [
    ("TOTAL REVENUE",  fmt(s["total_revenue"]),  s["revenue_growth"],  "green"),
    ("TOTAL EXPENSES", fmt(s["total_expenses"]), s["expense_growth"],  "red"),
    ("NET PROFIT",     fmt(s["net_profit"]),
        round(s["net_profit"] / s["total_revenue"] * 100, 1), "blue"),
    ("CASH FLOW",      fmt(s["total_cashflow"]), s["cashflow_growth"], "amber"),
]

st.markdown('<p class="section-header">Key Performance Indicators</p>', unsafe_allow_html=True)
cols = st.columns(4)
for col, (label, value, growth, color) in zip(cols, kpis):
    with col:
        dc = delta_class(growth)
        st.markdown(f"""
        <div class="kpi-card {color}">
            <div class="kpi-label">{label}</div>
            <div class="kpi-value">{value}</div>
            <div class="kpi-delta {dc}">{delta_arrow(growth)} {abs(growth):.1f}% vs prior period</div>
        </div>""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# CHARTS — Revenue & Expenses
# ─────────────────────────────────────────────
st.markdown('<p class="section-header">Revenue & Expenses</p>', unsafe_allow_html=True)

chart_col1, chart_col2 = st.columns([3, 2])

with chart_col1:
    df = data["monthly"]
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=df["month"], y=df["revenue"],
        name="Revenue", marker_color="#3b82f6", marker_opacity=0.85,
    ))
    fig.add_trace(go.Bar(
        x=df["month"], y=df["expenses"],
        name="Expenses", marker_color="#ef4444", marker_opacity=0.75,
    ))
    fig.add_trace(go.Scatter(
        x=df["month"], y=df["net_profit"],
        name="Net Profit", mode="lines+markers",
        line=dict(color="#22c55e", width=2),
        marker=dict(size=6),
    ))
    fig.update_layout(
        barmode="group",
        plot_bgcolor="#13161f", paper_bgcolor="#13161f",
        font=dict(family="DM Mono, monospace", color="#94a3b8", size=11),
        legend=dict(orientation="h", y=1.1, x=0,
                    bgcolor="rgba(0,0,0,0)", font=dict(size=11)),
        margin=dict(l=0, r=0, t=30, b=0),
        xaxis=dict(gridcolor="#1e2130", tickfont=dict(size=10)),
        yaxis=dict(gridcolor="#1e2130", tickformat="$,.0f"),
        hovermode="x unified",
    )
    st.plotly_chart(fig, use_container_width=True)

with chart_col2:
    # Expense breakdown donut
    expense_cats = {
        "Salaries":    38,
        "Operations":  22,
        "Marketing":   16,
        "R&D":         14,
        "Other":       10,
    }
    fig2 = go.Figure(go.Pie(
        labels=list(expense_cats.keys()),
        values=list(expense_cats.values()),
        hole=0.6,
        marker=dict(colors=["#3b82f6","#8b5cf6","#f59e0b","#22c55e","#64748b"]),
        textfont=dict(family="DM Mono", size=11),
        hovertemplate="%{label}: %{percent}<extra></extra>",
    ))
    fig2.add_annotation(
        text="Expenses", x=0.5, y=0.55, showarrow=False,
        font=dict(size=12, color="#94a3b8", family="DM Mono"),
    )
    fig2.add_annotation(
        text="breakdown", x=0.5, y=0.42, showarrow=False,
        font=dict(size=11, color="#475569", family="DM Mono"),
    )
    fig2.update_layout(
        plot_bgcolor="#13161f", paper_bgcolor="#13161f",
        font=dict(family="DM Mono", color="#94a3b8"),
        legend=dict(orientation="v", x=1.0, y=0.5,
                    font=dict(size=10), bgcolor="rgba(0,0,0,0)"),
        margin=dict(l=0, r=60, t=10, b=0),
        showlegend=True,
    )
    st.plotly_chart(fig2, use_container_width=True)

# ─────────────────────────────────────────────
# CASH FLOW
# ─────────────────────────────────────────────
st.markdown('<p class="section-header">Cash Flow</p>', unsafe_allow_html=True)

cf_col1, cf_col2 = st.columns([2, 3])

with cf_col1:
    cf_df = data["cashflow_breakdown"]
    fig3 = go.Figure()
    fig3.add_trace(go.Bar(
        x=cf_df["category"], y=cf_df["inflow"],
        name="Inflow", marker_color="#22c55e", marker_opacity=0.85,
    ))
    fig3.add_trace(go.Bar(
        x=cf_df["category"], y=cf_df["outflow"],
        name="Outflow", marker_color="#ef4444", marker_opacity=0.75,
    ))
    fig3.update_layout(
        barmode="group",
        plot_bgcolor="#13161f", paper_bgcolor="#13161f",
        font=dict(family="DM Mono", color="#94a3b8", size=11),
        legend=dict(orientation="h", y=1.1, bgcolor="rgba(0,0,0,0)"),
        margin=dict(l=0, r=0, t=30, b=0),
        xaxis=dict(gridcolor="#1e2130"),
        yaxis=dict(gridcolor="#1e2130", tickformat="$,.0f"),
    )
    st.plotly_chart(fig3, use_container_width=True)

with cf_col2:
    df = data["monthly"]
    fig4 = go.Figure()
    fig4.add_trace(go.Scatter(
        x=df["month"], y=df["cash_flow"].cumsum(),
        fill="tozeroy", name="Cumulative cash flow",
        line=dict(color="#f59e0b", width=2),
        fillcolor="rgba(245,158,11,0.12)",
    ))
    fig4.add_trace(go.Scatter(
        x=df["month"], y=df["cash_flow"],
        name="Monthly cash flow", mode="lines+markers",
        line=dict(color="#3b82f6", width=1.5, dash="dot"),
        marker=dict(size=5),
    ))
    fig4.update_layout(
        plot_bgcolor="#13161f", paper_bgcolor="#13161f",
        font=dict(family="DM Mono", color="#94a3b8", size=11),
        legend=dict(orientation="h", y=1.1, bgcolor="rgba(0,0,0,0)"),
        margin=dict(l=0, r=0, t=30, b=0),
        xaxis=dict(gridcolor="#1e2130"),
        yaxis=dict(gridcolor="#1e2130", tickformat="$,.0f"),
        hovermode="x unified",
    )
    st.plotly_chart(fig4, use_container_width=True)

# ─────────────────────────────────────────────
# BALANCE SHEET
# ─────────────────────────────────────────────
st.markdown('<p class="section-header">Balance Sheet</p>', unsafe_allow_html=True)

bs = data["balance_sheet"]
bs_col1, bs_col2 = st.columns(2)

def bs_section_html(title, items, total_label="Total"):
    rows = f'<tr class="section-row"><td colspan="2">{title}</td></tr>'
    total = 0
    for name, val in items.items():
        sign = "positive" if val >= 0 else "negative"
        rows += f'<tr><td>{name}</td><td class="{sign}" style="text-align:right">${val:,.0f}</td></tr>'
        total += val
    rows += f'''<tr class="total-row">
        <td>{total_label}</td>
        <td style="text-align:right">${total:,.0f}</td>
    </tr>'''
    return rows, total

assets_html,      assets_total      = bs_section_html("ASSETS",      bs["assets"],      "Total Assets")
liabilities_html, liabilities_total = bs_section_html("LIABILITIES", bs["liabilities"], "Total Liabilities")
equity_html,      equity_total      = bs_section_html("EQUITY",      bs["equity"],      "Total Equity")

with bs_col1:
    st.markdown(f"""
    <table class="bs-table">
        <thead><tr><th>Item</th><th style="text-align:right">Amount</th></tr></thead>
        <tbody>
            {assets_html}
        </tbody>
    </table>""", unsafe_allow_html=True)

with bs_col2:
    balanced = liabilities_total + equity_total
    check_color = "positive" if abs(balanced - assets_total) < 1 else "negative"
    check_text  = "✓ Balanced" if abs(balanced - assets_total) < 1 else "✗ Imbalanced"
    st.markdown(f"""
    <table class="bs-table">
        <thead><tr><th>Item</th><th style="text-align:right">Amount</th></tr></thead>
        <tbody>
            {liabilities_html}
            {equity_html}
            <tr class="total-row">
                <td>Liabilities + Equity</td>
                <td class="{check_color}" style="text-align:right">
                    ${balanced:,.0f} &nbsp; <span style="font-size:11px">{check_text}</span>
                </td>
            </tr>
        </tbody>
    </table>""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# PROFIT MARGIN TREND
# ─────────────────────────────────────────────
st.markdown('<p class="section-header">Profit Margin Trend</p>', unsafe_allow_html=True)

df = data["monthly"]
df["margin"] = (df["net_profit"] / df["revenue"] * 100).round(1)

fig5 = go.Figure()
fig5.add_trace(go.Scatter(
    x=df["month"], y=df["margin"],
    fill="tozeroy",
    line=dict(color="#8b5cf6", width=2.5),
    fillcolor="rgba(139,92,246,0.10)",
    marker=dict(size=7, color="#8b5cf6"),
    text=[f"{v}%" for v in df["margin"]],
    textposition="top center",
    textfont=dict(family="DM Mono", size=10, color="#8b5cf6"),
    mode="lines+markers+text",
    hovertemplate="<b>%{x}</b><br>Margin: %{y:.1f}%<extra></extra>",
))
fig5.add_hline(
    y=df["margin"].mean(), line_dash="dot",
    line_color="#475569", line_width=1,
    annotation_text=f"avg {df['margin'].mean():.1f}%",
    annotation_font=dict(family="DM Mono", size=10, color="#475569"),
)
fig5.update_layout(
    plot_bgcolor="#13161f", paper_bgcolor="#13161f",
    font=dict(family="DM Mono", color="#94a3b8", size=11),
    margin=dict(l=0, r=0, t=10, b=0),
    xaxis=dict(gridcolor="#1e2130"),
    yaxis=dict(gridcolor="#1e2130", ticksuffix="%"),
    showlegend=False,
)
st.plotly_chart(fig5, use_container_width=True)

# ─────────────────────────────────────────────
# RAW DATA EXPANDER
# ─────────────────────────────────────────────
with st.expander("🗂  Raw monthly data"):
    st.dataframe(
        data["monthly"].style.format({
            "revenue":    "${:,.0f}",
            "expenses":   "${:,.0f}",
            "net_profit": "${:,.0f}",
            "cash_flow":  "${:,.0f}",
        }),
        use_container_width=True,
    )
