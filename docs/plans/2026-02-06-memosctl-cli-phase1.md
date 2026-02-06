# MemOS CLI (memosctl) Phase 1 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Create `memosctl` CLI tool with `init`, `start`, `stop`, `status` commands and interactive mode selection wizard.

**Architecture:** Python CLI using Typer + Rich for interactive prompts and beautiful output. Configuration stored in TOML format at `~/.memos/config.toml`. Mode-specific configurations generate cube config files and Claude Code skills/hooks templates.

**Tech Stack:** Python 3.10+, Typer, Rich, tomli/tomli_w, Jinja2 (templates)

---

## Prerequisites

Before starting, ensure:
1. Python 3.10+ installed
2. MemOS project cloned at `/mnt/g/test/MemOS`
3. Neo4j and Qdrant running (for testing)

---

## Task 1: Create CLI Project Structure

**Files:**
- Create: `memos-cli/pyproject.toml`
- Create: `memos-cli/memosctl/__init__.py`
- Create: `memos-cli/memosctl/__main__.py`
- Create: `memos-cli/memosctl/cli.py`

**Step 1: Create directory structure**

```bash
mkdir -p /mnt/g/test/MemOS/memos-cli/memosctl
mkdir -p /mnt/g/test/MemOS/memos-cli/memosctl/modes
mkdir -p /mnt/g/test/MemOS/memos-cli/memosctl/templates
```

**Step 2: Write pyproject.toml**

```toml
[project]
name = "memos-cli"
version = "0.1.0"
description = "CLI tool for MemOS - Multi-mode Memory Management"
readme = "README.md"
requires-python = ">=3.10"
license = {text = "Apache-2.0"}
authors = [
    {name = "MemOS Team"}
]
dependencies = [
    "typer[all]>=0.9.0",
    "rich>=13.0.0",
    "tomli>=2.0.0;python_version<'3.11'",
    "tomli_w>=1.0.0",
    "jinja2>=3.1.0",
    "httpx>=0.25.0",
]

[project.scripts]
memosctl = "memosctl.cli:app"

[project.optional-dependencies]
dev = [
    "pytest>=7.0.0",
    "pytest-cov>=4.0.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["memosctl"]
```

**Step 3: Write `__init__.py`**

```python
"""MemOS CLI - Multi-mode Memory Management Tool."""

__version__ = "0.1.0"
```

**Step 4: Write `__main__.py`**

```python
"""Entry point for `python -m memosctl`."""

from memosctl.cli import app

if __name__ == "__main__":
    app()
```

**Step 5: Write basic `cli.py` skeleton**

```python
#!/usr/bin/env python3
"""
MemOS CLI (memosctl) - Multi-mode Memory Management

Commands:
    init    Initialize a new MemOS project with interactive wizard
    start   Start MemOS services for specified mode(s)
    stop    Stop running MemOS services
    status  Show status of MemOS services
"""

import typer
from rich.console import Console

app = typer.Typer(
    name="memosctl",
    help="MemOS CLI - Multi-mode Memory Management",
    no_args_is_help=True,
)
console = Console()


@app.command()
def version():
    """Show memosctl version."""
    from memosctl import __version__
    console.print(f"memosctl version {__version__}")


if __name__ == "__main__":
    app()
```

**Step 6: Verify installation works**

Run:
```bash
cd /mnt/g/test/MemOS/memos-cli && pip install -e .
```
Expected: Installation succeeds

Run:
```bash
memosctl version
```
Expected: `memosctl version 0.1.0`

**Step 7: Commit**

```bash
git add memos-cli/
git commit -m "$(cat <<'EOF'
feat(cli): initialize memos-cli project structure

- Add pyproject.toml with Typer, Rich, TOML dependencies
- Create basic CLI skeleton with version command
- Set up entry point for `memosctl` command

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: Implement Configuration Module

**Files:**
- Create: `memos-cli/memosctl/config.py`
- Test: `memos-cli/tests/test_config.py`

**Step 1: Write the failing test**

Create `memos-cli/tests/__init__.py`:
```python
"""Tests for memosctl."""
```

Create `memos-cli/tests/test_config.py`:
```python
"""Tests for configuration module."""

import tempfile
from pathlib import Path

import pytest

from memosctl.config import MemosConfig, load_config, save_config


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
```

**Step 2: Run test to verify it fails**

Run:
```bash
cd /mnt/g/test/MemOS/memos-cli && python -m pytest tests/test_config.py -v
```
Expected: FAIL with "No module named 'memosctl.config'"

**Step 3: Write minimal implementation**

Create `memos-cli/memosctl/config.py`:
```python
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
```

**Step 4: Run test to verify it passes**

Run:
```bash
cd /mnt/g/test/MemOS/memos-cli && python -m pytest tests/test_config.py -v
```
Expected: All 3 tests PASS

**Step 5: Commit**

```bash
git add memos-cli/memosctl/config.py memos-cli/tests/
git commit -m "$(cat <<'EOF'
feat(cli): add configuration module with TOML support

- MemosConfig dataclass with all settings
- load_config/save_config for TOML persistence
- Support for Neo4j, Qdrant, Ollama settings
- Default paths: ~/.memos/config.toml

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: Implement Mode Definitions

**Files:**
- Create: `memos-cli/memosctl/modes/__init__.py`
- Create: `memos-cli/memosctl/modes/base.py`
- Create: `memos-cli/memosctl/modes/coding.py`
- Create: `memos-cli/memosctl/modes/student.py`
- Test: `memos-cli/tests/test_modes.py`

**Step 1: Write the failing test**

Create `memos-cli/tests/test_modes.py`:
```python
"""Tests for mode definitions."""

import pytest

from memosctl.modes import get_mode, list_modes, ModeNotFoundError
from memosctl.modes.coding import CodingMode
from memosctl.modes.student import StudentMode


def test_list_modes_returns_all():
    """Test that list_modes returns all available modes."""
    modes = list_modes()
    assert "coding" in modes
    assert "student" in modes
    assert len(modes) >= 2


def test_get_mode_coding():
    """Test getting coding mode."""
    mode = get_mode("coding")
    assert isinstance(mode, CodingMode)
    assert mode.name == "coding"
    assert mode.port == 18001


def test_get_mode_student():
    """Test getting student mode."""
    mode = get_mode("student")
    assert isinstance(mode, StudentMode)
    assert mode.name == "student"
    assert mode.port == 18002


def test_get_mode_invalid_raises():
    """Test that invalid mode raises ModeNotFoundError."""
    with pytest.raises(ModeNotFoundError):
        get_mode("nonexistent")


def test_coding_mode_memory_types():
    """Test coding mode has expected memory types."""
    mode = get_mode("coding")
    assert "BUGFIX" in mode.memory_types
    assert "ERROR_PATTERN" in mode.memory_types
    assert "DECISION" in mode.memory_types


def test_student_mode_memory_types():
    """Test student mode has expected memory types."""
    mode = get_mode("student")
    assert "LECTURE" in mode.memory_types
    assert "CONCEPT" in mode.memory_types
    assert "CITATION" in mode.memory_types
```

