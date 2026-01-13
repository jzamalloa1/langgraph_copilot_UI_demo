"""
Display Data Sub-Agent

Responsible for displaying tabular data.
Receives structured data from the orchestrator and generates tables.
"""

from langchain.agents import create_agent
from langchain.agents.middleware import ToolCallLimitMiddleware, SummarizationMiddleware

from utils.skills import load_skill
from utils.skill_tools import display_table


DISPLAY_DATA_PROMPT = """You are a data display specialist. Your ONLY job is to create formatted tables from data provided by the orchestrator.

## Your Role
- Receive structured data (columns, rows) from the orchestrator
- Load the table-display skill for formatting guidance
- Create the table using display_table
- Return the table_id to the orchestrator

## Available Skills (call load_skill first)
- table-display: For formatted tabular data display

## Workflow
1. Analyze the data provided by the orchestrator
2. Call load_skill("table-display") for formatting guidance
3. Call display_table with columns and rows
4. Return the table_id on success

## Important Rules
1. ALWAYS call load_skill("table-display") BEFORE using display_table
2. Ensure columns and rows are properly structured
3. Only create ONE table per request
4. Return the table_id when done - do NOT repeat the table data

## Output Format
After creating the table, return:
- table_id: The generated table ID
- title: The table title
- Brief confirmation message

After completing your task, return results to the orchestrator."""


def create_display_data_agent(model: str = "openai:gpt-4o-mini"):
    """Create the display data sub-agent.

    Args:
        model: Model identifier (default: gpt-4o-mini for efficiency)

    Returns:
        Compiled agent graph
    """
    return create_agent(
        model=model,
        system_prompt=DISPLAY_DATA_PROMPT,
        tools=[load_skill, display_table],
        middleware=[
            ToolCallLimitMiddleware(
                tool_name="load_skill",
                run_limit=1,
                exit_behavior="end",
            ),
            ToolCallLimitMiddleware(
                tool_name="display_table",
                run_limit=1,  # One table per request
                exit_behavior="end",
            ),
            SummarizationMiddleware(
                model=model,
                trigger=("fraction", 0.75),
                keep=("fraction", 0.10),
            ),
        ],
        name="display_data_agent",
    )
