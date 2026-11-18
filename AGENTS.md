# Project guidance

This is an educational market-making simulator for a learner working toward
quant trading. Preserve clarity over cleverness.

- Explain model changes in small, concrete steps.
- Keep the simulation engine independent from Streamlit.
- Add or update tests when quantitative behavior changes.
- Do not present simulated returns as evidence of real-world profitability.
- Before claiming something is missing, inspect the current code.
- `market_buy`: a customer buys from us at the ask; our inventory falls.
- `market_sell`: a customer sells to us at the bid; our inventory rises.
