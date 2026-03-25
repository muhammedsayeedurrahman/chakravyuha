"""Tool abstractions for the agentic retrieval pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ToolResult:
    """Immutable result from a tool execution."""

    tool_name: str
    status: str  # "success", "partial", "error"
    data: dict = field(default_factory=dict)
    summary: str = ""
    next_actions: tuple[str, ...] = ()


def make_success(
    tool_name: str,
    data: dict,
    summary: str,
    next_actions: list[str] | None = None,
) -> ToolResult:
    """Build a successful ``ToolResult``."""
    return ToolResult(
        tool_name=tool_name,
        status="success",
        data=data,
        summary=summary,
        next_actions=tuple(next_actions or []),
    )


def make_error(tool_name: str, message: str) -> ToolResult:
    """Build an error ``ToolResult``."""
    return ToolResult(
        tool_name=tool_name,
        status="error",
        data={"error": message},
        summary=f"Error: {message}",
        next_actions=("retry", "fallback"),
    )