**Step 2: Run test to verify it fails**

Run:
```bash
cd /mnt/g/test/MemOS/memos-cli && python -m pytest tests/test_modes.py -v
```
Expected: FAIL with "No module named 'memosctl.modes'"

**Step 3: Write base mode class**

Create `memos-cli/memosctl/modes/base.py`:
```python
#!/usr/bin/env python3
"""
Base Mode Definition

All modes inherit from BaseMode and define:
- Memory types specific to the mode
- MCP tools available in the mode
- Port number for mode's MCP server
- Skill/Hook templates for the mode
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class BaseMode(ABC):
    """Abstract base class for all modes."""

    name: str
    display_name: str
    description: str
    emoji: str
    port: int

    # Memory types available in this mode
    memory_types: list[str] = field(default_factory=list)

    # MCP tools enabled for this mode
    mcp_tools: list[str] = field(default_factory=list)

    # Relationship types used in graph
    relation_types: list[str] = field(default_factory=list)

    # Default tags for memories
    default_tags: list[str] = field(default_factory=list)

    @abstractmethod
    def get_skill_template(self) -> str:
        """Return the SKILL.md template content for this mode."""
        pass

    @abstractmethod
    def get_hook_patterns(self) -> dict[str, list[str]]:
        """Return hook patterns for intent detection.

        Returns:
            Dict mapping intent type to list of regex patterns.
            Example: {"history_query": [r"上次", r"之前", r"previously"]}
        """
        pass

    def get_cube_config_overrides(self) -> dict:
        """Return cube config overrides for this mode.

        Default implementation returns empty dict.
        Override in subclasses for mode-specific settings.
        """
        return {}


class ModeNotFoundError(Exception):
    """Raised when a requested mode is not found."""
    pass
```

**Step 4: Write coding mode**

Create `memos-cli/memosctl/modes/coding.py`:
```python
#!/usr/bin/env python3
"""
Coding Mode Definition

For programmers and AI coding assistants.
Memory types focused on bugs, decisions, patterns.
"""

from dataclasses import dataclass, field

from .base import BaseMode


@dataclass
class CodingMode(BaseMode):
    """Coding mode for developers."""

    name: str = "coding"
    display_name: str = "编码开发"
    description: str = "适合程序员、AI助手用户"
    emoji: str = "🖥️"
    port: int = 18001

    memory_types: list[str] = field(default_factory=lambda: [
        "BUGFIX",
        "ERROR_PATTERN",
        "DECISION",
        "CODE_PATTERN",
        "CONFIG",
        "GOTCHA",
        "MILESTONE",
        "FEATURE",
        "PROGRESS",
    ])

    mcp_tools: list[str] = field(default_factory=lambda: [
        "memos_search",
        "memos_search_context",
        "memos_save",
        "memos_list_v2",
        "memos_get",
        "memos_get_graph",
        "memos_trace_path",
        "memos_export_schema",
        "memos_suggest",
        "memos_get_stats",
    ])

    relation_types: list[str] = field(default_factory=lambda: [
        "CAUSE",
        "RELATE",
        "CONDITION",
        "CONFLICT",
    ])

    default_tags: list[str] = field(default_factory=lambda: [
        "coding",
        "debug",
        "architecture",
    ])

    def get_skill_template(self) -> str:
        """Return coding mode SKILL.md template."""
        return '''---
name: project-memory
description: "Proactive coding memory management via MemOS MCP."
---

# Project Memory (Coding Mode)

## Memory Types

| Type | When to Use |
|------|-------------|
| `BUGFIX` | One-time bug fix |
| `ERROR_PATTERN` | Reusable error solution |
| `DECISION` | Technical decision with rationale |
| `CODE_PATTERN` | Reusable code template |
| `CONFIG` | Configuration change |
| `GOTCHA` | Non-obvious trap or workaround |
| `MILESTONE` | Major achievement |
| `FEATURE` | New functionality |

## Auto-Save Rules

- After fixing a bug → Save as `BUGFIX` or `ERROR_PATTERN`
- After making a technical choice → Save as `DECISION`
- After discovering a gotcha → Save as `GOTCHA`

## Search Triggers

- "之前的bug" / "previous bug" → Search ERROR_PATTERN
- "上次怎么解决" / "how did we fix" → Search BUGFIX
- "架构决策" / "architecture decision" → Search DECISION
'''

    def get_hook_patterns(self) -> dict[str, list[str]]:
        """Return coding-specific hook patterns."""
        return {
            "history_query": [
                r"之前.*bug",
                r"上次.*错误",
                r"以前.*怎么",
                r"previous.*error",
                r"last time.*fix",
            ],
            "error_report": [
                r"error|错误|报错",
                r"exception|异常",
                r"traceback|stack trace",
                r"failed|失败",
            ],
            "decision_making": [
                r"应该(用|选|采用)",
                r"哪个.*好",
                r"vs\.?|versus",
                r"方案|approach",
            ],
            "task_completion": [
                r"修复了|fixed",
                r"实现了|implemented",
                r"完成了|completed",
            ],
        }
```

**Step 5: Write student mode**

