"""WHO-aligned, minimal/card-based visual styling for the Streamlit dashboard.

Design language: airy white canvas, soft bordered white cards, small uppercase
"eyebrow" section labels, a spacious centered header band and subtle shadows —
rendered entirely in the WHO colour palette (blue / navy / teal).

Every page calls :func:`apply_theme` once, then uses :func:`header`,
:func:`eyebrow`, :func:`section` and :func:`callout` for consistent layout.
"""

from __future__ import annotations

import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st

# --- WHO-aligned palette ---------------------------------------------------
WHO_BLUE = "#0093D5"      # WHO primary blue
WHO_DARK = "#002D72"      # WHO dark navy
WHO_TEAL = "#00A19A"
WHO_AMBER = "#F4A81D"
WHO_RED = "#E5202E"
WHO_GREEN = "#5AA700"
WHO_PURPLE = "#6A4C93"
WHO_GREY = "#6C757D"
WHO_LIGHT = "#F4F8FB"

# Minimal-design neutrals.
CANVAS = "#F6F8FA"        # page background
CARD = "#FFFFFF"          # card background
BORDER = "#E6ECF2"        # hairline borders
INK = "#1F2937"           # body text
MUTED = "#5B6B7B"         # secondary text

CATEGORICAL = [WHO_BLUE, WHO_TEAL, WHO_AMBER, WHO_RED, WHO_GREEN, WHO_PURPLE, WHO_DARK, WHO_GREY]
SEQUENTIAL_BLUE = ["#E3F2FB", "#B3DCF2", "#73BFE6", "#3AA4DC", "#0093D5", "#0067A6", "#002D72"]

FONT_FAMILY = "Lato, -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif"


def _plotly_template() -> go.layout.Template:
    return go.layout.Template(
        layout=go.Layout(
            font=dict(family=FONT_FAMILY, size=14, color=INK),
            colorway=CATEGORICAL,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            title=dict(font=dict(size=17, color=WHO_DARK), x=0.0, xanchor="left"),
            xaxis=dict(gridcolor="#EDF1F5", zerolinecolor="#EDF1F5", linecolor="#D5DEE7"),
            yaxis=dict(gridcolor="#EDF1F5", zerolinecolor="#EDF1F5", linecolor="#D5DEE7"),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
            margin=dict(l=40, r=20, t=60, b=40),
            colorscale=dict(sequential=[[i / (len(SEQUENTIAL_BLUE) - 1), c]
                                        for i, c in enumerate(SEQUENTIAL_BLUE)]),
        )
    )


