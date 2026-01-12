"""
Plot Analytics Sub-Agent

Responsible for creating visualizations from data.
Receives structured data from the orchestrator and generates plots.
"""

from langchain.agents import create_agent
from langchain.agents.middleware import ToolCallLimitMiddleware, SummarizationMiddleware

from utils.skills import load_skill
from utils.skill_tools import plot_historical_data, plot_distribution_comparison


PLOT_ANALYTICS_PROMPT = """You are a data visualization specialist. Your ONLY job is to create plots from data provided by the orchestrator.

## Your Role
- Receive structured data (dates, values, groups) from the orchestrator
- Load the appropriate skill for the visualization type
- Create the visualization using the correct plotting tool
- Return the image_id to the orchestrator

## Available Skills (call load_skill first)
- historical-plotter: For time series line plots (dates + values)
- distribution-comparison: For comparing distributions (KDE, histogram, violin, box, etc.)

## Workflow
1. Analyze the data provided by the orchestrator
2. Call load_skill() for the appropriate visualization type
3. Call the plotting tool with the structured data
4. Return the image_id on success

## Important Rules
1. ALWAYS call load_skill BEFORE using a plot tool
2. Use plot_historical_data for time series with dates
3. Use plot_distribution_comparison for comparing groups/distributions
4. Only create ONE plot per request
5. Return the image_id when done - do NOT describe the plot in detail

## Output Format
After creating the plot, return:
- image_id: The generated plot ID
- title: The plot title
- Brief confirmation message

After completing your task, return results to the orchestrator."""


def create_plot_analytics_agent(model: str = "openai:gpt-4o-mini"):
    """Create the plot analytics sub-agent.

    Args:
        model: Model identifier (default: gpt-4o-mini for efficiency)

    Returns:
        Compiled agent graph
    """
    return create_agent(
        model=model,
        system_prompt=PLOT_ANALYTICS_PROMPT,
        tools=[load_skill, plot_historical_data, plot_distribution_comparison],
        middleware=[
            ToolCallLimitMiddleware(
                tool_name="load_skill",
                run_limit=2,  # May need to load different skills
                exit_behavior="end",
            ),
            ToolCallLimitMiddleware(
                tool_name="plot_historical_data",
                run_limit=1,  # One plot per request
                exit_behavior="end",
            ),
            ToolCallLimitMiddleware(
                tool_name="plot_distribution_comparison",
                run_limit=1,  # One plot per request
                exit_behavior="end",
            ),
            SummarizationMiddleware(
                model=model,
                trigger=("fraction", 0.75),
                keep=("fraction", 0.10),
            ),
        ],
        name="plot_analytics_agent",
    )
