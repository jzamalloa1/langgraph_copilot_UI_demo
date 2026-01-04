# Deep Agent V2

A LangGraph-based agent with progressive disclosure skills and Generative UI integration.

## Key Solutions

This project solved two challenging integration problems:

### 1. Agent Tool Looping Prevention

**Problem**: Agent repeatedly calls the same tools despite prompt instructions to stop.

**Solution**: `ToolCallLimitMiddleware` from `langchain.agents.middleware` enforces hard limits at the framework level.

```python
from langchain.agents.middleware import ToolCallLimitMiddleware

middleware=[
    ToolCallLimitMiddleware(tool_name="tavily_search", run_limit=1, exit_behavior="end"),
    ToolCallLimitMiddleware(tool_name="plot_historical_data", run_limit=1, exit_behavior="end"),
]
```

### 2. Displaying Backend Tool Results in UI

**Problem**: Frontend tools registered with `useFrontendTool` are NOT automatically available to LangGraph agents using `create_agent`.

**Solution**: Use `useRenderToolCall` hook to intercept backend tool results and render them:

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

See [LANGGRAPH_UI_INTEGRATION.md](copilot-deepagent-app/LANGGRAPH_UI_INTEGRATION.md) for detailed documentation on what works, what doesn't, and why.

## Architecture

### Execution Environment

The system operates across two distinct environments:

```
┌─────────────────────────────────────────────────────────────────┐
│                     LangGraph Sandbox                           │
│  ┌─────────────┐    ┌──────────────┐    ┌──────────────────┐   │
│  │   Agent     │───▶│ skill_tools  │───▶│ subprocess.run() │   │
│  │  (create_   │    │   .py        │    │                  │   │
│  │   agent)    │    │              │    │ Breaks out to    │   │
│  └─────────────┘    └──────────────┘    │ host machine     │   │
│                                          └────────┬─────────┘   │
│  - Agent logic runs here                          │             │
│  - In-memory metadata (_session_images)           │             │
│  - Sandbox /tmp ≠ Host /tmp                       │             │
└───────────────────────────────────────────────────┼─────────────┘
                                                    │
                                                    ▼
┌─────────────────────────────────────────────────────────────────┐
│                        Host Machine                              │
│  ┌──────────────────┐         ┌─────────────────────────────┐   │
│  │ scripts/         │         │ /tmp/plots/                 │   │
│  │ plot_historical_ │────────▶│  plot_abc123.png            │   │
│  │ data.py          │ writes  │  plot_def456.png            │   │
│  └──────────────────┘         └──────────────┬──────────────┘   │
│                                               │                  │
│  ┌──────────────────────────────────────────┐│                  │
│  │ Next.js Frontend (copilot-deepagent-app) ││                  │
│  │                                          ││                  │
│  │  /api/images/[filename] ◀────────────────┘│                  │
│  │       │                    reads          │                  │
│  │       ▼                                   │                  │
│  │  ImageDisplay component                   │                  │
│  └──────────────────────────────────────────┘                   │
└─────────────────────────────────────────────────────────────────┘
```

### Key Points

1. **LangGraph Sandbox Isolation**
   - `langgraph dev` runs the agent in an isolated environment
   - The sandbox has its own `/tmp` directory, separate from the host
   - Tools like `ls` (if enabled) would see the sandbox's filesystem, not the host's

2. **Subprocess Breaks Out to Host**
   - `subprocess.run(["python3", script_path, ...])` executes on the **host machine**
   - Scripts in `utils/scripts/` run with host Python and host filesystem access
   - This is how images get saved to the host's `/tmp/plots`

3. **Frontend Reads from Host**
   - Next.js runs on the host machine
   - `/api/images/[filename]` route reads directly from host's `/tmp/plots`
   - Frontend can display images because it shares the host filesystem

### Data Flow for Plotting

```
1. Agent receives user request
   └─▶ "Plot AAPL stock price"

2. Agent calls tools (in sandbox):
   ├─▶ tavily_search() → gets data
   ├─▶ load_skill("historical-plotter") → gets instructions
   └─▶ plot_historical_data(dates, values, title)
       │
       └─▶ subprocess.run() breaks out to host
           └─▶ scripts/plot_historical_data.py
               └─▶ Saves to /tmp/plots/plot_abc123.png (HOST)

3. Tool returns to agent (minimal response):
   └─▶ {image_id: "plot_abc123", title: "...", status: "success"}
       (No base64 data - keeps agent context small)

4. Frontend intercepts tool result via useRenderToolCall:
   └─▶ Renders <img src="/api/images/plot_abc123" />
       └─▶ API route reads /tmp/plots/plot_abc123.png
           └─▶ Returns image binary to browser

5. Agent replies to user with confirmation
```

### Session Storage

- **In-memory metadata**: `_session_images` dict in `skill_tools.py`
  - Stores image metadata (id, title, path, description)
  - Persists within the `langgraph dev` process lifetime
  - Lost when the server restarts

- **On-disk images**: `/tmp/plots/` on host
  - Actual PNG files persist across restarts
  - Frontend can always serve them if they exist

- **Agent tools for session data**:
  - `list_stored_images()` - Lists images from current session (in-memory)
  - `get_stored_image(image_id)` - Gets metadata and verifies file exists

## Progressive Disclosure

Skills use a two-level disclosure pattern:

1. **System prompt** shows only skill names and descriptions
2. **Full instructions** loaded on-demand via `load_skill()`
3. **Script code** is NEVER loaded into context - executed externally via subprocess

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

## File Structure

```
deep-agent-v2/
├── agent.py                 # Agent configuration
├── utils/
│   ├── skills.py           # Skill loading (progressive disclosure)
│   ├── skills.md           # Skill instructions
│   ├── skill_tools.py      # Tool implementations
│   └── scripts/
│       └── plot_historical_data.py  # External script (runs on host)
├── copilot-deepagent-app/   # Next.js frontend
│   └── app/
│       ├── api/images/      # Image serving API
│       └── components/      # UI components
└── langgraph.json          # LangGraph configuration
```
