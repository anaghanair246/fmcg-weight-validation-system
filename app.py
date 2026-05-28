"""
app.py — Weight Validation System (v2)
Frozen Food Division · Production Line Monitor

Features:
  • Tab 1: Live Scan — QR scanning, product lookup, weight validation
  • Tab 2: History / Reports — collective + per-product history, analytics, export
  • SQLite persistence (scan_history.db)
  • Plotly charts: donut
"""

import streamlit as st
import pandas as pd
import sqlite3
import os
import subprocess
import sys
from datetime import datetime
import plotly.graph_objects as go
import io

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Weight Validation System",
    page_icon="",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── CSS ────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

  html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
    background-color: #f4f6f9;
    color: #1a2035;
  }
  .stApp { background: #f4f6f9; }
  #MainMenu, footer, header { visibility: hidden; }
  .block-container { padding: 1.5rem 2rem 4rem; max-width: 1500px; }

  /* ── Header ── */
  .app-header {
    background: #ffffff;
    border: 1px solid #dde3ee;
    border-radius: 10px;
    padding: 1.3rem 2rem;
    margin-bottom: 1.5rem;
    display: flex;
    align-items: center;
    gap: 1rem;
    box-shadow: 0 1px 6px rgba(0,0,0,0.06);
  }
  .app-header h1 {
    font-family: 'Inter', sans-serif;
    font-size: 1.45rem;
    font-weight: 700;
    letter-spacing: 0.02em;
    color: #1a2035;
    margin: 0;
  }
  .app-header .subtitle {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.7rem;
    color: #2563eb;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    margin-top: 3px;
  }
  .live-dot {
    width: 9px; height: 9px;
    background: #16a34a;
    border-radius: 50%;
    animation: pulse 1.6s infinite;
    flex-shrink: 0;
  }
  @keyframes pulse {
    0%, 100% { opacity: 1; box-shadow: 0 0 0 0 rgba(22,163,74,0.4); }
    50%       { opacity: 0.7; box-shadow: 0 0 0 5px rgba(22,163,74,0); }
  }

  /* ── Metric cards ── */
  .metric-row { display: flex; gap: 1rem; margin-bottom: 1.5rem; flex-wrap: wrap; }
  .metric-card {
    flex: 1; min-width: 130px;
    background: #ffffff;
    border: 1px solid #dde3ee;
    border-radius: 10px;
    padding: 1.1rem 1.4rem;
    position: relative;
    overflow: hidden;
    box-shadow: 0 1px 4px rgba(0,0,0,0.05);
  }
  .metric-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 3px;
  }
  .metric-card.total::before  { background: #2563eb; }
  .metric-card.accept::before { background: #16a34a; }
  .metric-card.reject::before { background: #dc2626; }
  .metric-card.rate::before   { background: #d97706; }
  .metric-label {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.63rem;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: #7a8aaa;
    margin-bottom: 0.4rem;
  }
  .metric-value {
    font-family: 'Inter', sans-serif;
    font-size: 2.1rem;
    font-weight: 700;
    color: #1a2035;
    line-height: 1;
  }
  .metric-card.reject .metric-value { color: #dc2626; }
  .metric-card.accept .metric-value { color: #16a34a; }
  .metric-card.rate   .metric-value { color: #d97706; }

  /* ── Section headings ── */
  .section-title {
    font-family: 'Inter', sans-serif;
    font-size: 0.78rem;
    font-weight: 600;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: #2563eb;
    border-left: 3px solid #2563eb;
    padding-left: 0.7rem;
    margin: 1.4rem 0 0.9rem;
  }

  /* ── Panels ── */
  .panel {
    background: #ffffff;
    border: 1px solid #dde3ee;
    border-radius: 10px;
    padding: 1.3rem 1.5rem;
    margin-bottom: 1rem;
    box-shadow: 0 1px 4px rgba(0,0,0,0.04);
  }

  /* ── Result badge ── */
  .badge {
    display: inline-block;
    font-family: 'Inter', sans-serif;
    font-size: 1.5rem;
    font-weight: 700;
    letter-spacing: 0.1em;
    padding: 0.3rem 1.4rem;
    border-radius: 6px;
    margin-top: 0.5rem;
  }
  .badge.accept { background: #f0fdf4; color: #16a34a; border: 1px solid #bbf7d0; }
  .badge.reject { background: #fef2f2; color: #dc2626; border: 1px solid #fecaca; }

  /* ── Detail rows inside panel ── */
  .detail-row {
    display: flex; justify-content: space-between; align-items: baseline;
    border-bottom: 1px solid #eef1f8; padding: 0.4rem 0;
  }
  .detail-key { font-size: 0.73rem; color: #7a8aaa; text-transform: uppercase; letter-spacing: 0.08em; }
  .detail-val { font-family: 'JetBrains Mono', monospace; font-size: 0.86rem; color: #1a2035; }

  /* ── QR display ── */
  .qr-display {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.98rem;
    background: #f0f4ff;
    border: 1px solid #c7d7f8;
    border-radius: 6px;
    padding: 0.7rem 1rem;
    letter-spacing: 0.18em;
    color: #2563eb;
    margin: 0.4rem 0;
  }

  /* ── Warning diff ── */
  .diff-warning {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.83rem;
    background: #fef2f2;
    border: 1px solid #fecaca;
    border-radius: 6px;
    padding: 0.5rem 0.9rem;
    color: #dc2626;
    margin-top: 0.5rem;
  }

  /* ── Timestamp ── */
  .timestamp-badge {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.73rem;
    color: #7a8aaa;
    background: #f4f6f9;
    border: 1px solid #dde3ee;
    border-radius: 4px;
    padding: 0.25rem 0.7rem;
    display: inline-block;
    margin-bottom: 0.5rem;
  }

  /* ── Stat card row for product summary ── */
  .stat-row { display: flex; gap: 0.8rem; margin-bottom: 1rem; flex-wrap: wrap; }
  .stat-card {
    flex: 1; min-width: 110px;
    background: #ffffff;
    border: 1px solid #dde3ee;
    border-radius: 8px;
    padding: 0.9rem 1.1rem;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04);
  }
  .stat-label { font-family: 'JetBrains Mono', monospace; font-size: 0.6rem; color: #7a8aaa; letter-spacing: 0.12em; text-transform: uppercase; margin-bottom: 0.3rem; }
  .stat-value { font-family: 'Inter', sans-serif; font-size: 1.65rem; font-weight: 700; color: #1a2035; }
  .stat-value.green { color: #16a34a; }
  .stat-value.red   { color: #dc2626; }
  .stat-value.amber { color: #d97706; }

  /* ── Tab overrides ── */
  .stTabs [data-baseweb="tab-list"] {
    background: #ffffff;
    border-radius: 8px;
    padding: 0.3rem;
    border: 1px solid #dde3ee;
    gap: 0.3rem;
    margin-bottom: 1.2rem;
    box-shadow: 0 1px 4px rgba(0,0,0,0.04);
  }
  .stTabs [data-baseweb="tab"] {
    background: transparent !important;
    color: #7a8aaa !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 0.85rem !important;
    font-weight: 600 !important;
    letter-spacing: 0.06em !important;
    border-radius: 6px !important;
    padding: 0.5rem 1.5rem !important;
    border: none !important;
  }
  .stTabs [aria-selected="true"] {
    background: #eff6ff !important;
    color: #1d4ed8 !important;
    border: 1px solid #bfdbfe !important;
  }
  .stTabs [data-baseweb="tab-border"] { display: none !important; }

  /* ── Inputs ── */
  .stTextInput > div > div > input {
    background: #ffffff !important;
    border: 1px solid #cbd5e1 !important;
    border-radius: 6px !important;
    color: #1a2035 !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.93rem !important;
    letter-spacing: 0.06em !important;
    padding: 0.6rem 1rem !important;
  }
  .stTextInput > div > div > input:focus {
    border-color: #2563eb !important;
    box-shadow: 0 0 0 2px rgba(37,99,235,0.15) !important;
  }
  .stNumberInput > div > div > input {
    background: #ffffff !important;
    border: 1px solid #cbd5e1 !important;
    border-radius: 6px !important;
    color: #1a2035 !important;
    font-family: 'JetBrains Mono', monospace !important;
  }
  .stSelectbox > div > div {
    background: #ffffff !important;
    border: 1px solid #cbd5e1 !important;
    border-radius: 6px !important;
    color: #1a2035 !important;
  }

  /* ── Buttons ── */
  .stButton > button {
    background: #ffffff !important;
    border: 1px solid #cbd5e1 !important;
    color: #374151 !important;
    border-radius: 6px !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 0.86rem !important;
    font-weight: 600 !important;
    letter-spacing: 0.04em !important;
    padding: 0.45rem 1.2rem !important;
    transition: all 0.15s !important;
  }
  .stButton > button:hover {
    background: #f8fafc !important;
    border-color: #2563eb !important;
    color: #1d4ed8 !important;
  }
  .stButton > button[kind="primary"] {
    background: #2563eb !important;
    border-color: #1d4ed8 !important;
    color: #ffffff !important;
  }
  .stButton > button[kind="primary"]:hover {
    background: #1d4ed8 !important;
    color: #ffffff !important;
  }

  /* ── DataFrames ── */
  div[data-testid="stDataFrame"] {
    border: 1px solid #dde3ee !important;
    border-radius: 8px !important;
    overflow: hidden;
    box-shadow: 0 1px 4px rgba(0,0,0,0.04);
  }

  /* ── Alerts ── */
  div[data-testid="stAlert"] {
    border-radius: 8px !important;
    border-left: 4px solid !important;
  }
  hr { border-color: #dde3ee; margin: 1.2rem 0; }
</style>
""", unsafe_allow_html=True)

# ── Constants ──────────────────────────────────────────────────────────────────
PACKAGE_WEIGHT = 0.5   # KG  (box + packaging)
TOLERANCE      = 0.1   # KG  (±)
DB_FILE        = "scan_history.db"
EXCEL_FILE     = "Meat Items.xlsx"

# ── SQLite helpers ─────────────────────────────────────────────────────────────
def get_conn():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS scans (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp        TEXT    NOT NULL,
                qr_code          TEXT    NOT NULL,
                product          TEXT    NOT NULL,
                expected_weight  REAL    NOT NULL,
                measured_weight  REAL    NOT NULL,
                actual_net       REAL    NOT NULL,
                tolerance        REAL    NOT NULL,
                status           TEXT    NOT NULL
            )
        """)
        conn.commit()

def insert_scan(timestamp, qr_code, product, expected_weight,
                measured_weight, actual_net, tolerance, status):
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO scans
              (timestamp, qr_code, product, expected_weight,
               measured_weight, actual_net, tolerance, status)
            VALUES (?,?,?,?,?,?,?,?)
        """, (timestamp, qr_code, product, expected_weight,
              measured_weight, actual_net, tolerance, status))
        conn.commit()

def load_all_scans() -> pd.DataFrame:
    with get_conn() as conn:
        df = pd.read_sql_query(
            "SELECT * FROM scans ORDER BY id DESC", conn
        )
    return df

def reset_db():
    with get_conn() as conn:
        conn.execute("DELETE FROM scans")
        conn.commit()

# ── Product data ───────────────────────────────────────────────────────────────
@st.cache_data
def load_product_db():
    df = pd.read_excel(EXCEL_FILE, dtype={"SEGMENT1": str})
    df["SEGMENT1"] = df["SEGMENT1"].str.strip().str.zfill(12)
    return df

def lookup_product(qr: str, product_df: pd.DataFrame):
    match = product_df[product_df["SEGMENT1"] == qr]
    if match.empty:
        match = product_df[product_df["SEGMENT1"].str[-9:] == qr[-9:]]
    if match.empty:
        return None
    return match.iloc[0]

# ── Plotly helpers ─────────────────────────────────────────────────────────────
CHART_BG   = "#ffffff"
CHART_PLOT = "#f8fafc"
GRID_COLOR = "#e5eaf4"
FONT_SANS  = "Inter"
TEXT_COLOR = "#1a2035"
DIM_COLOR  = "#7a8aaa"

def donut_chart(accept: int, reject: int, title: str = "Accept / Reject Split", height=240):
    labels = ["ACCEPT", "REJECT"]
    values = [accept, reject]
    colors = ["#16a34a", "#dc2626"]
    fig = go.Figure(go.Pie(
        labels=labels, values=values, hole=0.55,
        marker=dict(colors=colors, line=dict(color="#f4f6f9", width=3)),
        textinfo="percent",
        textfont=dict(size=13, color="white", family=FONT_SANS),
        hovertemplate="%{label}: %{value}<extra></extra>",
    ))
    fig.update_layout(
        paper_bgcolor=CHART_BG, plot_bgcolor=CHART_BG,
        margin=dict(t=42, b=10, l=8, r=8), height=height,
        title=dict(text=title, font=dict(color=TEXT_COLOR, size=11, family=FONT_SANS),
                   x=0.5, xanchor="center"),
        legend=dict(font=dict(color=TEXT_COLOR, size=10, family=FONT_SANS),
                    bgcolor="rgba(0,0,0,0)", orientation="h",
                    x=0.5, xanchor="center", y=-0.05),
    )
    return fig

# ── Export helpers ─────────────────────────────────────────────────────────────
def df_to_csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8")

def df_to_excel_bytes(df: pd.DataFrame) -> bytes:
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Scan History")
    return buf.getvalue()

# ── Initialise ─────────────────────────────────────────────────────────────────
init_db()
product_df = load_product_db()

# ── Session state ──────────────────────────────────────────────────────────────
for k, v in {
    "last_submitted_key": "",
    "weight_key":         0,
    "qr_key":             0,
    "webcam_result":      "",
}.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ── Header ─────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="app-header">
  <div class="live-dot"></div>
  <div>
    <h1>WEIGHT VALIDATION SYSTEM</h1>
    <div class="subtitle">Frozen Food Division &nbsp;·&nbsp; Production Line Monitor &nbsp;·&nbsp; v2</div>
  </div>
</div>
""", unsafe_allow_html=True)

# ── Global metrics row ─────────────────────────────────────────────────────────
history_all = load_all_scans()
total    = len(history_all)
accepted = int((history_all["status"] == "ACCEPT").sum()) if total else 0
rejected = int((history_all["status"] == "REJECT").sum()) if total else 0
rate     = round((rejected / total) * 100, 1) if total else 0.0

st.markdown(f"""
<div class="metric-row">
  <div class="metric-card total">
    <div class="metric-label">Total Scans</div>
    <div class="metric-value">{total}</div>
  </div>
  <div class="metric-card accept">
    <div class="metric-label">Accepted</div>
    <div class="metric-value">{accepted}</div>
  </div>
  <div class="metric-card reject">
    <div class="metric-label">Rejected</div>
    <div class="metric-value">{rejected}</div>
  </div>
  <div class="metric-card rate">
    <div class="metric-label">Reject Rate</div>
    <div class="metric-value">{rate}%</div>
  </div>
</div>
""", unsafe_allow_html=True)

# ── Tabs ───────────────────────────────────────────────────────────────────────
tab_scan, tab_history = st.tabs(["Live Scan", "History / Reports"])

# ══════════════════════════════════════════════════════════════════════════════
#  TAB 1 — LIVE SCAN
# ══════════════════════════════════════════════════════════════════════════════
with tab_scan:
    left, right = st.columns([1, 1], gap="large")

    # ── LEFT: scan + weight input ──────────────────────────────────────────────
    with left:
        st.markdown('<div class="section-title">QR Code Input</div>', unsafe_allow_html=True)

        _k = f"qr_{st.session_state.qr_key}"
        if _k not in st.session_state:
            st.session_state[_k] = st.session_state.get("webcam_result", "")

        qr_input = st.text_input(
            "Scan or type QR code",
            placeholder="e.g. 004035039064",
            key=_k,
            label_visibility="collapsed",
        )

        if st.button("Open Webcam Scanner"):
            scanner_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scanner.py")
            result = subprocess.run(
                [sys.executable, scanner_path],
                capture_output=True, text=True,
            )
            scanned = result.stdout.strip()
            if scanned:
                st.session_state.webcam_result = scanned.zfill(12)
                st.session_state.qr_key       += 1
                st.session_state.weight_key   += 1
                st.rerun()
            else:
                st.error("Could not open webcam or no QR code detected. "
                         "Run  fuser -k /dev/video0 /dev/video1  in a terminal if this persists.")

        st.markdown("""
        <div style="font-size:0.72rem; color:#7a8aaa; margin-top:0.3rem; margin-bottom:0.6rem;
                    font-family:'JetBrains Mono',monospace; letter-spacing:0.04em;">
          Use webcam button above, or point a barcode scanner at the box to type directly
        </div>
        """, unsafe_allow_html=True)

        st.markdown('<div class="section-title">Measured Weight (KG)</div>', unsafe_allow_html=True)

        measured_weight = st.number_input(
            "Weight on scale",
            min_value=0.0,
            step=0.1,
            format="%.2f",
            key=f"weight_{st.session_state.weight_key}",
            label_visibility="collapsed",
        )
        st.markdown("""
        <div style="font-size:0.72rem; color:#7a8aaa; margin-top:0.3rem;
                    font-family:'JetBrains Mono',monospace;">
          Gross weight — includes packaging (box + plastic wrap)
        </div>
        """, unsafe_allow_html=True)

    # ── RIGHT: product info + result ───────────────────────────────────────────
    with right:
        qr = qr_input.strip().zfill(12) if qr_input.strip() else ""

        if qr:
            st.markdown(f"""
            <div class="qr-display">
              QR &nbsp;·&nbsp; {qr[:4]}·{qr[4:9]}·{qr[9:]}
            </div>
            """, unsafe_allow_html=True)

            row = lookup_product(qr, product_df)
            if row is not None:
                product_name = row["DESCRIPTION"]
                net_weight   = float(row["INTER_CONV"])

                actual_net   = measured_weight - PACKAGE_WEIGHT
                lower        = net_weight - TOLERANCE
                upper        = net_weight + TOLERANCE
                status       = "ACCEPT" if lower <= actual_net <= upper else "REJECT"
                ts           = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                # ── Timestamp ──────────────────────────────────────────────────
                st.markdown(f'<div class="timestamp-badge">{ts}</div>',
                            unsafe_allow_html=True)

                # ── Result badge ───────────────────────────────────────────────
                st.markdown(f'<div class="badge {status.lower()}">{status}</div>',
                            unsafe_allow_html=True)

                if status == "REJECT":
                    if actual_net < lower:
                        st.markdown(
                            f'<div class="diff-warning">Underweight by {lower - actual_net:.3f} KG</div>',
                            unsafe_allow_html=True)
                    else:
                        st.markdown(
                            f'<div class="diff-warning">Overweight by {actual_net - upper:.3f} KG</div>',
                            unsafe_allow_html=True)

                # ── Product details ────────────────────────────────────────────
                st.markdown('<div class="section-title">Product Details</div>',
                            unsafe_allow_html=True)
                st.markdown(f"""
                <div class="panel">
                  <div class="detail-row">
                    <span class="detail-key">Product</span>
                    <span class="detail-val" style="font-size:0.8rem; color:#1a2035">{product_name}</span>
                  </div>
                  <div class="detail-row">
                    <span class="detail-key">QR / Item Code</span>
                    <span class="detail-val">{qr}</span>
                  </div>
                  <div class="detail-row">
                    <span class="detail-key">Expected Net Weight</span>
                    <span class="detail-val">{net_weight:.2f} KG</span>
                  </div>
                  <div class="detail-row">
                    <span class="detail-key">Measured (Gross)</span>
                    <span class="detail-val">{measured_weight:.2f} KG</span>
                  </div>
                  <div class="detail-row">
                    <span class="detail-key">Packaging Deduction</span>
                    <span class="detail-val">- {PACKAGE_WEIGHT:.2f} KG</span>
                  </div>
                  <div class="detail-row">
                    <span class="detail-key">Actual Net Weight</span>
                    <span class="detail-val" style="color:#1a2035; font-weight:600">{actual_net:.2f} KG</span>
                  </div>
                  <div class="detail-row">
                    <span class="detail-key">Acceptable Range</span>
                    <span class="detail-val">{lower:.2f} – {upper:.2f} KG</span>
                  </div>
                  <div class="detail-row">
                    <span class="detail-key">Tolerance</span>
                    <span class="detail-val">+/- {TOLERANCE:.2f} KG</span>
                  </div>
                </div>
                """, unsafe_allow_html=True)

                # ── Save to DB (deduplicated by qr+weight) ─────────────────────
                if measured_weight > 0:
                    scan_key = f"{qr}_{measured_weight}"
                    if scan_key != st.session_state.last_submitted_key:
                        st.session_state.last_submitted_key = scan_key
                        insert_scan(
                            ts, qr, product_name, net_weight,
                            measured_weight, actual_net, TOLERANCE, status,
                        )

                # ── Clear button ───────────────────────────────────────────────
                st.markdown("<br>", unsafe_allow_html=True)

                def clear_scan():
                    st.session_state.qr_key            += 1
                    st.session_state.webcam_result      = ""
                    st.session_state.last_submitted_key = ""
                    st.session_state.weight_key        += 1

                st.button("Clear — Scan Next Product", type="primary", on_click=clear_scan)

            else:
                st.warning(f"Product not found in database — QR: `{qr}`")
                st.caption("Tip: Ensure the QR code is fully scanned (12 digits).")

        else:
            st.markdown("""
            <div class="panel" style="text-align:center; padding:3rem; color:#7a8aaa;">
              <div style="font-size:1.4rem; font-weight:700; margin-bottom:0.6rem; color:#cbd5e1;">
                WEIGHT VALIDATION
              </div>
              <div style="font-family:'JetBrains Mono',monospace; font-size:0.8rem; letter-spacing:0.1em;">
                Awaiting QR code scan
              </div>
              <div style="font-size:0.75rem; margin-top:0.4rem;">
                Use the webcam scanner or type the 12-digit code
              </div>
            </div>
            """, unsafe_allow_html=True)

    # ── Reset button (below columns) ───────────────────────────────────────────
    st.markdown("<hr>", unsafe_allow_html=True)
    if st.button("Reset All History"):
        reset_db()
        st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
#  TAB 2 — HISTORY / REPORTS
# ══════════════════════════════════════════════════════════════════════════════
with tab_history:

    # Reload fresh from DB
    history = load_all_scans()

    if history.empty:
        st.markdown("""
        <div class="panel" style="text-align:center; padding:3rem; color:#7a8aaa;">
          <div style="font-size:1.4rem; font-weight:700; margin-bottom:0.5rem; color:#cbd5e1;">
            NO DATA
          </div>
          <div style="font-family:'JetBrains Mono',monospace; font-size:0.8rem; letter-spacing:0.1em;">
            No scan data yet
          </div>
          <div style="font-size:0.75rem; margin-top:0.3rem;">
            Go to Live Scan and scan your first QR code to begin
          </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        # ── A. COLLECTIVE HISTORY ──────────────────────────────────────────────
        st.markdown('<div class="section-title">Collective Scan History</div>',
                    unsafe_allow_html=True)

        # Search / filter row
        fcol1, fcol2, fcol3 = st.columns([2, 2, 2])
        with fcol1:
            search_qr = st.text_input("Filter by QR / Product", placeholder="Type to search…",
                                      label_visibility="collapsed", key="search_qr")
        with fcol2:
            filter_status = st.selectbox("Status filter", ["All", "ACCEPT", "REJECT"],
                                         label_visibility="collapsed", key="filter_status")
        with fcol3:
            sort_order = st.selectbox("Sort", ["Newest first", "Oldest first"],
                                      label_visibility="collapsed", key="sort_order")

        filtered = history.copy()
        if search_qr.strip():
            q = search_qr.strip().lower()
            filtered = filtered[
                filtered["qr_code"].str.lower().str.contains(q) |
                filtered["product"].str.lower().str.contains(q)
            ]
        if filter_status != "All":
            filtered = filtered[filtered["status"] == filter_status]
        if sort_order == "Oldest first":
            filtered = filtered.iloc[::-1].reset_index(drop=True)

        display_cols = {
            "timestamp":       "Timestamp",
            "qr_code":         "QR Code",
            "product":         "Product",
            "expected_weight": "Expected (KG)",
            "measured_weight": "Measured (KG)",
            "actual_net":      "Net (KG)",
            "tolerance":       "Tolerance",
            "status":          "Status",
        }
        display_df = filtered[list(display_cols.keys())].rename(columns=display_cols)

        def style_status_col(val):
            if val == "ACCEPT": return "color: #16a34a; font-weight: 600;"
            if val == "REJECT": return "color: #dc2626; font-weight: 600;"
            return ""

        styled_df = display_df.style.map(style_status_col, subset=["Status"])
        st.dataframe(styled_df, use_container_width=True, hide_index=True)

        # Download buttons
        dl_col1, dl_col2, _ = st.columns([1, 1, 3])
        with dl_col1:
            st.download_button(
                "Download CSV",
                data=df_to_csv_bytes(display_df),
                file_name=f"scan_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
            )
        with dl_col2:
            st.download_button(
                "Download Excel",
                data=df_to_excel_bytes(display_df),
                file_name=f"scan_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

        st.markdown("<hr>", unsafe_allow_html=True)

        # ── B. INDIVIDUAL PRODUCT HISTORY ──────────────────────────────────────
        st.markdown('<div class="section-title">Individual Product History</div>',
                    unsafe_allow_html=True)

        # ── 2-digit search bar ─────────────────────────────────────────────────
        st.markdown("""
        <style>
          /* Critical-identifier badge: large, vivid blue pill */
          .id2-badge {
            display: inline-block;
            font-family: 'JetBrains Mono', monospace;
            font-size: 1.05rem;
            font-weight: 700;
            letter-spacing: 0.18em;
            color: #1d4ed8;
            background: #eff6ff;
            border: 2px solid #93c5fd;
            border-radius: 7px;
            padding: 0.18rem 0.7rem;
            margin-right: 0.4rem;
            vertical-align: middle;
            box-shadow: 0 1px 4px rgba(37,99,235,0.10);
          }
          /* Inline highlight for the 2-digit suffix inside a mono code */
          .qr-suffix-hl {
            background: #fef9c3;
            color: #92400e;
            border-radius: 3px;
            padding: 0 0.18em;
            font-weight: 700;
            border-bottom: 2px solid #fbbf24;
          }
          /* Result card per matching product */
          .prod-result-card {
            background: #f8fafc;
            border: 1px solid #dde3ee;
            border-left: 4px solid #2563eb;
            border-radius: 8px;
            padding: 0.75rem 1rem;
            margin-bottom: 0.6rem;
          }
          .prod-result-name {
            font-family: 'Inter', sans-serif;
            font-size: 0.83rem;
            font-weight: 600;
            color: #1a2035;
          }
          .prod-result-qr {
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.76rem;
            color: #7a8aaa;
            margin-top: 0.18rem;
          }
          /* Detail panel critical-ID row */
          .critical-id-row {
            display: flex;
            align-items: center;
            gap: 0.7rem;
            background: #fffbeb;
            border: 1px solid #fde68a;
            border-radius: 7px;
            padding: 0.55rem 1rem;
            margin: 0.5rem 0 0.2rem;
          }
          .critical-id-label {
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.65rem;
            letter-spacing: 0.13em;
            text-transform: uppercase;
            color: #92400e;
            flex-shrink: 0;
          }
          .critical-id-value {
            font-family: 'JetBrains Mono', monospace;
            font-size: 1.65rem;
            font-weight: 800;
            color: #b45309;
            letter-spacing: 0.22em;
            line-height: 1;
          }
        </style>
        """, unsafe_allow_html=True)

        st.markdown("""
        <div style="font-size:0.72rem; color:#7a8aaa; font-family:'JetBrains Mono',monospace;
                    letter-spacing:0.06em; margin-bottom:0.35rem;">
          SEARCH BY LAST 2 DIGITS OF QR CODE
        </div>
        """, unsafe_allow_html=True)

        digit2_search = st.text_input(
            "Search by last 2 digits",
            placeholder="e.g. 12  →  matches code ending in …12",
            max_chars=2,
            label_visibility="collapsed",
            key="digit2_search",
        )

        # Build a deduplicated index: (last2, qr_code, product_name)
        # so we can show every unique QR that matches the 2-digit input
        history["_last2"] = history["qr_code"].str[-2:]

        if digit2_search.strip():
            q2 = digit2_search.strip().zfill(2)
            matched_records = history[history["_last2"] == q2]
        else:
            matched_records = pd.DataFrame()  # show nothing until user types

        # Unique (product, qr_code) pairs in the matches
        if not matched_records.empty:
            unique_pairs = (
                matched_records[["product", "qr_code", "_last2"]]
                .drop_duplicates(subset=["qr_code"])
                .sort_values("product")
                .reset_index(drop=True)
            )

            n_matches = len(unique_pairs)
            st.markdown(
                f'<div style="font-size:0.72rem; color:#2563eb; font-family:\'JetBrains Mono\','
                f'monospace; letter-spacing:0.06em; margin-bottom:0.4rem;">'
                f'{n_matches} PRODUCT CODE(S) MATCHED</div>',
                unsafe_allow_html=True,
            )

            # Radio to pick one of the matching (product, qr_code) pairs
            pair_labels = []
            for _, row in unique_pairs.iterrows():
                last2   = row["_last2"]
                full_qr = row["qr_code"]
                prefix  = full_qr[:-2]
                pair_labels.append(f"[{last2}]  {row['product']}  ·  {prefix}{last2}")

            chosen_idx = st.radio(
                "Select a product to view its history",
                options=range(len(pair_labels)),
                format_func=lambda i: pair_labels[i],
                label_visibility="collapsed",
                key="prod_radio_choice",
            )

            selected_row = unique_pairs.iloc[chosen_idx]
            selected_qr      = selected_row["qr_code"]
            selected_product = selected_row["product"]
            selected_last2   = selected_row["_last2"]

            # ── Critical identifier callout ────────────────────────────────────
            qr_prefix = selected_qr[:-2]
            st.markdown(f"""
            <div class="critical-id-row">
              <div class="critical-id-label">Critical Identifier</div>
              <div class="critical-id-value">{selected_last2}</div>
              <div style="font-family:'JetBrains Mono',monospace; font-size:0.74rem;
                          color:#92400e; letter-spacing:0.1em;">
                QR Full Code:&nbsp;
                <span style="color:#7a8aaa;">{qr_prefix}</span><span class="qr-suffix-hl">{selected_last2}</span>
              </div>
            </div>
            """, unsafe_allow_html=True)

            # Filter history to this specific QR code
            prod_df = history[history["qr_code"] == selected_qr].copy()

            p_total    = len(prod_df)
            p_accepted = int((prod_df["status"] == "ACCEPT").sum())
            p_rejected = int((prod_df["status"] == "REJECT").sum())
            p_acc_pct  = round((p_accepted / p_total) * 100, 1) if p_total else 0.0
            p_rej_pct  = round((p_rejected / p_total) * 100, 1) if p_total else 0.0

            st.markdown(f"""
            <div class="stat-row">
              <div class="stat-card">
                <div class="stat-label">Total Scans</div>
                <div class="stat-value">{p_total}</div>
              </div>
              <div class="stat-card">
                <div class="stat-label">Accepted</div>
                <div class="stat-value green">{p_accepted}</div>
              </div>
              <div class="stat-card">
                <div class="stat-label">Rejected</div>
                <div class="stat-value red">{p_rejected}</div>
              </div>
              <div class="stat-card">
                <div class="stat-label">Acceptance %</div>
                <div class="stat-value amber">{p_acc_pct}%</div>
              </div>
              <div class="stat-card">
                <div class="stat-label">Rejection %</div>
                <div class="stat-value red">{p_rej_pct}%</div>
              </div>
            </div>
            """, unsafe_allow_html=True)

            prod_display = prod_df[list(display_cols.keys())].rename(columns=display_cols)
            styled_prod = prod_display.style.map(style_status_col, subset=["Status"])
            st.dataframe(styled_prod, use_container_width=True, hide_index=True)

            # Download for individual product
            dl_p1, dl_p2, _ = st.columns([1, 1, 3])
            with dl_p1:
                st.download_button(
                    "CSV (this product)",
                    data=df_to_csv_bytes(prod_display),
                    file_name=f"{selected_product[:30]}_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv",
                    key="dl_prod_csv",
                )
            with dl_p2:
                st.download_button(
                    "Excel (this product)",
                    data=df_to_excel_bytes(prod_display),
                    file_name=f"{selected_product[:30]}_{datetime.now().strftime('%Y%m%d')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="dl_prod_xlsx",
                )

        elif digit2_search.strip() == "":
            st.markdown("""
            <div class="panel" style="text-align:center; padding:1.8rem; color:#7a8aaa;">
              <div style="font-family:'JetBrains Mono',monospace; font-size:0.8rem;
                          letter-spacing:0.1em;">
                Type the last 2 digits of a QR code above to search
              </div>
              <div style="font-size:0.72rem; margin-top:0.3rem;">
                Example: enter <strong>12</strong> to find all products whose code ends in …12
              </div>
            </div>
            """, unsafe_allow_html=True)

        else:
            st.markdown(f"""
            <div class="panel" style="text-align:center; padding:1.4rem; color:#dc2626;">
              <div style="font-family:'JetBrains Mono',monospace; font-size:0.82rem;
                          letter-spacing:0.08em;">
                No scan records found for codes ending in <strong>{digit2_search.strip().zfill(2)}</strong>
              </div>
            </div>
            """, unsafe_allow_html=True)

        # Clean up helper column (do not persist into analytics below)
        history.drop(columns=["_last2"], inplace=True, errors="ignore")

        st.markdown("<hr>", unsafe_allow_html=True)

        # ── C. ANALYTICS / CHARTS ──────────────────────────────────────────────
        st.markdown('<div class="section-title">Analytics Dashboard</div>',
                    unsafe_allow_html=True)

        chart_col1, chart_col2 = st.columns(2, gap="large")

        _prod_chart_ready = (
            digit2_search.strip() != "" and not matched_records.empty
        )

        with chart_col1:
            if _prod_chart_ready:
                _chart_label = (
                    f"Accept / Reject — {selected_product[:28]}..."
                    if len(selected_product) > 28
                    else f"Accept / Reject — {selected_product}"
                )
                st.plotly_chart(
                    donut_chart(p_accepted, p_rejected, title=_chart_label),
                    use_container_width=True, config={"displayModeBar": False},
                )
            else:
                st.markdown("""
                <div class="panel" style="text-align:center; padding:2rem; color:#7a8aaa;">
                  <div style="font-family:'JetBrains Mono',monospace; font-size:0.75rem;
                              letter-spacing:0.08em;">
                    Search a product above to see its chart
                  </div>
                </div>
                """, unsafe_allow_html=True)

        with chart_col2:
            st.plotly_chart(
                donut_chart(accepted, rejected, title="Overall Accept / Reject (All Products)"),
                use_container_width=True, config={"displayModeBar": False},
            )


# ── Footer ─────────────────────────────────────────────────────────────────────
st.markdown("""
<hr>
<div style="text-align:center; font-family:'JetBrains Mono',monospace;
            font-size:0.65rem; color:#aab4cc; letter-spacing:0.12em; padding-bottom:1rem;">
  WEIGHT VALIDATION SYSTEM v2 &nbsp;·&nbsp; FROZEN FOOD DIVISION &nbsp;·&nbsp;
  DB: {:,} PRODUCTS LOADED
</div>
""".format(len(product_df)), unsafe_allow_html=True)
