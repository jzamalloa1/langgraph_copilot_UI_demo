#!/usr/bin/env python3
"""
Plot distribution comparisons using seaborn.
Supports multiple plot types: histogram, kde, ecdf, violin, box, strip, swarm.
Can compare one or more groups of data.
"""

import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import sys
import json
from typing import Literal


PlotType = Literal["histogram", "kde", "ecdf", "violin", "box", "strip", "swarm", "ridge"]


def plot_distribution_comparison(
    groups: list[dict],
    output_file: str,
    plot_type: PlotType = "kde",
    title: str = "Distribution Comparison",
    xlabel: str = "Value",
    ylabel: str | None = None,
    fill: bool = True,
    alpha: float = 0.5,
    common_norm: bool = False,
    stat: str = "density",
):
    """
    Create a distribution comparison plot.

    Args:
        groups: List of dicts with 'name' and 'values' keys.
                Example: [{"name": "Group A", "values": [1,2,3]}, {"name": "Group B", "values": [4,5,6]}]
        output_file: Path where the plot should be saved
        plot_type: Type of plot - 'histogram', 'kde', 'ecdf', 'violin', 'box', 'strip', 'swarm', 'ridge'
        title: Plot title
        xlabel: X-axis label
        ylabel: Y-axis label (auto-generated if None)
        fill: Whether to fill the distribution (for kde/histogram)
        alpha: Transparency level (0-1)
        common_norm: If True, normalize across all groups together
        stat: Statistic for histogram ('count', 'density', 'probability', 'percent', 'frequency')
    """
    # Set seaborn style
    sns.set_theme(style="whitegrid")

    # Build dataframe from groups
    data_records = []
    for group in groups:
        group_name = group["name"]
        for value in group["values"]:
            data_records.append({"Group": group_name, "Value": value})

    df = pd.DataFrame(data_records)

    # Determine number of groups for color palette
    n_groups = len(groups)
    palette = sns.color_palette("husl", n_groups) if n_groups > 1 else None

    # Create figure based on plot type
    if plot_type == "ridge":
        # Ridge plot (multiple kde plots stacked)
        fig, axes = plt.subplots(
            nrows=n_groups,
            ncols=1,
            figsize=(12, 2 * n_groups),
            sharex=True
        )
        if n_groups == 1:
            axes = [axes]

        for idx, (ax, group) in enumerate(zip(axes, groups)):
            color = palette[idx] if palette else sns.color_palette()[0]
            sns.kdeplot(
                data=group["values"],
                ax=ax,
                fill=fill,
                alpha=alpha,
                color=color,
                linewidth=1.5,
            )
            ax.set_ylabel(group["name"], rotation=0, ha="right", va="center")
            ax.set_yticks([])
            if idx < n_groups - 1:
                ax.set_xlabel("")

        axes[-1].set_xlabel(xlabel, fontsize=12)
        fig.suptitle(title, fontsize=14, fontweight="bold", y=1.02)

    else:
        # Standard single-axis plots
        fig, ax = plt.subplots(figsize=(12, 6))

        if plot_type == "histogram":
            sns.histplot(
                data=df,
                x="Value",
                hue="Group" if n_groups > 1 else None,
                palette=palette,
                alpha=alpha,
                stat=stat,
                common_norm=common_norm,
                element="step" if n_groups > 1 else "bars",
                ax=ax,
            )
            default_ylabel = stat.capitalize()

        elif plot_type == "kde":
            sns.kdeplot(
                data=df,
                x="Value",
                hue="Group" if n_groups > 1 else None,
                palette=palette,
                fill=fill,
                alpha=alpha,
                common_norm=common_norm,
                linewidth=2,
                ax=ax,
            )
            default_ylabel = "Density"

        elif plot_type == "ecdf":
            sns.ecdfplot(
                data=df,
                x="Value",
                hue="Group" if n_groups > 1 else None,
                palette=palette,
                linewidth=2,
                ax=ax,
            )
            default_ylabel = "Proportion"

        elif plot_type == "violin":
            sns.violinplot(
                data=df,
                x="Group" if n_groups > 1 else None,
                y="Value",
                hue="Group" if n_groups > 1 else None,
                palette=palette,
                alpha=alpha,
                inner="quart",
                ax=ax,
                legend=False,
            )
            default_ylabel = xlabel
            xlabel = "Group" if n_groups > 1 else ""

        elif plot_type == "box":
            sns.boxplot(
                data=df,
                x="Group" if n_groups > 1 else None,
                y="Value",
                hue="Group" if n_groups > 1 else None,
                palette=palette,
                ax=ax,
                legend=False,
            )
            default_ylabel = xlabel
            xlabel = "Group" if n_groups > 1 else ""

        elif plot_type == "strip":
            sns.stripplot(
                data=df,
                x="Group" if n_groups > 1 else None,
                y="Value",
                hue="Group" if n_groups > 1 else None,
                palette=palette,
                alpha=alpha,
                jitter=True,
                ax=ax,
                legend=False,
            )
            default_ylabel = xlabel
            xlabel = "Group" if n_groups > 1 else ""

        elif plot_type == "swarm":
            sns.swarmplot(
                data=df,
                x="Group" if n_groups > 1 else None,
                y="Value",
                hue="Group" if n_groups > 1 else None,
                palette=palette,
                ax=ax,
                legend=False,
                size=4,
            )
            default_ylabel = xlabel
            xlabel = "Group" if n_groups > 1 else ""

        else:
            raise ValueError(f"Unknown plot_type: {plot_type}")

        # Apply labels
        ax.set_title(title, fontsize=14, fontweight="bold")
        ax.set_xlabel(xlabel, fontsize=12)
        ax.set_ylabel(ylabel if ylabel else default_ylabel, fontsize=12)

        # Seaborn handles legend automatically when hue is used

    # Tight layout and save
    plt.tight_layout()
    plt.savefig(output_file, dpi=150, bbox_inches="tight")
    plt.close()

    print(f"Plot saved to: {output_file}")


def main():
    """Main entry point for the script."""
    if len(sys.argv) < 2:
        print("Usage: python plot_distribution_comparison.py <config_json>")
        print("\nConfig JSON should contain:")
        print('  {"groups": [{"name": "A", "values": [...]}, ...], "output_file": "...", ')
        print('   "plot_type": "kde", "title": "...", "xlabel": "...", ...}')
        sys.exit(1)

    # Load configuration from JSON argument
    config = json.loads(sys.argv[1])

    groups = config["groups"]
    output_file = config.get("output_file", "/tmp/distribution_comparison.png")
    plot_type = config.get("plot_type", "kde")
    title = config.get("title", "Distribution Comparison")
    xlabel = config.get("xlabel", "Value")
    ylabel = config.get("ylabel")
    fill = config.get("fill", True)
    alpha = config.get("alpha", 0.5)
    common_norm = config.get("common_norm", False)
    stat = config.get("stat", "density")

    plot_distribution_comparison(
        groups=groups,
        output_file=output_file,
        plot_type=plot_type,
        title=title,
        xlabel=xlabel,
        ylabel=ylabel,
        fill=fill,
        alpha=alpha,
        common_norm=common_norm,
        stat=stat,
    )


if __name__ == "__main__":
    main()