Create `memos-cli/memosctl/modes/student.py`:
```python
#!/usr/bin/env python3
"""
Student Mode Definition

For students managing course notes, thesis, and academic work.
Memory types focused on lectures, concepts, citations.
"""

from dataclasses import dataclass, field

from .base import BaseMode


@dataclass
class StudentMode(BaseMode):
    """Student mode for academic work."""

    name: str = "student"
    display_name: str = "学习笔记"
    description: str = "适合学生、课程、论文"
    emoji: str = "📚"
    port: int = 18002

    memory_types: list[str] = field(default_factory=lambda: [
        "LECTURE",
        "CONCEPT",
        "EXAMPLE",
        "QUESTION",
        "SUMMARY",
        "CITATION",
        "ARGUMENT",
        "EVIDENCE",
        "DRAFT",
        "TODO",
    ])

    mcp_tools: list[str] = field(default_factory=lambda: [
        "memos_search",
        "memos_search_context",
        "memos_save",
        "memos_list_v2",
        "memos_get",
        "memos_get_graph",
        "memos_calendar",  # Student-specific
        "memos_export",    # Student-specific
        "memos_cite",      # Student-specific
        "memos_get_stats",
    ])

    relation_types: list[str] = field(default_factory=lambda: [
        "RELATES_TO",
        "BUILDS_ON",
        "CONTRADICTS",
        "SUPPORTS",
        "CITES",
    ])

    default_tags: list[str] = field(default_factory=lambda: [
        "学习",
        "课程",
        "笔记",
    ])

    def get_skill_template(self) -> str:
        """Return student mode SKILL.md template."""
        return '''---
name: student-memory
description: "Academic memory management for courses, thesis, and study notes."
---

# Student Memory (学习笔记模式)

## Memory Types

| Type | When to Use | Example |
|------|-------------|---------|
| `LECTURE` | 课堂笔记 | 《数据结构》第3章 - 链表 |
| `CONCEPT` | 概念定义 | 什么是时间复杂度 O(n) |
| `EXAMPLE` | 例题/案例 | 快速排序的实现示例 |
| `QUESTION` | 疑问/待解决 | 为什么递归比迭代慢？ |
| `SUMMARY` | 章节总结 | 第3章重点：链表操作 |
| `CITATION` | 文献引用 | Smith et al. 2024, AI综述 |
| `ARGUMENT` | 论点/观点 | 论文主张：LLM需要记忆 |
| `EVIDENCE` | 论据/数据 | 实验结果：准确率提升15% |
| `DRAFT` | 论文草稿 | 第2章初稿 - 相关工作 |
| `TODO` | 学习待办 | 周五前完成文献综述 |

## Auto-Save Rules

- 上完课后 → Save as `LECTURE`
- 学到新概念 → Save as `CONCEPT`
- 找到文献 → Save as `CITATION`
- 有疑问 → Save as `QUESTION`

## Search Triggers

- "上节课" / "last lecture" → Search LECTURE
- "这个概念" / "this concept" → Search CONCEPT
- "引用" / "citation" → Search CITATION
'''

    def get_hook_patterns(self) -> dict[str, list[str]]:
        """Return student-specific hook patterns."""
        return {
            "history_query": [
                r"上节课",
                r"上次.*课",
                r"之前.*讲",
                r"last lecture",
                r"previous class",
            ],
            "concept_query": [
                r"什么是",
                r"怎么理解",
                r"定义",
                r"what is",
                r"definition of",
            ],
            "citation_needed": [
                r"引用|cite",
                r"参考文献|reference",
                r"出处|source",
            ],
            "task_completion": [
                r"上完课|finished class",
                r"看完了|finished reading",
                r"整理.*笔记|organized notes",
            ],
        }

    def get_cube_config_overrides(self) -> dict:
        """Return student-specific cube config overrides."""
        return {
            "metadata_fields": ["course", "semester", "week", "chapter"],
        }
```

**Step 6: Write modes `__init__.py`**

Create `memos-cli/memosctl/modes/__init__.py`:
```python
#!/usr/bin/env python3
"""
MemOS CLI Modes

Available modes:
- coding: For programmers and AI coding assistants
- student: For students managing course notes and thesis
- daily: For personal daily journaling (TODO)
- writing: For creative writing (TODO)
"""

from .base import BaseMode, ModeNotFoundError
from .coding import CodingMode
from .student import StudentMode

# Registry of all available modes
_MODES: dict[str, type[BaseMode]] = {
    "coding": CodingMode,
    "student": StudentMode,
}


def list_modes() -> list[str]:
    """Return list of available mode names."""
    return list(_MODES.keys())


def get_mode(name: str) -> BaseMode:
    """Get a mode instance by name.

    Args:
        name: Mode name (e.g., "coding", "student")

    Returns:
        Mode instance

    Raises:
        ModeNotFoundError: If mode name is not found
    """
    if name not in _MODES:
        raise ModeNotFoundError(f"Mode '{name}' not found. Available: {list_modes()}")

    return _MODES[name]()


def get_all_modes() -> list[BaseMode]:
    """Return instances of all available modes."""
    return [mode_cls() for mode_cls in _MODES.values()]


__all__ = [
    "BaseMode",
    "ModeNotFoundError",
    "CodingMode",
    "StudentMode",
    "list_modes",
    "get_mode",
    "get_all_modes",
]
```

**Step 7: Run test to verify it passes**

Run:
```bash
cd /mnt/g/test/MemOS/memos-cli && python -m pytest tests/test_modes.py -v
```
Expected: All 6 tests PASS

**Step 8: Commit**

```bash
git add memos-cli/memosctl/modes/
git commit -m "$(cat <<'EOF'
feat(cli): add mode definitions for coding and student

- BaseMode abstract class with memory types, tools, patterns
- CodingMode: BUGFIX, ERROR_PATTERN, DECISION, etc.
- StudentMode: LECTURE, CONCEPT, CITATION, etc.
- Each mode has port, skill template, hook patterns

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 4: Implement Interactive Init Wizard

**Files:**
- Create: `memos-cli/memosctl/init_wizard.py`
- Modify: `memos-cli/memosctl/cli.py`
- Test: `memos-cli/tests/test_init_wizard.py`

**Step 1: Write the failing test**

Create `memos-cli/tests/test_init_wizard.py`:
```python
"""Tests for init wizard."""

import tempfile
from pathlib import Path
from unittest.mock import patch

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
```

**Step 2: Run test to verify it fails**

Run:
```bash
cd /mnt/g/test/MemOS/memos-cli && python -m pytest tests/test_init_wizard.py -v
```
Expected: FAIL with "No module named 'memosctl.init_wizard'"

**Step 3: Write init wizard implementation**

Create `memos-cli/memosctl/init_wizard.py`:
```python
#!/usr/bin/env python3
"""
MemOS CLI Init Wizard

Interactive initialization wizard for setting up a new MemOS project.
"""

import json
import re
import shutil
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table

from .config import DEFAULT_CONFIG_DIR, MemosConfig, save_config
from .modes import get_all_modes, get_mode

console = Console()

# ASCII art logo
LOGO = r"""
  __  __                  ___  ____
 |  \/  | ___ _ __ ___   / _ \/ ___|
 | |\/| |/ _ \ '_ ` _ \ | | | \___ \
 | |  | |  __/ | | | | || |_| |___) |
 |_|  |_|\___|_| |_| |_| \___/|____/
"""


class ProjectNameError(Exception):
    """Raised when project name is invalid."""
    pass


def validate_project_name(name: str) -> str:
    """Validate and normalize project name.

    Args:
        name: Raw project name input

    Returns:
        Normalized project name (lowercase, underscores)

    Raises:
        ProjectNameError: If name is invalid
    """
    if not name or not name.strip():
        raise ProjectNameError("Project name cannot be empty")

    # Normalize: lowercase, replace hyphens/dots with underscores
    normalized = name.lower().strip()
    normalized = re.sub(r"[-.\s]+", "_", normalized)

    # Validate: must start with letter, only alphanumeric and underscore
    if not re.match(r"^[a-z][a-z0-9_]*$", normalized):
        raise ProjectNameError(
            f"Invalid project name '{name}'. "
            "Must start with a letter, contain only letters, numbers, and underscores."
        )

    return normalized


