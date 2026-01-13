"""
Web Research Sub-Agent

Responsible for web search and data retrieval using Tavily.
Returns structured data to the orchestrator for further processing.
"""

from langchain.agents import create_agent
from langchain.agents.middleware import ToolCallLimitMiddleware, SummarizationMiddleware

from utils.tools import tavily_search


WEB_RESEARCH_PROMPT = """You are a web research specialist. Your ONLY job is to search the web and return structured data.

## Your Role
- Search the web for information requested by the orchestrator
- Extract and structure relevant data (dates, values, facts, statistics)
- Return data in a clear, organized format that can be used by other agents

## Important Rules
1. ONLY use tavily_search - you have no other tools
2. Extract relevant data points from search results
3. Return data in structured format (lists, key-value pairs)
4. Do NOT visualize or display data - just retrieve and return it
5. After completing the search, summarize findings and STOP

## Output Format
When returning data, structure it clearly:
- For time series: list dates and corresponding values
- For comparisons: list items with their attributes
- For facts: list key points with sources

After completing your task, return your findings to the orchestrator."""


def create_web_research_agent(model: str = "openai:gpt-4o-mini"):
    """Create the web research sub-agent.

    Args:
        model: Model identifier (default: gpt-4o-mini for efficiency)

    Returns:
        Compiled agent graph
    """
    return create_agent(
        model=model,
        system_prompt=WEB_RESEARCH_PROMPT,
        tools=[tavily_search],
        middleware=[
            ToolCallLimitMiddleware(
                tool_name="tavily_search",
                run_limit=5,  # Allow multiple searches for comprehensive research
                exit_behavior="end",
            ),
            SummarizationMiddleware(
                model=model,
                trigger=("fraction", 0.75),
                keep=("fraction", 0.10),
            ),
        ],
        name="web_research_agent",
    )
