#!/usr/bin/env python3
"""Coding Mode Definition - For programmers and AI coding assistants."""

from dataclasses import dataclass, field
from .base import BaseMode


@dataclass
class CodingMode(BaseMode):
    """Coding mode for developers."""

    name: str = "coding"
    display_name: str = "编码开�?
    description: str = "适合程序员、AI助手用户"
    emoji: str = "🖥�?
    port: int = 18001

    memory_types: list[str] = field(default_factory=lambda: [
        "BUGFIX", "ERROR_PATTERN", "DECISION", "CODE_PATTERN",
        "CONFIG", "GOTCHA", "MILESTONE", "FEATURE", "PROGRESS",
    ])

    mcp_tools: list[str] = field(default_factory=lambda: [
        "memos_search", "memos_search_context", "memos_save",
        "memos_list_v2", "memos_get", "memos_get_graph",
        "memos_trace_path", "memos_export_schema", "memos_suggest", "memos_get_stats",
    ])

    relation_types: list[str] = field(default_factory=lambda: [
        "CAUSE", "RELATE", "CONDITION", "CONFLICT",
    ])

    default_tags: list[str] = field(default_factory=lambda: [
        "coding", "debug", "architecture",
    ])

    def get_skill_template(self) -> str:
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
'''

    def get_hook_patterns(self) -> dict[str, list[str]]:
        return {
            "history_query": [r"之前.*bug", r"上次.*错误", r"previous.*error", r"last time.*fix"],
            "error_report": [r"error|错误|报错", r"exception|异常", r"traceback", r"failed|失败"],
            "decision_making": [r"应该(用|选|采用)", r"哪个.*�?, r"vs\.?|versus", r"方案|approach"],
            "task_completion": [r"修复了|fixed", r"实现了|implemented", r"完成了|completed"],
        }