def generate_cube_config(
    cube_id: str,
    mode: str,
    neo4j_password: str,
    neo4j_uri: str = "bolt://localhost:7687",
    qdrant_host: str = "localhost",
    qdrant_port: int = 6333,
    llm_backend: str = "ollama",
    llm_api_base: str = "http://localhost:11434/v1",
) -> dict[str, Any]:
    """Generate cube config.json content.

    Args:
        cube_id: Cube identifier
        mode: Mode name (coding, student, etc.)
        neo4j_password: Neo4j database password
        neo4j_uri: Neo4j connection URI
        qdrant_host: Qdrant host
        qdrant_port: Qdrant port
        llm_backend: LLM backend (ollama, openai, siliconflow)
        llm_api_base: LLM API base URL

    Returns:
        Cube configuration dictionary
    """
    mode_obj = get_mode(mode)

    # Base config from template
    config = {
        "model_schema": "memos.configs.mem_cube.GeneralMemCubeConfig",
        "user_id": cube_id,
        "cube_id": cube_id,
        "config_filename": "config.json",
        "text_mem": {
            "backend": "tree_text",
            "config": {
                "cube_id": cube_id,
                "memory_filename": "textual_memory.json",
                "reorganize": True,
                "extractor_llm": {
                    "backend": "openai",
                    "config": {
                        "model_name_or_path": "qwen2.5:7b" if llm_backend == "ollama" else "gpt-4o-mini",
                        "temperature": 0.6,
                        "max_tokens": 6000,
                        "api_key": "ollama" if llm_backend == "ollama" else "placeholder",
                        "api_base": llm_api_base,
                    },
                },
                "dispatcher_llm": {
                    "backend": "openai",
                    "config": {
                        "model_name_or_path": "qwen2.5:7b" if llm_backend == "ollama" else "gpt-4o-mini",
                        "temperature": 0.6,
                        "max_tokens": 6000,
                        "api_key": "ollama" if llm_backend == "ollama" else "placeholder",
                        "api_base": llm_api_base,
                    },
                },
                "embedder": {
                    "backend": "universal_api",
                    "config": {
                        "model_name_or_path": "BAAI/bge-m3",
                        "provider": "openai",
                        "base_url": llm_api_base,
                        "api_key": "ollama" if llm_backend == "ollama" else "placeholder",
                        "embedding_dims": 1024,
                    },
                },
                "reranker": {
                    "backend": "http_bge",
                    "config": {
                        "url": "https://api.siliconflow.cn/v1/rerank",
                        "model": "netease-youdao/bce-reranker-base_v1",
                        "headers_extra": "{}",
                    },
                },
                "graph_db": {
                    "backend": "neo4j-community",
                    "config": {
                        "uri": neo4j_uri,
                        "user": "neo4j",
                        "password": neo4j_password,
                        "db_name": "neo4j",
                        "use_multi_db": False,
                        "user_name": cube_id,
                        "embedding_dimension": 1024,
                        "vec_config": {
                            "backend": "qdrant",
                            "config": {
                                "collection_name": f"{cube_id}_graph",
                                "vector_dimension": 1024,
                                "distance_metric": "cosine",
                                "host": qdrant_host,
                                "port": qdrant_port,
                            },
                        },
                    },
                },
                "search_strategy": {
                    "bm25": True,
                    "cot": False,
                },
            },
        },
        "act_mem": {},
        "para_mem": {},
    }

    # Apply mode-specific overrides
    overrides = mode_obj.get_cube_config_overrides()
    if overrides:
        config["mode_config"] = overrides

    return config


def generate_env_file(
    output_path: Path,
    neo4j_password: str,
    cube_id: str,
    cubes_dir: str,
    api_url: str = "http://localhost:18000",
) -> None:
    """Generate .env file for MCP server.

    Args:
        output_path: Path to write .env file
        neo4j_password: Neo4j password
        cube_id: Default cube ID
        cubes_dir: Path to cubes directory
        api_url: MemOS API URL
    """
    content = f"""# MemOS MCP Server Configuration
# Generated by memosctl init

# API Connection
MEMOS_URL={api_url}
MEMOS_USER={cube_id}
MEMOS_DEFAULT_CUBE={cube_id}
MEMOS_CUBES_DIR={cubes_dir}

# Neo4j
NEO4J_HTTP_URL=http://localhost:7474
NEO4J_USER=neo4j
NEO4J_PASSWORD={neo4j_password}

# Timeouts (seconds)
MEMOS_TIMEOUT_TOOL=120
MEMOS_TIMEOUT_STARTUP=30
MEMOS_TIMEOUT_HEALTH=5
MEMOS_API_WAIT_MAX=60

# Feature Flags
MEMOS_ENABLE_DELETE=false
MEMOS_LOG_LEVEL=WARNING
"""
    output_path.write_text(content)


def show_welcome():
    """Display welcome message with logo."""
    console.print(Panel(LOGO, title="Welcome to MemOS Setup Wizard!", border_style="blue"))


def select_mode() -> str:
    """Interactive mode selection.

    Returns:
        Selected mode name
    """
    console.print("\n[bold]? 选择使用场景:[/bold]\n")

    modes = get_all_modes()
    table = Table(show_header=False, box=None, padding=(0, 2))

    for i, mode in enumerate(modes, 1):
        table.add_row(
            f"[bold cyan]{i}[/bold cyan]",
            f"{mode.emoji}  {mode.display_name}",
            f"[dim]{mode.description}[/dim]",
        )

    console.print(table)
    console.print()

    while True:
        choice = Prompt.ask(
            "选择 (输入数字)",
            default="1",
        )
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(modes):
                return modes[idx].name
        except ValueError:
            pass
        console.print("[red]无效选择，请重试[/red]")


