"""Tests for configuration module."""

import tempfile
from pathlib import Path

import pytest

from oh_memosctl.config import oh_memosConfig, load_config, save_config


def test_default_config_values():
    """Test that default config has expected values."""
    config = MemosConfig()
    assert config.api_url == "http://localhost:18000"
    assert config.neo4j_uri == "bolt://localhost:7687"
    assert config.qdrant_host == "localhost"
    assert config.qdrant_port == 6333


def test_save_and_load_config():
    """Test saving and loading config from TOML file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "config.toml"

        # Create and save config
        config = MemosConfig(
            neo4j_password="testpass123",
            default_mode="student",
        )
        save_config(config, config_path)

        # Load and verify
        loaded = load_config(config_path)
        assert loaded.neo4j_password == "testpass123"
        assert loaded.default_mode == "student"


def test_load_nonexistent_config_returns_default():
    """Test loading from nonexistent path returns default config."""
    config = load_config(Path("/nonexistent/path/config.toml"))
    assert config.api_url == "http://localhost:18000"
