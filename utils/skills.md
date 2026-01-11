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

---
name: distribution-comparison
description: Compare distributions of one or more data groups using various plot types (kde, histogram, violin, box, etc.).
---

Call `plot_distribution_comparison` with:
- groups: list of dicts, each with 'name' (str) and 'values' (list of floats)
- plot_type: one of 'histogram', 'kde', 'ecdf', 'violin', 'box', 'strip', 'swarm', 'ridge' (default: 'kde')
- title: plot title
- xlabel: x-axis label or value label (default: 'Value')
- ylabel: y-axis label (optional, auto-generated based on plot type)

## Plot Types

| Type | Best For |
|------|----------|
| `kde` | Smooth density curves, good for comparing shape of distributions |
| `histogram` | Discrete bin counts, shows data frequency |
| `ecdf` | Cumulative distribution, shows proportion below each value |
| `violin` | Density + quartiles, compact comparison of multiple groups |
| `box` | Quartiles + outliers, classic statistical summary |
| `strip` | Individual points with jitter, good for small datasets |
| `swarm` | Non-overlapping points, shows all data clearly |
| `ridge` | Stacked KDE plots, good for many groups |

## Examples

Compare two groups with KDE:
```
plot_distribution_comparison(
    groups=[
        {"name": "Treatment", "values": [23.5, 25.1, 22.8, 26.3, 24.9]},
        {"name": "Control", "values": [20.1, 19.8, 21.2, 18.9, 20.5]}
    ],
    plot_type="kde",
    title="Treatment vs Control Distribution",
    xlabel="Measurement"
)
```

Single group violin plot:
```
plot_distribution_comparison(
    groups=[{"name": "Scores", "values": [85, 90, 78, 92, 88, 76, 95]}],
    plot_type="violin",
    title="Score Distribution"
)
```

Three groups with box plot:
```
plot_distribution_comparison(
    groups=[
        {"name": "Group A", "values": [10, 12, 11, 13, 9]},
        {"name": "Group B", "values": [15, 18, 14, 16, 17]},
        {"name": "Group C", "values": [8, 7, 9, 6, 10]}
    ],
    plot_type="box",
    title="Comparison Across Groups"
)
```

---
name: table-display
description: Display tabular data as a formatted, styled table in the UI.
---

Call `display_table` with:
- columns: list of column header names (strings)
- rows: list of rows, each row is a list of values matching the column count
- title: table title (default: "Data Table")
- caption: optional description below the table

## When to Use

Use `display_table` when:
- User asks to show data "as a table" or "in tabular format"
- User asks for a "table", "spreadsheet view", or "data grid"
- The result is naturally tabular (e.g., stock prices over time, comparison data)
- User explicitly requests NOT to plot/visualize but wants structured data display

Do NOT use for:
- Simple key-value pairs (just present as text)
- Single data points
- When user asks for a chart/plot/visualization

## Examples

Stock price data:
```
display_table(
    columns=["Date", "Open", "High", "Low", "Close", "Volume"],
    rows=[
        ["2024-01-08", "185.20", "186.50", "184.80", "185.90", "45.2M"],
        ["2024-01-09", "186.10", "187.30", "185.50", "186.80", "52.1M"],
        ["2024-01-10", "186.90", "188.00", "186.20", "187.50", "48.7M"]
    ],
    title="AAPL Stock Prices",
    caption="Last 3 trading days"
)
```

Comparison data:
```
display_table(
    columns=["Metric", "Q1 2024", "Q2 2024", "Change"],
    rows=[
        ["Revenue", "$10.5M", "$12.3M", "+17.1%"],
        ["Users", "45,000", "52,000", "+15.6%"],
        ["Churn Rate", "3.2%", "2.8%", "-12.5%"]
    ],
    title="Quarterly Performance"
)
