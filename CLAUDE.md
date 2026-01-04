# Deep Agent V2 - Claude Code Guide

LangGraph agent with progressive disclosure skills and CopilotKit Generative UI integration.

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

### 3. Tool Loop Prevention

`ToolCallLimitMiddleware` enforces hard limits at framework level:

```python
middleware=[
    ToolCallLimitMiddleware(tool_name="tavily_search", run_limit=1, exit_behavior="end"),
    ToolCallLimitMiddleware(tool_name="plot_historical_data", run_limit=1, exit_behavior="end"),
]
```

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
│       └── plot_historical_data.py  # External matplotlib script
└── copilot-deepagent-app/      # Next.js frontend
    ├── app/
    │   ├── api/
    │   │   ├── copilotkit/route.ts  # CopilotKit runtime
    │   │   └── images/[filename]/   # Serves /tmp/plots/
    │   ├── components/
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

```python
from utils.skill_tools import your_skill_tool

agent = create_agent(
    tools=[tavily_search, load_skill, your_skill_tool],
    middleware=[
        ToolCallLimitMiddleware(tool_name="your_skill_tool", run_limit=1, exit_behavior="end"),
    ],
)
```

### Step 4: Add Skill Documentation

Create or add to `utils/skills.md`:

```markdown
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

### Step 5: Frontend Rendering (if applicable)

In the frontend, add a `useRenderToolCall` hook if the tool returns visual content.

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

## Dependencies

- Python 3.13+, managed with `uv`
- Key packages: `langgraph`, `langchain`, `copilotkit`, `matplotlib`, `tavily`
- Frontend: Next.js 15, React 19, CopilotKit
