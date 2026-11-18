from dataclasses import replace

import pytest

from market_maker import (
    MarketParameters,
    compare_strategies,
    run_monte_carlo,
    simulate_market,
)


def small_parameters(**changes):
    return replace(MarketParameters(num_steps=200), **changes)


def test_simulation_is_reproducible():
    parameters = small_parameters()
    first = simulate_market(parameters, seed=123)
    second = simulate_market(parameters, seed=123)
    assert first == second


@pytest.mark.parametrize("strategy", ["fixed", "inventory_aware"])
def test_inventory_limit_is_never_violated(strategy):
    parameters = small_parameters(max_inventory=3, num_steps=1_000)
    result = simulate_market(parameters, strategy=strategy, seed=8)
    assert all(abs(step.inventory) <= 3 for step in result.steps)


def test_fixed_quotes_are_centered_on_fair_value():
    result = simulate_market(small_parameters(), strategy="fixed", seed=4)
    assert all(
        step.quote_center == pytest.approx(step.fair_value)
        for step in result.steps
    )


def test_inventory_aware_center_uses_inventory_before_trade():
    parameters = small_parameters(inventory_skew=0.07)
    result = simulate_market(parameters, strategy="inventory_aware", seed=5)
    assert all(
        step.quote_center
        == pytest.approx(
            step.fair_value - step.inventory_before * parameters.inventory_skew
        )
        for step in result.steps
    )


def test_zero_skew_makes_strategies_identical():
    parameters = small_parameters(inventory_skew=0)
    fixed = simulate_market(parameters, strategy="fixed", seed=19)
    aware = simulate_market(parameters, strategy="inventory_aware", seed=19)
    assert fixed.steps == aware.steps


def test_probabilities_are_valid():
    result = simulate_market(small_parameters(), seed=6)
    for step in result.steps:
        assert 0 <= step.buy_probability <= 0.5
        assert 0 <= step.sell_probability <= 0.5
        assert step.buy_probability + step.sell_probability <= 1


def test_monte_carlo_summary_contains_requested_runs():
    summary = run_monte_carlo(
        small_parameters(num_steps=30),
        strategy="fixed",
        num_runs=12,
        seed=7,
    )
    assert len(summary.outcomes) == 12
    assert 0 <= summary.loss_probability <= 100


def test_comparison_returns_both_strategies():
    summaries = compare_strategies(
        small_parameters(num_steps=30), num_runs=10, seed=2
    )
    assert set(summaries) == {"fixed", "inventory_aware"}


@pytest.mark.parametrize(
    "parameters",
    [
        small_parameters(start_fair_value=0),
        small_parameters(spread=-0.1),
        small_parameters(max_fill_probability=0.6),
        small_parameters(num_steps=0),
    ],
)
def test_invalid_parameters_are_rejected(parameters):
    with pytest.raises(ValueError):
        simulate_market(parameters)
