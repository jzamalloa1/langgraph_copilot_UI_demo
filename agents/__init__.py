"""
Multi-agent system with orchestrator and specialized sub-agents.

Architecture:
- Orchestrator (agent.py): Plans work, delegates to sub-agents, does NOT execute tasks directly
- Sub-agents: Specialized agents that execute specific tasks and return results

Sub-agents:
- web-research: Web search and data retrieval (tavily_search)
- plot-analytics: Data visualization and plotting (plot_historical_data, plot_distribution_comparison)
- display-data: Tabular data display (display_table)
"""

from agents.subagents import (
    create_web_research_agent,
    create_plot_analytics_agent,
    create_display_data_agent,
)

__all__ = [
    "create_web_research_agent",
    "create_plot_analytics_agent",
    "create_display_data_agent",
]
