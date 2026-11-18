"""Core simulation engine for the market-making simulator.

The module intentionally depends only on Python's standard library. This keeps
the quantitative logic easy to inspect, test and reuse from the Streamlit app
or the command line.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
import random
import statistics
from typing import Iterable, Literal


Strategy = Literal["fixed", "inventory_aware"]
STRATEGIES: tuple[Strategy, ...] = ("fixed", "inventory_aware")


@dataclass(frozen=True)
class MarketParameters:
    """Parameters that describe one simulated market."""

    start_fair_value: float = 100.0
    spread: float = 0.20
    inventory_skew: float = 0.05
    max_inventory: int = 5
    fill_sensitivity: float = 5.0
    max_fill_probability: float = 0.45
    volatility: float = 0.10
    num_steps: int = 1_000

    def validate(self) -> None:
        """Raise ``ValueError`` if a parameter would break the model."""

        if self.start_fair_value <= 0:
            raise ValueError("start_fair_value must be positive")
        if self.spread < 0:
            raise ValueError("spread must be non-negative")
        if self.inventory_skew < 0:
            raise ValueError("inventory_skew must be non-negative")
        if self.max_inventory < 1:
            raise ValueError("max_inventory must be at least 1")
        if self.fill_sensitivity < 0:
            raise ValueError("fill_sensitivity must be non-negative")
        if not 0 <= self.max_fill_probability <= 0.5:
            raise ValueError("max_fill_probability must be between 0 and 0.5")
        if self.volatility < 0:
            raise ValueError("volatility must be non-negative")
        if self.num_steps < 1:
            raise ValueError("num_steps must be at least 1")


@dataclass(frozen=True)
class StepRecord:
    """State of the market maker after one simulation step."""

    step: int
    fair_value: float
    quote_center: float
    bid: float
    ask: float
    inventory_before: int
    inventory: int
    cash: float
    pnl: float
    trade: str
    buy_probability: float
    sell_probability: float


@dataclass(frozen=True)
class SimulationResult:
    """Complete time series and summary values for one simulated path."""

    strategy: Strategy
    steps: tuple[StepRecord, ...]
    trade_count: int

    @property
    def final_pnl(self) -> float:
        return self.steps[-1].pnl

    @property
    def final_inventory(self) -> int:
        return self.steps[-1].inventory

    @property
    def max_inventory_reached(self) -> int:
        return max(abs(step.inventory) for step in self.steps)

    @property
    def fill_rate(self) -> float:
        return self.trade_count / len(self.steps) * 100

    def to_rows(self) -> list[dict[str, int | float | str]]:
        """Return records that can be passed directly to pandas or CSV tools."""

        return [
            {
                "step": step.step,
                "fair_value": step.fair_value,
                "quote_center": step.quote_center,
                "bid": step.bid,
                "ask": step.ask,
                "inventory_before": step.inventory_before,
                "inventory": step.inventory,
                "cash": step.cash,
                "pnl": step.pnl,
                "trade": step.trade,
                "buy_probability": step.buy_probability,
                "sell_probability": step.sell_probability,
            }
            for step in self.steps
        ]


@dataclass(frozen=True)
class RunOutcome:
    """Memory-efficient summary of one Monte Carlo run."""

    final_pnl: float
    final_inventory: int
    max_inventory_reached: int
    fill_rate: float
    trade_count: int


@dataclass(frozen=True)
class MonteCarloSummary:
    """Aggregate results for many paths of one strategy."""

    strategy: Strategy
    outcomes: tuple[RunOutcome, ...]

    @property
    def average_pnl(self) -> float:
        return statistics.fmean(item.final_pnl for item in self.outcomes)

    @property
    def median_pnl(self) -> float:
        return statistics.median(item.final_pnl for item in self.outcomes)

    @property
    def pnl_std(self) -> float:
        values = [item.final_pnl for item in self.outcomes]
        return statistics.stdev(values) if len(values) > 1 else 0.0

    @property
    def loss_probability(self) -> float:
        losses = sum(item.final_pnl < 0 for item in self.outcomes)
        return losses / len(self.outcomes) * 100

    @property
    def average_max_inventory(self) -> float:
        return statistics.fmean(
            item.max_inventory_reached for item in self.outcomes
        )

    @property
    def average_absolute_final_inventory(self) -> float:
        return statistics.fmean(
            abs(item.final_inventory) for item in self.outcomes
        )

    @property
    def average_fill_rate(self) -> float:
        return statistics.fmean(item.fill_rate for item in self.outcomes)

    @property
    def average_trade_count(self) -> float:
        return statistics.fmean(item.trade_count for item in self.outcomes)

    def as_row(self) -> dict[str, str | float | int]:
        """Return the headline metrics in a table-friendly format."""

        return {
            "strategy": self.strategy,
            "runs": len(self.outcomes),
            "average_pnl": self.average_pnl,
            "median_pnl": self.median_pnl,
            "pnl_std": self.pnl_std,
            "loss_probability_pct": self.loss_probability,
            "average_max_inventory": self.average_max_inventory,
            "average_abs_final_inventory": self.average_absolute_final_inventory,
            "average_fill_rate_pct": self.average_fill_rate,
            "average_trade_count": self.average_trade_count,
        }


def _quote_center(
    fair_value: float,
    inventory: int,
    inventory_skew: float,
    strategy: Strategy,
) -> float:
    """Return the midpoint around which bid and ask are placed."""

    if strategy == "fixed":
        return fair_value
    if strategy == "inventory_aware":
        return fair_value - inventory * inventory_skew
    raise ValueError(f"Unknown strategy: {strategy}")


def simulate_market(
    parameters: MarketParameters,
    strategy: Strategy = "inventory_aware",
    seed: int | None = None,
) -> SimulationResult:
    """Simulate one market path.

    ``market_buy`` means a customer buys at our ask, so our inventory falls.
    ``market_sell`` means a customer sells at our bid, so our inventory rises.
    """

    parameters.validate()
    if strategy not in STRATEGIES:
        raise ValueError(f"strategy must be one of {STRATEGIES}")

    rng = random.Random(seed)
    fair_value = parameters.start_fair_value
    inventory = 0
    cash = 0.0
    trade_count = 0
    records: list[StepRecord] = []

    for step_number in range(1, parameters.num_steps + 1):
        fair_value += rng.gauss(0, parameters.volatility)
        inventory_before = inventory

        quote_center = _quote_center(
            fair_value,
            inventory_before,
            parameters.inventory_skew,
            strategy,
        )
        bid = quote_center - parameters.spread / 2
        ask = quote_center + parameters.spread / 2

        # Customers trade more often when a quote is close to fair value.
        ask_distance = max(0.0, ask - fair_value)
        bid_distance = max(0.0, fair_value - bid)
        buy_probability = parameters.max_fill_probability * math.exp(
            -parameters.fill_sensitivity * ask_distance
        )
        sell_probability = parameters.max_fill_probability * math.exp(
            -parameters.fill_sensitivity * bid_distance
        )

        # A quote that would violate the inventory limit is withdrawn.
        if inventory_before <= -parameters.max_inventory:
            buy_probability = 0.0
        if inventory_before >= parameters.max_inventory:
            sell_probability = 0.0

        trade_random = rng.random()
        if trade_random < buy_probability:
            trade = "market_buy"
            inventory -= 1
            cash += ask
            trade_count += 1
        elif trade_random < buy_probability + sell_probability:
            trade = "market_sell"
            inventory += 1
            cash -= bid
            trade_count += 1
        else:
            trade = "none"

        pnl = cash + inventory * fair_value
        records.append(
            StepRecord(
                step=step_number,
                fair_value=fair_value,
                quote_center=quote_center,
                bid=bid,
                ask=ask,
                inventory_before=inventory_before,
                inventory=inventory,
                cash=cash,
                pnl=pnl,
                trade=trade,
                buy_probability=buy_probability,
                sell_probability=sell_probability,
            )
        )

    return SimulationResult(
        strategy=strategy,
        steps=tuple(records),
        trade_count=trade_count,
    )


def _outcome(result: SimulationResult) -> RunOutcome:
    return RunOutcome(
        final_pnl=result.final_pnl,
        final_inventory=result.final_inventory,
        max_inventory_reached=result.max_inventory_reached,
        fill_rate=result.fill_rate,
        trade_count=result.trade_count,
    )


def run_monte_carlo(
    parameters: MarketParameters,
    strategy: Strategy,
    num_runs: int = 1_000,
    seed: int | None = None,
    run_seeds: Iterable[int] | None = None,
) -> MonteCarloSummary:
    """Run many independent paths and aggregate their results."""

    if num_runs < 1:
        raise ValueError("num_runs must be at least 1")

    if run_seeds is None:
        master_rng = random.Random(seed)
        seeds = [master_rng.randrange(0, 2**63) for _ in range(num_runs)]
    else:
        seeds = list(run_seeds)
        if len(seeds) != num_runs:
            raise ValueError("run_seeds must contain exactly num_runs values")

    outcomes = tuple(
        _outcome(simulate_market(parameters, strategy=strategy, seed=run_seed))
        for run_seed in seeds
    )
    return MonteCarloSummary(strategy=strategy, outcomes=outcomes)


def compare_strategies(
    parameters: MarketParameters,
    num_runs: int = 1_000,
    seed: int | None = None,
) -> dict[Strategy, MonteCarloSummary]:
    """Compare both strategies with identical random seeds for fairness."""

    master_rng = random.Random(seed)
    shared_seeds = [master_rng.randrange(0, 2**63) for _ in range(num_runs)]
    return {
        strategy: run_monte_carlo(
            parameters,
            strategy=strategy,
            num_runs=num_runs,
            run_seeds=shared_seeds,
        )
        for strategy in STRATEGIES
    }
