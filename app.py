"""
app.py — Weight Validation System (v3)
Frozen Food Division · Production Line Monitor

Changes from v2:
  • Replaced OpenCV/subprocess webcam scanner with browser-based QR scanner
    using streamlit-qrcode-scanner (html5-qrcode under the hood).
    Works on Streamlit Cloud because the camera runs in the user's browser,
    not on the server.
  • Removed: scanner.py, subprocess, sys, cv2, pyzbar dependencies
  • Redesigned UI: industrial quality-control aesthetic
"""

import streamlit as st
import pandas as pd
import sqlite3
import os
from datetime import datetime
import plotly.graph_objects as go
import io

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Weight Validation System",
    page_icon="⚖",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── CSS ────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@300;400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600&display=swap');

  html, body, [class*="css"] {
    font-family: 'IBM Plex Sans', sans-serif;
    background-color: #f0f2f5;
    color: #111827;
  }
  .stApp { background: #f0f2f5; }
  #MainMenu, footer, header { visibility: hidden; }
  .block-container { padding: 1.25rem 2.25rem 4rem; max-width: 1600px; }

  /* ── App Header ── */
  .app-header {
    background: #111827;
    border-radius: 0;
    padding: 0.9rem 1.8rem;
    margin: -1.25rem -2.25rem 1.6rem;
    display: flex;
    align-items: center;
    justify-content: space-between;
  }
  .app-header-left { display: flex; align-items: center; gap: 1rem; }
  .app-header h1 {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 1.05rem;
    font-weight: 600;
    letter-spacing: 0.12em;
    color: #f9fafb;
    margin: 0;
    text-transform: uppercase;
  }
  .app-header .subtitle {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.65rem;
    color: #6b7280;
    letter-spacing: 0.1em;
    margin-top: 2px;
  }
  .live-indicator {
    display: flex; align-items: center; gap: 0.45rem;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.62rem;
    color: #34d399;
    letter-spacing: 0.1em;
  }
  .live-dot {
    width: 7px; height: 7px;
    background: #34d399;
    border-radius: 50%;
    animation: pulse 2s infinite;
  }
  @keyframes pulse {
    0%, 100% { opacity: 1; }
    50%       { opacity: 0.35; }
  }

  /* ── KPI strip ── */
  .kpi-strip {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 1px;
    background: #d1d5db;
    border: 1px solid #d1d5db;
    border-radius: 8px;
    overflow: hidden;
    margin-bottom: 1.5rem;
  }
  .kpi-cell {
    background: #ffffff;
    padding: 1.1rem 1.5rem;
    position: relative;
  }
  .kpi-label {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.6rem;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: #9ca3af;
    margin-bottom: 0.5rem;
  }
  .kpi-value {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 2rem;
    font-weight: 600;
    line-height: 1;
    color: #111827;
  }
  .kpi-value.green { color: #059669; }
  .kpi-value.red   { color: #dc2626; }
  .kpi-value.amber { color: #d97706; }
  .kpi-bar {
    position: absolute;
    bottom: 0; left: 0; right: 0;
    height: 2px;
  }
  .kpi-bar.blue  { background: #2563eb; }
  .kpi-bar.green { background: #059669; }
  .kpi-bar.red   { background: #dc2626; }
  .kpi-bar.amber { background: #d97706; }

  /* ── Section label ── */
  .section-label {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.6rem;
    font-weight: 600;
    letter-spacing: 0.16em;
    text-transform: uppercase;
    color: #6b7280;
    margin: 1.4rem 0 0.65rem;
    display: flex; align-items: center; gap: 0.5rem;
  }
  .section-label::after {
    content: '';
    flex: 1;
    height: 1px;
    background: #e5e7eb;
  }

  /* ── Card ── */
  .card {
    background: #ffffff;
    border: 1px solid #e5e7eb;
    border-radius: 6px;
    padding: 1.2rem 1.4rem;
    margin-bottom: 0.85rem;
  }

  /* ── Result display ── */
  .result-block {
    border-radius: 6px;
    padding: 1.1rem 1.4rem;
    margin: 0.5rem 0;
    display: flex; align-items: center; gap: 1rem;
  }
  .result-block.accept { background: #f0fdf4; border: 1px solid #bbf7d0; }
  .result-block.reject { background: #fef2f2; border: 1px solid #fecaca; }
  .result-icon { font-size: 1.6rem; line-height: 1; }
  .result-text {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 1.3rem;
    font-weight: 600;
    letter-spacing: 0.12em;
  }
  .result-block.accept .result-text { color: #059669; }
  .result-block.reject .result-text { color: #dc2626; }
  .result-sub {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.72rem;
    color: #6b7280;
    margin-top: 0.15rem;
  }

  /* ── Detail table ── */
  .dtable { width: 100%; border-collapse: collapse; }
  .dtable tr { border-bottom: 1px solid #f3f4f6; }
  .dtable tr:last-child { border-bottom: none; }
  .dtable td { padding: 0.45rem 0; vertical-align: baseline; }
  .dtable td:first-child {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.63rem;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: #9ca3af;
    width: 46%;
  }
  .dtable td:last-child {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.83rem;
    color: #111827;
    text-align: right;
  }
  .dtable td:last-child.bold { font-weight: 600; }
  .dtable td:last-child.blue { color: #2563eb; }

  /* ── QR code pill ── */
  .qr-pill {
    display: inline-block;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.95rem;
    font-weight: 500;
    background: #eff6ff;
    border: 1px solid #bfdbfe;
    border-radius: 4px;
    padding: 0.45rem 0.9rem;
    letter-spacing: 0.18em;
    color: #1d4ed8;
    margin: 0.3rem 0 0.7rem;
  }

  /* ── Warning inline ── */
  .inline-warn {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.78rem;
    color: #dc2626;
    background: #fef2f2;
    border-left: 3px solid #dc2626;
    padding: 0.4rem 0.8rem;
    border-radius: 0 4px 4px 0;
    margin: 0.4rem 0;
  }

  /* ── Camera scanner panel ── */
  .scanner-wrap {
    background: #111827;
    border-radius: 6px;
    overflow: hidden;
    padding: 0;
    margin: 0.6rem 0;
  }
  .scanner-header {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.62rem;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: #6b7280;
    padding: 0.55rem 0.9rem;
    border-bottom: 1px solid #1f2937;
    display: flex; align-items: center; gap: 0.4rem;
  }
  .scanner-dot {
    width: 6px; height: 6px;
    background: #f59e0b;
    border-radius: 50%;
    animation: pulse 1s infinite;
  }

  /* ── Tabs ── */
  .stTabs [data-baseweb="tab-list"] {
    background: transparent;
    border-bottom: 2px solid #e5e7eb;
    gap: 0;
    padding: 0;
    margin-bottom: 1.4rem;
    box-shadow: none !important;
    border-radius: 0;
  }
  .stTabs [data-baseweb="tab"] {
    background: transparent !important;
    color: #6b7280 !important;
    font-family: 'IBM Plex Sans', sans-serif !important;
    font-size: 0.84rem !important;
    font-weight: 500 !important;
    letter-spacing: 0.03em !important;
    border-radius: 0 !important;
    padding: 0.65rem 1.4rem 0.65rem 0 !important;
    border: none !important;
    margin-right: 1.8rem !important;
  }
  .stTabs [aria-selected="true"] {
    background: transparent !important;
    color: #111827 !important;
    border: none !important;
    border-bottom: 2px solid #111827 !important;
    font-weight: 600 !important;
  }
  .stTabs [data-baseweb="tab-border"] { display: none !important; }
  .stTabs [data-baseweb="tab-highlight"] { display: none !important; }

  /* ── Inputs ── */
  .stTextInput > div > div > input {
    background: #ffffff !important;
    border: 1px solid #d1d5db !important;
    border-radius: 4px !important;
    color: #111827 !important;
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 0.93rem !important;
    letter-spacing: 0.06em !important;
    padding: 0.55rem 0.9rem !important;
  }
  .stTextInput > div > div > input:focus {
    border-color: #111827 !important;
    box-shadow: 0 0 0 2px rgba(17,24,39,0.1) !important;
  }
  .stNumberInput > div > div > input {
    background: #ffffff !important;
    border: 1px solid #d1d5db !important;
    border-radius: 4px !important;
    font-family: 'IBM Plex Mono', monospace !important;
    color: #111827 !important;
    font-size: 1.05rem !important;
  }
  .stSelectbox > div > div {
    background: #ffffff !important;
    border: 1px solid #d1d5db !important;
    border-radius: 4px !important;
    color: #111827 !important;
    font-family: 'IBM Plex Sans', sans-serif !important;
    font-size: 0.85rem !important;
  }

  /* ── Buttons ── */
  .stButton > button {
    background: #ffffff !important;
    border: 1px solid #d1d5db !important;
    color: #374151 !important;
    border-radius: 4px !important;
    font-family: 'IBM Plex Sans', sans-serif !important;
    font-size: 0.84rem !important;
    font-weight: 500 !important;
    letter-spacing: 0.02em !important;
    padding: 0.45rem 1.1rem !important;
    transition: border-color 0.12s, background 0.12s !important;
  }
  .stButton > button:hover {
    background: #f9fafb !important;
    border-color: #111827 !important;
    color: #111827 !important;
  }
  .stButton > button[kind="primary"] {
    background: #111827 !important;
    border-color: #111827 !important;
    color: #ffffff !important;
  }
  .stButton > button[kind="primary"]:hover {
    background: #1f2937 !important;
    color: #ffffff !important;
  }

  /* ── DataFrames ── */
  div[data-testid="stDataFrame"] {
    border: 1px solid #e5e7eb !important;
    border-radius: 6px !important;
    overflow: hidden;
  }

  /* ── Alerts ── */
  div[data-testid="stAlert"] {
    border-radius: 4px !important;
    border-left: 3px solid !important;
  }

  /* ── Stat cards (product summary) ── */
  .stat-strip {
    display: grid;
    grid-template-columns: repeat(5, 1fr);
    gap: 1px;
    background: #e5e7eb;
    border: 1px solid #e5e7eb;
    border-radius: 6px;
    overflow: hidden;
    margin-bottom: 1rem;
  }
  .stat-cell {
    background: #ffffff;
    padding: 0.85rem 1rem;
  }
  .stat-label { font-family: 'IBM Plex Mono', monospace; font-size: 0.58rem; color: #9ca3af; letter-spacing: 0.12em; text-transform: uppercase; margin-bottom: 0.3rem; }
  .stat-value { font-family: 'IBM Plex Mono', monospace; font-size: 1.55rem; font-weight: 600; color: #111827; }
  .stat-value.green { color: #059669; }
  .stat-value.red   { color: #dc2626; }
  .stat-value.amber { color: #d97706; }

  /* ── Empty state ── */
  .empty-state {
    text-align: center;
    padding: 3.5rem 2rem;
    color: #9ca3af;
  }
  .empty-state .empty-icon {
    font-size: 2rem;
    margin-bottom: 0.8rem;
    opacity: 0.4;
  }
  .empty-state .empty-title {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.78rem;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: #d1d5db;
    margin-bottom: 0.35rem;
  }
  .empty-state .empty-sub {
    font-size: 0.78rem;
    color: #9ca3af;
  }

  /* ── QR search highlight ── */
  .qr-suffix-hl {
    background: #fef3c7;
    color: #92400e;
    border-radius: 2px;
    padding: 0 0.15em;
    font-weight: 600;
    border-bottom: 2px solid #fbbf24;
  }
  .critical-id-row {
    display: flex; align-items: center; gap: 0.7rem;
    background: #fffbeb;
    border: 1px solid #fde68a;
    border-radius: 5px;
    padding: 0.5rem 0.9rem;
    margin: 0.5rem 0 0.3rem;
  }
  .critical-id-label {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.6rem; letter-spacing: 0.13em; text-transform: uppercase; color: #92400e;
  }
  .critical-id-value {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 1.5rem; font-weight: 700; color: #b45309; letter-spacing: 0.22em;
  }

  hr { border: none; border-top: 1px solid #e5e7eb; margin: 1.2rem 0; }

  /* streamlit-qrcode-scanner iframe container fix */
  iframe { border-radius: 6px; }
</style>
""", unsafe_allow_html=True)

# ── Constants ──────────────────────────────────────────────────────────────────
PACKAGE_WEIGHT = 0.5   # KG
TOLERANCE      = 0.1   # KG ±
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
        df = pd.read_sql_query("SELECT * FROM scans ORDER BY id DESC", conn)
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

# ── Chart helpers ──────────────────────────────────────────────────────────────
def donut_chart(accept: int, reject: int, title: str = "Accept / Reject", height=240):
    total_v = accept + reject
    if total_v == 0:
        accept, reject = 1, 0   # placeholder
        colors = ["#e5e7eb", "#e5e7eb"]
        textinfo = "none"
    else:
        colors  = ["#059669", "#dc2626"]
        textinfo = "percent"

    fig = go.Figure(go.Pie(
        labels=["ACCEPT", "REJECT"],
        values=[accept, reject],
        hole=0.58,
        marker=dict(colors=colors, line=dict(color="#f0f2f5", width=2)),
        textinfo=textinfo,
        textfont=dict(size=12, color="white", family="IBM Plex Mono"),
        hovertemplate="%{label}: %{value}<extra></extra>",
    ))
    fig.update_layout(
        paper_bgcolor="#ffffff", plot_bgcolor="#ffffff",
        margin=dict(t=40, b=8, l=8, r=8), height=height,
        title=dict(
            text=title,
            font=dict(color="#6b7280", size=10, family="IBM Plex Mono"),
            x=0.5, xanchor="center",
        ),
        legend=dict(
            font=dict(color="#374151", size=10, family="IBM Plex Mono"),
            bgcolor="rgba(0,0,0,0)", orientation="h",
            x=0.5, xanchor="center", y=-0.05,
        ),
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
    "show_scanner":       False,
}.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ── Header ─────────────────────────────────────────────────────────────────────
st.markdown(f"""
<div class="app-header">
  <div class="app-header-left">
    <div>
      <h1>Weight Validation System</h1>
      <div class="subtitle">Frozen Food Division &nbsp;·&nbsp; Production Line Monitor &nbsp;·&nbsp; v3</div>
    </div>
  </div>
  <div class="live-indicator">
    <div class="live-dot"></div>
    LIVE · {len(product_df):,} PRODUCTS
  </div>
</div>
""", unsafe_allow_html=True)

# ── Global KPI strip ───────────────────────────────────────────────────────────
history_all = load_all_scans()
total    = len(history_all)
accepted = int((history_all["status"] == "ACCEPT").sum()) if total else 0
rejected = int((history_all["status"] == "REJECT").sum()) if total else 0
rate     = round((rejected / total) * 100, 1) if total else 0.0

st.markdown(f"""
<div class="kpi-strip">
  <div class="kpi-cell">
    <div class="kpi-label">Total Scans</div>
    <div class="kpi-value">{total}</div>
    <div class="kpi-bar blue"></div>
  </div>
  <div class="kpi-cell">
    <div class="kpi-label">Accepted</div>
    <div class="kpi-value green">{accepted}</div>
    <div class="kpi-bar green"></div>
  </div>
  <div class="kpi-cell">
    <div class="kpi-label">Rejected</div>
    <div class="kpi-value red">{rejected}</div>
    <div class="kpi-bar red"></div>
  </div>
  <div class="kpi-cell">
    <div class="kpi-label">Reject Rate</div>
    <div class="kpi-value amber">{rate}%</div>
    <div class="kpi-bar amber"></div>
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

    with left:
        # ── QR Code section ────────────────────────────────────────────────────
        st.markdown('<div class="section-label">QR Code</div>', unsafe_allow_html=True)

        _k = f"qr_{st.session_state.qr_key}"
        if _k not in st.session_state:
            st.session_state[_k] = st.session_state.get("webcam_result", "")

        qr_input = st.text_input(
            "QR code",
            placeholder="Scan with camera or type 12-digit code",
            key=_k,
            label_visibility="collapsed",
        )

        # ── Camera scanner toggle ──────────────────────────────────────────────
        cam_col1, cam_col2 = st.columns([1, 2])
        with cam_col1:
            cam_label = "Close Scanner" if st.session_state.show_scanner else "📷  Open Camera"
            if st.button(cam_label, key="cam_toggle"):
                st.session_state.show_scanner = not st.session_state.show_scanner
                st.rerun()

        if st.session_state.show_scanner:
            st.markdown("""
            <div style="font-size:0.71rem; color:#6b7280; font-family:'IBM Plex Mono',monospace;
                        letter-spacing:0.05em; margin:0.3rem 0 0.5rem;">
              Point your camera at the QR code on the box.
              Detected codes will populate the field above automatically.
            </div>
            """, unsafe_allow_html=True)

            # ── Browser-based QR scanner ───────────────────────────────────────
            # streamlit-qrcode-scanner renders an html5-qrcode component in the
            # browser. The camera runs entirely client-side — no server webcam
            # access needed. Works on Streamlit Cloud.
            try:
                from streamlit_qrcode_scanner import qrcode_scanner
                scanned_qr = qrcode_scanner(key="browser_cam_scanner")
                if scanned_qr:
                    cleaned = scanned_qr.strip().zfill(12)
                    st.session_state.webcam_result = cleaned
                    st.session_state.qr_key       += 1
                    st.session_state.weight_key   += 1
                    st.session_state.show_scanner  = False
                    st.rerun()
            except ImportError:
                st.error(
                    "streamlit-qrcode-scanner not installed. "
                    "Add `streamlit-qrcode-scanner` to requirements.txt and redeploy."
                )
        else:
            st.markdown("""
            <div style="font-size:0.71rem; color:#9ca3af; font-family:'IBM Plex Mono',monospace;
                        letter-spacing:0.05em; margin:0.2rem 0 0.4rem;">
              Or point a USB barcode gun at the box — it types directly into the field above.
            </div>
            """, unsafe_allow_html=True)

        # ── Weight input ───────────────────────────────────────────────────────
        st.markdown('<div class="section-label">Gross Weight (KG)</div>', unsafe_allow_html=True)

        measured_weight = st.number_input(
            "Gross weight",
            min_value=0.0,
            step=0.1,
            format="%.2f",
            key=f"weight_{st.session_state.weight_key}",
            label_visibility="collapsed",
        )
        st.markdown(f"""
        <div style="font-size:0.68rem; color:#9ca3af; margin-top:0.2rem;
                    font-family:'IBM Plex Mono',monospace; letter-spacing:0.05em;">
          Includes box + plastic wrap &nbsp;(−{PACKAGE_WEIGHT:.2f} KG deducted automatically)
        </div>
        """, unsafe_allow_html=True)

    # ── RIGHT: product + result ────────────────────────────────────────────────
    with right:
        qr = qr_input.strip().zfill(12) if qr_input.strip() else ""

        if qr:
            st.markdown(f'<div class="qr-pill">⬛  {qr[:4]} · {qr[4:9]} · {qr[9:]}</div>',
                        unsafe_allow_html=True)

            row = lookup_product(qr, product_df)
            if row is not None:
                product_name = row["DESCRIPTION"]
                net_weight   = float(row["INTER_CONV"])

                actual_net = measured_weight - PACKAGE_WEIGHT
                lower      = net_weight - TOLERANCE
                upper      = net_weight + TOLERANCE
                status     = "ACCEPT" if lower <= actual_net <= upper else "REJECT"
                ts         = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                # ── Result badge ───────────────────────────────────────────────
                icon = "✓" if status == "ACCEPT" else "✕"
                st.markdown(f"""
                <div class="result-block {status.lower()}">
                  <div class="result-icon">{icon}</div>
                  <div>
                    <div class="result-text">{status}</div>
                    <div class="result-sub">{ts}</div>
                  </div>
                </div>
                """, unsafe_allow_html=True)

                if status == "REJECT":
                    if actual_net < lower:
                        diff_msg = f"Underweight by {lower - actual_net:.3f} KG"
                    else:
                        diff_msg = f"Overweight by {actual_net - upper:.3f} KG"
                    st.markdown(f'<div class="inline-warn">⚠ {diff_msg}</div>',
                                unsafe_allow_html=True)

                # ── Product details ────────────────────────────────────────────
                st.markdown('<div class="section-label">Product Details</div>',
                            unsafe_allow_html=True)
                st.markdown(f"""
                <div class="card">
                  <table class="dtable">
                    <tr>
                      <td>Product</td>
                      <td class="bold" style="font-family:'IBM Plex Sans',sans-serif;
                          font-size:0.82rem; color:#111827;">{product_name}</td>
                    </tr>
                    <tr>
                      <td>Item Code</td>
                      <td class="blue">{qr}</td>
                    </tr>
                    <tr>
                      <td>Expected Net</td>
                      <td>{net_weight:.2f} KG</td>
                    </tr>
                    <tr>
                      <td>Measured (Gross)</td>
                      <td>{measured_weight:.2f} KG</td>
                    </tr>
                    <tr>
                      <td>Packaging Deduction</td>
                      <td>−{PACKAGE_WEIGHT:.2f} KG</td>
                    </tr>
                    <tr>
                      <td>Actual Net</td>
                      <td class="bold">{actual_net:.2f} KG</td>
                    </tr>
                    <tr>
                      <td>Acceptable Range</td>
                      <td>{lower:.2f} – {upper:.2f} KG</td>
                    </tr>
                    <tr>
                      <td>Tolerance</td>
                      <td>± {TOLERANCE:.2f} KG</td>
                    </tr>
                  </table>
                </div>
                """, unsafe_allow_html=True)

                # ── Save to DB ─────────────────────────────────────────────────
                if measured_weight > 0:
                    scan_key = f"{qr}_{measured_weight}"
                    if scan_key != st.session_state.last_submitted_key:
                        st.session_state.last_submitted_key = scan_key
                        insert_scan(
                            ts, qr, product_name, net_weight,
                            measured_weight, actual_net, TOLERANCE, status,
                        )

                # ── Clear ──────────────────────────────────────────────────────
                st.markdown("<br>", unsafe_allow_html=True)
                def clear_scan():
                    st.session_state.qr_key            += 1
                    st.session_state.webcam_result      = ""
                    st.session_state.last_submitted_key = ""
                    st.session_state.weight_key        += 1
                    st.session_state.show_scanner       = False

                st.button("Clear — Scan Next Product", type="primary", on_click=clear_scan)

            else:
                st.warning(f"Product not found — QR: `{qr}`")
                st.caption("Ensure the QR code is fully scanned (12 digits).")

        else:
            st.markdown("""
            <div class="card empty-state">
              <div class="empty-icon">⚖</div>
              <div class="empty-title">Awaiting QR Code</div>
              <div class="empty-sub">Open the camera scanner or type the 12-digit item code</div>
            </div>
            """, unsafe_allow_html=True)

    # ── Reset (below columns) ──────────────────────────────────────────────────
    st.markdown("<hr>", unsafe_allow_html=True)
    if st.button("Reset All History", key="reset_btn"):
        reset_db()
        st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
#  TAB 2 — HISTORY / REPORTS
# ══════════════════════════════════════════════════════════════════════════════
with tab_history:

    history = load_all_scans()

    if history.empty:
        st.markdown("""
        <div class="card empty-state">
          <div class="empty-icon">📋</div>
          <div class="empty-title">No Scan Data</div>
          <div class="empty-sub">Go to Live Scan and scan your first QR code to begin</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        # ── A. COLLECTIVE HISTORY ──────────────────────────────────────────────
        st.markdown('<div class="section-label">Collective Scan History</div>',
                    unsafe_allow_html=True)

        fcol1, fcol2, fcol3 = st.columns([2, 2, 2])
        with fcol1:
            search_qr = st.text_input(
                "Filter", placeholder="Search QR or product…",
                label_visibility="collapsed", key="search_qr",
            )
        with fcol2:
            filter_status = st.selectbox(
                "Status", ["All", "ACCEPT", "REJECT"],
                label_visibility="collapsed", key="filter_status",
            )
        with fcol3:
            sort_order = st.selectbox(
                "Sort", ["Newest first", "Oldest first"],
                label_visibility="collapsed", key="sort_order",
            )

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
            if val == "ACCEPT": return "color: #059669; font-weight: 600;"
            if val == "REJECT": return "color: #dc2626; font-weight: 600;"
            return ""

        styled_df = display_df.style.map(style_status_col, subset=["Status"])
        st.dataframe(styled_df, use_container_width=True, hide_index=True)

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
        st.markdown('<div class="section-label">Individual Product History</div>',
                    unsafe_allow_html=True)

        st.markdown("""
        <div style="font-size:0.68rem; color:#9ca3af; font-family:'IBM Plex Mono',monospace;
                    letter-spacing:0.06em; margin-bottom:0.4rem;">
          SEARCH BY LAST 2 DIGITS OF QR CODE
        </div>
        """, unsafe_allow_html=True)

        digit2_search = st.text_input(
            "Last 2 digits",
            placeholder="e.g. 12  →  matches codes ending in …12",
            max_chars=2,
            label_visibility="collapsed",
            key="digit2_search",
        )

        history["_last2"] = history["qr_code"].str[-2:]

        if digit2_search.strip():
            q2 = digit2_search.strip().zfill(2)
            matched_records = history[history["_last2"] == q2]
        else:
            matched_records = pd.DataFrame()

        if not matched_records.empty:
            unique_pairs = (
                matched_records[["product", "qr_code", "_last2"]]
                .drop_duplicates(subset=["qr_code"])
                .sort_values("product")
                .reset_index(drop=True)
            )
            n_matches = len(unique_pairs)
            st.markdown(
                f'<div style="font-size:0.68rem; color:#2563eb; font-family:\'IBM Plex Mono\','
                f'monospace; letter-spacing:0.06em; margin-bottom:0.4rem;">'
                f'{n_matches} CODE(S) MATCHED</div>',
                unsafe_allow_html=True,
            )

            pair_labels = []
            for _, row in unique_pairs.iterrows():
                last2   = row["_last2"]
                full_qr = row["qr_code"]
                prefix  = full_qr[:-2]
                pair_labels.append(f"[{last2}]  {row['product']}  ·  {prefix}{last2}")

            chosen_idx = st.radio(
                "Select product",
                options=range(len(pair_labels)),
                format_func=lambda i: pair_labels[i],
                label_visibility="collapsed",
                key="prod_radio_choice",
            )

            selected_row     = unique_pairs.iloc[chosen_idx]
            selected_qr      = selected_row["qr_code"]
            selected_product = selected_row["product"]
            selected_last2   = selected_row["_last2"]

            qr_prefix = selected_qr[:-2]
            st.markdown(f"""
            <div class="critical-id-row">
              <div class="critical-id-label">Critical ID</div>
              <div class="critical-id-value">{selected_last2}</div>
              <div style="font-family:'IBM Plex Mono',monospace; font-size:0.72rem; color:#92400e; letter-spacing:0.08em;">
                Full Code:&nbsp;
                <span style="color:#9ca3af;">{qr_prefix}</span><span class="qr-suffix-hl">{selected_last2}</span>
              </div>
            </div>
            """, unsafe_allow_html=True)

            prod_df    = history[history["qr_code"] == selected_qr].copy()
            p_total    = len(prod_df)
            p_accepted = int((prod_df["status"] == "ACCEPT").sum())
            p_rejected = int((prod_df["status"] == "REJECT").sum())
            p_acc_pct  = round((p_accepted / p_total) * 100, 1) if p_total else 0.0
            p_rej_pct  = round((p_rejected / p_total) * 100, 1) if p_total else 0.0

            st.markdown(f"""
            <div class="stat-strip">
              <div class="stat-cell">
                <div class="stat-label">Scans</div>
                <div class="stat-value">{p_total}</div>
              </div>
              <div class="stat-cell">
                <div class="stat-label">Accepted</div>
                <div class="stat-value green">{p_accepted}</div>
              </div>
              <div class="stat-cell">
                <div class="stat-label">Rejected</div>
                <div class="stat-value red">{p_rejected}</div>
              </div>
              <div class="stat-cell">
                <div class="stat-label">Accept %</div>
                <div class="stat-value amber">{p_acc_pct}%</div>
              </div>
              <div class="stat-cell">
                <div class="stat-label">Reject %</div>
                <div class="stat-value red">{p_rej_pct}%</div>
              </div>
            </div>
            """, unsafe_allow_html=True)

            prod_display = prod_df[list(display_cols.keys())].rename(columns=display_cols)
            styled_prod  = prod_display.style.map(style_status_col, subset=["Status"])
            st.dataframe(styled_prod, use_container_width=True, hide_index=True)

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
            <div class="card" style="text-align:center; padding:1.6rem; color:#9ca3af;">
              <div style="font-family:'IBM Plex Mono',monospace; font-size:0.75rem; letter-spacing:0.1em;">
                Type the last 2 digits of a QR code to search
              </div>
              <div style="font-size:0.72rem; margin-top:0.3rem;">
                Example: enter <strong>12</strong> to find all products whose code ends in …12
              </div>
            </div>
            """, unsafe_allow_html=True)

        else:
            st.markdown(f"""
            <div class="card" style="text-align:center; padding:1.2rem; color:#dc2626;">
              <div style="font-family:'IBM Plex Mono',monospace; font-size:0.78rem; letter-spacing:0.08em;">
                No records for codes ending in <strong>{digit2_search.strip().zfill(2)}</strong>
              </div>
            </div>
            """, unsafe_allow_html=True)

        history.drop(columns=["_last2"], inplace=True, errors="ignore")
        st.markdown("<hr>", unsafe_allow_html=True)

        # ── C. ANALYTICS ──────────────────────────────────────────────────────
        st.markdown('<div class="section-label">Analytics</div>', unsafe_allow_html=True)

        chart_col1, chart_col2 = st.columns(2, gap="large")

        _prod_chart_ready = (
            digit2_search.strip() != "" and not matched_records.empty
        )

        with chart_col1:
            if _prod_chart_ready:
                _chart_label = (
                    f"{selected_product[:30]}…" if len(selected_product) > 30
                    else selected_product
                )
                st.plotly_chart(
                    donut_chart(p_accepted, p_rejected, title=_chart_label),
                    use_container_width=True, config={"displayModeBar": False},
                )
            else:
                st.markdown("""
                <div class="card" style="text-align:center; padding:2rem; color:#9ca3af;">
                  <div style="font-family:'IBM Plex Mono',monospace; font-size:0.72rem; letter-spacing:0.08em;">
                    Search a product above to see its chart
                  </div>
                </div>
                """, unsafe_allow_html=True)

        with chart_col2:
            st.plotly_chart(
                donut_chart(accepted, rejected, title="Overall — All Products"),
                use_container_width=True, config={"displayModeBar": False},
            )


# ── Footer ─────────────────────────────────────────────────────────────────────
st.markdown("""
<hr>
<div style="text-align:center; font-family:'IBM Plex Mono',monospace;
            font-size:0.6rem; color:#9ca3af; letter-spacing:0.12em; padding-bottom:1rem;">
  WEIGHT VALIDATION SYSTEM v3 &nbsp;·&nbsp; FROZEN FOOD DIVISION
</div>
""", unsafe_allow_html=True)
         
