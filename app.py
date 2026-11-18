"""Interactive Streamlit interface for the market-making simulator."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from market_maker import (
    MarketParameters,
    MonteCarloSummary,
    SimulationResult,
    compare_strategies,
    simulate_market,
)


st.set_page_config(
    page_title="Market-Making Simulator",
    page_icon="📈",
    layout="wide",
)

st.markdown(
    """
    <style>
    .block-container {padding-top: 2rem; padding-bottom: 3rem;}
    [data-testid="stMetricValue"] {font-variant-numeric: tabular-nums;}
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(show_spinner=False)
def cached_path(
    parameters: MarketParameters, strategy: str, seed: int
) -> SimulationResult:
    return simulate_market(parameters, strategy=strategy, seed=seed)  # type: ignore[arg-type]


@st.cache_data(show_spinner=False)
def cached_comparison(
    parameters: MarketParameters, num_runs: int, seed: int
) -> dict[str, MonteCarloSummary]:
    return compare_strategies(parameters, num_runs=num_runs, seed=seed)


def money(value: float) -> str:
    return f"{value:+,.2f}"


def parameter_sidebar() -> tuple[MarketParameters, str, int, int]:
    st.sidebar.header("Simulation einstellen")
    strategy_label = st.sidebar.selectbox(
        "Strategie",
        ("Inventory-aware", "Fixed"),
        help="Inventory-aware verschiebt die Quotes, um Positionen abzubauen.",
    )
    strategy = "inventory_aware" if strategy_label == "Inventory-aware" else "fixed"

    start_fair_value = st.sidebar.number_input(
        "Start Fair Value", min_value=1.0, value=100.0, step=1.0
    )
    spread = st.sidebar.number_input(
        "Spread", min_value=0.0, value=0.20, step=0.05, format="%.2f"
    )
    inventory_skew = st.sidebar.number_input(
        "Inventory Skew", min_value=0.0, value=0.05, step=0.01, format="%.2f"
    )
    max_inventory = st.sidebar.slider("Maximales Inventory", 1, 25, 5)
    volatility = st.sidebar.number_input(
        "Volatilität pro Schritt",
        min_value=0.0,
        value=0.10,
        step=0.05,
        format="%.2f",
    )
    fill_sensitivity = st.sidebar.number_input(
        "Fill Sensitivity", min_value=0.0, value=5.0, step=0.5
    )
    max_fill_probability = st.sidebar.slider(
        "Max. Fill-Wahrscheinlichkeit", 0.01, 0.50, 0.45, 0.01
    )
    num_steps = st.sidebar.slider("Schritte pro Run", 50, 5_000, 1_000, 50)
    num_runs = st.sidebar.slider("Monte-Carlo-Runs", 50, 5_000, 1_000, 50)
    seed = int(
        st.sidebar.number_input("Random Seed", min_value=0, value=42, step=1)
    )
    st.sidebar.caption(
        "Der Seed macht Ergebnisse reproduzierbar. Ändere ihn für einen neuen Pfad."
    )

    parameters = MarketParameters(
        start_fair_value=float(start_fair_value),
        spread=float(spread),
        inventory_skew=float(inventory_skew),
        max_inventory=int(max_inventory),
        fill_sensitivity=float(fill_sensitivity),
        max_fill_probability=float(max_fill_probability),
        volatility=float(volatility),
        num_steps=int(num_steps),
    )
    return parameters, strategy, num_runs, seed


def show_path(result: SimulationResult) -> None:
    data = pd.DataFrame(result.to_rows())
    metrics = st.columns(5)
    metrics[0].metric("Final P&L", money(result.final_pnl))
    metrics[1].metric("Final Inventory", result.final_inventory)
    metrics[2].metric("Max. |Inventory|", result.max_inventory_reached)
    metrics[3].metric("Trades", result.trade_count)
    metrics[4].metric("Fill Rate", f"{result.fill_rate:.1f}%")

    prices = go.Figure()
    prices.add_trace(
        go.Scatter(x=data["step"], y=data["fair_value"], name="Fair Value")
    )
    prices.add_trace(
        go.Scatter(x=data["step"], y=data["bid"], name="Bid", opacity=0.75)
    )
    prices.add_trace(
        go.Scatter(x=data["step"], y=data["ask"], name="Ask", opacity=0.75)
    )
    prices.update_layout(
        title="Fair Value und Quotes",
        xaxis_title="Schritt",
        yaxis_title="Preis",
        hovermode="x unified",
    )
    st.plotly_chart(prices, use_container_width=True)

    left, right = st.columns(2)
    inventory_chart = px.line(
        data, x="step", y="inventory", title="Inventory über die Zeit"
    )
    inventory_chart.add_hline(y=0, line_dash="dot", opacity=0.5)
    left.plotly_chart(inventory_chart, use_container_width=True)

    pnl_chart = px.line(data, x="step", y="pnl", title="Mark-to-Market P&L")
    pnl_chart.add_hline(y=0, line_dash="dot", opacity=0.5)
    right.plotly_chart(pnl_chart, use_container_width=True)

    with st.expander("Trade- und Wahrscheinlichkeitsdaten anzeigen"):
        st.dataframe(data, use_container_width=True, hide_index=True)
        st.download_button(
            "Pfad als CSV herunterladen",
            data.to_csv(index=False).encode("utf-8"),
            file_name=f"market_making_{result.strategy}.csv",
            mime="text/csv",
        )


