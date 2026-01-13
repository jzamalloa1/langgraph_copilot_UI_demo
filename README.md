# Deep Agent V2

A multi-agent LangGraph system with orchestrator pattern, progressive disclosure skills, and Generative UI integration.

## Architecture Overview

This project uses a **multi-agent orchestrator pattern** where a main orchestrator agent coordinates specialized sub-agents:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           ORCHESTRATOR (agent.py)                            │
│  - Plans work using TodoListMiddleware                                       │
│  - Delegates to sub-agents (does NOT execute tasks directly)                 │
│  - Collects results and determines completion                                │
│                                                                              │
│              ┌─────────────────────┬─────────────────────┐                  │
│              ▼                     ▼                     ▼                  │
│  ┌───────────────────┐ ┌───────────────────┐ ┌───────────────────┐         │
│  │   web_research    │ │  plot_analytics   │ │   display_data    │         │
│  │   (sub-agent)     │ │   (sub-agent)     │ │   (sub-agent)     │         │
│  ├───────────────────┤ ├───────────────────┤ ├───────────────────┤         │
│  │ • tavily_search   │ │ • plot_historical │ │ • display_table   │         │
│  │                   │ │ • plot_distrib..  │ │                   │         │
│  └───────────────────┘ └───────────────────┘ └───────────────────┘         │
└─────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼ subprocess.run()
┌─────────────────────────────────────────────────────────────────────────────┐
│                              HOST MACHINE                                    │
│  • utils/scripts/*.py → External scripts (matplotlib, seaborn)              │
│  • /tmp/plots/, /tmp/tables/ → Generated outputs                            │
│  • copilot-deepagent-app/ → Next.js frontend with CopilotKit                │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Key Solutions

### 1. Multi-Agent Orchestration

**Pattern**: Orchestrator delegates to specialized sub-agents, each with focused responsibilities.

```python
from langchain.agents import create_agent
from langchain.agents.middleware import TodoListMiddleware
from langchain_core.tools import tool

# Create sub-agents
_web_research_agent = create_web_research_agent()

# Wrap sub-agents as tools using @tool decorator
# See: https://docs.langchain.com/oss/python/langchain/multi-agent/subagents
@tool("web_research")
def web_research(query: str) -> str:
    """Search the web for data. Returns structured data."""
    result = _web_research_agent.invoke({"messages": [{"role": "user", "content": query}]})
    return result["messages"][-1].content

# Orchestrator uses sub-agents as tools
agent = create_agent(
    model="openai:gpt-4o",
    system_prompt=ORCHESTRATOR_PROMPT,
    tools=[web_research, plot_analytics, display_data],
    middleware=[TodoListMiddleware()],
)
```

### 2. Agent Tool Looping Prevention

**Problem**: Agent repeatedly calls the same tools despite prompt instructions to stop.

**Solution**: `ToolCallLimitMiddleware` enforces hard limits at the framework level within each sub-agent.

### 3. Displaying Backend Tool Results in UI

**Solution**: Use `useRenderToolCall` hook to intercept backend tool results and render them:

```typescript
useRenderToolCall({
  name: "plot_analytics",  // Orchestrator-level tool name
  render: ({ result, status }) => {
    const resultText = resultToString(result);
    const imageId = extractImageId(resultText);
    if (status === "complete" && imageId) {
      return <img src={`/api/images/${imageId}`} />;
    }
  },
});
```

### 4. Defensive UI Rendering

**Problem**: Empty `src` attributes cause React errors when CopilotKit renders markdown or tool results.

**Solution**: Guard against empty URLs at multiple levels:

```typescript
// Custom markdown renderer for CopilotChat
const safeMarkdownComponents = {
  img: ({ src, alt }) => {
    if (!src || src.trim() === "") return null;
    return <img src={src} alt={alt || "Image"} />;
  },
};

<CopilotChat markdownTagRenderers={safeMarkdownComponents} />
```

## Progressive Disclosure

Skills use a two-level disclosure pattern:

1. **Sub-agent prompt** - Sub-agent knows which skills it can load
2. **Full instructions** loaded on-demand via `load_skill()`
3. **Script code** is NEVER loaded into context - executed via subprocess

This keeps the agent's context window small while maintaining full functionality.

## Running the System

### Backend (LangGraph)
```bash
cd deep-agent-v2
uv run langgraph dev
```

### Frontend (CopilotKit)
```bash
cd deep-agent-v2/copilot-deepagent-app
npm run dev
```

## Available Sub-Agents

| Sub-Agent | Purpose | Tools/Skills |
|-----------|---------|--------------|
| `web_research` | Web search and data retrieval | `tavily_search` |
| `plot_analytics` | Data visualization | `historical-plotter`, `distribution-comparison` |
| `display_data` | Tabular data display | `table-display` |

## File Structure

```
deep-agent-v2/
├── agent.py                    # Orchestrator agent
├── agents/                     # Multi-agent system
│   └── subagents/
│       ├── web_research.py     # Web search sub-agent
│       ├── plot_analytics.py   # Plotting sub-agent
│       └── display_data.py     # Table display sub-agent
├── utils/
│   ├── skills.py               # Skill loading
│   ├── skills.md               # Skill definitions
│   ├── skill_tools.py          # Tool implementations
│   ├── tools.py                # tavily_search
│   └── scripts/                # External scripts (matplotlib, etc.)
├── copilot-deepagent-app/      # Next.js frontend
│   └── app/
│       ├── api/                # API routes for images/tables
│       └── components/         # React components
└── langgraph.json              # LangGraph configuration
```

For detailed development guidance, see [CLAUDE.md](CLAUDE.md).
