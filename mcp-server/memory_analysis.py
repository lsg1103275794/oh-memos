#!/usr/bin/env python3
"""
MemOS MCP Server Memory Analysis Module

Contains memory type detection and suggestion functions.
"""

import re


def detect_memory_type(content: str) -> tuple[str, float]:
    """
    Automatically detect memory type, returning (type, confidence).

    Confidence levels:
    - 1.0: Explicitly specified type
    - 0.85-0.95: Strong pattern match (e.g., traceback, "decided to use")
    - 0.7-0.84: Moderate pattern match
    - 0.3: Default PROGRESS (no pattern match)

    When confidence < 0.6, recommend explicitly specifying memory_type parameter.
    """
    content_lower = content.lower()

    # Strong pattern detection (pattern, confidence)
    # Grouped by type, each pattern has a confidence weight
    strong_patterns: dict[str, list[tuple[str, float]]] = {
        "ERROR_PATTERN": [
            (r"error[:\s]", 0.9),
            (r"exception[:\s]", 0.9),
            (r"traceback", 0.95),
            (r"报错[：:]", 0.9),
            (r"错误原因", 0.85),
            (r"stack\s*trace", 0.9),
            (r"异常[：:]", 0.85),
        ],
        "BUGFIX": [
            (r"修复了", 0.9),
            (r"fixed\s+(the\s+)?bug", 0.9),
            (r"根本原因.*解决", 0.85),
            (r"bug\s*fix", 0.9),
            (r"修好了", 0.85),
            (r"patch(ed)?", 0.8),
        ],
        "DECISION": [
            (r"决定采用", 0.9),
            (r"技术选型", 0.9),
            (r"架构方案", 0.85),
            (r"options?\s+considered", 0.85),
            (r"选择了.*而不是", 0.9),
            (r"权衡.*之后", 0.85),
            (r"decided\s+to\s+use", 0.9),
            (r"chose\s+.*\s+over", 0.85),
        ],
        "GOTCHA": [
            (r"注意[：:!]", 0.85),
            (r"陷阱", 0.9),
            (r"gotcha", 0.9),
            (r"小心", 0.8),
            (r"踩坑", 0.9),
            (r"坑[：:]", 0.85),
            (r"caveat", 0.85),
            (r"watch\s+out", 0.85),
            (r"警告[：:]", 0.8),
        ],
        "CODE_PATTERN": [
            (r"代码模板", 0.9),
            (r"code\s+template", 0.9),
            (r"可复用.*模式", 0.85),
            (r"reusable\s+pattern", 0.85),
            (r"snippet[：:]", 0.8),
        ],
        "CONFIG": [
            (r"环境变量", 0.9),
            (r"配置文件", 0.85),
            (r"\.env\b", 0.8),
            (r"config\s+(file|change)", 0.85),
            (r"设置.*参数", 0.8),
        ],
        "FEATURE": [
            (r"新增功能", 0.9),
            (r"implemented?\s+new", 0.85),
            (r"added\s+feature", 0.85),
            (r"新功能[：:]", 0.9),
            (r"feature\s+complete", 0.85),
        ],
        "MILESTONE": [
            (r"里程碑", 0.9),
            (r"完成了.*项目", 0.8),
            (r"release\s+v?\d", 0.85),
            (r"发布.*版本", 0.85),
            (r"milestone\s+achieved", 0.9),
            (r"项目完成", 0.85),
        ],
    }

    best_match: tuple[str, float] = ("PROGRESS", 0.3)  # Default low confidence

    for mem_type, patterns in strong_patterns.items():
        for pattern, confidence in patterns:
            if re.search(pattern, content_lower):
                if confidence > best_match[1]:
                    best_match = (mem_type, confidence)

    return best_match


def detect_memory_type_simple(content: str) -> str:
    """
    Simplified type detection, returns only the type string.
    For backward compatibility.
    """
    mem_type, _ = detect_memory_type(content)
    return mem_type


def suggest_search_queries(context: str) -> list[str]:
    """Suggest relevant search queries based on context."""
    suggestions = []
    context_lower = context.lower()

    # Error-related suggestions
    if any(word in context_lower for word in ["error", "exception", "failed", "错误", "报错", "失败"]):
        # Try to extract error type
        error_match = re.search(r"(\w+Error|\w+Exception)", context)
        if error_match:
            suggestions.append(f"ERROR_PATTERN {error_match.group(1)}")
        suggestions.append("ERROR_PATTERN solution")

    # Config-related suggestions
    if any(word in context_lower for word in ["config", "setting", "env", "配置", "环境"]):
        suggestions.append("CONFIG environment")

    # Decision-related suggestions
    if any(word in context_lower for word in ["why", "为什么", "decision", "选择", "决定", "优化"]):
        suggestions.append("DECISION architecture")

    # Gotcha-related suggestions
    if any(word in context_lower for word in ["注意", "warning", "careful", "小心", "坑"]):
        suggestions.append("GOTCHA warning")

    # History-related suggestions
    if any(word in context_lower for word in ["之前", "上次", "previously", "last time", "earlier"]):
        suggestions.append("PROGRESS history")

    return suggestions[:3]  # Return top 3 suggestions
