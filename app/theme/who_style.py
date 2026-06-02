"""WHO-aligned visual styling for the Streamlit dashboard.

Provides a colour palette, a Plotly template and an ``apply_theme`` helper that
every page calls once to inject CSS and register the chart template.
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

CATEGORICAL = [WHO_BLUE, WHO_TEAL, WHO_AMBER, WHO_RED, WHO_GREEN, WHO_PURPLE, WHO_DARK, WHO_GREY]
SEQUENTIAL_BLUE = ["#E3F2FB", "#B3DCF2", "#73BFE6", "#3AA4DC", "#0093D5", "#0067A6", "#002D72"]

FONT_FAMILY = "Lato, Arial, Helvetica, sans-serif"


def _plotly_template() -> go.layout.Template:
    return go.layout.Template(
        layout=go.Layout(
            font=dict(family=FONT_FAMILY, size=14, color="#1f2937"),
            colorway=CATEGORICAL,
            paper_bgcolor="white",
            plot_bgcolor="white",
            title=dict(font=dict(size=18, color=WHO_DARK), x=0.0, xanchor="left"),
            xaxis=dict(gridcolor="#E9EEF3", zerolinecolor="#E9EEF3", linecolor="#CBD5E1"),
            yaxis=dict(gridcolor="#E9EEF3", zerolinecolor="#E9EEF3", linecolor="#CBD5E1"),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
            margin=dict(l=40, r=20, t=60, b=40),
            colorscale=dict(sequential=[[i / (len(SEQUENTIAL_BLUE) - 1), c]
                                        for i, c in enumerate(SEQUENTIAL_BLUE)]),
        )
    )


_CSS = f"""
<style>
    html, body, [class*="css"] {{ font-family: {FONT_FAMILY}; }}
    .block-container {{ padding-top: 1.5rem; max-width: 1300px; }}
    /* WHO header band */
    .who-header {{
        background: linear-gradient(90deg, {WHO_DARK} 0%, {WHO_BLUE} 100%);
        color: white; padding: 18px 26px; border-radius: 10px;
        margin-bottom: 22px; box-shadow: 0 2px 8px rgba(0,0,0,0.08);
    }}
    .who-header h1 {{ color: white; font-size: 1.6rem; margin: 0; font-weight: 700; }}
    .who-header p {{ color: #E3F2FB; margin: 4px 0 0 0; font-size: 0.95rem; }}
    /* KPI cards */
    div[data-testid="stMetric"] {{
        background: white; border: 1px solid #E3EAF1; border-left: 5px solid {WHO_BLUE};
        border-radius: 10px; padding: 14px 18px; box-shadow: 0 1px 4px rgba(0,0,0,0.05);
    }}
    div[data-testid="stMetricLabel"] {{ color: {WHO_GREY}; font-weight: 600; }}
    div[data-testid="stMetricValue"] {{ color: {WHO_DARK}; }}
    h2, h3 {{ color: {WHO_DARK}; }}

    /* --- Dark sidebar with light text --- */
    section[data-testid="stSidebar"] {{ background-color: {WHO_DARK}; }}
    /* Labels, headings, captions, nav links, markdown -> light */
    section[data-testid="stSidebar"] label,
    section[data-testid="stSidebar"] h1,
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3,
    section[data-testid="stSidebar"] p,
    section[data-testid="stSidebar"] [data-testid="stWidgetLabel"],
    section[data-testid="stSidebar"] [data-testid="stWidgetLabel"] *,
    section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a,
    section[data-testid="stSidebar"] [data-testid="stSidebarNav"] span,
    section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"],
    section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] * {{
        color: #E3F2FB !important;
    }}
    /* Keep input controls (multiselect, date) readable: dark text on light field */
    section[data-testid="stSidebar"] [data-baseweb="select"],
    section[data-testid="stSidebar"] [data-baseweb="input"] {{
        background-color: #FFFFFF;
    }}
    section[data-testid="stSidebar"] [data-baseweb="select"] *,
    section[data-testid="stSidebar"] [data-baseweb="input"] input {{
        color: {WHO_DARK} !important;
    }}
</style>
"""


def apply_theme() -> None:
    """Register the Plotly template and inject WHO CSS. Call once per page."""
    pio.templates["who"] = _plotly_template()
    pio.templates.default = "plotly_white+who"
    st.markdown(_CSS, unsafe_allow_html=True)


def header(title: str, subtitle: str | None = None) -> None:
    """Render the WHO header band."""
    sub = f"<p>{subtitle}</p>" if subtitle else ""
    st.markdown(
        f'<div class="who-header"><h1>{title}</h1>{sub}</div>', unsafe_allow_html=True
    )


def style_fig(fig: go.Figure, height: int = 420) -> go.Figure:
    fig.update_layout(template="plotly_white+who", height=height)
    return fig