def show_comparison(
    summaries: dict[str, MonteCarloSummary], parameters: MarketParameters
) -> None:
    rows = [summary.as_row() for summary in summaries.values()]
    table = pd.DataFrame(rows).set_index("strategy")
    display = table.rename(
        columns={
            "runs": "Runs",
            "average_pnl": "Ø P&L",
            "median_pnl": "Median P&L",
            "pnl_std": "P&L Risiko (Std.)",
            "loss_probability_pct": "Verlustwahrscheinlichkeit %",
            "average_max_inventory": "Ø Max. Inventory",
            "average_abs_final_inventory": "Ø Final |Inventory|",
            "average_fill_rate_pct": "Ø Fill Rate %",
            "average_trade_count": "Ø Trades",
        }
    )
    st.dataframe(display.style.format("{:.2f}"), use_container_width=True)

    pnl_rows: list[dict[str, str | float]] = []
    for strategy, summary in summaries.items():
        pnl_rows.extend(
            {"strategy": strategy, "final_pnl": item.final_pnl}
            for item in summary.outcomes
        )
    distribution = px.histogram(
        pd.DataFrame(pnl_rows),
        x="final_pnl",
        color="strategy",
        barmode="overlay",
        opacity=0.60,
        nbins=60,
        title="Verteilung des finalen P&L",
    )
    distribution.add_vline(x=0, line_dash="dot")
    st.plotly_chart(distribution, use_container_width=True)

    fixed = summaries["fixed"]
    aware = summaries["inventory_aware"]
    risk_change = aware.pnl_std - fixed.pnl_std
    inventory_change = aware.average_max_inventory - fixed.average_max_inventory
    st.markdown("#### Interpretation")
    st.write(
        f"Bei diesen Parametern verändert Inventory-Awareness die P&L-"
        f"Standardabweichung um **{risk_change:+.2f}** und das durchschnittliche "
        f"maximale Inventory um **{inventory_change:+.2f}** gegenüber Fixed. "
        "Eine einzelne Simulation ist Zufall; entscheidend ist die Verteilung "
        "über viele Runs."
    )
    st.caption(
        f"Identische Zufalls-Seeds; Spread {parameters.spread:.2f}; "
        f"Inventory Skew {parameters.inventory_skew:.2f}."
    )
    st.download_button(
        "Vergleich als CSV herunterladen",
        table.reset_index().to_csv(index=False).encode("utf-8"),
        file_name="strategy_comparison.csv",
        mime="text/csv",
    )


def show_explanation() -> None:
    st.subheader("So funktioniert das Modell")
    st.markdown(
        r"""
1. Der Fair Value bewegt sich als zufälliger Prozess:
   $F_{t+1}=F_t+\epsilon_t$, mit $\epsilon_t\sim N(0,\sigma)$.
2. **Fixed** quotiert symmetrisch um den Fair Value.
3. **Inventory-aware** verschiebt den Mittelpunkt:
   $Q_t=F_t-I_t\cdot k$.
4. Bid und Ask sind $Q_t-s/2$ und $Q_t+s/2$.
5. Die Fill-Wahrscheinlichkeit fällt exponentiell mit dem Abstand zum Fair Value.
6. P&L wird mark-to-market berechnet: $Cash_t+Inventory_t\cdot F_t$.

Ein positives Inventory verschiebt beide Quotes nach unten. Dadurch wird der Ask
attraktiver und der Bid weniger attraktiv: Der Market Maker verkauft eher und
kauft weniger hinzu. Bei negativem Inventory gilt das Gegenteil.
        """
    )
    st.warning(
        "Das Modell ist für Lernen und Experimente gedacht. Es enthält keine "
        "Orderbuch-Priorität, Gebühren, Latenz oder adverse selection und ist "
        "keine Anlageberatung."
    )

    st.subheader("Quellcode ansehen")
    root = Path(__file__).resolve().parent
    selected = st.selectbox("Datei", ("market_maker.py", "app.py", "main.py"))
    st.code((root / selected).read_text(encoding="utf-8"), language="python")


st.title("Market-Making Simulator")
st.markdown(
    "Simuliere Quotes, Inventory, Cash und P&L – und vergleiche eine feste "
    "Strategie fair mit einem inventory-bewussten Market Maker."
)

parameters, strategy, num_runs, seed = parameter_sidebar()
path_tab, comparison_tab, explanation_tab = st.tabs(
    ("Einzelner Marktpfad", "Strategien vergleichen", "Modell & Code")
)

with path_tab:
    show_path(cached_path(parameters, strategy, seed))

with comparison_tab:
    st.write(
        "Beide Strategien erhalten pro Run dieselben Zufalls-Seeds. Dadurch ist "
        "der Vergleich weniger vom Zufall verzerrt."
    )
    if st.button("Monte-Carlo-Vergleich starten", type="primary"):
        with st.spinner(f"Berechne {num_runs:,} Runs pro Strategie …"):
            st.session_state["comparison"] = cached_comparison(
                parameters, num_runs, seed
            )
            st.session_state["comparison_parameters"] = parameters
    if "comparison" in st.session_state:
        show_comparison(
            st.session_state["comparison"],
            st.session_state["comparison_parameters"],
        )
    else:
        st.info("Starte den Vergleich, um Risiko und Inventory beider Strategien zu sehen.")

with explanation_tab:
    show_explanation()
