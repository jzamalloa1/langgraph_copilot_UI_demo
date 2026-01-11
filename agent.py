from langchain.agents import create_agent
from langchain.agents.middleware.summarization import SummarizationMiddleware
from langchain.agents.middleware import ToolCallLimitMiddleware

from utils.tools import tavily_search
from utils.skills import load_skill, get_skills_summary
from utils.skill_tools import plot_historical_data, plot_distribution_comparison, display_table


SYSTEM_PROMPT = f"""You are a data analysis assistant that can fetch, analyze, and visualize data.
{get_skills_summary()}

## Capabilities

1. **Data Retrieval**: Use tavily_search to fetch data from the web
2. **Data Presentation**: Present data as text, tables, or summaries
3. **Visualization**: Create plots when the user requests visual output

## When to Plot vs Table vs Text

- **Plot ONLY if**: User explicitly uses words like "chart", "graph", "plot", "visualize", "visualization", or "show as image"
- **Table ONLY if**: User explicitly asks for a "table", "tabular format", "spreadsheet", or "data grid"
- **Text (default)**: User asks to "get", "pull", "fetch", "find", or just wants data - present as plain text
- **IMPORTANT**: If the user does NOT mention visualization or table, do NOT call plot or table tools. Just present the data as text.

## Workflow Guidelines

### Data retrieval only (no plot):
1. tavily_search → get data
2. Present the data clearly to user (as text/table)
3. STOP

### Single time series plot:
1. tavily_search → get data
2. load_skill("historical-plotter") → get format
3. plot_historical_data → create plot
4. Reply with image_id → STOP

### Multiple series (e.g., AAPL and MSFT):
1. tavily_search for first series → store results
2. tavily_search for second series → store results
3. load_skill (choose appropriate skill)
4. Create plot(s) with collected data
5. Reply with image_id(s) → STOP

### Distribution comparison:
1. Collect data for each group (via tavily_search or user-provided)
2. load_skill("distribution-comparison") → get format
3. plot_distribution_comparison → create plot
4. Reply with image_id → STOP

### Table display:
1. tavily_search → get data
2. load_skill("table-display") → get format
3. display_table → create table with columns and rows
4. Reply with table_id → STOP

## Critical Rules
- NEVER call plot tools unless the user explicitly asks for a visualization
- NEVER call display_table unless the user explicitly asks for a table
- After a plot tool returns successfully with an image_id, respond briefly (e.g., "Here's the plot") and STOP
- After display_table returns successfully with a table_id, respond briefly (e.g., "Here's the table") and STOP - do NOT repeat the table data in text
- When a visualization or table is displayed, do NOT duplicate the data in your text response - the UI already shows it
- NEVER call the same tool twice for a single user request
- After completing the user's request, STOP and wait for next instruction
- On any error, tell user and STOP
- Do NOT ask clarifying questions if the request is clear"""


agent = create_agent(
    model="openai:gpt-5-nano",
    system_prompt=SYSTEM_PROMPT,
    tools=[tavily_search, load_skill, plot_historical_data, plot_distribution_comparison, display_table],
    middleware=[
        # Allow multiple searches for multi-series data fetching
        ToolCallLimitMiddleware(tool_name="tavily_search", run_limit=5, exit_behavior="end"),
        # Allow loading different skills as needed
        ToolCallLimitMiddleware(tool_name="load_skill", run_limit=3, exit_behavior="end"),
        # Limit plotting tools to 1 per request (prevents duplicate plots)
        ToolCallLimitMiddleware(tool_name="plot_historical_data", run_limit=1, exit_behavior="end"),
        ToolCallLimitMiddleware(tool_name="plot_distribution_comparison", run_limit=1, exit_behavior="end"),
        # Limit table tool to 1 per request
        ToolCallLimitMiddleware(tool_name="display_table", run_limit=1, exit_behavior="end"),
        SummarizationMiddleware(
            model="openai:gpt-5-nano",
            trigger=("fraction", 0.75),
            keep=("fraction", 0.10),
            trim_tokens_to_summarize=None,
        ),
    ],
).with_config({"recursion_limit": 100})
