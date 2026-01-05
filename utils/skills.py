"""
Skill management system - progressive disclosure pattern.

Skills show name/description in system prompt. Full instructions loaded on-demand via load_skill.
"""

import re
from pathlib import Path
from typing import TypedDict
from langchain_core.tools import tool


class Skill(TypedDict):
    name: str
    description: str
    content: str


def parse_skill_file(file_path: Path) -> list[Skill]:
    """Parse a skill markdown file with YAML frontmatter. Supports multiple skills separated by ---."""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Split by skill separator (--- on its own line, but not the opening ---)
    # Pattern: starts with ---, then content, then --- to close, then body until next --- or EOF
    skill_pattern = r'---\s*\n(.*?)\n---\s*\n(.*?)(?=\n---\s*\nname:|\Z)'
    matches = re.findall(skill_pattern, content, re.DOTALL)

    if not matches:
        raise ValueError(f"Invalid skill file: {file_path}")

    skills = []
    for frontmatter, body in matches:
        name_match = re.search(r'^name:\s*(.+)$', frontmatter, re.MULTILINE)
        desc_match = re.search(r'^description:\s*(.+)$', frontmatter, re.MULTILINE)

        if not name_match or not desc_match:
            continue  # Skip invalid entries

        skills.append(Skill(
            name=name_match.group(1).strip(),
            description=desc_match.group(1).strip(),
            content=body.strip()
        ))

    if not skills:
        raise ValueError(f"No valid skills found in: {file_path}")

    return skills


def discover_skills(skills_dir: Path = None) -> dict[str, Skill]:
    """Discover all skills from the skills directory."""
    if skills_dir is None:
        skills_dir = Path(__file__).parent

    skills = {}
    for skill_file in skills_dir.glob('*.md'):
        if skill_file.name.lower() in ('skill.md', 'skills.md'):
            try:
                parsed_skills = parse_skill_file(skill_file)
                for skill in parsed_skills:
                    skills[skill['name']] = skill
            except Exception as e:
                print(f"Warning: Failed to parse {skill_file}: {e}")
    return skills


SKILL_REGISTRY = discover_skills()


@tool(parse_docstring=True)
def load_skill(skill_name: str) -> str:
    """Load instructions for a skill. Call ONCE before using the skill's tool.

    Args:
        skill_name: Skill name (e.g., 'historical-plotter')
    """
    if skill_name not in SKILL_REGISTRY:
        available = ', '.join(SKILL_REGISTRY.keys())
        return f"ERROR: '{skill_name}' not found. Available: {available}"

    skill = SKILL_REGISTRY[skill_name]
    return f"""SKILL: {skill['name']}

{skill['content']}

---
Now call the tool as shown above. Do NOT call load_skill again."""


def get_skills_summary() -> str:
    """Get minimal skill summary for system prompt."""
    if not SKILL_REGISTRY:
        return ""

    lines = ["\n## Skills (call load_skill for details)"]
    for name, skill in SKILL_REGISTRY.items():
        lines.append(f"- {name}: {skill['description']}")
    return "\n".join(lines)
