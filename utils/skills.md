---
name: historical-plotter
description: Create line plots from historical time series data (dates/values).
---

Call `plot_historical_data` with:
- dates: list of date strings
- values: list of numeric values
- title: plot title
- ylabel: y-axis label (optional)

Example:
```
plot_historical_data(dates=["2024-01-01", "2024-01-02"], values=[150.25, 155.50], title="AAPL Stock Price", ylabel="Price ($)")
```
