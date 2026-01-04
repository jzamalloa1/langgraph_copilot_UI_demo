from langchain.agents import create_agent
from langchain.agents.middleware.summarization import SummarizationMiddleware
from langchain.agents.middleware import ToolCallLimitMiddleware

from utils.tools import tavily_search
from utils.skills import load_skill, get_skills_summary
from utils.skill_tools import plot_historical_data


SYSTEM_PROMPT = f"""You are a data visualization assistant.
{get_skills_summary()}

## Workflow (call each tool exactly ONCE)
1. tavily_search → get data
2. load_skill("historical-plotter") → get format
3. plot_historical_data → create plot → returns image_id
4. Reply to user with the image_id → STOP

## Critical Rules
- Each tool can only be called ONCE per request
- After plot_historical_data succeeds, immediately reply to user and STOP
- On any error, tell user and STOP"""


agent = create_agent(
    model="openai:gpt-5-nano",
    system_prompt=SYSTEM_PROMPT,
    tools=[tavily_search, load_skill, plot_historical_data],
    middleware=[
        # Limit each tool to 1 call per run to prevent loops
        ToolCallLimitMiddleware(tool_name="tavily_search", run_limit=1, exit_behavior="end"),
        ToolCallLimitMiddleware(tool_name="load_skill", run_limit=1, exit_behavior="end"),
        ToolCallLimitMiddleware(tool_name="plot_historical_data", run_limit=1, exit_behavior="end"),
        SummarizationMiddleware(
            model="openai:gpt-5-nano",
            trigger=("fraction", 0.75),
            keep=("fraction", 0.10),
            trim_tokens_to_summarize=None,
        ),
    ],
).with_config({"recursion_limit": 25})
