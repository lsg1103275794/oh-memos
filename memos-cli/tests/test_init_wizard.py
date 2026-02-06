"""Tests for init wizard."""

import tempfile
from pathlib import Path

import pytest

from memosctl.init_wizard import (
    generate_cube_config,
    generate_env_file,
    validate_project_name,
    ProjectNameError,
)


def test_validate_project_name_valid():
    """Test valid project names."""
    assert validate_project_name("my_project") == "my_project"
    assert validate_project_name("MyProject") == "myproject"
    assert validate_project_name("my-project") == "my_project"
    assert validate_project_name("project123") == "project123"


def test_validate_project_name_invalid():
    """Test invalid project names."""
    with pytest.raises(ProjectNameError):
        validate_project_name("")
    with pytest.raises(ProjectNameError):
        validate_project_name("123project")  # Starts with number
    with pytest.raises(ProjectNameError):
        validate_project_name("my project")  # Has space


def test_generate_cube_config():
    """Test cube config generation."""
    config = generate_cube_config(
        cube_id="test_cube",
        mode="coding",
        neo4j_password="secret123",
    )

    assert config["cube_id"] == "test_cube"
    assert config["text_mem"]["config"]["cube_id"] == "test_cube"
    assert config["text_mem"]["config"]["graph_db"]["config"]["password"] == "secret123"


def test_generate_env_file():
    """Test .env file generation."""
    with tempfile.TemporaryDirectory() as tmpdir:
        env_path = Path(tmpdir) / ".env"
        generate_env_file(
            output_path=env_path,
            neo4j_password="secret123",
            cube_id="test_cube",
            cubes_dir="/path/to/cubes",
        )

        content = env_path.read_text()
        assert "NEO4J_PASSWORD=secret123" in content
        assert "MEMOS_DEFAULT_CUBE=test_cube" in content
        assert "MEMOS_CUBES_DIR=/path/to/cubes" in content
