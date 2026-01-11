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

## Skill Tool Architecture: Two-File Pattern

Each skill that generates output (like plots) uses a **two-file pattern**: a LangChain Tool (orchestrator) and an External Script (executor).

### Why Two Files?

| File | Role | Runs In | Context Impact |
|------|------|---------|----------------|
| `skill_tools.py::plot_historical_data()` | **LangChain Tool** - orchestrates workflow, validates inputs, manages metadata | LangGraph sandbox | Only docstring visible to LLM |
| `scripts/plot_historical_data.py` | **External Script** - does actual work (matplotlib plotting) | Host machine (via subprocess) | NEVER loaded into context |

### Detailed Flow: `plot_historical_data`

```
User: "Plot AAPL stock price"
           │
           ▼
┌─────────────────────────────────────────────────────────────────┐
│  AGENT (agent.py)                                                │
│  Tools: [tavily_search, load_skill, plot_historical_data]       │
│                                                                  │
│  1. tavily_search("AAPL stock price") → gets dates/values       │
│  2. load_skill("historical-plotter") → gets formatting guide    │
│  3. plot_historical_data(dates, values, title, ylabel)          │
│           │                                                      │
└───────────┼──────────────────────────────────────────────────────┘
            │
            ▼
┌─────────────────────────────────────────────────────────────────┐
│  skill_tools.py :: plot_historical_data() [LangChain Tool]      │
│                                                                  │
│  • Validates inputs (dates/values not empty, lengths match)     │
│  • Generates unique image_id: "plot_abc123"                     │
│  • Creates output path: /tmp/plots/plot_abc123.png              │
│  • Builds config JSON with dates, values, title, output_file    │
│  • Calls subprocess.run():                                       │
│           │                                                      │
│    subprocess.run([                                              │
│      "python3",                                                  │
│      "utils/scripts/plot_historical_data.py",  ◄── SCRIPT       │
│      '{"dates": [...], "values": [...], ...}'                   │
│    ])                                                            │
│           │                                                      │
└───────────┼──────────────────────────────────────────────────────┘
            │
            ▼
┌─────────────────────────────────────────────────────────────────┐
│  scripts/plot_historical_data.py [External Script]              │
│                                                                  │
│  • Parses JSON config from sys.argv[1]                          │
│  • Parses date strings into datetime objects                    │
│  • Creates matplotlib figure (12x6, line plot with markers)     │
│  • Formats axes, grid, title                                    │
│  • Saves PNG to /tmp/plots/plot_abc123.png                      │
│  • Prints: "Plot saved to: /tmp/plots/plot_abc123.png"          │
│           │                                                      │
└───────────┼──────────────────────────────────────────────────────┘
            │
            ▼
┌─────────────────────────────────────────────────────────────────┐
│  skill_tools.py :: plot_historical_data() [Continues]           │
│                                                                  │
│  • Verifies file was created at /tmp/plots/plot_abc123.png     │
│  • Stores metadata in _session_images dict                      │
│  • Returns: {                                                    │
│      "type": "image",                                           │
│      "status": "success",                                       │
│      "image_id": "plot_abc123",                                 │
│      "title": "AAPL Stock Price",                               │
│      "data_points": 10                                          │
│    }                                                             │
└─────────────────────────────────────────────────────────────────┘
            │
            ▼
┌─────────────────────────────────────────────────────────────────┐
│  Frontend (useRenderToolCall or /api/images/[filename])         │
│                                                                  │
│  • Receives image_id from tool result                           │
│  • Renders: <img src="/api/images/plot_abc123" />               │
│  • API route reads /tmp/plots/plot_abc123.png and serves it    │
└─────────────────────────────────────────────────────────────────┘
```

### Design Benefits

1. **Context Efficiency**: The matplotlib script (~100 lines) is NEVER loaded into the agent's context. Only the tool's docstring is visible to the LLM.

2. **Sandbox Escape**: The subprocess breaks out of LangGraph's isolated sandbox to the host filesystem, where `/tmp/plots/` is accessible by the frontend.

3. **Separation of Concerns**: The tool handles orchestration (validation, ID generation, metadata storage) while the script handles the actual work (matplotlib, date parsing, formatting).

4. **Reusability**: The same script can be called with different parameters, or even from other tools, without duplicating visualization logic.

### Creating New Skills

When creating a new skill that generates output:

1. **Create the LangChain Tool** in `skill_tools.py`:
   - Validate inputs
   - Generate unique output ID
   - Build config JSON
   - Call external script via `subprocess.run()`
   - Store metadata and return result

2. **Create the External Script** in `utils/scripts/`:
   - Accept JSON config via `sys.argv[1]`
   - Do the actual work (plotting, file generation, etc.)
   - Save output to `/tmp/` directory
   - Print confirmation message

3. **Register the tool** in `agent.py`:
   - Import from `skill_tools.py`
   - Add to the `tools` list
   - Add `ToolCallLimitMiddleware` if needed

4. **Add skill documentation** to `utils/skills.md`:
   - YAML frontmatter with name and description
   - Full instructions for the agent

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

## Available Skills

The agent supports multiple skills through progressive disclosure:

| Skill | Tool | Description |
|-------|------|-------------|
| `historical-plotter` | `plot_historical_data` | Line plots from time series data |
| `distribution-comparison` | `plot_distribution_comparison` | Distribution plots (KDE, histogram, violin, box, etc.) |
| `table-display` | `display_table` | Formatted tabular data display |

Skills are triggered by explicit user requests:
- **Plot**: "chart", "graph", "plot", "visualize"
- **Table**: "table", "tabular format", "spreadsheet"
- **Text** (default): "get", "pull", "fetch", "find"

## File Structure

```
deep-agent-v2/
├── agent.py                 # Agent configuration
├── utils/
│   ├── skills.py           # Skill loading (progressive disclosure)
│   ├── skills.md           # Skill instructions (YAML frontmatter)
│   ├── skill_tools.py      # Tool implementations
│   └── scripts/
│       ├── plot_historical_data.py       # Time series plots
│       ├── plot_distribution_comparison.py  # Distribution plots
│       └── render_table.py               # Table data generation
├── copilot-deepagent-app/   # Next.js frontend
│   └── app/
│       ├── api/
│       │   ├── copilotkit/  # CopilotKit runtime
│       │   ├── images/      # Image serving API
│       │   └── tables/      # Table data API
│       └── components/
│           ├── GenerativeUIDemo.tsx  # Main UI with useRenderToolCall hooks
│           ├── ImageDisplay.tsx      # Image gallery component
│           └── TableDisplay.tsx      # Table rendering component
└── langgraph.json          # LangGraph configuration
```

For detailed development guidance, see [CLAUDE.md](CLAUDE.md).
