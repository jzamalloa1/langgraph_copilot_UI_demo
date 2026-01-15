"""
Specialized sub-agents for the multi-agent system.

Each sub-agent:
- Has a focused responsibility
- Owns specific tools
- Uses progressive disclosure for skills
- Returns results to the orchestrator
"""

from agents.subagents.web_research import create_web_research_agent
from agents.subagents.plot_analytics import create_plot_analytics_agent
from agents.subagents.display_data import create_display_data_agent
from agents.subagents.document_analysis import create_document_analysis_agent

__all__ = [
    "create_web_research_agent",
    "create_plot_analytics_agent",
    "create_display_data_agent",
    "create_document_analysis_agent",
]
