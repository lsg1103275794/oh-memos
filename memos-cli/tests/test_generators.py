"""Tests for template generators."""

import tempfile
from pathlib import Path

import pytest

from memosctl.generators import generate_skill_file, generate_hook_file


def test_generate_skill_file():
    """Test SKILL.md generation."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / "SKILL.md"
        generate_skill_file(
            mode="coding",
            cube_id="test_cube",
            output_path=output_path,
        )

        content = output_path.read_text()
        assert "BUGFIX" in content
        assert "ERROR_PATTERN" in content


def test_generate_hook_file():
    """Test hook.js generation."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / "hook.js"
        generate_hook_file(
            mode="student",
            output_path=output_path,
        )

        content = output_path.read_text()
        assert "detectIntents" in content
        assert "history_query" in content
