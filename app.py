"""
India Economic Policy Simulator (Streamlit app)

Run from the folder that contains this file and the CSV files:
    streamlit run app.py
"""

import os

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

st.set_page_config(page_title="India Economic Policy Simulator", layout="wide")

# ---------------------------------------------------------------------------
# Data loading (the app still opens if a file is missing)
# ---------------------------------------------------------------------------
HERE = os.path.dirname(os.path.abspath(__file__))


@st.cache_data
def load_csv(name, **kwargs):
    path = os.path.join(HERE, name)
    if not os.path.exists(path):
        return None
    return pd.read_csv(path, **kwargs)


macro = load_csv("india_macro_fiscal_year.csv")
monthly = load_csv("india_monthly_cpi_repo.csv", parse_dates=["date"])
plfs = load_csv("india_plfs_unemployment_annual.csv")

# ---------------------------------------------------------------------------
# The simulator (baselines calibrated to official data; see "Evidence" tab)
# ---------------------------------------------------------------------------
BASE_GDP = 7.4          # median real GDP growth, 2014-15 to 2023-24
BASE_INFLATION = 5.1    # mean CPI inflation, 2014-15 to 2023-24
BASE_UNEMPLOYMENT = 4.5  # mean PLFS unemployment rate, 2017-18 to 2023-24


def simulate(repo_change=0.0, spending_change=0.0, income_tax_change=0.0, gst_change=0.0):
    gdp, inflation = BASE_GDP, BASE_INFLATION
    unemployment, investment, consumption = BASE_UNEMPLOYMENT, 100.0, 100.0

    # Repo rate: inflation effect consistent with data; GDP effect consistent in sign
    gdp -= 0.35 * repo_change
    investment -= 2.0 * repo_change
    inflation -= 0.20 * repo_change

    # Government spending (assumed)
    gdp += 0.08 * spending_change
    inflation += 0.025 * spending_change
    investment += 0.10 * spending_change

    # Income tax (assumed)
    gdp -= 0.04 * income_tax_change
    consumption -= 0.50 * income_tax_change

    # GST (assumed)
    gdp -= 0.035 * gst_change
    consumption -= 0.35 * gst_change
    inflation -= 0.05 * gst_change

    # Growth -> unemployment (Okun-style rule; NOT supported by PLFS data)
    unemployment -= 0.10 * (gdp - BASE_GDP)

    return {
        "GDP growth (%)": round(gdp, 2),
        "Inflation (%)": round(inflation, 2),
        "Unemployment (%)": round(unemployment, 2),
        "Private investment index": round(investment, 2),
        "Consumption index": round(consumption, 2),
    }


# ---------------------------------------------------------------------------
# Page header and sidebar controls
# ---------------------------------------------------------------------------
st.title("India Economic Policy Simulator")
st.caption(
    "A teaching model. Baselines are calibrated to official Indian data (MoSPI, RBI). "
    "Most policy effects are illustrative assumptions, not estimates. "
    "See the Evidence tab for what the data does and does not support."
)

st.sidebar.header("Policy controls")
repo_change = st.sidebar.slider("Repo rate change (percentage points)", -2.0, 3.0, 0.0, 0.25)
spending_change = st.sidebar.slider("Government spending change (%)", -20, 40, 0, 1)
income_tax_change = st.sidebar.slider("Income tax change (percentage points)", -5, 5, 0, 1)
gst_change = st.sidebar.slider("GST change (percentage points)", -5, 5, 0, 1)
st.sidebar.markdown("---")
st.sidebar.caption("Move the sliders to see how the model responds.")

baseline = simulate()
scenario = simulate(repo_change, spending_change, income_tax_change, gst_change)

tab_sim, tab_data, tab_evidence, tab_about = st.tabs(
    ["Simulator", "Real Indian data", "Evidence", "About"]
)

# ---------------------------------------------------------------------------
# Tab 1: simulator
# ---------------------------------------------------------------------------
with tab_sim:
    st.subheader("Baseline vs your policy scenario")

    cols = st.columns(4)
    for col, key in zip(
        cols,
        ["GDP growth (%)", "Inflation (%)", "Unemployment (%)", "Private investment index"],
    ):
        delta = round(scenario[key] - baseline[key], 2)
        col.metric(key, scenario[key], delta)

    table = pd.DataFrame({"Baseline": baseline, "Your scenario": scenario})
    table["Change"] = (table["Your scenario"] - table["Baseline"]).round(2)
    st.dataframe(table)

    fig, ax = plt.subplots(figsize=(9, 4))
    plot_keys = ["GDP growth (%)", "Inflation (%)", "Unemployment (%)"]
    x = range(len(plot_keys))
    ax.bar([i - 0.2 for i in x], [baseline[k] for k in plot_keys], width=0.4, label="Baseline")
    ax.bar([i + 0.2 for i in x], [scenario[k] for k in plot_keys], width=0.4, label="Your scenario")
    ax.set_xticks(list(x))
    ax.set_xticklabels(plot_keys)
    ax.set_ylabel("Per cent")
    ax.grid(axis="y", alpha=0.3)
    ax.legend()
    fig.tight_layout()
    st.pyplot(fig)
    plt.close(fig)

    st.info(
        "These results come from simple linear rules. They are illustrations of "
        "direction and rough size, not forecasts."
    )

