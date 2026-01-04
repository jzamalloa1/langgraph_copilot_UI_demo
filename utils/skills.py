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


def parse_skill_file(file_path: Path) -> Skill:
    """Parse a skill markdown file with YAML frontmatter."""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    match = re.match(r'^---\s*\n(.*?)\n---\s*\n(.*)$', content, re.DOTALL)
    if not match:
        raise ValueError(f"Invalid skill file: {file_path}")

    frontmatter = match.group(1)
    body = match.group(2)

    name_match = re.search(r'^name:\s*(.+)$', frontmatter, re.MULTILINE)
    desc_match = re.search(r'^description:\s*(.+)$', frontmatter, re.MULTILINE)

    if not name_match or not desc_match:
        raise ValueError(f"Missing name or description: {file_path}")

    return Skill(
        name=name_match.group(1).strip(),
        description=desc_match.group(1).strip(),
        content=body.strip()
    )


def discover_skills(skills_dir: Path = None) -> dict[str, Skill]:
    """Discover all skills from the skills directory."""
    if skills_dir is None:
        skills_dir = Path(__file__).parent

    skills = {}
    for skill_file in skills_dir.glob('*.md'):
        if skill_file.name.lower() in ('skill.md', 'skills.md'):
            try:
                skill = parse_skill_file(skill_file)
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
