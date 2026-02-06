#!/usr/bin/env python3
"""Student Mode Definition - For course notes and academic work."""

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
        "LECTURE", "CONCEPT", "EXAMPLE", "QUESTION",
        "SUMMARY", "CITATION", "ARGUMENT", "EVIDENCE", "DRAFT", "TODO",
    ])

    mcp_tools: list[str] = field(default_factory=lambda: [
        "memos_search", "memos_search_context", "memos_save",
        "memos_list_v2", "memos_get", "memos_get_graph",
        "memos_calendar", "memos_export", "memos_cite", "memos_get_stats",
    ])

    relation_types: list[str] = field(default_factory=lambda: [
        "RELATES_TO", "BUILDS_ON", "CONTRADICTS", "SUPPORTS", "CITES",
    ])

    default_tags: list[str] = field(default_factory=lambda: [
        "学习", "课程", "笔记",
    ])

    def get_skill_template(self) -> str:
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
| `CITATION` | 文献引用 | Smith et al. 2024, AI综述 |
| `QUESTION` | 疑问/待解决 | 为什么递归比迭代慢？ |
'''

    def get_hook_patterns(self) -> dict[str, list[str]]:
        return {
            "history_query": [r"上节课", r"上次.*课", r"之前.*讲", r"last lecture"],
            "concept_query": [r"什么是", r"怎么理解", r"定义", r"what is", r"definition"],
            "citation_needed": [r"引用|cite", r"参考文献|reference", r"出处|source"],
            "task_completion": [r"上完课", r"看完了", r"整理.*笔记"],
        }

    def get_cube_config_overrides(self) -> dict:
        return {"metadata_fields": ["course", "semester", "week", "chapter"]}