def run_init_wizard(
    project_name: str | None = None,
    mode: str | None = None,
    neo4j_password: str | None = None,
    output_dir: Path | None = None,
    non_interactive: bool = False,
) -> dict[str, Any]:
    """Run the interactive init wizard.

    Args:
        project_name: Pre-set project name (skip prompt)
        mode: Pre-set mode (skip selection)
        neo4j_password: Pre-set password (skip prompt)
        output_dir: Output directory (default: ~/.memos/{project})
        non_interactive: If True, use defaults without prompting

    Returns:
        Dict with created paths and settings
    """
    if not non_interactive:
        show_welcome()

    # 1. Get project name
    if not project_name:
        if non_interactive:
            project_name = "my_project"
        else:
            while True:
                project_name = Prompt.ask("? 项目名称", default="my_project")
                try:
                    project_name = validate_project_name(project_name)
                    break
                except ProjectNameError as e:
                    console.print(f"[red]{e}[/red]")
    else:
        project_name = validate_project_name(project_name)

    cube_id = f"{project_name}_cube"

    # 2. Select mode
    if not mode:
        if non_interactive:
            mode = "coding"
        else:
            mode = select_mode()

    mode_obj = get_mode(mode)

    # 3. Get Neo4j password
    if not neo4j_password:
        if non_interactive:
            neo4j_password = "12345678"
        else:
            neo4j_password = Prompt.ask(
                "? Neo4j 密码",
                password=True,
                default="12345678",
            )

    # 4. Select LLM backend
    if non_interactive:
        llm_backend = "ollama"
    else:
        console.print("\n[bold]? 选择 LLM 后端:[/bold]")
        console.print("  [cyan]1[/cyan]  Ollama (本地运行，免费，推荐)")
        console.print("  [cyan]2[/cyan]  OpenAI (需要 API Key)")
        console.print("  [cyan]3[/cyan]  SiliconFlow (国内可用)")

        llm_choice = Prompt.ask("选择", default="1")
        llm_backend = {"1": "ollama", "2": "openai", "3": "siliconflow"}.get(llm_choice, "ollama")

    # 5. Create directories and files
    project_dir = output_dir or (DEFAULT_CONFIG_DIR / project_name)
    cubes_dir = project_dir / "cubes"
    cube_dir = cubes_dir / cube_id

    project_dir.mkdir(parents=True, exist_ok=True)
    cube_dir.mkdir(parents=True, exist_ok=True)

    # Generate cube config
    cube_config = generate_cube_config(
        cube_id=cube_id,
        mode=mode,
        neo4j_password=neo4j_password,
        llm_backend=llm_backend,
    )

    config_path = cube_dir / "config.json"
    with open(config_path, "w") as f:
        json.dump(cube_config, f, indent=2)

    # Generate .env file
    env_path = project_dir / ".env"
    generate_env_file(
        output_path=env_path,
        neo4j_password=neo4j_password,
        cube_id=cube_id,
        cubes_dir=str(cubes_dir),
    )

    # Save global config
    global_config = MemosConfig(
        neo4j_password=neo4j_password,
        default_mode=mode,
        active_modes=[mode],
        cubes_dir=str(cubes_dir),
    )
    save_config(global_config, project_dir / "config.toml")

    # 6. Show completion message
    if not non_interactive:
        console.print()
        console.print(Panel(
            f"""[green]✅ 配置完成！[/green]

📁 配置目录: [cyan]{project_dir}[/cyan]
🧊 Cube ID:   [cyan]{cube_id}[/cyan]
📝 模式:      [cyan]{mode_obj.emoji} {mode_obj.display_name}[/cyan]

🚀 下一步:
   1. 启动服务:  [bold]memosctl start[/bold]
   2. 查看状态:  [bold]memosctl status[/bold]
""",
            title="Setup Complete",
            border_style="green",
        ))

    return {
        "project_name": project_name,
        "cube_id": cube_id,
        "mode": mode,
        "project_dir": str(project_dir),
        "cube_dir": str(cube_dir),
        "config_path": str(config_path),
        "env_path": str(env_path),
    }
```

**Step 4: Run test to verify it passes**

Run:
```bash
cd /mnt/g/test/MemOS/memos-cli && python -m pytest tests/test_init_wizard.py -v
```
Expected: All 4 tests PASS

**Step 5: Update cli.py to add init command**

Update `memos-cli/memosctl/cli.py`:
```python
#!/usr/bin/env python3
"""
MemOS CLI (memosctl) - Multi-mode Memory Management

Commands:
    init    Initialize a new MemOS project with interactive wizard
    start   Start MemOS services for specified mode(s)
    stop    Stop running MemOS services
    status  Show status of MemOS services
"""

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from memosctl import __version__
from memosctl.init_wizard import run_init_wizard
from memosctl.modes import list_modes

app = typer.Typer(
    name="memosctl",
    help="MemOS CLI - Multi-mode Memory Management",
    no_args_is_help=True,
)
console = Console()


@app.command()
def version():
    """Show memosctl version."""
    console.print(f"memosctl version {__version__}")


@app.command()
def init(
    name: Optional[str] = typer.Option(
        None, "--name", "-n",
        help="Project name (will be normalized to lowercase with underscores)"
    ),
    mode: Optional[str] = typer.Option(
        None, "--mode", "-m",
        help=f"Mode to use: {', '.join(list_modes())}"
    ),
    password: Optional[str] = typer.Option(
        None, "--password", "-p",
        help="Neo4j password"
    ),
    output: Optional[Path] = typer.Option(
        None, "--output", "-o",
        help="Output directory (default: ~/.memos/<project>)"
    ),
    non_interactive: bool = typer.Option(
        False, "--yes", "-y",
        help="Non-interactive mode, use defaults"
    ),
):
    """Initialize a new MemOS project with interactive wizard."""
    try:
        result = run_init_wizard(
            project_name=name,
            mode=mode,
            neo4j_password=password,
            output_dir=output,
            non_interactive=non_interactive,
        )

        if non_interactive:
            console.print(f"✅ Created project at {result['project_dir']}")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def start(
    mode: Optional[str] = typer.Option(
        None, "--mode", "-m",
        help="Mode(s) to start (comma-separated)"
    ),
):
    """Start MemOS services for specified mode(s)."""
    console.print("[yellow]TODO: Implement start command[/yellow]")


@app.command()
def stop():
    """Stop running MemOS services."""
    console.print("[yellow]TODO: Implement stop command[/yellow]")


@app.command()
def status():
    """Show status of MemOS services."""
    console.print("[yellow]TODO: Implement status command[/yellow]")


if __name__ == "__main__":
    app()
```

**Step 6: Test init command**

Run:
```bash
memosctl init --help
```
Expected: Shows init command help with options

Run:
```bash
memosctl init --name test_project --mode coding --password testpass --yes
```
Expected: Creates project at ~/.memos/test_project

**Step 7: Commit**

```bash
git add memos-cli/
git commit -m "$(cat <<'EOF'
feat(cli): add interactive init wizard

- Project name validation and normalization
- Interactive mode selection with emoji display
- Neo4j password and LLM backend prompts
- Generates cube config.json with mode-specific settings
- Generates .env file for MCP server
- Supports --yes flag for non-interactive mode

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 5: Implement Service Management (start/stop/status)

**Files:**
- Create: `memos-cli/memosctl/service.py`
- Modify: `memos-cli/memosctl/cli.py`
- Test: `memos-cli/tests/test_service.py`

**Step 1: Write the failing test**

