# Skill System Implementation for LangGraph Agent

## Overview

This implementation brings Claude Code's **Skill system with progressive disclosure** to your LangGraph agent. Skills allow the agent to discover and use specialized capabilities without loading full implementation details into the context window until needed.

## Architecture

### Progressive Disclosure Pattern

The implementation follows Claude's progressive disclosure pattern:

1. **Discovery Phase**: Agent sees only skill names and descriptions in the system prompt
2. **Loading Phase**: When needed, agent calls `load_skill` tool to get full instructions
3. **Execution Phase**: Agent uses the detailed instructions to execute scripts via `execute` tool (from FilesystemMiddleware)

This keeps the context window lean while providing access to complex capabilities.

## Implementation Components

### 1. Skill Registry ([utils/skills.py](utils/skills.py))

**Key Functions:**
- `parse_skill_file()`: Parses markdown files with YAML frontmatter
- `discover_skills()`: Auto-discovers skills from the utils directory
- `SKILL_REGISTRY`: Global dictionary of discovered skills
- `load_skill`: LangChain tool that agents call to load full skill content
- `get_skills_summary()`: Generates lightweight skill descriptions for system prompt

**Skill Format:**
```markdown
---
name: skill-name
description: Brief description for semantic matching
---

# Full Skill Content
Detailed instructions...
```

### 2. Dynamic System Prompt ([utils/prompt.py](utils/prompt.py))

The system prompt now includes:
- Base research assistant instructions
- Tavily search guidance
- **Dynamic skills section** injected at runtime

Example skills section:
```
## Available Skills

You have access to specialized skills. To use a skill, first call the
`load_skill` tool with the skill name to get detailed instructions.

**historical-plotter**: Create line plots of historical time series data...
```

### 3. Agent Integration ([agent.py](agent.py))

The agent is configured with:
```python
agent = create_agent(
    model="openai:gpt-5-nano",
    system_prompt=SYSTEM_PROMPT,  # Includes skill discovery
    tools=[tavily_search, load_skill],  # Both tools available
    middleware=[...]
)
```

## Usage Workflow

### For the Agent

1. **Discovery**: Agent reads system prompt and sees available skills
2. **Decision**: When user requests visualization, agent recognizes it matches `historical-plotter`
3. **Load**: Agent calls `load_skill("historical-plotter")` to get full instructions
4. **Execute**: Agent follows instructions to run the plotting script
5. **Result**: Script saves plot to temp location, agent reports success

### Example Agent Interaction

**User**: "Search for AAPL stock prices in the last 10 days and plot them"

**Agent thinking**:
1. Uses `tavily_search` to find stock data
2. Recognizes "plot" matches `historical-plotter` skill
3. Calls `load_skill("historical-plotter")`
4. Reads full instructions from skill content
5. Extracts dates and values from search results
6. Constructs JSON config
7. Executes: `python3 scripts/plot_historical_data.py '{"dates": [...], "values": [...]}'`
8. Reports plot location to user

## Key Differences from Claude Code

| Aspect | Claude Code | This Implementation |
|--------|-------------|---------------------|
| **Skill Definition** | `.claude/skills/SKILL.md` | `utils/skills.md` with YAML frontmatter |
| **Discovery** | Claude scans skills directory | Python `discover_skills()` at import |
| **Loading** | Built-in skill loader | `load_skill` LangChain tool |
| **Execution** | Native sandbox | Agent uses Bash tool to run scripts |
| **Context** | Managed by Claude Code | Managed via progressive disclosure pattern |

## Adding New Skills

To add a new skill:

1. **Create skill definition** in `utils/` directory:

```markdown
---
name: my-new-skill
description: What this skill does and when to use it
---

# My New Skill

## Instructions
Step-by-step guidance for the agent...

## Example
Usage examples...
```

2. **Create supporting scripts** in `utils/scripts/`:

```python
#!/usr/bin/env python3
import sys
import json

config = json.loads(sys.argv[1])
# Implementation...
print(f"Result: {result}")
```

3. **Skills auto-discovered** on next agent startup

## Testing

Run the test suite:
```bash
uv run python test_skill_workflow.py
```

This validates:
- ✓ Skill discovery from markdown files
- ✓ System prompt injection
- ✓ `load_skill` tool functionality
- ✓ Script execution

## Deployment

Deploy to LangSmith:
```bash
uv run langgraph dev
```

The agent will:
- Automatically discover all skills in `utils/`
- Include skill descriptions in system prompt
- Provide `load_skill` tool to access full content
- Execute skill scripts using the Bash tool

## Benefits

1. **Context Efficiency**: Skill descriptions consume ~100 tokens vs. full content (~1000+ tokens)
2. **Scalability**: Add unlimited skills without overwhelming context window
3. **Modularity**: Skills are self-contained markdown + scripts
4. **Discoverability**: Agent semantically matches user requests to skill descriptions
5. **Maintainability**: Update skills independently without modifying agent code

## Architecture Decisions

### Why Not Use LangChain's SkillMiddleware?

LangChain's skill implementation (from their SQL assistant example) is rudimentary:
- Requires manual TypedDict definitions
- No auto-discovery mechanism
- No standardized format
- Limited documentation

This implementation provides:
- Markdown-based skill definitions (like Claude Code)
- Auto-discovery from file system
- YAML frontmatter for metadata
- Progressive disclosure pattern

### Why Not Create Custom Middleware?

LangGraph's middleware architecture is designed for:
- Model/tool call limits
- Human-in-the-loop approvals
- Retry logic
- Context editing

Our needs are simpler:
- Parse markdown files → Use Python functions
- Add to system prompt → Direct string injection
- Provide load mechanism → Standard LangChain tool

Using tools instead of middleware is more maintainable and follows LangChain's design patterns.

## Future Enhancements

Potential improvements:

1. **Multi-file Skills**: Support `skills/skill-name/SKILL.md` directory structure
2. **Skill Parameters**: Pass runtime config to skills via tool parameters
3. **Skill Dependencies**: Skills that call other skills
4. **Skill Versioning**: Track skill versions for reproducibility
5. **LangSmith Integration**: Log skill usage metrics
6. **Sandbox Policies**: Configure execution policies (Docker, restricted syscalls)

## Troubleshooting

### Skill Not Discovered

Check:
- File is in `utils/` directory
- File has `.md` extension
- YAML frontmatter is properly formatted
- `name` and `description` fields are present

### load_skill Returns Error

Verify:
- Skill name matches exactly (case-sensitive)
- SKILL_REGISTRY contains the skill: `python -c "from utils.skills import SKILL_REGISTRY; print(SKILL_REGISTRY.keys())"`

### Script Execution Fails

Check:
- Script has executable permissions
- JSON config is properly formatted
- Required Python packages installed (matplotlib, etc.)
- Output path is writable

## References

- [Claude Code Skills Documentation](https://code.claude.com/docs/en/skills)
- [LangChain Middleware Documentation](https://docs.langchain.com/oss/python/langchain/middleware/built-in)
- [LangGraph Multi-Agent Skills](https://docs.langchain.com/oss/python/langchain/multi-agent/skills-sql-assistant)
