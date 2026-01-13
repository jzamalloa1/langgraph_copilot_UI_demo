# Deep Agent V2 - Claude Code Guide

Multi-agent data analysis system with orchestrator pattern, progressive disclosure skills, and CopilotKit Generative UI integration.

## Quick Start

```bash
# Backend (LangGraph) - from deep-agent-v2/
uv run langgraph dev

# Frontend (CopilotKit) - from deep-agent-v2/copilot-deepagent-app/
npm run dev
```

Required environment variables in `.env`:
- `TAVILY_API_KEY` - For web search
- `OPENAI_API_KEY` - For LLM

Frontend env in `copilot-deepagent-app/.env`:
- `LANGGRAPH_DEPLOYMENT_URL` - LangGraph server URL
- `LANGSMITH_API_KEY` - LangSmith API key

## Multi-Agent Architecture

**IMPORTANT**: DO NOT use `create_deep_agent` from langchain. We manually implement the orchestrator pattern using `create_agent` for full customization control.

**Sub-agent Pattern**: Sub-agents are wrapped as tools using the `@tool` decorator as documented at:
https://docs.langchain.com/oss/python/langchain/multi-agent/subagents

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           ORCHESTRATOR (agent.py)                            │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │ create_agent with TodoListMiddleware                                    ││
│  │ - Plans work using write_todos                                          ││
│  │ - Delegates to sub-agents (does NOT execute tasks directly)             ││
│  │ - Collects results and determines completion                            ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                    │                                         │
│              ┌─────────────────────┼─────────────────────┐                  │
│              ▼                     ▼                     ▼                  │
│  ┌───────────────────┐ ┌───────────────────┐ ┌───────────────────┐         │
│  │   web_research    │ │  plot_analytics   │ │   display_data    │         │
│  │   (sub-agent)     │ │   (sub-agent)     │ │   (sub-agent)     │         │
│  ├───────────────────┤ ├───────────────────┤ ├───────────────────┤         │
│  │ Tools:            │ │ Tools:            │ │ Tools:            │         │
│  │ - tavily_search   │ │ - load_skill      │ │ - load_skill      │         │
│  │                   │ │ - plot_historical │ │ - display_table   │         │
│  │                   │ │ - plot_distrib..  │ │                   │         │
│  └───────────────────┘ └───────────────────┘ └───────────────────┘         │
│                                    │                                         │
└────────────────────────────────────┼─────────────────────────────────────────┘
                                     │ subprocess.run() breaks out to host
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              HOST MACHINE                                    │
│  ├── utils/scripts/*.py    → External scripts (matplotlib, seaborn)        │
│  ├── /tmp/plots/           → Generated images                              │
│  ├── /tmp/tables/          → Generated table JSON                          │
│  └── copilot-deepagent-app/                                                 │
│      ├── app/api/images/   → Serves /tmp/plots/ to browser                 │
│      ├── app/api/tables/   → Serves /tmp/tables/ to browser                │
│      └── app/components/   → React components                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Key Design Principles

1. **Orchestrator doesn't execute** - Only plans and delegates to sub-agents
2. **Sub-agents are tools** - Wrapped with `@tool` decorator and passed to orchestrator
3. **Progressive disclosure at sub-agent level** - Skills loaded on-demand within sub-agents
4. **Context quarantine** - Sub-agent tool calls don't clutter orchestrator context
5. **Defensive UI rendering** - Always guard against empty/null values before rendering images

### Sub-Agent Definitions

Each sub-agent is created with `create_agent` and has its own:
- System prompt focused on its specialty
- Tools specific to its domain
- Middleware for limits and summarization

```python
# agents/subagents/web_research.py
def create_web_research_agent(model: str = "openai:gpt-4o-mini"):
    return create_agent(
        model=model,
        system_prompt=WEB_RESEARCH_PROMPT,
        tools=[tavily_search],
        middleware=[
            ToolCallLimitMiddleware(tool_name="tavily_search", run_limit=5, exit_behavior="end"),
            SummarizationMiddleware(...),
        ],
        name="web_research_agent",
    )
```

### Converting Sub-Agents to Tools

Sub-agents are wrapped as tools using the `@tool` decorator (documented pattern):

```python
# In agent.py
from langchain_core.tools import tool

# Create sub-agents
_web_research_agent = create_web_research_agent()

# Wrap as tool using @tool decorator
# See: https://docs.langchain.com/oss/python/langchain/multi-agent/subagents
@tool("web_research")
def web_research(query: str) -> str:
    """Search the web for data. Returns structured data (dates, values, facts)."""
    result = _web_research_agent.invoke({"messages": [{"role": "user", "content": query}]})
    return result["messages"][-1].content

# Pass to orchestrator
agent = create_agent(
    model="openai:gpt-4o",
    system_prompt=ORCHESTRATOR_PROMPT,
    tools=[web_research, plot_analytics, display_data],
    middleware=[TodoListMiddleware(), SummarizationMiddleware(...)],
)
```

## Key Patterns

### 0. CopilotKit-First UI Development

**IMPORTANT**: Before building any custom UI components, ALWAYS check CopilotKit's built-in features first:

1. **Check CopilotKit hooks**: `useRenderToolCall`, `useFrontendTool`, `useCoAgentStateRender`
2. **Check CopilotKit components**: `CopilotChat`, `CopilotPopup`, `CopilotSidebar`, `Markdown`, `ImageRenderer`
3. **Check node_modules types**: `@copilotkit/react-core` and `@copilotkit/react-ui` for available props

CopilotKit provides the Generative UI pattern through `useRenderToolCall` - use this to render custom components inline in the chat for tool results. Only create custom components (like `TableDisplay.tsx`) when CopilotKit doesn't have a built-in equivalent.

### 1. Progressive Disclosure

Skills are disclosed in two levels to minimize context usage:

1. **Sub-agent prompt** - Sub-agent knows which skills it can load
2. **On-demand** - Full instructions loaded via `load_skill("skill-name")`
3. **Scripts** - NEVER loaded into context; executed via subprocess

### 2. Two-File Skill Pattern

Each skill that generates output uses two files:

| File | Role | Runs In |
|------|------|---------|
| `utils/skill_tools.py::tool_name()` | LangChain Tool - orchestrates workflow | LangGraph sandbox |
| `utils/scripts/tool_name.py` | External Script - does actual work | Host machine |

The tool validates inputs, generates IDs, calls the script via `subprocess.run()`, and returns metadata.
The script receives JSON config, does heavy work (matplotlib, etc.), saves output to `/tmp/`.

### 3. TodoListMiddleware for Orchestrator

The orchestrator uses `TodoListMiddleware` to plan complex multi-step tasks:

```python
from langchain.agents.middleware import TodoListMiddleware

agent = create_agent(
    model="openai:gpt-4o",
    system_prompt=ORCHESTRATOR_PROMPT,
    tools=subagent_tools,
    middleware=[
        TodoListMiddleware(),  # Provides write_todos tool for planning
        SummarizationMiddleware(...),
    ],
)
```

The orchestrator can use `write_todos` to plan steps, mark progress, and ensure complex tasks are completed.

### 4. Frontend Tool Result Rendering

`useRenderToolCall` hook intercepts backend tool results for custom rendering:

```typescript
useRenderToolCall({
  name: "plot_historical_data",
  render: ({ result, status }) => {
    if (status === "complete" && result?.image_id) {
      return <img src={`/api/images/${result.image_id}`} />;
    }
  },
});
```

Note: There's a known bug (Issue #2622) where `useRenderToolCall` may not fire during LangGraph streaming. Use `useCopilotChat().isLoading` as workaround for activity indication.

## File Structure

```
deep-agent-v2/
├── agent.py                    # Orchestrator agent with sub-agents as tools
├── langgraph.json              # LangGraph entry point config
├── pyproject.toml              # Python deps (uv)
├── agents/                     # Multi-agent system
│   ├── __init__.py
│   └── subagents/
│       ├── __init__.py
│       ├── web_research.py     # Web search sub-agent (tavily_search)
│       ├── plot_analytics.py   # Plotting sub-agent (plot tools + skills)
│       └── display_data.py     # Table display sub-agent (display_table + skill)
├── utils/
│   ├── skills.py               # Skill loading (progressive disclosure)
│   ├── skills.md               # Skill definitions (YAML frontmatter)
│   ├── skill_tools.py          # LangChain tool implementations
│   ├── tools.py                # tavily_search and other tools
│   └── scripts/
│       ├── plot_historical_data.py       # External matplotlib script
│       ├── plot_distribution_comparison.py  # Seaborn distribution plots
│       └── render_table.py               # Table data generation
└── copilot-deepagent-app/      # Next.js frontend
    ├── app/
    │   ├── api/
    │   │   ├── copilotkit/route.ts  # CopilotKit runtime
    │   │   ├── images/[filename]/   # Serves /tmp/plots/
    │   │   └── tables/[tableId]/    # Serves /tmp/tables/
    │   ├── components/
    │   │   ├── GenerativeUIDemo.tsx # Main UI with useRenderToolCall hooks
    │   │   ├── ImageDisplay.tsx     # Image gallery component
    │   │   └── TableDisplay.tsx     # Table rendering component
    │   ├── page.tsx
    │   └── globals.css         # Contains CopilotKit scrolling fix
    └── package.json
```

## Creating a New Sub-Agent

### Step 1: Create the Sub-Agent File

Create `agents/subagents/your_agent.py`:

```python
"""
Your Agent Description

Responsible for [specific domain].
"""

from langchain.agents import create_agent
from langchain.agents.middleware import ToolCallLimitMiddleware, SummarizationMiddleware

from utils.your_tools import your_tool


YOUR_AGENT_PROMPT = """You are a [specialty] specialist. Your ONLY job is to [specific task].

## Your Role
- [What this agent does]
- [What data it returns]

## Important Rules
1. ONLY use your assigned tools
2. Return structured results to the orchestrator
3. After completing your task, STOP

After completing your task, return your findings to the orchestrator."""


def create_your_agent(model: str = "openai:gpt-4o-mini"):
    return create_agent(
        model=model,
        system_prompt=YOUR_AGENT_PROMPT,
        tools=[your_tool],
        middleware=[
            ToolCallLimitMiddleware(tool_name="your_tool", run_limit=1, exit_behavior="end"),
            SummarizationMiddleware(model=model, trigger=("fraction", 0.75), keep=("fraction", 0.10)),
        ],
        name="your_agent",
    )
```

### Step 2: Register in agents/__init__.py

```python
from agents.subagents.your_agent import create_your_agent

__all__ = [
    # ... existing exports
    "create_your_agent",
]
```

### Step 3: Add to Orchestrator

In `agent.py`:

```python
from agents.subagents import create_your_agent

_your_agent = create_your_agent()

subagent_tools = [
    # ... existing sub-agents
    _your_agent.as_tool(
        name="your_agent",
        description="Description of what this agent does and returns.",
    ),
]
```

### Step 4: Update Orchestrator Prompt

Add your new sub-agent to the `ORCHESTRATOR_PROMPT` in `agent.py`:

```python
### your_agent
- **Purpose**: What it does
- **Use for**: When to use it
- **Returns**: What it returns
```

## Creating a New Skill (for existing sub-agents)

### Step 1: Create the External Script

Create `utils/scripts/your_skill.py`:

```python
#!/usr/bin/env python3
import sys
import json

def main():
    config = json.loads(sys.argv[1])
    output_file = config['output_file']
    # Do actual work here
    print(f"Output saved to: {output_file}")

if __name__ == "__main__":
    main()
```

### Step 2: Create the LangChain Tool

Add to `utils/skill_tools.py`:

```python
@tool(parse_docstring=True)
def your_skill_tool(param1: str) -> dict:
    """Brief description. Load skill 'your-skill' for usage details."""
    # Validate, generate ID, call script, return metadata
```

### Step 3: Add to Appropriate Sub-Agent

In the relevant sub-agent file (e.g., `agents/subagents/plot_analytics.py`):

```python
from utils.skill_tools import your_skill_tool

# Add to tools list
tools=[load_skill, plot_historical_data, your_skill_tool],

# Add ToolCallLimitMiddleware
ToolCallLimitMiddleware(tool_name="your_skill_tool", run_limit=1, exit_behavior="end"),
```

### Step 4: Add Skill Documentation

Add to `utils/skills.md`:

```markdown
---
name: your-skill
description: One-line description.
---

Call `your_skill_tool` with:
- param1: description

Example:
\```
your_skill_tool(param1="value")
\```
```

## Common Issues

### Chatbox grows infinitely instead of scrolling

The fix is in `globals.css`:

```css
.copilotKitChat {
  display: flex !important;
  flex-direction: column !important;
  height: 100% !important;
}
.copilotKitMessages {
  flex: 1 1 0% !important;
  min-height: 0 !important;
  overflow-y: auto !important;
}
.copilotKitInput {
  flex: 0 0 auto !important;
}
```

### CopilotKit recursion limit issues

Set recursion_limit in **three places**:

1. **Backend** (`agent.py`): `.with_config({"recursion_limit": 100})`
2. **CopilotKit Runtime** (`route.ts`): `assistantConfig: { recursion_limit: 100 }`
3. **Frontend** (`useCoAgent`): `config: { recursion_limit: 100 }`

### Images/Tables not displaying in UI

1. Check script saves to `/tmp/plots/` or `/tmp/tables/`
2. Check API routes read from correct paths
3. Check `useRenderToolCall` returns correct component

### Empty `src` attribute error in CopilotChat

**Problem**: React error "An empty string was passed to the src attribute" when CopilotKit renders markdown images or tool results with empty URLs.

**Solution**: Apply defensive rendering at multiple levels:

1. **Custom markdown renderer** - Override CopilotChat's default image rendering:

```typescript
// Guard against empty URLs in markdown images
const safeMarkdownComponents = {
  img: ({ src, alt, ...props }: { src?: string; alt?: string; [key: string]: unknown }) => {
    if (!src || typeof src !== "string" || src.trim() === "") {
      return null;
    }
    return <img src={src} alt={alt || "Image"} {...props} />;
  },
};

<CopilotChat
  markdownTagRenderers={safeMarkdownComponents}
  // ... other props
/>
```

2. **Component-level guards** - Always validate URLs before rendering `<img>` tags:

```typescript
// In ImageDisplay.tsx or any image component
if (!url || url.trim() === "") {
  return null;
}
```

3. **Safe result parsing** - Handle undefined/null results from tool calls:

```typescript
function resultToString(result: unknown): string {
  if (result === null || result === undefined) return "";
  if (typeof result === "string") return result;
  try { return JSON.stringify(result); } catch { return ""; }
}
```

### Sub-agent tool rendering in orchestrator architecture

**Problem**: When using orchestrator pattern, the frontend sees orchestrator-level tools (`web_research`, `plot_analytics`, `display_data`) NOT inner tools (`plot_historical_data`, `tavily_search`).

**Solution**:
1. Only register `useRenderToolCall` hooks for orchestrator-level tools
2. Extract IDs from sub-agent text responses using regex patterns:

```typescript
const extractImageId = (text: string | null | undefined): string | null => {
  if (!text) return null;
  const patterns = [
    /image_id[:\s]+["']?([a-zA-Z]+_[a-f0-9]+)["']?/i,
    /\b(plot_[a-f0-9]+)\b/i,
  ];
  for (const pattern of patterns) {
    const match = text.match(pattern);
    if (match) return match[1];
  }
  return null;
};
```

## Available Sub-Agents

### web_research
Searches the web for data using Tavily. Returns structured data.

### plot_analytics
Creates visualizations using matplotlib/seaborn. Skills:
- `historical-plotter`: Time series line plots
- `distribution-comparison`: KDE, histogram, violin, box plots

### display_data
Displays tabular data. Skills:
- `table-display`: Formatted tables

## Dependencies

- Python 3.13+, managed with `uv`
- Key packages: `langgraph`, `langchain`, `copilotkit`, `matplotlib`, `seaborn`, `pandas`, `tavily`
- Frontend: Next.js 15, React 19, CopilotKit
