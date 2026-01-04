#!/usr/bin/env python3
"""
Plot historical data with dates on x-axis and values on y-axis.
Saves the plot to a specified output file.
"""

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime
import sys
import json


def parse_date(date_str):
    """Parse a date string in various common formats."""
    date_formats = [
        "%Y-%m-%d",
        "%m/%d/%Y",
        "%d/%m/%Y",
        "%Y/%m/%d",
        "%b %d, %Y",
        "%B %d, %Y",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%SZ",
    ]
    
    for fmt in date_formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    
    raise ValueError(f"Unable to parse date: {date_str}")


def plot_historical_data(dates, values, output_file, title="Historical Data", 
                        xlabel="Date", ylabel="Value"):
    """
    Create a line plot of historical data.
    
    Args:
        dates: List of date strings or datetime objects
        values: List of numeric values
        output_file: Path where the plot should be saved
        title: Plot title
        xlabel: X-axis label
        ylabel: Y-axis label
    """
    # Parse dates if they're strings
    if dates and isinstance(dates[0], str):
        parsed_dates = [parse_date(d) for d in dates]
    else:
        parsed_dates = dates
    
    # Create the plot
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.plot(parsed_dates, values, marker='o', linestyle='-', linewidth=2, markersize=4)
    
    # Format the plot
    ax.set_title(title, fontsize=14, fontweight='bold')
    ax.set_xlabel(xlabel, fontsize=12)
    ax.set_ylabel(ylabel, fontsize=12)
    ax.grid(True, alpha=0.3)
    
    # Format x-axis dates
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    fig.autofmt_xdate()  # Rotate date labels
    
    # Tight layout to prevent label cutoff
    plt.tight_layout()
    
    # Save the plot
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    plt.close()
    
    print(f"Plot saved to: {output_file}")


def main():
    """Main entry point for the script."""
    if len(sys.argv) < 2:
        print("Usage: python plot_historical_data.py <config_json>")
        print("\nConfig JSON should contain:")
        print('  {"dates": [...], "values": [...], "output_file": "...", '
              '"title": "...", "xlabel": "...", "ylabel": "..."}')
        sys.exit(1)
    
    # Load configuration from JSON argument
    config = json.loads(sys.argv[1])
    
    dates = config['dates']
    values = config['values']
    output_file = config.get('output_file', '/tmp/historical_plot.png')
    title = config.get('title', 'Historical Data')
    xlabel = config.get('xlabel', 'Date')
    ylabel = config.get('ylabel', 'Value')
    
    plot_historical_data(dates, values, output_file, title, xlabel, ylabel)


if __name__ == "__main__":
    main()