Create `memos-cli/tests/test_service.py`:
```python
"""Tests for service management."""

import pytest

from memosctl.service import (
    ServiceStatus,
    check_port_in_use,
    get_service_status,
)


def test_service_status_enum():
    """Test ServiceStatus enum values."""
    assert ServiceStatus.RUNNING.value == "running"
    assert ServiceStatus.STOPPED.value == "stopped"
    assert ServiceStatus.ERROR.value == "error"


def test_check_port_in_use():
    """Test port checking (assumes 18000 may or may not be in use)."""
    # Port 65535 is rarely used
    result = check_port_in_use(65535)
    assert isinstance(result, bool)


def test_get_service_status_returns_dict():
    """Test service status returns expected structure."""
    status = get_service_status()
    assert "api" in status
    assert "neo4j" in status
    assert "qdrant" in status
    assert all(isinstance(s, ServiceStatus) for s in status.values())
```

**Step 2: Run test to verify it fails**

Run:
```bash
cd /mnt/g/test/MemOS/memos-cli && python -m pytest tests/test_service.py -v
```
Expected: FAIL with "No module named 'memosctl.service'"

**Step 3: Write service module**

Create `memos-cli/memosctl/service.py`:
```python
#!/usr/bin/env python3
"""
MemOS CLI Service Management

Handles starting, stopping, and checking status of MemOS services.
"""

import socket
import subprocess
import sys
from enum import Enum
from pathlib import Path
from typing import Optional

import httpx
from rich.console import Console
from rich.table import Table

from .config import DEFAULT_CONFIG_DIR, load_config
from .modes import get_mode

console = Console()


class ServiceStatus(Enum):
    """Service status enum."""
    RUNNING = "running"
    STOPPED = "stopped"
    ERROR = "error"
    UNKNOWN = "unknown"


def check_port_in_use(port: int, host: str = "localhost") -> bool:
    """Check if a port is in use.

    Args:
        port: Port number to check
        host: Host to check (default: localhost)

    Returns:
        True if port is in use, False otherwise
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1)
        try:
            s.connect((host, port))
            return True
        except (socket.timeout, ConnectionRefusedError, OSError):
            return False


def check_http_health(url: str, timeout: float = 2.0) -> bool:
    """Check if HTTP endpoint is healthy.

    Args:
        url: URL to check
        timeout: Request timeout in seconds

    Returns:
        True if endpoint returns 200, False otherwise
    """
    try:
        response = httpx.get(url, timeout=timeout)
        return response.status_code == 200
    except Exception:
        return False


def get_service_status() -> dict[str, ServiceStatus]:
    """Get status of all MemOS services.

    Returns:
        Dict mapping service name to status
    """
    config = load_config()

    status = {}

    # Check MemOS API
    api_healthy = check_http_health(f"{config.api_url}/health")
    status["api"] = ServiceStatus.RUNNING if api_healthy else ServiceStatus.STOPPED

    # Check Neo4j (port 7687 for bolt)
    neo4j_port = int(config.neo4j_uri.split(":")[-1]) if ":" in config.neo4j_uri else 7687
    neo4j_up = check_port_in_use(neo4j_port)
    status["neo4j"] = ServiceStatus.RUNNING if neo4j_up else ServiceStatus.STOPPED

    # Check Qdrant
    qdrant_up = check_port_in_use(config.qdrant_port, config.qdrant_host)
    status["qdrant"] = ServiceStatus.RUNNING if qdrant_up else ServiceStatus.STOPPED

    # Check Ollama (optional)
    ollama_healthy = check_http_health(f"{config.ollama_url}/api/tags")
    status["ollama"] = ServiceStatus.RUNNING if ollama_healthy else ServiceStatus.STOPPED

    return status


def display_status(status: dict[str, ServiceStatus], mode_status: dict[str, ServiceStatus] | None = None):
    """Display service status in a table.

    Args:
        status: Service status dict
        mode_status: Optional mode-specific status
    """
    table = Table(title="MemOS Service Status")
    table.add_column("Service", style="cyan")
    table.add_column("Status", style="bold")
    table.add_column("Port/URL")

    config = load_config()

    status_icons = {
        ServiceStatus.RUNNING: "[green]● running[/green]",
        ServiceStatus.STOPPED: "[red]○ stopped[/red]",
        ServiceStatus.ERROR: "[yellow]⚠ error[/yellow]",
        ServiceStatus.UNKNOWN: "[dim]? unknown[/dim]",
    }

    service_info = {
        "api": ("MemOS API", config.api_url),
        "neo4j": ("Neo4j", config.neo4j_uri),
        "qdrant": ("Qdrant", f"{config.qdrant_host}:{config.qdrant_port}"),
        "ollama": ("Ollama", config.ollama_url),
    }

    for service, (name, url) in service_info.items():
        s = status.get(service, ServiceStatus.UNKNOWN)
        table.add_row(name, status_icons[s], url)

    # Add mode-specific MCP servers
    if mode_status:
        table.add_section()
        for mode_name, s in mode_status.items():
            mode = get_mode(mode_name)
            table.add_row(
                f"MCP:{mode_name}",
                status_icons[s],
                f":{mode.port}",
            )

    console.print(table)


def start_services(
    modes: list[str] | None = None,
    project_dir: Path | None = None,
) -> bool:
    """Start MemOS services.

    Args:
        modes: List of modes to start MCP servers for
        project_dir: Project directory with config

    Returns:
        True if all services started successfully
    """
    project_dir = project_dir or DEFAULT_CONFIG_DIR
    config = load_config(project_dir / "config.toml")

    console.print("[bold]Starting MemOS services...[/bold]")

    # Check dependencies
    status = get_service_status()

    if status["neo4j"] != ServiceStatus.RUNNING:
        console.print("[yellow]⚠ Neo4j is not running. Please start Neo4j first.[/yellow]")
        console.print("   Windows: Run Neo4j Desktop or neo4j.bat console")
        return False

    if status["qdrant"] != ServiceStatus.RUNNING:
        console.print("[yellow]⚠ Qdrant is not running. Please start Qdrant first.[/yellow]")
        return False

    # Start MemOS API if not running
    if status["api"] != ServiceStatus.RUNNING:
        console.print("Starting MemOS API...")
        # TODO: Actually start the API server
        console.print("[yellow]TODO: Implement API server startup[/yellow]")

    # Start MCP servers for each mode
    modes = modes or config.active_modes
    for mode_name in modes:
        mode = get_mode(mode_name)
        console.print(f"Starting MCP server for {mode.emoji} {mode.display_name} on port {mode.port}...")
        # TODO: Actually start MCP server
        console.print("[yellow]TODO: Implement MCP server startup[/yellow]")

    console.print("[green]✅ Services started[/green]")
    return True


def stop_services(project_dir: Path | None = None) -> bool:
    """Stop MemOS services.

    Args:
        project_dir: Project directory with config

    Returns:
        True if all services stopped successfully
    """
    console.print("[bold]Stopping MemOS services...[/bold]")
    # TODO: Implement actual service stopping
    console.print("[yellow]TODO: Implement service stopping[/yellow]")
    return True
```

**Step 4: Run test to verify it passes**

Run:
```bash
cd /mnt/g/test/MemOS/memos-cli && python -m pytest tests/test_service.py -v
```
Expected: All 3 tests PASS

