"""Surveillance: regional summary, epidemic curve and cumulative incidence."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from data_access import (
    AGE_GROUP_POPULATION,
    DISTRICT_POPULATION,
    REGION_TO_DISTRICT,
    apply_filters,
    load_cases,
    parse_epi_week,
)
from filters import sidebar_filters
from components import case_forecast_section, rolling_case_panel
from theme import who_style as who

st.set_page_config(page_title="Surveillance", page_icon="📈", layout="wide")
who.apply_theme()
who.top_nav(active="Surveillance")
who.header("Surveillance", "Regional case summary, epidemic curve and cumulative incidence",
           eyebrow="Surveillance")

df = load_cases()
fdf = apply_filters(df, sidebar_filters(df))

# --- Regional surveillance summary -----------------------------------------
who.section("Regional summary", "Cases and attack rate by region")
if {"health_region", "case_classification"} <= set(fdf.columns):
    CLS = ["Suspected", "Confirmed", "Probable", "Unclassified"]
    work = fdf.copy()
    work["District"] = work["health_region"].map(REGION_TO_DISTRICT)
    work = work.dropna(subset=["District"])
    work["case_classification"] = work["case_classification"].fillna("Unclassified")
    tbl = (pd.crosstab(work["District"], work["case_classification"])
           .reindex(index=list(DISTRICT_POPULATION), columns=CLS, fill_value=0)
           .fillna(0).astype(int))
    tbl["Total"] = tbl[CLS].sum(axis=1)
    tbl["Population"] = pd.Series(DISTRICT_POPULATION)
    tbl["Attack Rate /100k"] = (tbl["Total"] / tbl["Population"] * 100_000).round(1)
    tbl = tbl.sort_values("Total", ascending=False)
    tbl.index = [d.title() for d in tbl.index]
    # Total row across all regions.
    total = tbl[CLS + ["Total", "Population"]].sum()
    total["Attack Rate /100k"] = round(total["Total"] / total["Population"] * 100_000, 1)
    tbl.loc["Total"] = total
    POP_COL = "Population²⁰²⁰"  # "Population" + superscript 2020
    summary = tbl.reset_index().rename(columns={"index": "Region",
                                                "Suspected": "Suspected Cases",
                                                "Population": POP_COL})
    int_cols = ["Suspected Cases", "Confirmed", "Probable", "Unclassified",
                "Total", POP_COL]
    fmt = {c: "{:,.0f}" for c in int_cols}
    fmt["Attack Rate /100k"] = "{:,.1f}"
    st.dataframe(summary.style.format(fmt), hide_index=True, use_container_width=True)
    st.caption(
        "Cases by health region (mapped to district) with district population "
        "denominators (2020 figures). Attack rate = total cases per 100,000 residents.")
    who.notes(
        "Per-region case counts split by WHO/PAHO classification (Suspected, "
        "Confirmed, Probable, Unclassified) with the cumulative attack rate — "
        "total cases per 100,000 residents using district population denominators.",
        "Requires `health_region` to be populated and mapped to a district "
        "(Regions 1–8 → districts; only Regions 1–5 appear in the data so far, "
        "the rest show 0). Attack rates use **2020** population figures — update "
        "`DISTRICT_POPULATION` in `data_access.py` when newer census/projections "
        "are available. Counts depend on the derived `case_classification`.")
else:
    st.info("Region or classification data not available for the current filter.")

st.divider()

# --- Rolling case windows (24h / 3d / 7d) ----------------------------------
who.section("Rolling case windows", "Recent activity")
rolling_case_panel(fdf, show_chart=True, key="surv_roll")

st.divider()

freq_label = st.radio("Time resolution", ["Weekly", "Daily"], horizontal=True)
rule = "W" if freq_label == "Weekly" else "D"

col = st.selectbox(
    "Date basis",
    [c for c in ["date_of_onset_symptoms", "date_of_notification", "date_of_sample_taken"] if c in fdf],
    format_func=lambda c: c.replace("_", " ").title(),
)

series = fdf.dropna(subset=[col])
if series.empty:
    st.info("No dated cases for the current filter.")
    st.stop()

curve = (
    series.assign(bucket=lambda d: d[col].dt.to_period(rule).dt.start_time)
    .groupby("bucket")
    .size()
    .reset_index(name="cases")
    .sort_values("bucket")
)
curve["cumulative"] = curve["cases"].cumsum()

fig = px.bar(curve, x="bucket", y="cases", labels={"bucket": "Date", "cases": "Cases"},
             title=f"Cases by {freq_label.lower()} {col.replace('_', ' ')}")
fig.update_traces(marker_color=who.WHO_BLUE)
st.plotly_chart(who.style_fig(fig), use_container_width=True)
who.notes(
    "Epidemic curve — case counts bucketed by the selected date basis (onset / "
    "notification / sample) at weekly or daily resolution.",
    "Requires the chosen date field to be populated and parseable; the pipeline "
    "normalises all dates to ISO 8601, so consistent source date entry matters. "
    "Cases with a missing/unparseable date in that field drop out of the curve. "
    "Onset date best reflects true epidemic timing but is the most often blank.")

fig2 = px.area(curve, x="bucket", y="cumulative", labels={"bucket": "Date", "cumulative": "Cumulative cases"},
               title="Cumulative incidence")
fig2.update_traces(line_color=who.WHO_DARK, fillcolor="rgba(0,147,213,0.2)")
st.plotly_chart(who.style_fig(fig2), use_container_width=True)
who.notes(
    "Running cumulative total of cases over time on the selected date basis.",
    "Same date-completeness dependency as the curve above; because it accumulates, "
    "missing or late-entered dates flatten or shift the line. Re-running the "
    "pipeline after dates are back-filled will revise it.")

st.divider()

# --- Case-progression forecast ---------------------------------------------
who.section("Case-progression forecast", "Next 3 months")
horizon = st.slider("Forecast horizon (weeks)", min_value=6, max_value=20,
                    value=13, key="fc_horizon")
case_forecast_section(fdf, horizon_weeks=horizon, key="surv_fc")

st.divider()

# --- Cumulative confirmed cases by epi week --------------------------------
if {"epi_week", "case_classification"} <= set(fdf.columns):
    all_wk = fdf["epi_week"].map(parse_epi_week).dropna().astype(int)
    conf_wk = (fdf.loc[fdf["case_classification"] == "Confirmed", "epi_week"]
               .map(parse_epi_week).dropna().astype(int))
    if not all_wk.empty:
        # Continuous week range so the cumulative line stays flat across weeks
        # with no confirmed cases rather than dropping out.
        full = range(int(all_wk.min()), int(all_wk.max()) + 1)
        weekly = conf_wk.value_counts().reindex(full, fill_value=0).sort_index()
        cum = pd.DataFrame({"epi_week": list(weekly.index),
                            "confirmed": weekly.to_numpy()})
        cum["cumulative"] = cum["confirmed"].cumsum()
        fig3 = px.line(
            cum, x="epi_week", y="cumulative", markers=True,
            labels={"epi_week": "Epi week", "cumulative": "Cumulative confirmed cases"},
            title="Cumulative confirmed cases by epi week",
        )
        fig3.update_traces(line_color=who.WHO_RED, marker_color=who.WHO_RED)
        fig3.update_xaxes(dtick=1)
        st.plotly_chart(who.style_fig(fig3), use_container_width=True)
        st.caption(
            f"{int(cum['cumulative'].iloc[-1]):,} confirmed cases accumulated "
            f"across epi weeks {int(all_wk.min())}–{int(all_wk.max())}.")
        who.notes(
            "Running total of confirmed cases by epidemiological week.",
            "Requires `epi_week` populated and `case_classification = Confirmed`, "
            "which the pipeline derives from PCR result + epi-linkage + clinical "
            "symptoms. Weeks with no data are held flat (not zeroed). The line "
            "rises as pending PCR results are entered and reclassify suspected "
            "cases to confirmed, so late data revises earlier weeks.")

# --- Cumulative attack rate by district over epi weeks ---------------------
if {"epi_week", "health_region"} <= set(fdf.columns):
    ar_basis = st.radio("Attack rate basis", ["All reported cases", "Confirmed only"],
                        horizontal=True, key="ar_basis")
    base = (fdf if ar_basis == "All reported cases"
            else fdf[fdf.get("case_classification") == "Confirmed"]).copy()
    base["wk"] = base["epi_week"].map(parse_epi_week)
    base["district"] = base["health_region"].map(REGION_TO_DISTRICT)
    base = base.dropna(subset=["wk", "district"])
    all_weeks = fdf["epi_week"].map(parse_epi_week).dropna().astype(int)
    if not base.empty and not all_weeks.empty:
        base["wk"] = base["wk"].astype(int)
        full = list(range(int(all_weeks.min()), int(all_weeks.max()) + 1))
        # Weekly cases per district -> cumulative across the whole outbreak.
        weekly = (base.groupby(["district", "wk"]).size().unstack(fill_value=0)
                  .reindex(columns=full, fill_value=0))
        cum_cases = weekly.cumsum(axis=1)
        pop = pd.Series(DISTRICT_POPULATION)
        # Cumulative attack rate per 100,000 residents.
        rate = cum_cases.div(pop.reindex(cum_cases.index), axis=0) * 100_000
        rate.index = [d.title() for d in rate.index]
        long = (rate.reset_index(names="District")
                .melt(id_vars="District", var_name="epi_week", value_name="attack_rate"))
        fig4 = px.bar(
            long, x="epi_week", y="attack_rate", color="District", barmode="group",
            labels={"epi_week": "Epi week",
                    "attack_rate": "Cumulative attack rate / 100,000"},
            title="Cumulative attack rate by district and epi week",
        )
        fig4.update_xaxes(dtick=1)
        # Horizontal legend below the plot so it doesn't collide with the title.
        fig4.update_layout(
            legend=dict(orientation="h", yanchor="top", y=-0.18,
                        xanchor="center", x=0.5, title_text=""),
            title=dict(x=0, xanchor="left"),
        )
        st.plotly_chart(who.style_fig(fig4), use_container_width=True)
        peak = rate.iloc[:, -1].sort_values(ascending=False)
        st.caption(
            f"Cumulative {ar_basis.lower()} per 100,000 residents, by district of "
            f"the reporting health region. Highest at epi week {full[-1]}: "
            f"{peak.index[0]} ({peak.iloc[0]:,.0f}/100,000). Districts with no "
            "reported cases are omitted.")
        who.notes(
            "Cumulative attack rate per 100,000 residents by district, "
            "accumulating across the outbreak; the toggle switches between all "
            "reported cases and confirmed-only.",
            "Depends on the `health_region`→district mapping, `epi_week`, and the "
            "**2020** population denominators. Districts with no cases are omitted. "
            "Keep `DISTRICT_POPULATION` current and re-verify the region→district "
            "mapping if the Ministry's health-region definitions change.")

# --- National attack rate by age group -------------------------------------
st.divider()
who.section("Attack rate by age group", "National, per 100,000")
if "age_group" in fdf.columns and fdf["age_group"].notna().any():
    AGE_ORDER = ["0-19", "20-39", "40-59", "60-150"]
    AGE_LABEL = {"0-19": "0–19", "20-39": "20–39", "40-59": "40–59",
                 "60-150": "60+"}
    counts = fdf["age_group"].value_counts()
    rows = [{"Age group": AGE_LABEL[b], "cases": int(counts.get(b, 0)),
             "pop": AGE_GROUP_POPULATION[b],
             "attack_rate": int(counts.get(b, 0)) / AGE_GROUP_POPULATION[b] * 100_000}
            for b in AGE_ORDER if b in AGE_GROUP_POPULATION]
    ar_age = pd.DataFrame(rows)
    fig5 = px.bar(
        ar_age, x="Age group", y="attack_rate", text="attack_rate",
        labels={"attack_rate": "Attack rate / 100,000"},
        title="National attack rate per 100,000 by age group",
    )
    fig5.update_traces(marker_color=who.WHO_RED, textposition="outside",
                       texttemplate="%{text:.0f}")
    fig5.update_layout(yaxis_title="Attack rate / 100,000")
    st.plotly_chart(who.style_fig(fig5), use_container_width=True)
    st.caption(
        "Population denominators: **World Bank 2023** national estimates "
        "(data/popdata/mau_population.csv), 5-year bands aggregated to the "
        "analysis age groups. These are 2023/national and so differ from the "
        "2020 district figures used for the regional attack rates above.")
    who.notes(
        "Cases per 100,000 population in each age band — shows which ages carry "
        "the highest relative burden (attack rates rise steeply with age here).",
        "Numerator = cases by `age_group` (respects the sidebar filters); "
        "denominator = fixed **World Bank 2023** national age-band population in "
        "`AGE_GROUP_POPULATION`. Because the denominator is always the full "
        "national population, filtering to a sub-group makes the rate a "
        "filtered-cases-over-national figure — read the unfiltered view for the "
        "true national attack rate. Update the constant when newer census data is "
        "available; if the analysis age bands change, re-aggregate the source CSV.")
else:
    st.info("Age group not available for the current filter.")
