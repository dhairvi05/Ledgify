"""
backend/dashboard.py — Ledgify v6
-----------------------------------
Simplified, responsive layout.

  - Header is a normal (non-fixed, non-sticky) flex bar at the top of the
    page, with flex-wrap so it never overlaps on narrow viewports.
  - Wordmark "LEDGIFY" uses weight contrast only (LED = light/dim,
    GIFY = bold/white) — no colour.
  - Numbers use Space Mono everywhere (slashed zero -> 0 never reads as O).
  - Auto-refresh via st.cache_data TTL + a lightweight st.rerun() loop,
    but WITHOUT a blocking time.sleep before render — instead a tiny
    meta-refresh handles the page reload so layout never "jumps" mid-paint.

Run with:
    streamlit run backend/dashboard.py
"""

from datetime import datetime
from typing import Any

import requests
import streamlit as st

API_BASE_URL    = "http://localhost:8000"
LEDGER_ENDPOINT = f"{API_BASE_URL}/api/ledger"
ALERTS_ENDPOINT = f"{API_BASE_URL}/api/alerts"
REFRESH_S       = 10

st.set_page_config(
    page_title="Ledgify",
    page_icon="🔲",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Global styles ────────────────────────────────────────────────────────────
st.markdown("""
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;700&family=Space+Mono:wght@400;700&display=swap" rel="stylesheet">

<style>
html, body, [class*="css"] {
  background-color: #0a0a0c !important;
  color: #eeedf2;
  font-family: 'Space Grotesk', sans-serif;
}
.block-container { padding-top: 1.5rem !important; padding-bottom: 2rem !important; max-width: 100% !important; }
header[data-testid="stHeader"] { background: transparent !important; }
section[data-testid="stSidebar"] { background: #111115 !important; }

/* ── Header — normal flow, wraps on narrow screens ── */
.lfy-header {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding-bottom: 14px;
  margin-bottom: 14px;
  border-bottom: 0.5px solid rgba(255,255,255,0.08);
}
.lfy-header-left {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 14px;
  min-width: 0;
}
.lfy-wm {
  font-family: 'Space Grotesk', sans-serif;
  font-size: clamp(18px, 2.4vw, 26px);
  letter-spacing: 0.12em;
  text-transform: uppercase;
  line-height: 1;
  white-space: nowrap;
}
.lfy-wm .thin { font-weight: 300; color: rgba(255,255,255,0.38); }
.lfy-wm .bold { font-weight: 700; color: #ffffff; }
.lfy-subt {
  font-family: 'Space Mono', monospace;
  font-size: 10px;
  letter-spacing: 0.2em;
  text-transform: uppercase;
  color: #52526a;
  white-space: nowrap;
}
.lfy-header-right {
  display: flex;
  align-items: center;
  gap: 16px;
  flex-shrink: 0;
}
.lfy-live {
  display: flex; align-items: center; gap: 6px;
  font-family: 'Space Mono', monospace; font-size: 11px; color: #2dce89;
  white-space: nowrap;
}
.lfy-ldot { width: 6px; height: 6px; border-radius: 50%; background: #2dce89; animation: lblink 2s infinite; }
@keyframes lblink { 0%,100%{opacity:1} 50%{opacity:.2} }
.lfy-clock { font-family: 'Space Mono', monospace; font-size: 11px; color: #52526a; white-space: nowrap; }

/* ── Metric bar ── */
.lfy-mbar {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  background: #111115;
  border: 0.5px solid rgba(255,255,255,0.06);
  border-radius: 10px;
  overflow: hidden;
  margin-bottom: 18px;
}
.lfy-mc { padding: 14px 20px; border-right: 0.5px solid rgba(255,255,255,0.06); }
.lfy-mc:last-child { border-right: none; }
.lfy-mc-l { font-family: 'Space Mono', monospace; font-size: 9px; letter-spacing: .14em; text-transform: uppercase; color: #52526a; margin-bottom: 6px; }
.lfy-mc-v { font-family: 'Space Mono', monospace; font-weight: 700; font-size: 24px; line-height: 1; color: #eeedf2; }
.lfy-mc-v.r { color: #f04f5f; }
.lfy-mc-v.g { color: #2dce89; }
.lfy-mc-s { font-family: 'Space Mono', monospace; font-size: 9px; color: #2a2a38; margin-top: 4px; }

/* ── Section label ── */
.lfy-sec {
  font-family: 'Space Mono', monospace; font-size: 9px; letter-spacing: .18em;
  text-transform: uppercase; color: #52526a;
  display: flex; align-items: center; gap: 8px; margin-bottom: 10px;
}
.lfy-sec::after { content: ''; flex: 1; height: 0.5px; background: rgba(255,255,255,0.06); }

/* ── TX rows ── */
.lfy-tx { display: flex; align-items: center; gap: 8px; padding: 7px 10px; border-radius: 6px; margin-bottom: 4px; font-size: 12px; flex-wrap: wrap; }
.lfy-tx.s { background:rgba(45,206,137,.07); border:0.5px solid rgba(45,206,137,.17); }
.lfy-tx.f { background:rgba(240,79,95,.08);  border:0.5px solid rgba(240,79,95,.2);   }
.lfy-tb { font-family: 'Space Mono', monospace; font-size: 9px; letter-spacing: .04em; padding: 2px 7px; border-radius: 3px; flex-shrink: 0; }
.lfy-tb.s { color:#2dce89; background:rgba(45,206,137,.1); border:0.5px solid rgba(45,206,137,.2); }
.lfy-tb.f { color:#f04f5f; background:rgba(240,79,95,.1);  border:0.5px solid rgba(240,79,95,.22); }
.lfy-tu { font-weight:500; color:#eeedf2; min-width:76px; }
.lfy-ta { font-family:'Space Mono',monospace; font-size:12px; min-width:82px; text-align:right; color:#eeedf2; }
.lfy-ti { color:#52526a; font-size:11px; flex:1; min-width:120px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.lfy-tt { font-family:'Space Mono',monospace; font-size:10px; color:#2a2a38; flex-shrink:0; }

/* ── Alert cards ── */
.lfy-ac { background: #16161c; border: 0.5px solid rgba(255,255,255,0.06); border-radius: 0 8px 8px 0; padding: 10px 12px; margin-bottom: 7px; border-left: 2px solid transparent; }
.lfy-ac.cr { border-left-color: #f04f5f; }
.lfy-ac.hi { border-left-color: #f97316; }
.lfy-ac.md { border-left-color: #facc15; }
.lfy-at { display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:6px; margin-bottom:5px; }
.lfy-rb { font-family:'Space Mono',monospace; font-size:9px; letter-spacing:.05em; padding:2px 8px; border-radius:3px; }
.rc { color:#f04f5f; background:rgba(240,79,95,.1);  border:0.5px solid rgba(240,79,95,.22); }
.rh { color:#f97316; background:rgba(249,115,22,.1); border:0.5px solid rgba(249,115,22,.28); }
.rm { color:#facc15; background:rgba(250,204,21,.08);border:0.5px solid rgba(250,204,21,.25); }
.lfy-aw  { font-family:'Space Mono',monospace; font-size:10px; color:#52526a; }
.lfy-atp { font-size:12px; font-weight:500; color:#eeedf2; margin-bottom:6px; }
.lfy-af  { display:flex; gap:14px; flex-wrap:wrap; border-top:0.5px solid rgba(255,255,255,0.05); padding-top:7px; margin-top:2px; }
.lfy-afl { font-family:'Space Mono',monospace; font-size:9px; letter-spacing:.1em; text-transform:uppercase; color:#52526a; margin-bottom:2px; }
.lfy-afv { font-size:11px; color:#ccd0f0; }
.lfy-an  { font-family:'Space Mono',monospace; font-size:10px; line-height:1.65; color:#2a2a38; font-style:italic; margin-top:6px; }
</style>
""", unsafe_allow_html=True)


# ── Data fetchers ─────────────────────────────────────────────────────────────

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


# ── Render helpers ─────────────────────────────────────────────────────────────

def _rb_cls(risk: str) -> str:
    r = risk.upper()
    if "CRITICAL" in r: return "rc"
    if "HIGH"     in r: return "rh"
    return "rm"

def _ac_cls(risk: str) -> str:
    r = risk.upper()
    if "CRITICAL" in r: return "cr"
    if "HIGH"     in r: return "hi"
    return "md"


def render_header() -> None:
    now = datetime.utcnow().strftime("%H:%M:%S UTC")
    st.markdown(f"""
    <div class="lfy-header">
      <div class="lfy-header-left">
        <div class="lfy-wm"><span class="thin">LED</span><span class="bold">GIFY</span></div>
        <div class="lfy-subt">Financial Fraud Monitor</div>
      </div>
      <div class="lfy-header-right">
        <div class="lfy-live"><span class="lfy-ldot"></span>Pipeline live</div>
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
    <div class="lfy-mbar">
      <div class="lfy-mc">
        <div class="lfy-mc-l">Transactions</div>
        <div class="lfy-mc-v">{total:02d}</div>
        <div class="lfy-mc-s">latest window</div>
      </div>
      <div class="lfy-mc">
        <div class="lfy-mc-l">Settled</div>
        <div class="lfy-mc-v g">{settled:02d}</div>
        <div class="lfy-mc-s">{pct}</div>
      </div>
      <div class="lfy-mc">
        <div class="lfy-mc-l">Flagged</div>
        <div class="lfy-mc-v r">{flagged:02d}</div>
        <div class="lfy-mc-s">routed to AI</div>
      </div>
      <div class="lfy-mc">
        <div class="lfy-mc-l">AI Alerts</div>
        <div class="lfy-mc-v r">{len(alerts):02d}</div>
        <div class="lfy-mc-s">forensic logs</div>
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
        sc     = "f" if status == "FLAGGED" else "s"
        ts     = tx.get("timestamp", "")
        try:
            ts_d = datetime.fromisoformat(ts).strftime("%H:%M:%S")
        except Exception:
            ts_d = ts[:8] if ts else "—"
        amt = float(tx.get("amount", 0))
        html += (
            f'<div class="lfy-tx {sc}">'
            f'<span class="lfy-tb {sc}">{status}</span>'
            f'<span class="lfy-tu">{tx.get("user_id","—")}</span>'
            f'<span class="lfy-ta">${amt:,.2f}</span>'
            f'<span class="lfy-ti">{tx.get("merchant_type","—")} · {tx.get("location","—")}</span>'
            f'<span class="lfy-tt">{ts_d}</span>'
            f'</div>'
        )
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

        card = (
            f'<div class="lfy-ac {_ac_cls(risk)}">'
            f'<div class="lfy-at">'
            f'<span class="lfy-rb {_rb_cls(risk)}">{risk}</span>'
            f'<span class="lfy-aw">{user_id} · ${amt:,.2f} {currency}</span>'
            f'</div>'
            f'<div class="lfy-atp">{typology}</div>'
            f'<div class="lfy-af">'
            f'<div><div class="lfy-afl">Action</div><div class="lfy-afv">{action}</div></div>'
            f'<div><div class="lfy-afl">Location</div><div class="lfy-afv">{location}</div></div>'
            f'<div><div class="lfy-afl">TX ID</div>'
            f'<div class="lfy-afv" style="font-family:\'Space Mono\',monospace;font-size:10px">{tx_id}…</div></div>'
            f'<div><div class="lfy-afl">Audited</div><div class="lfy-afv">{audited}</div></div>'
            f'</div>'
            f'<div class="lfy-an">"{narrative}"</div>'
            f'</div>'
        )

        with st.expander(
            f"#{idx}  {user_id}  ·  ${amt:,.2f}  ·  {risk}  ·  {typology[:36]}",
            expanded=(idx == 1),
        ):
            st.markdown(card, unsafe_allow_html=True)
            with st.expander("Full AI output", expanded=False):
                st.code(raw_ai, language=None)


def render_sidebar() -> None:
    with st.sidebar:
        st.markdown(
            '<div style="font-family:\'Space Grotesk\',sans-serif;font-size:15px;'
            'letter-spacing:.12em;text-transform:uppercase;color:#fff;margin-bottom:1rem">'
            '<span style="font-weight:300;color:rgba(255,255,255,.38)">LED</span>'
            '<span style="font-weight:700">GIFY</span></div>',
            unsafe_allow_html=True,
        )
        st.markdown("---")
        st.caption(f"Auto-refreshes every {REFRESH_S}s")
        if st.button("Refresh now", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
        st.markdown("---")
        st.markdown(
            '<div style="font-family:\'Space Mono\',monospace;font-size:10px;'
            'color:#52526a;line-height:2.2">'
            "API&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;localhost:8000<br>"
            "Postgres&nbsp;&nbsp;localhost:5432<br>"
            "MongoDB&nbsp;&nbsp;localhost:27017<br>"
            "Redis&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;localhost:6379<br>"
            "Ollama&nbsp;&nbsp;&nbsp;&nbsp;localhost:11434"
            "</div>",
            unsafe_allow_html=True,
        )


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    render_sidebar()
    transactions = fetch_ledger()
    alerts       = fetch_alerts()

    render_header()
    render_metrics(transactions, alerts)

    left, right = st.columns([1, 1], gap="large")
    with left:
        render_ledger(transactions)
    with right:
        render_alerts(alerts)

    # Browser-level periodic reload — simple, predictable, no scroll-jank
    # from mid-render st.rerun() calls.
    st.markdown(
        f'<meta http-equiv="refresh" content="{REFRESH_S}">',
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()