**Step 5: Update cli.py with service commands**

Update the start, stop, status commands in `memos-cli/memosctl/cli.py`:

```python
# Add these imports at top
from memosctl.service import (
    display_status,
    get_service_status,
    start_services,
    stop_services,
    check_port_in_use,
    ServiceStatus,
)

# Replace the placeholder commands:

@app.command()
def start(
    mode: Optional[str] = typer.Option(
        None, "--mode", "-m",
        help="Mode(s) to start (comma-separated)"
    ),
    project: Optional[Path] = typer.Option(
        None, "--project", "-p",
        help="Project directory"
    ),
):
    """Start MemOS services for specified mode(s)."""
    modes = mode.split(",") if mode else None
    success = start_services(modes=modes, project_dir=project)
    if not success:
        raise typer.Exit(1)


@app.command()
def stop(
    project: Optional[Path] = typer.Option(
        None, "--project", "-p",
        help="Project directory"
    ),
):
    """Stop running MemOS services."""
    success = stop_services(project_dir=project)
    if not success:
        raise typer.Exit(1)


@app.command()
def status():
    """Show status of MemOS services."""
    svc_status = get_service_status()

    # Check mode-specific MCP servers
    mode_status = {}
    from memosctl.config import load_config
    config = load_config()
    for mode_name in config.active_modes:
        mode = get_mode(mode_name)
        is_running = check_port_in_use(mode.port)
        mode_status[mode_name] = ServiceStatus.RUNNING if is_running else ServiceStatus.STOPPED

    display_status(svc_status, mode_status)
```

**Step 6: Test status command**

Run:
```bash
memosctl status
```
Expected: Shows table with service status (likely all stopped unless services are running)

**Step 7: Commit**

```bash
git add memos-cli/
git commit -m "$(cat <<'EOF'
feat(cli): add service management (start/stop/status)

- ServiceStatus enum for tracking state
- Port and HTTP health checking
- Rich table display for status
- start_services with dependency checking
- stop_services placeholder

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 6: Add Skill/Hook Template Generation

**Files:**
- Create: `memos-cli/memosctl/templates/skill.md.j2`
- Create: `memos-cli/memosctl/templates/hook.js.j2`
- Create: `memos-cli/memosctl/generators.py`
- Modify: `memos-cli/memosctl/init_wizard.py`
- Test: `memos-cli/tests/test_generators.py`

**Step 1: Write the failing test**

Create `memos-cli/tests/test_generators.py`:
```python
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
        assert "project-memory" in content or "coding" in content
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
        assert "上节课" in content or "lecture" in content.lower()
```

**Step 2: Run test to verify it fails**

Run:
```bash
cd /mnt/g/test/MemOS/memos-cli && python -m pytest tests/test_generators.py -v
```
Expected: FAIL with "No module named 'memosctl.generators'"

**Step 3: Create Jinja2 templates**

Create `memos-cli/memosctl/templates/skill.md.j2`:
```jinja2
---
name: {{ skill_name }}
description: "{{ description }}"
---

# {{ title }}

{{ mode_obj.get_skill_template() }}

---

## Configuration

- **Cube ID**: `{{ cube_id }}`
- **Mode**: {{ mode_obj.emoji }} {{ mode_obj.display_name }}
- **MCP Port**: {{ mode_obj.port }}

## Available MCP Tools

{% for tool in mode_obj.mcp_tools %}
- `{{ tool }}`
{% endfor %}
```

Create `memos-cli/memosctl/templates/hook.js.j2`:
```jinja2
#!/usr/bin/env node
/**
 * MemOS Hook: UserPromptSubmit - {{ mode_obj.display_name }} Mode
 * Auto-generated by memosctl init
 *
 * Analyzes user prompts and suggests relevant memory actions.
 */

let input = '';
process.stdin.on('data', chunk => input += chunk);
process.stdin.on('end', () => {
  try {
    const data = JSON.parse(input);
    const prompt = (data.prompt || '').toLowerCase();

    const intents = detectIntents(prompt);

    if (intents.length > 0) {
      const suggestions = intents.map(i => i.suggestion).join('\n');
      console.log(JSON.stringify({
        continue: true,
        suppressOutput: false,
        message: `🧠 Memory hints:\n${suggestions}`
      }));
    } else {
      console.log(JSON.stringify({
        continue: true,
        suppressOutput: true
      }));
    }
  } catch (e) {
    console.log(JSON.stringify({
      continue: true,
      suppressOutput: true
    }));
  }
});

function detectIntents(prompt) {
  const intents = [];

{% for intent, patterns in hook_patterns.items() %}
  // {{ intent }}
  const {{ intent }}Patterns = [
{% for pattern in patterns %}
    /{{ pattern }}/,
{% endfor %}
  ];

  if ({{ intent }}Patterns.some(p => p.test(prompt))) {
    intents.push({
      type: '{{ intent }}',
      suggestion: '{{ intent_suggestions.get(intent, "→ Check memory") }}'
    });
  }

{% endfor %}
  return intents.slice(0, 2);
}
```

**Step 4: Write generators module**

Create `memos-cli/memosctl/generators.py`:
```python
#!/usr/bin/env python3
"""
MemOS CLI Template Generators

Generates Skill and Hook files from mode definitions.
"""

from pathlib import Path

from jinja2 import Environment, PackageLoader, select_autoescape

from .modes import get_mode

# Jinja2 environment
_env = Environment(
    loader=PackageLoader("memosctl", "templates"),
    autoescape=select_autoescape(),
)


# Intent suggestions for hooks
INTENT_SUGGESTIONS = {
    "history_query": "→ Consider: memos_search to find related past work",
    "error_report": "→ Consider: memos_search(query='ERROR_PATTERN ...') for past solutions",
    "decision_making": "→ After deciding: memos_save(..., memory_type='DECISION')",
    "task_completion": "→ Consider saving: MILESTONE (big feature) / BUGFIX (fix) / FEATURE (new)",
    "concept_query": "→ Consider: memos_search(query='CONCEPT ...') for definitions",
    "citation_needed": "→ Consider: memos_search(query='CITATION ...') for references",
    "relationship_query": "→ Consider: memos_get_graph or memos_trace_path for causal chains",
}


def generate_skill_file(
    mode: str,
    cube_id: str,
    output_path: Path,
) -> None:
    """Generate SKILL.md file for a mode.

    Args:
        mode: Mode name
        cube_id: Cube identifier
        output_path: Path to write SKILL.md
    """
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


def generate_hook_file(
    mode: str,
    output_path: Path,
) -> None:
    """Generate hook.js file for a mode.

    Args:
        mode: Mode name
        output_path: Path to write hook.js
    """
    mode_obj = get_mode(mode)

    template = _env.get_template("hook.js.j2")
    content = template.render(
        mode_obj=mode_obj,
        hook_patterns=mode_obj.get_hook_patterns(),
        intent_suggestions=INTENT_SUGGESTIONS,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content)


