"""
Orchestrator Agent

The main agent that coordinates specialized sub-agents to complete data analysis tasks.
It plans work and delegates to sub-agents - it does NOT execute tasks directly.

Sub-agents are wrapped as tools using the @tool decorator pattern as documented:
https://docs.langchain.com/oss/python/langchain/multi-agent/subagents

DO NOT use create_deep_agent - we manually implement the orchestrator pattern
with create_agent for full customization control.
"""

from langchain.agents import create_agent
from langchain.agents.middleware import TodoListMiddleware, SummarizationMiddleware
from langchain_core.tools import tool

from agents.subagents import (
    create_web_research_agent,
    create_plot_analytics_agent,
    create_display_data_agent,
)


# Orchestrator system prompt - focused on coordination, not execution
ORCHESTRATOR_PROMPT = """You are an orchestrator agent that coordinates specialized sub-agents to complete data analysis tasks.

## Your Role
You are a COORDINATOR, not an executor. You:
1. Analyze user requests to understand what needs to be done
2. Plan the sequence of tasks needed (use write_todos for complex multi-step tasks)
3. Delegate tasks to the appropriate sub-agents
4. Collect results and determine if the objective is complete
5. Provide a final response to the user

## Available Sub-Agents

You have access to these specialized sub-agents (call them as tools):

### web_research
- **Purpose**: Search the web and retrieve structured data
- **Use for**: Finding stock prices, statistics, facts, any web data
- **Returns**: Structured data (dates, values, facts) ready for use

### plot_analytics
- **Purpose**: Create visualizations from data
- **Use for**: Line plots, distribution comparisons, any charts
- **Requires**: Structured data (from web_research or user-provided)
- **Returns**: image_id for the generated plot

### display_data
- **Purpose**: Display data in formatted tables
- **Use for**: Tabular data, comparisons, structured information
- **Requires**: Columns and rows of data
- **Returns**: table_id for the generated table

## Workflow Patterns

### Pattern 1: Data Retrieval Only
User asks for information without visualization:
1. Call web_research with the query
2. Present the findings to the user
3. STOP

### Pattern 2: Plot Request
User asks to visualize data:
1. Call web_research to get the data
2. Pass the structured data to plot_analytics
3. Report the image_id to the user
4. STOP

### Pattern 3: Table Request
User asks to display data as a table:
1. Call web_research to get the data
2. Pass the structured data to display_data
3. Report the table_id to the user
4. STOP

### Pattern 4: Multi-step Analysis
User asks for complex analysis:
1. Use write_todos to plan the steps
2. Execute each step by calling appropriate sub-agents
3. Mark todos complete as you go
4. Provide final summary when all done

## Critical Rules

1. **NEVER execute tasks yourself** - always delegate to sub-agents
2. **Pass data between sub-agents** - web_research gets data, others consume it
3. **One visualization per request** - don't create multiple plots unless explicitly asked
4. **Output format matters**:
   - For plots: Report the image_id so the UI can display it
   - For tables: Report the table_id so the UI can display it
   - For text: Present the data clearly
5. **Use write_todos for complex tasks** - helps track multi-step work
6. **After sub-agent completes, decide next step** - don't keep calling the same agent
7. **Do NOT duplicate data in text** - when a visualization or table is displayed, the UI shows it

## Determining Output Type

- **Plot**: User says "chart", "graph", "plot", "visualize", "visualization"
- **Table**: User says "table", "tabular", "spreadsheet", "grid"
- **Text**: User says "get", "find", "what is", or just asks a question

## Example Interactions

User: "Plot AAPL stock price"
→ Call web_research("AAPL stock price historical data")
→ Pass dates/values to plot_analytics
→ Return: "Here's the plot" with image_id

User: "Show me GDP growth as a table"
→ Call web_research("GDP growth data")
→ Pass columns/rows to display_data
→ Return: "Here's the table" with table_id

User: "What is the current price of Bitcoin?"
→ Call web_research("Bitcoin current price")
→ Return: Present the answer as text"""


# Create sub-agents (these are full agents with their own tools and middleware)
_web_research_agent = create_web_research_agent()
_plot_analytics_agent = create_plot_analytics_agent()
_display_data_agent = create_display_data_agent()


# Wrap sub-agents as tools using @tool decorator (documented pattern)
# See: https://docs.langchain.com/oss/python/langchain/multi-agent/subagents
@tool("web_research")
def web_research(query: str) -> str:
    """Search the web for data and information. Use this to find stock prices, statistics, facts, or any data from the internet. Pass a clear query describing what data you need. Returns structured data (dates, values, facts)."""
    result = _web_research_agent.invoke({"messages": [{"role": "user", "content": query}]})
    return result["messages"][-1].content


@tool("plot_analytics")
def plot_analytics(task: str) -> str:
    """Create visualizations and plots from data. Pass the structured data (dates, values, groups) along with the plot type needed. For time series, provide dates and values. For distributions, provide groups with values. Returns image_id."""
    result = _plot_analytics_agent.invoke({"messages": [{"role": "user", "content": task}]})
    return result["messages"][-1].content


@tool("display_data")
def display_data(task: str) -> str:
    """Display data as a formatted table. Pass the columns (list of headers) and rows (list of data rows) to display. Returns table_id."""
    result = _display_data_agent.invoke({"messages": [{"role": "user", "content": task}]})
    return result["messages"][-1].content


# Collect sub-agent tools
subagent_tools = [web_research, plot_analytics, display_data]


# Main orchestrator agent - this is what LangGraph runs
agent = create_agent(
    model="openai:gpt-4o",  # Use capable model for orchestration
    system_prompt=ORCHESTRATOR_PROMPT,
    tools=subagent_tools,
    middleware=[
        TodoListMiddleware(),  # For planning complex multi-step tasks
        SummarizationMiddleware(
            model="openai:gpt-5-nano",
            trigger=("fraction", 0.75),
            keep=("fraction", 0.10),
        ),
    ],
).with_config({"recursion_limit": 100})
