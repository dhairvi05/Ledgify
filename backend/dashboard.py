"""
backend/dashboard.py
---------------------
Ledgify — Streamlit monitoring dashboard v3.

Font choices
------------
  Space Grotesk (700) — wordmark and metric numerals. Has a native
  slashed zero so digits are never confused with letters.
  Space Mono (400/700) — all data labels, timestamps, badge text,
  small caps identifiers. Same slashed-zero guarantee for numbers.

Header treatment
----------------
  No box, no card, no background fill. Just the wordmark on the dark
  page with a small red dot as a bullet, a hairline separator, and
  the sub-label in Space Mono small caps. Clean and typographic.

Run with:
    streamlit run backend/dashboard.py
"""

import time
from datetime import datetime
from typing import Any

import requests
import streamlit as st

API_BASE_URL      = "http://localhost:8000"
LEDGER_ENDPOINT   = f"{API_BASE_URL}/api/ledger"
ALERTS_ENDPOINT   = f"{API_BASE_URL}/api/alerts"
REFRESH_S         = 10

st.set_page_config(
    page_title="Ledgify — Fraud Monitor",
    page_icon="🔴",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;700&family=Space+Mono:ital,wght@0,400;0,700;1,400&display=swap" rel="stylesheet">

<style>
html, body, [class*="css"] {
  background-color: #0a0a0c !important;
  color: #eeedf2;
  font-family: 'Space Grotesk', sans-serif;
}
.block-container { padding-top: 1rem !important; padding-bottom: 2rem !important; }
section[data-testid="stSidebar"] { background: #111115 !important; }

/* ── Header — no box, pure type ── */
.lfy-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 0 18px 0;
  border-bottom: 0.5px solid rgba(255,255,255,0.06);
  margin-bottom: 14px;
}
.lfy-wm {
  display: flex;
  align-items: center;
  gap: 12px;
}
.lfy-dot {
  width: 8px; height: 8px;
  border-radius: 50%;
  background: #f04f5f;
  flex-shrink: 0;
}
.lfy-word {
  font-family: 'Space Grotesk', sans-serif;
  font-weight: 700;
  font-size: 22px;
  letter-spacing: 0.08em;
  color: #ffffff;
  text-transform: uppercase;
  line-height: 1;
}
.lfy-word span { color: #f04f5f; }
.lfy-sep {
  width: 0.5px; height: 18px;
  background: rgba(255,255,255,0.1);
}
.lfy-sub {
  font-family: 'Space Mono', monospace;
  font-size: 10px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: #52526a;
}
.lfy-right { display: flex; align-items: center; gap: 16px; }
.lfy-live {
  display: flex; align-items: center; gap: 6px;
  border: 0.5px solid rgba(45,206,137,0.22);
  border-radius: 20px; padding: 3px 12px;
  font-family: 'Space Mono', monospace;
  font-size: 10px; color: #2dce89;
}
.lfy-live-dot {
  width: 5px; height: 5px; border-radius: 50%;
  background: #2dce89;
  animation: blink 2s infinite;
}
@keyframes blink { 0%,100%{opacity:1} 50%{opacity:.3} }
.lfy-clock {
  font-family: 'Space Mono', monospace;
  font-size: 11px; color: #52526a;
}

/* ── Metrics ── */
.lfy-metrics {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  background: #111115;
  border: 0.5px solid rgba(255,255,255,0.06);
  border-radius: 10px;
  overflow: hidden;
  margin-bottom: 16px;
}
.lfy-mc {
  padding: 14px 18px;
  border-right: 0.5px solid rgba(255,255,255,0.06);
}
.lfy-mc:last-child { border-right: none; }
.lfy-mc-lbl {
  font-family: 'Space Mono', monospace;
  font-size: 9px; letter-spacing: .14em;
  text-transform: uppercase; color: #52526a;
  margin-bottom: 6px;
}
/* Space Mono has a slashed zero — zero is always a zero */
.lfy-mc-val {
  font-family: 'Space Mono', monospace;
  font-weight: 700; font-size: 26px;
  color: #eeedf2; line-height: 1;
}
.lfy-mc-val.r { color: #f04f5f; }
.lfy-mc-val.g { color: #2dce89; }
.lfy-mc-sub {
  font-family: 'Space Mono', monospace;
  font-size: 9px; color: #2e2e3e;
  margin-top: 4px; letter-spacing: .04em;
}

/* ── Section label ── */
.lfy-sec {
  font-family: 'Space Mono', monospace;
  font-size: 9px; letter-spacing: .18em;
  text-transform: uppercase; color: #52526a;
  display: flex; align-items: center; gap: 8px;
  margin-bottom: 10px;
}
.lfy-sec::after {
  content: ''; flex: 1; height: 0.5px;
  background: rgba(255,255,255,0.06);
}

/* ── TX rows ── */
.lfy-tx {
  display: flex; align-items: center; gap: 8px;
  padding: 7px 10px; border-radius: 6px;
  margin-bottom: 4px; font-size: 12px;
}
.lfy-tx.s { background:rgba(45,206,137,.07); border:0.5px solid rgba(45,206,137,.18); }
.lfy-tx.f { background:rgba(240,79,95,.08);  border:0.5px solid rgba(240,79,95,.22);  }
.lfy-tx-b {
  font-family: 'Space Mono', monospace;
  font-size: 9px; letter-spacing: .05em;
  padding: 2px 7px; border-radius: 3px; flex-shrink: 0;
}
.lfy-tx-b.s { color:#2dce89; background:rgba(45,206,137,.1); border:0.5px solid rgba(45,206,137,.2); }
.lfy-tx-b.f { color:#f04f5f; background:rgba(240,79,95,.1);  border:0.5px solid rgba(240,79,95,.22); }
.lfy-tx-usr { font-weight:500; color:#eeedf2; min-width:76px; font-size:12px; }
.lfy-tx-amt { font-family:'Space Mono',monospace; font-size:12px; min-width:82px; text-align:right; color:#eeedf2; }
.lfy-tx-inf { color:#52526a; font-size:11px; flex:1; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.lfy-tx-t   { font-family:'Space Mono',monospace; font-size:10px; color:#2e2e3e; flex-shrink:0; }

/* ── Alert cards ── */
.lfy-ac {
  background: #16161c;
  border: 0.5px solid rgba(255,255,255,0.06);
  border-radius: 8px;
  padding: 10px 12px;
  margin-bottom: 7px;
  border-left: 0 solid transparent;
}
.lfy-ac.crit { border-left-width:2px; border-left-color:#f04f5f; border-radius:0 8px 8px 0; }
.lfy-ac.high { border-left-width:2px; border-left-color:#f97316; border-radius:0 8px 8px 0; }
.lfy-ac.med  { border-left-width:2px; border-left-color:#facc15; border-radius:0 8px 8px 0; }
.lfy-ac-top { display:flex; align-items:center; justify-content:space-between; margin-bottom:5px; }
.lfy-rb {
  font-family:'Space Mono',monospace; font-size:9px;
  letter-spacing:.05em; padding:2px 8px; border-radius:3px;
}
.rb-c { color:#f04f5f; background:rgba(240,79,95,.1); border:0.5px solid rgba(240,79,95,.24); }
.rb-h { color:#f97316; background:rgba(249,115,22,.1); border:0.5px solid rgba(249,115,22,.28); }
.rb-m { color:#facc15; background:rgba(250,204,21,.08); border:0.5px solid rgba(250,204,21,.25); }
.lfy-ac-who { font-family:'Space Mono',monospace; font-size:10px; color:#52526a; }
.lfy-ac-type { font-size:12px; font-weight:500; color:#eeedf2; margin-bottom:6px; }
.lfy-ac-fields {
  display:flex; gap:14px; flex-wrap:wrap;
  border-top:0.5px solid rgba(255,255,255,0.05);
  padding-top:7px; margin-top:2px;
}
.lfy-afl  { font-family:'Space Mono',monospace; font-size:9px; letter-spacing:.1em; text-transform:uppercase; color:#52526a; margin-bottom:2px; }
.lfy-afv  { font-size:11px; color:#ccd0f0; }
.lfy-narr { font-family:'Space Mono',monospace; font-size:10px; line-height:1.65; color:#2e2e3e; font-style:italic; margin-top:6px; }
</style>
""", unsafe_allow_html=True)


# ── Data fetchers ───────────────────────────────────────────────────────────

@st.cache_data(ttl=REFRESH_S)
def fetch_ledger() -> list[dict]:
    try:
        r = requests.get(LEDGER_ENDPOINT, timeout=5)
        r.raise_for_status()
        return r.json()
    except Exception as exc:
        st.error(f"Ledger API unreachable: {exc}")
        return []

@st.cache_data(ttl=REFRESH_S)
def fetch_alerts() -> list[dict[str, Any]]:
    try:
        r = requests.get(ALERTS_ENDPOINT, timeout=5)
        r.raise_for_status()
        return r.json()
    except Exception as exc:
        st.error(f"Alerts API unreachable: {exc}")
        return []


# ── Helpers ─────────────────────────────────────────────────────────────────

def _rb(risk: str) -> str:
    r = risk.upper()
    if "CRITICAL" in r: return "rb-c"
    if "HIGH"     in r: return "rb-h"
    return "rb-m"

def _ac_cls(risk: str) -> str:
    r = risk.upper()
    if "CRITICAL" in r: return "crit"
    if "HIGH"     in r: return "high"
    return "med"


# ── Render functions ─────────────────────────────────────────────────────────

def render_header() -> None:
    now = datetime.utcnow().strftime("%Y-%m-%d  %H:%M:%S UTC")
    st.markdown(f"""
    <div class="lfy-header">
      <div class="lfy-wm">
        <div class="lfy-dot"></div>
        <div class="lfy-word"><span>L</span>EDGIFY</div>
        <div class="lfy-sep"></div>
        <div class="lfy-sub">Fraud Monitor</div>
      </div>
      <div class="lfy-right">
        <div class="lfy-live"><span class="lfy-live-dot"></span>Pipeline live</div>
        <div class="lfy-clock">{now}</div>
      </div>
    </div>
    """, unsafe_allow_html=True)


def render_metrics(transactions: list[dict], alerts: list[dict]) -> None:
    total   = len(transactions)
    settled = sum(1 for t in transactions if t.get("status") == "SETTLED")
    flagged = total - settled
    pct     = f"{settled/total*100:.1f}% pass" if total else "—"

    st.markdown(f"""
    <div class="lfy-metrics">
      <div class="lfy-mc">
        <div class="lfy-mc-lbl">Transactions</div>
        <div class="lfy-mc-val">{total:02d}</div>
        <div class="lfy-mc-sub">latest window</div>
      </div>
      <div class="lfy-mc">
        <div class="lfy-mc-lbl">Settled</div>
        <div class="lfy-mc-val g">{settled:02d}</div>
        <div class="lfy-mc-sub">{pct}</div>
      </div>
      <div class="lfy-mc">
        <div class="lfy-mc-lbl">Flagged</div>
        <div class="lfy-mc-val r">{flagged:02d}</div>
        <div class="lfy-mc-sub">routed to AI</div>
      </div>
      <div class="lfy-mc">
        <div class="lfy-mc-lbl">AI Alerts</div>
        <div class="lfy-mc-val r">{len(alerts):02d}</div>
        <div class="lfy-mc-sub">forensic logs</div>
      </div>
    </div>
    """, unsafe_allow_html=True)


def render_ledger(transactions: list[dict]) -> None:
    st.markdown('<div class="lfy-sec">Transaction Ledger</div>', unsafe_allow_html=True)
    if not transactions:
        st.info("No transactions yet — start the stream generator and ingestion worker.")
        return

    html = ""
    for tx in transactions:
        status = tx.get("status", "SETTLED")
        sc = "f" if status == "FLAGGED" else "s"
        ts = tx.get("timestamp", "")
        try:
            ts_disp = datetime.fromisoformat(ts).strftime("%H:%M:%S")
        except Exception:
            ts_disp = ts[:8] if ts else "—"
        amt = float(tx.get("amount", 0))
        html += f"""
        <div class="lfy-tx {sc}">
          <span class="lfy-tx-b {sc}">{status}</span>
          <span class="lfy-tx-usr">{tx.get('user_id','—')}</span>
          <span class="lfy-tx-amt">${amt:,.2f}</span>
          <span class="lfy-tx-inf">{tx.get('merchant_type','—')} · {tx.get('location','—')}</span>
          <span class="lfy-tx-t">{ts_disp}</span>
        </div>"""
    st.markdown(html, unsafe_allow_html=True)


def render_alerts(alerts: list[dict[str, Any]]) -> None:
    st.markdown('<div class="lfy-sec">AI Forensic Alerts</div>', unsafe_allow_html=True)
    if not alerts:
        st.info("No alerts yet — waiting for the compliance worker.")
        return

    for idx, a in enumerate(alerts, 1):
        risk      = str(a.get("risk_rating", "MEDIUM")).strip()
        typology  = a.get("threat_typology", "Unknown")
        action    = a.get("enforcement_action", "—")
        narrative = a.get("narrative_rationale", "No narrative.")
        user_id   = a.get("user_id", "—")
        amt       = float(a.get("amount", 0))
        currency  = a.get("currency", "USD")
        location  = a.get("location", "—")
        tx_id     = str(a.get("transaction_id", "—"))[:14]
        audited   = str(a.get("audited_at", "—"))[:19]
        raw_ai    = a.get("raw_ai_output", "Not available.")

        rb  = _rb(risk)
        cls = _ac_cls(risk)

        card = f"""
        <div class="lfy-ac {cls}">
          <div class="lfy-ac-top">
            <span class="lfy-rb {rb}">{risk}</span>
            <span class="lfy-ac-who">{user_id} · ${amt:,.2f} {currency}</span>
          </div>
          <div class="lfy-ac-type">{typology}</div>
          <div class="lfy-ac-fields">
            <div><div class="lfy-afl">Action</div><div class="lfy-afv">{action}</div></div>
            <div><div class="lfy-afl">Location</div><div class="lfy-afv">{location}</div></div>
            <div><div class="lfy-afl">TX ID</div><div class="lfy-afv" style="font-family:'Space Mono',monospace;font-size:10px">{tx_id}…</div></div>
            <div><div class="lfy-afl">Audited</div><div class="lfy-afv">{audited}</div></div>
          </div>
          <div class="lfy-narr">"{narrative}"</div>
        </div>"""

        with st.expander(f"#{idx}  {user_id}  ·  ${amt:,.2f}  ·  {risk}  ·  {typology[:36]}", expanded=(idx == 1)):
            st.markdown(card, unsafe_allow_html=True)
            with st.expander("Full AI output", expanded=False):
                st.code(raw_ai, language=None)


def render_sidebar() -> int:
    with st.sidebar:
        st.markdown(
            '<div style="font-family:\'Space Grotesk\',sans-serif;font-weight:700;'
            'font-size:16px;letter-spacing:.08em;text-transform:uppercase;color:#fff;'
            'margin-bottom:1rem"><span style="color:#f04f5f">L</span>EDGIFY</div>',
            unsafe_allow_html=True,
        )
        st.markdown("---")
        interval = st.slider("Refresh interval (s)", 5, 60, REFRESH_S, 5)
        if st.button("Refresh now", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
        st.markdown("---")
        st.markdown(
            '<div style="font-family:\'Space Mono\',monospace;font-size:10px;'
            'color:#52526a;line-height:2.2">'
            "API&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;localhost:8000<br>"
            "Postgres&nbsp;&nbsp;localhost:5432<br>"
            "MongoDB&nbsp;&nbsp;&nbsp;localhost:27017<br>"
            "Redis&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;localhost:6379<br>"
            "Ollama&nbsp;&nbsp;&nbsp;&nbsp;localhost:11434"
            "</div>",
            unsafe_allow_html=True,
        )
    return interval


# ── Main ────────────────────────────────────────────────────────────────────

def main() -> None:
    interval     = render_sidebar()
    transactions = fetch_ledger()
    alerts       = fetch_alerts()

    render_header()
    render_metrics(transactions, alerts)

    left, right = st.columns([1, 1], gap="large")
    with left:
        render_ledger(transactions)
    with right:
        render_alerts(alerts)

    time.sleep(interval)
    st.rerun()


if __name__ == "__main__":
    main()