def generate_claude_files(
    mode: str,
    cube_id: str,
    project_dir: Path,
) -> dict[str, Path]:
    """Generate all Claude Code files (skills, hooks) for a mode.

    Args:
        mode: Mode name
        cube_id: Cube identifier
        project_dir: Project directory

    Returns:
        Dict mapping file type to path
    """
    claude_dir = project_dir / ".claude"
    skills_dir = claude_dir / "skills" / f"{mode}-memory"
    hooks_dir = claude_dir / "hooks" / "node"

    # Generate SKILL.md
    skill_path = skills_dir / "SKILL.md"
    generate_skill_file(mode, cube_id, skill_path)

    # Generate hook
    hook_path = hooks_dir / f"memos_{mode}_hook.js"
    generate_hook_file(mode, hook_path)

    return {
        "skill": skill_path,
        "hook": hook_path,
    }
```

**Step 5: Run test to verify it passes**

Run:
```bash
cd /mnt/g/test/MemOS/memos-cli && python -m pytest tests/test_generators.py -v
```
Expected: All 2 tests PASS

**Step 6: Update init_wizard to generate Claude files**

Add to `run_init_wizard()` in `memos-cli/memosctl/init_wizard.py`, after saving config:

```python
    # Generate Claude Code files (skills, hooks)
    from .generators import generate_claude_files
    claude_files = generate_claude_files(
        mode=mode,
        cube_id=cube_id,
        project_dir=project_dir,
    )
```

And update the completion panel to show the generated files:

```python
        console.print(Panel(
            f"""[green]✅ 配置完成！[/green]

📁 配置目录: [cyan]{project_dir}[/cyan]
🧊 Cube ID:   [cyan]{cube_id}[/cyan]
📝 模式:      [cyan]{mode_obj.emoji} {mode_obj.display_name}[/cyan]

📄 生成的文件:
   - Cube Config: {config_path}
   - .env: {env_path}
   - SKILL.md: {claude_files.get('skill', 'N/A')}
   - Hook: {claude_files.get('hook', 'N/A')}

🚀 下一步:
   1. 启动服务:  [bold]memosctl start[/bold]
   2. 查看状态:  [bold]memosctl status[/bold]
""",
            title="Setup Complete",
            border_style="green",
        ))
```

**Step 7: Commit**

```bash
git add memos-cli/
git commit -m "$(cat <<'EOF'
feat(cli): add Skill/Hook template generation

- Jinja2 templates for SKILL.md and hook.js
- Mode-specific intent patterns in hooks
- generate_claude_files() creates full structure
- Init wizard now generates Claude Code files

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 7: Final Integration and Documentation

**Files:**
- Create: `memos-cli/README.md`
- Modify: `memos-cli/pyproject.toml` (add classifiers)
- Test: Full integration test

**Step 1: Write README.md**

Create `memos-cli/README.md`:
```markdown
# MemOS CLI (memosctl)

Command-line tool for MemOS - Multi-mode Memory Management for AI assistants.

## Installation

```bash
pip install memos-cli
```

Or install from source:

```bash
cd memos-cli
pip install -e .
```

## Quick Start

### Initialize a new project

```bash
# Interactive wizard
memosctl init

# Non-interactive with options
memosctl init --name my_project --mode coding --password myneo4jpass --yes
```

### Manage services

```bash
# Check status
memosctl status

# Start services
memosctl start

# Start specific mode
memosctl start --mode student

# Stop services
memosctl stop
```

## Available Modes

| Mode | Description | Port |
|------|-------------|------|
| 🖥️ coding | For programmers and AI assistants | 18001 |
| 📚 student | For course notes and academic work | 18002 |
| 📅 daily | For personal journaling (coming soon) | 18003 |
| ✍️ writing | For creative writing (coming soon) | 18004 |

## Configuration

Configuration is stored in `~/.memos/config.toml`:

```toml
[api]
url = "http://localhost:18000"
timeout = 30.0

[neo4j]
uri = "bolt://localhost:7687"
user = "neo4j"
password = "your-password"

[qdrant]
host = "localhost"
port = 6333

[modes]
default = "coding"
active = ["coding"]
```

## Generated Files

When you run `memosctl init`, the following files are created:

```
~/.memos/<project>/
├── config.toml           # CLI configuration
├── .env                  # MCP server environment
├── cubes/
│   └── <project>_cube/
│       └── config.json   # Cube configuration
└── .claude/
    ├── skills/
    │   └── <mode>-memory/
    │       └── SKILL.md  # AI behavior rules
    └── hooks/
        └── node/
            └── memos_<mode>_hook.js
```

## License

Apache-2.0
```

**Step 2: Update pyproject.toml with classifiers**

Add to `memos-cli/pyproject.toml`:

```toml
classifiers = [
    "Development Status :: 3 - Alpha",
    "Environment :: Console",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: Apache Software License",
    "Operating System :: OS Independent",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Topic :: Software Development :: Libraries :: Python Modules",
]

[project.urls]
Homepage = "https://github.com/anthropics/memos"
Documentation = "https://github.com/anthropics/memos#readme"
Repository = "https://github.com/anthropics/memos"
```

**Step 3: Run full test suite**

Run:
```bash
cd /mnt/g/test/MemOS/memos-cli && python -m pytest tests/ -v --tb=short
```
Expected: All tests PASS

**Step 4: Test full init flow**

Run:
```bash
# Clean up any previous test
rm -rf ~/.memos/integration_test

# Run init
memosctl init --name integration_test --mode student --password testpass123 --yes

# Verify files created
ls -la ~/.memos/integration_test/
cat ~/.memos/integration_test/config.toml
cat ~/.memos/integration_test/cubes/integration_test_cube/config.json
```

Expected: All files created with correct content

**Step 5: Final commit**

```bash
git add memos-cli/
git commit -m "$(cat <<'EOF'
feat(cli): complete Phase 1 CLI framework

- README with installation and usage docs
- Full test coverage for config, modes, wizard
- Integration test verified
- Ready for Phase 2: MCP server integration

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
EOF
)"
```

---

## Summary

Phase 1 delivers:

1. ✅ **CLI Project Structure** - `memos-cli/` with Typer + Rich
2. ✅ **Configuration Module** - TOML-based config at `~/.memos/config.toml`
3. ✅ **Mode Definitions** - Coding and Student modes with memory types
4. ✅ **Interactive Init Wizard** - Project setup with prompts
5. ✅ **Service Management** - `start`, `stop`, `status` commands
6. ✅ **Template Generation** - SKILL.md and hook.js for Claude Code

**Next Phase (Phase 2):** Integrate with actual MCP servers, implement mode-specific port routing, add process management.
