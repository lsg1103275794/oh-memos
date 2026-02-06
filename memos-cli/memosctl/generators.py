#!/usr/bin/env python3
"""MemOS CLI Template Generators - Generates Skill and Hook files from mode definitions."""

from pathlib import Path

from jinja2 import Environment, PackageLoader, select_autoescape

from .modes import get_mode

_env = Environment(
    loader=PackageLoader("memosctl", "templates"),
    autoescape=select_autoescape(),
)

INTENT_SUGGESTIONS = {
    "history_query": "→ Consider: memos_search to find related past work",
    "error_report": "→ Consider: memos_search(query='ERROR_PATTERN ...') for past solutions",
    "decision_making": "→ After deciding: memos_save(..., memory_type='DECISION')",
    "task_completion": "→ Consider saving: MILESTONE (big feature) / BUGFIX (fix) / FEATURE (new)",
    "concept_query": "→ Consider: memos_search(query='CONCEPT ...') for definitions",
    "citation_needed": "→ Consider: memos_search(query='CITATION ...') for references",
}


def generate_skill_file(mode: str, cube_id: str, output_path: Path) -> None:
    """Generate SKILL.md file for a mode."""
    mode_obj = get_mode(mode)

    template = _env.get_template("skill.md.j2")
    content = template.render(
        skill_name=f"{mode}-memory",
        title=f"{mode_obj.display_name} Memory",
        description=f"Memory management for {mode_obj.display_name}",
        mode_obj=mode_obj,
        cube_id=cube_id,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content)


def generate_hook_file(mode: str, output_path: Path) -> None:
    """Generate hook.js file for a mode."""
    mode_obj = get_mode(mode)

    template = _env.get_template("hook.js.j2")
    content = template.render(
        mode_obj=mode_obj,
        hook_patterns=mode_obj.get_hook_patterns(),
        intent_suggestions=INTENT_SUGGESTIONS,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content)


def generate_claude_files(mode: str, cube_id: str, project_dir: Path) -> dict[str, Path]:
    """Generate all Claude Code files (skills, hooks) for a mode."""
    claude_dir = project_dir / ".claude"
    skills_dir = claude_dir / "skills" / f"{mode}-memory"
    hooks_dir = claude_dir / "hooks" / "node"

    skill_path = skills_dir / "SKILL.md"
    generate_skill_file(mode, cube_id, skill_path)

    hook_path = hooks_dir / f"memos_{mode}_hook.js"
    generate_hook_file(mode, hook_path)

    return {"skill": skill_path, "hook": hook_path}
