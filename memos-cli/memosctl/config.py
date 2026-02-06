#!/usr/bin/env python3
"""
MemOS CLI Configuration Module

Handles loading, saving, and validating configuration.
Config is stored in TOML format at ~/.memos/config.toml
"""

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

import tomli_w

# Default paths
DEFAULT_CONFIG_DIR = Path.home() / ".memos"
DEFAULT_CONFIG_PATH = DEFAULT_CONFIG_DIR / "config.toml"
DEFAULT_CUBES_DIR = DEFAULT_CONFIG_DIR / "cubes"

# Valid modes
VALID_MODES = ("coding", "student", "daily", "writing")
ModeType = Literal["coding", "student", "daily", "writing"]


@dataclass
class MemosConfig:
    """MemOS CLI configuration."""

    # API settings
    api_url: str = "http://localhost:18000"
    api_timeout: float = 30.0

    # Neo4j settings
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = ""

    # Qdrant settings
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333

    # Ollama settings (optional LLM backend)
    ollama_url: str = "http://localhost:11434"

    # Mode settings
    default_mode: ModeType = "coding"
    active_modes: list[str] = field(default_factory=lambda: ["coding"])

    # Cubes directory
    cubes_dir: str = str(DEFAULT_CUBES_DIR)

    def to_dict(self) -> dict:
        """Convert to dictionary for TOML serialization."""
        return {
            "api": {
                "url": self.api_url,
                "timeout": self.api_timeout,
            },
            "neo4j": {
                "uri": self.neo4j_uri,
                "user": self.neo4j_user,
                "password": self.neo4j_password,
            },
            "qdrant": {
                "host": self.qdrant_host,
                "port": self.qdrant_port,
            },
            "ollama": {
                "url": self.ollama_url,
            },
            "modes": {
                "default": self.default_mode,
                "active": self.active_modes,
            },
            "storage": {
                "cubes_dir": self.cubes_dir,
            },
        }

    @classmethod
    def from_dict(cls, data: dict) -> "MemosConfig":
        """Create config from dictionary (TOML data)."""
        api = data.get("api", {})
        neo4j = data.get("neo4j", {})
        qdrant = data.get("qdrant", {})
        ollama = data.get("ollama", {})
        modes = data.get("modes", {})
        storage = data.get("storage", {})

        return cls(
            api_url=api.get("url", "http://localhost:18000"),
            api_timeout=api.get("timeout", 30.0),
            neo4j_uri=neo4j.get("uri", "bolt://localhost:7687"),
            neo4j_user=neo4j.get("user", "neo4j"),
            neo4j_password=neo4j.get("password", ""),
            qdrant_host=qdrant.get("host", "localhost"),
            qdrant_port=qdrant.get("port", 6333),
            ollama_url=ollama.get("url", "http://localhost:11434"),
            default_mode=modes.get("default", "coding"),
            active_modes=modes.get("active", ["coding"]),
            cubes_dir=storage.get("cubes_dir", str(DEFAULT_CUBES_DIR)),
        )


def load_config(path: Path | None = None) -> MemosConfig:
    """Load configuration from TOML file.

    Args:
        path: Path to config file. Defaults to ~/.memos/config.toml

    Returns:
        MemosConfig instance (default values if file doesn't exist)
    """
    config_path = path or DEFAULT_CONFIG_PATH

    if not config_path.exists():
        return MemosConfig()

    with open(config_path, "rb") as f:
        data = tomllib.load(f)

    return MemosConfig.from_dict(data)


def save_config(config: MemosConfig, path: Path | None = None) -> None:
    """Save configuration to TOML file.

    Args:
        config: MemosConfig instance to save
        path: Path to config file. Defaults to ~/.memos/config.toml
    """
    config_path = path or DEFAULT_CONFIG_PATH

    # Ensure directory exists
    config_path.parent.mkdir(parents=True, exist_ok=True)

    with open(config_path, "wb") as f:
        tomli_w.dump(config.to_dict(), f)


def get_config_dir() -> Path:
    """Get the config directory path, creating if needed."""
    DEFAULT_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    return DEFAULT_CONFIG_DIR
