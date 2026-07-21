"""Shared visual identity for both Streamlit apps: an "official document"
look befitting an assistant for Polish bureaucracy -- a navy letterhead,
paper document cards, and ink-stamp verdicts. Colors mirror
.streamlit/config.toml (which handles the Streamlit-native widget theming);
this module handles the bespoke bits config.toml can't reach: fonts, the
letterhead band, and the stamp badge.
"""
import streamlit as st

NAVY = "#17324F"
PAPER = "#FFFDF8"
STAMP_RED = "#A6362A"
SEAL_GOLD = "#C9A24A"
INK = "#2A2620"

STAMP_STYLES = {
    "RELEVANT": ("VERIFIED", "#2F6B4F"),
    "PARTLY_RELEVANT": ("PARTIAL", SEAL_GOLD),
    "NON_RELEVANT": ("REJECTED", STAMP_RED),
}

_CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,600;0,9..144,700;1,9..144,600&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500;600&display=swap');

html, body, [class*="css"] {{ font-family: 'IBM Plex Sans', sans-serif; }}

.stApp {{
  background:
    radial-gradient(circle at 100% 0%, rgba(201,162,74,0.10), transparent 45%),
    #F4EFE1;
}}

/* -- Letterhead -- */
.jdg-letterhead {{
  background: {NAVY};
  padding: 1.6rem 2rem 1.35rem;
  border-radius: 0.6rem;
  margin-bottom: 1.6rem;
  border-bottom: 3px double {SEAL_GOLD};
}}
.jdg-eyebrow {{
  font-family: 'IBM Plex Mono', monospace;
  font-size: 0.68rem;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: {SEAL_GOLD};
  margin: 0 0 0.4rem 0;
}}
.jdg-letterhead h1 {{
  font-family: 'Fraunces', serif;
  font-weight: 700;
  font-size: 2.05rem;
  letter-spacing: 0.01em;
  color: #FBF6E9;
  margin: 0 0 0.4rem 0;
  line-height: 1.15;
}}
.jdg-letterhead p {{
  color: #D8CBAE;
  margin: 0;
  font-size: 0.95rem;
  max-width: 46rem;
}}

/* -- Form-field style labels: language / strategy selectors read like
   coded fields on an official form -- */
.stSelectbox label p, .stTextInput label p {{
  font-family: 'IBM Plex Mono', monospace !important;
  font-size: 0.7rem !important;
  letter-spacing: 0.1em !important;
  text-transform: uppercase;
  color: #6B5E45 !important;
}}

/* -- Buttons: stamped outline, lift on hover -- */
.stButton > button {{
  font-family: 'IBM Plex Mono', monospace;
  font-weight: 600;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  font-size: 0.78rem;
  border: 2px solid {NAVY};
  border-radius: 0.35rem;
  transition: transform 0.12s ease, box-shadow 0.12s ease;
}}
.stButton > button:hover {{
  transform: translateY(-1px);
  box-shadow: 0 3px 0 rgba(23,50,79,0.15);
}}
.stButton > button:active {{ transform: translateY(0); box-shadow: none; }}
.stButton > button[kind="primary"] {{ border-color: {STAMP_RED}; }}

/* -- Ledger-style budget bar -- */
.jdg-ledger-label {{
  font-family: 'IBM Plex Mono', monospace;
  font-size: 0.72rem;
  letter-spacing: 0.06em;
  color: #6B5E45;
  text-transform: uppercase;
  margin-bottom: 0.15rem;
}}

/* -- Document card wrapper for the answer -- */
.st-key-jdg-answer-card {{
  background: {PAPER};
  border: 1px solid #E4D9BC;
  border-radius: 0.5rem;
  padding: 1.4rem 1.6rem 1.1rem;
  box-shadow: 0 1px 3px rgba(23,50,79,0.08);
}}

/* -- Stamp verdict badge -- */
.jdg-verdict {{
  display: flex;
  align-items: center;
  gap: 1.1rem;
  margin-top: 0.9rem;
  padding-top: 0.9rem;
  border-top: 1px dashed #D8C89A;
}}
.jdg-stamp {{
  flex: 0 0 auto;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  width: 82px;
  height: 82px;
  border-radius: 50%;
  border: 2.5px solid currentColor;
  transform: rotate(-8deg);
  font-family: 'IBM Plex Mono', monospace;
  text-transform: uppercase;
  font-size: 0.62rem;
  font-weight: 600;
  letter-spacing: 0.05em;
  text-align: center;
  position: relative;
}}
.jdg-stamp::before {{
  content: "";
  position: absolute;
  inset: 6px;
  border: 1px dashed currentColor;
  border-radius: 50%;
  opacity: 0.55;
}}
.jdg-verdict-text {{ font-size: 0.92rem; color: {INK}; }}
.jdg-verdict-text b {{ font-family: 'IBM Plex Mono', monospace; letter-spacing: 0.03em; }}
</style>
"""


def inject_theme():
    st.markdown(_CSS, unsafe_allow_html=True)


def render_letterhead(title, subtitle, eyebrow="JDG · sole proprietorship in Poland"):
    st.markdown(
        f"""
        <div class="jdg-letterhead">
          <p class="jdg-eyebrow">{eyebrow}</p>
          <h1>{title}</h1>
          <p>{subtitle}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_verdict_stamp(relevance, explanation):
    """Render the LLM-judge relevance verdict as an ink-stamp badge instead
    of plain text -- a literal stamp of approval, fitting for an assistant
    about bureaucratic paperwork, and still showing the real judge data."""
    label, color = STAMP_STYLES.get(relevance, ("REVIEWED", SEAL_GOLD))
    st.markdown(
        f"""
        <div class="jdg-verdict">
          <div class="jdg-stamp" style="color:{color}"><span>{label}</span></div>
          <div class="jdg-verdict-text"><b>Judge verdict: {relevance}</b><br>{explanation}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