_CSS = f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Lato:wght@400;700;900&display=swap');

    html, body, [class*="css"] {{ font-family: {FONT_FAMILY}; }}
    .stApp {{ background-color: {CANVAS}; }}

    /* Remove Streamlit's default top toolbar (Deploy / main menu) and footer
       so the custom navbar sits at the very top, unobstructed. */
    header[data-testid="stHeader"] {{ display: none; }}
    [data-testid="stToolbar"] {{ display: none; }}
    [data-testid="stDecoration"] {{ display: none; }}
    #MainMenu {{ visibility: hidden; }}
    footer {{ visibility: hidden; }}

    /* Full-bleed content: 5px left/right padding, hero spans full width. */
    .block-container {{
        padding-top: 1.25rem; padding-bottom: 3rem;
        padding-left: 5px; padding-right: 5px; max-width: 100%;
    }}
    p, li, span {{ color: {INK}; }}

    /* Remove the vertical sidebar page nav (replaced by the top bar). */
    [data-testid="stSidebarNav"] {{ display: none !important; }}
    div[data-testid="stSidebarNavItems"] {{ display: none !important; }}

    /* --- Custom horizontal top menu bar --- */
    .who-nav {{
        display: flex; align-items: center; justify-content: space-between;
        flex-wrap: wrap; gap: 12px;
        background: {CARD}; border: 1px solid {BORDER}; border-radius: 12px;
        padding: 16px 24px; margin-bottom: 22px; min-height: 64px;
        box-shadow: 0 1px 3px rgba(16,42,67,0.05);
    }}
    .who-nav-brand {{
        display: flex; align-items: center; gap: 10px;
        font-weight: 900; font-size: 1.15rem; color: {WHO_DARK}; letter-spacing: -0.01em;
    }}
    .who-logo {{
        display: inline-grid; grid-template-columns: repeat(2, 9px);
        grid-gap: 3px; gap: 3px;
    }}
    .who-logo i {{ width: 9px; height: 9px; border-radius: 50%; display: block; }}
    .who-logo i.d1 {{ background: {WHO_BLUE}; }}
    .who-logo i.d2 {{ background: {WHO_TEAL}; }}
    .who-logo i.d3 {{ background: {WHO_AMBER}; }}
    .who-logo i.d4 {{ background: {WHO_RED}; }}
    .who-nav-links {{ display: flex; align-items: center; gap: 2px; flex-wrap: wrap; }}
    .who-nav-links a {{
        color: #33424F; font-weight: 600; font-size: 1.0rem;
        padding: 10px 16px; border-radius: 8px; text-decoration: none;
        transition: background 0.15s ease, color 0.15s ease;
    }}
    .who-nav-links a:hover {{ background: {WHO_LIGHT}; color: {WHO_DARK}; text-decoration: none; }}
    .who-nav-links a.active {{ background: {WHO_LIGHT}; color: {WHO_DARK}; font-weight: 700; }}
    a {{ color: #0067A6; text-decoration: none; }}
    a:hover {{ color: {WHO_TEAL}; text-decoration: underline; }}

    /* --- Spacious centered header band --- */
    .who-header {{
        background: linear-gradient(120deg, {WHO_DARK} 0%, {WHO_BLUE} 100%);
        background-image:
            radial-gradient(circle, rgba(255,255,255,0.14) 1px, transparent 1.4px),
            linear-gradient(120deg, {WHO_DARK} 0%, {WHO_BLUE} 100%);
        background-size: 22px 22px, 100% 100%;
        color: white; padding: 40px 32px; border-radius: 16px;
        margin-bottom: 26px; text-align: center;
        box-shadow: 0 6px 22px rgba(0,45,114,0.18);
    }}
    .who-header .eyebrow {{ color: #Bfe3F6; letter-spacing: 0.14em; }}
    .who-header h1 {{ color: white; font-size: 2.0rem; margin: 6px 0 0 0; font-weight: 900; }}
    .who-header p {{ color: #E3F2FB; margin: 8px 0 0 0; font-size: 1.02rem; }}

    /* --- Eyebrow section label --- */
    .who-eyebrow {{
        text-transform: uppercase; letter-spacing: 0.1em; font-size: 0.78rem;
        font-weight: 700; color: {WHO_TEAL}; margin: 6px 0 2px 0;
    }}

    h2, h3 {{ color: {WHO_DARK}; font-weight: 700; }}
    h2 {{ font-size: 1.45rem; }}
    h3 {{ font-size: 1.18rem; }}

    /* --- Cards: charts, tables and metrics --- */
    div[data-testid="stPlotlyChart"],
    div[data-testid="stDataFrame"] {{
        background: {CARD}; border: 1px solid {BORDER}; border-radius: 14px;
        padding: 10px 12px; box-shadow: 0 1px 3px rgba(16,42,67,0.05);
    }}
    div[data-testid="stMetric"] {{
        background: {CARD}; border: 1px solid {BORDER}; border-left: 4px solid {WHO_BLUE};
        border-radius: 14px; padding: 16px 18px; box-shadow: 0 1px 3px rgba(16,42,67,0.05);
    }}
    div[data-testid="stMetricLabel"] {{ color: {MUTED}; font-weight: 600; }}
    div[data-testid="stMetricValue"] {{ color: {WHO_DARK}; }}

    /* --- Callout boxes --- */
    .who-callout {{
        background: {CARD}; border: 1px solid {BORDER}; border-left: 5px solid {WHO_BLUE};
        border-radius: 12px; padding: 14px 18px; margin: 6px 0 18px 0;
        box-shadow: 0 1px 3px rgba(16,42,67,0.05); color: {INK};
    }}
    .who-callout.warning {{ background: #FEF7E6; border-left-color: {WHO_AMBER}; }}
    .who-callout.warning b {{ color: #7a5b00; }}

    hr {{ border-color: {BORDER}; }}
    .stDivider {{ border-color: {BORDER}; }}

    /* Margin-constrained content containers (Data Quality / Data Lineage) */
    .st-key-dq_content, .st-key-lineage_content {{
        margin-left: 5px; margin-right: 5px;
        max-width: calc(100% - 10px); overflow-x: auto;
    }}

    /* --- Clean light sidebar (minimal) --- */
    section[data-testid="stSidebar"] {{
        background-color: {CARD}; border-right: 1px solid {BORDER};
    }}
    section[data-testid="stSidebar"] h1,
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3,
    section[data-testid="stSidebar"] label,
    section[data-testid="stSidebar"] [data-testid="stWidgetLabel"] * {{
        color: {WHO_DARK} !important;
    }}
    /* Active page in the nav -> soft WHO-blue pill */
    section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a {{
        border-radius: 8px; color: {INK};
    }}
    section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a[aria-current="page"] {{
        background-color: {WHO_LIGHT}; color: {WHO_DARK}; font-weight: 700;
    }}
</style>
"""


# Horizontal top-menu pages: (URL slug, label). Slugs follow Streamlit's
# multipage URL scheme (Home is served at "/").
NAV_PAGES = [
    ("/", "Overview"),
    ("/Surveillance", "Surveillance"),
    ("/Demographics", "Demographics"),
    ("/Clinical", "Clinical"),
    ("/Spatial_Analysis", "Spatial Analysis"),
    ("/Data_Quality", "Data Quality"),
    ("/Data_Lineage", "Data Lineage"),
]

BRAND = "Chikungunya Surveillance"


def apply_theme() -> None:
    """Register the Plotly template and inject WHO CSS. Call once per page."""
    pio.templates["who"] = _plotly_template()
    pio.templates.default = "plotly_white+who"
    st.markdown(_CSS, unsafe_allow_html=True)


def top_nav(active: str = "") -> None:
    """Render the clean horizontal top menu bar (custom HTML).

    Pass the current page's label as ``active`` to highlight it.
    """
    links = "".join(
        f'<a href="{url}" target="_self" class="{"active" if label == active else ""}">{label}</a>'
        for url, label in NAV_PAGES
    )
    logo = '<span class="who-logo"><i class="d1"></i><i class="d2"></i>' \
           '<i class="d3"></i><i class="d4"></i></span>'
    html = (
        f'<div class="who-nav">'
        f'<div class="who-nav-brand">{logo}{BRAND}</div>'
        f'<nav class="who-nav-links">{links}</nav>'
        f'</div>'
    )
    st.markdown(html, unsafe_allow_html=True)


def header(title: str, subtitle: str | None = None, eyebrow: str | None = None) -> None:
    """Render the spacious, centered WHO header band."""
    eb = f'<div class="eyebrow who-eyebrow">{eyebrow}</div>' if eyebrow else ""
    sub = f"<p>{subtitle}</p>" if subtitle else ""
    st.markdown(
        f'<div class="who-header">{eb}<h1>{title}</h1>{sub}</div>', unsafe_allow_html=True
    )


def eyebrow(text: str) -> None:
    """Render a small uppercase section eyebrow label."""
    st.markdown(f'<div class="who-eyebrow">{text}</div>', unsafe_allow_html=True)


def section(title: str, eyebrow_text: str | None = None) -> None:
    """Render an eyebrow label followed by a section heading."""
    if eyebrow_text:
        eyebrow(eyebrow_text)
    st.markdown(f"### {title}")


def callout(text: str, kind: str = "info") -> None:
    """Render an info ('info') or warning ('warning') callout box."""
    cls = "who-callout warning" if kind == "warning" else "who-callout"
    st.markdown(f'<div class="{cls}">{text}</div>', unsafe_allow_html=True)


def style_fig(fig: go.Figure, height: int = 420) -> go.Figure:
    fig.update_layout(template="plotly_white+who", height=height)
    return fig


def notes(what: str, accurate: str,
          label: str = "ℹ️ Notes & data requirements") -> None:
    """Collapsible explanatory note placed under a chart.

    ``what`` describes the analytic; ``accurate`` states what is required to keep
    it correct as new data arrives.
    """
    with st.expander(label):
        st.markdown(f"**What it shows:** {what}")
        st.markdown(f"**Keeping it accurate with new data:** {accurate}")
