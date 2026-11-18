"""Command-line entry point for the market-making simulator."""

from __future__ import annotations

import argparse
from dataclasses import replace

from market_maker import MarketParameters, compare_strategies, run_monte_carlo


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the market-making Monte Carlo simulation."
    )
    parser.add_argument("--strategy", choices=("fixed", "inventory_aware"))
    parser.add_argument("--runs", type=int, default=1_000)
    parser.add_argument("--steps", type=int, default=1_000)
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


def print_summary(row: dict[str, str | float | int]) -> None:
    print(f"\nStrategy: {row['strategy']}")
    print(f"Average P&L: {row['average_pnl']:.2f}")
    print(f"Median P&L: {row['median_pnl']:.2f}")
    print(f"P&L standard deviation: {row['pnl_std']:.2f}")
    print(f"Loss probability: {row['loss_probability_pct']:.2f}%")
    print(f"Average maximum inventory: {row['average_max_inventory']:.2f}")
    print(
        "Average final |inventory|: "
        f"{row['average_abs_final_inventory']:.2f}"
    )
    print(f"Average fill rate: {row['average_fill_rate_pct']:.2f}%")
    print(f"Average number of trades: {row['average_trade_count']:.2f}")


def main() -> None:
    args = parse_args()
    parameters = replace(MarketParameters(), num_steps=args.steps)

    if args.strategy:
        summary = run_monte_carlo(
            parameters,
            strategy=args.strategy,
            num_runs=args.runs,
            seed=args.seed,
        )
        print_summary(summary.as_row())
        return

    summaries = compare_strategies(
        parameters,
        num_runs=args.runs,
        seed=args.seed,
    )
    for summary in summaries.values():
        print_summary(summary.as_row())


if __name__ == "__main__":
    main()
