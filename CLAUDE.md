# Deep Agent V2 - Claude Code Guide

LangGraph data analysis agent with progressive disclosure skills and CopilotKit Generative UI integration.

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

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     LangGraph Sandbox                           │
│  Agent runs here with isolated /tmp                             │
│  ├── agent.py          → create_agent with tools                │
│  ├── utils/skills.py   → load_skill, get_skills_summary         │
│  └── utils/skill_tools.py → LangChain tools (orchestrators)     │
│                                                                  │
│  subprocess.run() breaks out to host machine ──────────────────┐│
└────────────────────────────────────────────────────────────────┼┘
                                                                  │
┌─────────────────────────────────────────────────────────────────▼┐
│                        Host Machine                              │
│  ├── utils/scripts/*.py    → External scripts (matplotlib, etc) │
│  ├── /tmp/plots/           → Generated images                   │
│  └── copilot-deepagent-app/                                     │
│      ├── app/api/images/   → Serves /tmp/plots/ to browser      │
│      └── app/components/   → React components                   │
└──────────────────────────────────────────────────────────────────┘
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

1. **System prompt** - Only skill names and one-line descriptions via `get_skills_summary()`
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

### 3. Tool Call Limits

`ToolCallLimitMiddleware` enforces limits at framework level to prevent infinite loops while allowing multi-step workflows:

```python
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
]
```

The limits are set to support common workflows like fetching data for multiple stocks (AAPL, MSFT, etc.) while preventing duplicate outputs.

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
├── agent.py                    # Agent configuration with create_agent
├── langgraph.json              # LangGraph entry point config
├── pyproject.toml              # Python deps (uv)
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

## Creating a New Skill

### Step 1: Create the External Script

Create `utils/scripts/your_skill.py`:

```python
#!/usr/bin/env python3
import sys
import json

def main():
    config = json.loads(sys.argv[1])
    # Do actual work here (plotting, file generation, etc.)
    output_file = config['output_file']
    # Save output to output_file
    print(f"Output saved to: {output_file}")

if __name__ == "__main__":
    main()
```

### Step 2: Create the LangChain Tool

Add to `utils/skill_tools.py`:

```python
@tool(parse_docstring=True)
def your_skill_tool(param1: str, param2: list[float]) -> dict:
    """Brief description. Load skill 'your-skill' for usage details.

    Args:
        param1: Description
        param2: Description

    Returns:
        Dictionary with output_id for retrieval
    """
    # Validate inputs
    if not param1:
        return {"type": "error", "message": "param1 cannot be empty"}

    # Generate unique ID
    output_id = f"output_{uuid.uuid4().hex[:8]}"
    output_path = OUTPUT_DIR / f"{output_id}.png"

    config = {"param1": param1, "param2": param2, "output_file": str(output_path)}

    script_path = SCRIPTS_DIR / "your_skill.py"
    result = subprocess.run(
        ["python3", str(script_path), json.dumps(config)],
        capture_output=True, text=True, timeout=30
    )

    if result.returncode != 0:
        return {"type": "error", "message": result.stderr.strip()}

    # Store metadata
    _store_image_metadata(output_id, {"path": str(output_path), ...})

    return {"type": "output", "status": "success", "output_id": output_id}
```

### Step 3: Register the Tool

In `agent.py`:

1. Add the tool to the import line:
```python
from utils.skill_tools import plot_historical_data, plot_distribution_comparison, your_skill_tool
```

2. Add to the `tools` list and add a `ToolCallLimitMiddleware` entry:
```python
agent = create_agent(
    tools=[tavily_search, load_skill, plot_historical_data, plot_distribution_comparison, your_skill_tool],
    middleware=[
        # ... existing middleware ...
        ToolCallLimitMiddleware(tool_name="your_skill_tool", run_limit=1, exit_behavior="end"),
    ],
)
```

3. Update the `SYSTEM_PROMPT` to include workflow instructions for the new skill.

### Step 4: Add Dependencies (if needed)

If your script requires new packages, add them to `pyproject.toml`:

```toml
dependencies = [
    # ... existing deps ...
    "your-package>=1.0.0",
]
```

Then run `uv sync` to install.

### Step 5: Add Skill Documentation

Add a new skill entry to `utils/skills.md`. The file supports multiple skills, each separated by YAML frontmatter blocks:

```markdown
---
name: existing-skill
description: Existing skill description.
---

Existing skill content...

---
name: your-skill
description: One-line description of what this skill does.
---

Call `your_skill_tool` with:
- param1: description
- param2: description

Example:
\```
your_skill_tool(param1="value", param2=[1.0, 2.0])
\```
```

Each skill entry starts with `---`, followed by `name:` and `description:` fields, then another `---`, and finally the skill instructions. The parser automatically discovers all skills in the file.

### Step 6: Frontend Rendering (if applicable)

If your tool returns an `image_id`, the existing `useRenderToolCall` hook for `plot_historical_data` already handles image rendering via `/api/images/[image_id]`. For tools returning different types of visual content, add a new `useRenderToolCall` hook in the frontend:

```typescript
useRenderToolCall({
  name: "your_skill_tool",
  render: ({ result, status }) => {
    if (status === "complete" && result?.output_id) {
      return <YourCustomComponent data={result} />;
    }
  },
});
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
  min-height: 0 !important;  /* Critical for flex scrolling */
  overflow-y: auto !important;
}
.copilotKitInput {
  flex: 0 0 auto !important;
}
```

### Agent keeps calling the same tool repeatedly

Use `ToolCallLimitMiddleware` in `agent.py`. The `exit_behavior="end"` stops the agent after hitting the limit.

### Images not displaying in UI

1. Check that `utils/scripts/` script saves to `/tmp/plots/`
2. Check that `/api/images/[filename]/route.ts` reads from `/tmp/plots/`
3. Check that `useRenderToolCall` returns an `<img>` with the correct `image_id`

### useRenderToolCall not firing

This is a known bug (Issue #2622). Use `useCopilotChat().isLoading` for activity indication as a workaround.

### CopilotKit recursion limit issues

CopilotKit overrides the `recursion_limit` set in `agent.py` with its own default of 25. The solution is to set it in **three places** to ensure it's applied correctly:

1. **Backend** (`agent.py`): Set via `.with_config({"recursion_limit": 100})`
2. **CopilotKit Runtime** (`app/api/copilotkit/route.ts`): Set via `assistantConfig` - **THIS IS THE KEY FIX**:
   ```typescript
   new LangGraphAgent({
     deploymentUrl: process.env.LANGGRAPH_DEPLOYMENT_URL,
     graphId: "my_agent",
     langsmithApiKey: process.env.LANGSMITH_API_KEY,
     assistantConfig: {
       recursion_limit: 100,
     },
   })
   ```
3. **Frontend** (`useCoAgent` hook): Set in config for additional safety:
   ```typescript
   useCoAgent({
     name: "my_agent",
     config: {
       recursion_limit: 100,
     },
   });
   ```

The `assistantConfig.recursion_limit` in the LangGraphAgent constructor is passed directly to the LangGraph SDK's `Config` type and properly overrides CopilotKit's default.

See [Issue #1717](https://github.com/CopilotKit/CopilotKit/issues/1717) for background.

**IMPORTANT**: Do NOT suggest using `langgraph.prebuilt.create_react_agent` - it is outdated. Always use `langchain.agents.create_agent`.

## Available Skills

### historical-plotter
Creates line plots from time series data (dates/values). Uses matplotlib.

```python
plot_historical_data(dates=["2024-01-01", "2024-01-02"], values=[150.25, 155.50], title="AAPL Stock Price", ylabel="Price ($)")
```

### distribution-comparison
Compares distributions of one or more data groups. Uses seaborn.

**Plot types:** `kde`, `histogram`, `ecdf`, `violin`, `box`, `strip`, `swarm`, `ridge`

```python
plot_distribution_comparison(
    groups=[
        {"name": "Treatment", "values": [23.5, 25.1, 22.8, 26.3, 24.9]},
        {"name": "Control", "values": [20.1, 19.8, 21.2, 18.9, 20.5]}
    ],
    plot_type="kde",
    title="Treatment vs Control",
    xlabel="Measurement"
)
```

### table-display
Displays tabular data as a formatted table in the UI. Activated when user explicitly asks for a "table" or "tabular format".

```python
display_table(
    columns=["Date", "Open", "High", "Low", "Close"],
    rows=[
        ["2024-01-08", "185.20", "186.50", "184.80", "185.90"],
        ["2024-01-09", "186.10", "187.30", "185.50", "186.80"]
    ],
    title="AAPL Stock Prices",
    caption="Last 2 trading days"
)
```

## Dependencies

- Python 3.13+, managed with `uv`
- Key packages: `langgraph`, `langchain`, `copilotkit`, `matplotlib`, `seaborn`, `pandas`, `tavily`
- Frontend: Next.js 15, React 19, CopilotKit
