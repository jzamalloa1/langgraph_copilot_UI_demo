#!/usr/bin/env python3
"""
Test the skill workflow:
1. Agent discovers skills from system prompt
2. Agent loads skill content using load_skill tool
3. Agent executes the plotting script
"""

import os
import sys

# Set dummy env var for testing outside langgraph
if "TAVILY_API_KEY" not in os.environ:
    os.environ["TAVILY_API_KEY"] = "dummy"

from utils.skills import SKILL_REGISTRY, load_skill, get_skills_summary
from utils.prompt import get_system_prompt


def test_skill_discovery():
    """Test that skills are discovered properly."""
    print("=" * 60)
    print("TEST 1: Skill Discovery")
    print("=" * 60)
    print(f"✓ Discovered {len(SKILL_REGISTRY)} skill(s): {list(SKILL_REGISTRY.keys())}")
    print()


def test_system_prompt():
    """Test that system prompt includes skill information."""
    print("=" * 60)
    print("TEST 2: System Prompt with Skills")
    print("=" * 60)
    prompt = get_system_prompt()
    if "Available Skills" in prompt:
        print("✓ System prompt includes skill discovery section")
        print("\nSkills summary:")
        print(get_skills_summary())
    else:
        print("✗ System prompt missing skills section")
    print()


def test_load_skill():
    """Test that load_skill tool works."""
    print("=" * 60)
    print("TEST 3: Load Skill Tool")
    print("=" * 60)
    result = load_skill.invoke({"skill_name": "historical-plotter"})

    if "Historical Plotter" in result:
        print("✓ load_skill successfully loaded historical-plotter")
        print(f"\nFirst 300 characters of skill content:")
        print(result[:300] + "...")
    else:
        print("✗ load_skill failed")
    print()


def test_script_execution():
    """Test that the plotting script can be executed."""
    print("=" * 60)
    print("TEST 4: Script Execution")
    print("=" * 60)

    import json
    import subprocess
    from pathlib import Path

    script_path = Path(__file__).parent / "utils" / "scripts" / "plot_historical_data.py"

    config = {
        "dates": ["2024-01-01", "2024-02-01", "2024-03-01"],
        "values": [100, 105, 110],
        "output_file": "/tmp/test_plot.png",
        "title": "Test Plot",
        "xlabel": "Date",
        "ylabel": "Value"
    }

    try:
        result = subprocess.run(
            ["python3", str(script_path), json.dumps(config)],
            capture_output=True,
            text=True,
            check=True
        )
        print("✓ Script executed successfully")
        print(f"Output: {result.stdout}")

        if Path("/tmp/test_plot.png").exists():
            print("✓ Plot file created at /tmp/test_plot.png")
        else:
            print("✗ Plot file not created")

    except subprocess.CalledProcessError as e:
        print(f"✗ Script execution failed: {e}")
        print(f"STDERR: {e.stderr}")
    print()


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("SKILL SYSTEM INTEGRATION TEST")
    print("=" * 60 + "\n")

    test_skill_discovery()
    test_system_prompt()
    test_load_skill()
    test_script_execution()

    print("=" * 60)
    print("All tests completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
