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
        """Return hook patterns for intent detection."""
        pass

    def get_cube_config_overrides(self) -> dict:
        """Return cube config overrides for this mode."""
        return {}


class ModeNotFoundError(Exception):
    """Raised when a requested mode is not found."""
    pass