# ---------------------------------------------------------------------------
# Tab 2: real data
# ---------------------------------------------------------------------------
with tab_data:
    st.subheader("What actually happened (official data)")

    if macro is not None:
        st.markdown("**GDP growth, CPI inflation and repo rate by fiscal year**")
        fig, ax = plt.subplots(figsize=(10, 4.5))
        ax.bar(macro["fiscal_year"], macro["gdp_growth"], color="lightsteelblue", label="GDP growth (%)")
        ax.plot(macro["fiscal_year"], macro["avg_inflation"], color="red", marker="o", label="CPI inflation (%)")
        ax.plot(macro["fiscal_year"], macro["avg_repo_rate"], color="green", marker="s", label="Repo rate (%)")
        ax.axhline(0, color="black", linewidth=0.8)
        ax.legend()
        plt.xticks(rotation=30)
        fig.tight_layout()
        st.pyplot(fig)
        plt.close(fig)

        compare = pd.DataFrame(
            {
                "Simulator baseline": [BASE_GDP, BASE_INFLATION],
                "Actual average": [
                    round(macro["gdp_growth"].mean(), 2),
                    round(macro["avg_inflation"].mean(), 2),
                ],
                "Actual median": [
                    round(macro["gdp_growth"].median(), 2),
                    round(macro["avg_inflation"].median(), 2),
                ],
            },
            index=["GDP growth (%)", "Inflation (%)"],
        )
        st.markdown("**Simulator baseline vs actual (2014-15 to 2023-24)**")
        st.dataframe(compare)
    else:
        st.warning("india_macro_fiscal_year.csv not found in the app folder.")

    if monthly is not None:
        st.markdown("**Monthly CPI inflation and the repo rate**")
        fig, ax = plt.subplots(figsize=(10, 4))
        ax.plot(monthly["date"], monthly["inflation"], color="red", label="CPI inflation, y/y (%)")
        ax.plot(monthly["date"], monthly["repo"], color="green", label="Repo rate (%)")
        ax.grid(alpha=0.3)
        ax.legend()
        fig.tight_layout()
        st.pyplot(fig)
        plt.close(fig)
    else:
        st.warning("india_monthly_cpi_repo.csv not found in the app folder.")

    if plfs is not None:
        st.markdown("**Unemployment rate (PLFS, age 15+, usual status)**")
        fig, ax = plt.subplots(figsize=(10, 3.5))
        ax.plot(plfs["plfs_year"], plfs["unemployment_rate"], marker="o", color="purple")
        ax.axhline(BASE_UNEMPLOYMENT, color="grey", linestyle="--", label="Simulator baseline")
        ax.set_ylabel("Per cent")
        ax.grid(alpha=0.3)
        ax.legend()
        fig.tight_layout()
        st.pyplot(fig)
        plt.close(fig)
    else:
        st.warning("india_plfs_unemployment_annual.csv not found in the app folder.")

# ---------------------------------------------------------------------------
# Tab 3: evidence table
# ---------------------------------------------------------------------------
with tab_evidence:
    st.subheader("How well is each part of the model backed by data?")

    evidence = pd.DataFrame(
        [
            ["Baseline GDP growth 7.4%", "Calibrated to data",
             "Median of 10 fiscal years (2014-15 to 2023-24); mean is 6.1% because of COVID."],
            ["Baseline inflation 5.1%", "Calibrated to data",
             "Mean CPI inflation over the same years is 5.09%."],
            ["Baseline unemployment 4.5%", "Calibrated to data",
             "PLFS average 2017-18 to 2023-24 is 4.47%; the series trends down to 3.2%."],
            ["Repo rate -> inflation (-0.20 per point)", "Consistent with data",
             "Monthly regression, 132 months: about -0.20 at a 12-month lag, "
             "95% range -0.57 to +0.17. Not statistically significant."],
            ["Repo rate -> GDP growth (-0.35 per point)", "Consistent in sign",
             "Industrial production used as a proxy: -0.35 at a 12-month lag excluding COVID, "
             "95% range -0.78 to +0.07. Not statistically significant."],
            ["GDP growth -> unemployment (-0.10)", "Not supported",
             "In PLFS data, unemployment fell even in the 2020-21 contraction; "
             "changes in unemployment and GDP growth correlate positively (+0.41)."],
            ["Government spending effects", "Assumed", "Not tested against data."],
            ["Income tax and GST effects", "Assumed",
             "Rate changes are rare and coincide with other reforms, so data cannot isolate them."],
            ["Investment and consumption effects", "Assumed", "Not tested against data."],
        ],
        columns=["Part of the model", "Status", "Evidence"],
    )
    st.dataframe(evidence, hide_index=True)

    st.markdown(
        "**Why most estimates are weak:** the samples are small (10 annual points, "
        "132 monthly points), the RBI changes rates in response to inflation and growth "
        "(so cause and effect are tangled), and COVID dominates the period."
    )

# ---------------------------------------------------------------------------
# Tab 4: about
# ---------------------------------------------------------------------------
with tab_about:
    st.subheader("About this project")
    st.markdown(
        """
**Purpose.** A learning tool to explore how monetary and fiscal choices might move
growth, inflation and unemployment in India, and to be honest about how much of the
model the data supports.

**Data sources**
- CPI inflation: Ministry of Statistics and Programme Implementation (MoSPI), 2024-base back series, All India, Combined.
- GDP growth: MoSPI National Accounts Statistics, base 2011-12, constant prices, expenditure approach (mixed revision stages).
- Industrial production: MoSPI IIP, base 2011-12.
- Unemployment: MoSPI Periodic Labour Force Survey (PLFS), All India, persons, age 15+, usual status. Survey years run July to June.
- Repo rate: RBI policy rate changes as compiled in a Reuters timeline; the RBI website is the official source and should be used to verify.

**Limitations**
- Fiscal years (April to March) are used for GDP, CPI and repo; PLFS years run July to June.
- Ten annual observations cannot support reliable regression estimates.
- Most coefficients are illustrative assumptions.
- Nothing here is a forecast or policy advice.
        """
    )
