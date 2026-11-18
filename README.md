# Market-Making Simulator

An educational Python application that simulates a market maker, visualizes a
single market path and compares two quoting strategies over many Monte Carlo
runs.

## What it does

- simulates a stochastic fair value;
- quotes bid and ask prices around a quote center;
- models customer fills with distance-sensitive probabilities;
- tracks inventory, cash and mark-to-market P&L;
- enforces a configurable inventory limit;
- compares **Fixed** and **Inventory-aware** quoting with common random seeds;
- shows interactive charts and tables in a Streamlit interface;
- exports simulation data as CSV;
- exposes the source code inside the app for learning.

## Strategies

**Fixed** keeps quotes symmetric around fair value:

```python
quote_center = fair_value
```

**Inventory-aware** moves quotes against the current position:

```python
quote_center = fair_value - inventory * inventory_skew
```

When inventory is positive, the quote center moves down. This encourages the
market maker to sell and discourages additional buying. Negative inventory has
the opposite effect.

## Quick start

Python 3.11 or newer is recommended.

```powershell
.\setup.ps1
.\run_app.ps1
```

`setup.ps1` creates an isolated environment, installs dependencies and runs the
tests. The equivalent manual commands are:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m streamlit run app.py
```

## Command line

```powershell
python main.py --runs 1000 --steps 1000 --seed 42
python main.py --strategy inventory_aware --runs 1000
```

## Tests

```powershell
python -m pip install -r requirements-dev.txt
python -m pytest
```

## Project structure

```text
market-making-simulator/
├── app.py                 # Streamlit interface and charts
├── main.py                # Command-line entry point
├── market_maker.py        # Simulation and Monte Carlo engine
├── tests/                 # Automated model tests
├── setup.ps1              # One-command Windows setup
├── run_app.ps1            # Starts the Streamlit app
├── requirements.txt       # Application dependencies
└── requirements-dev.txt   # Test dependencies
```

## Model limitations

This is a learning model, not a production trading system. Fills depend only on
quote distance. It does not model an order book, queue position, fees, latency,
market impact, adverse selection or correlated order flow. Results are useful
for understanding mechanics and comparing variants, not for predicting real
trading profits.

## Publish on GitHub

```powershell
git init
git add .
git commit -m "Build interactive market-making simulator"
git branch -M main
git remote add origin https://github.com/YOUR-USER/market-making-simulator.git
git push -u origin main
```

## Disclaimer

For educational purposes only. This project is not financial advice and is not
intended for live trading.
