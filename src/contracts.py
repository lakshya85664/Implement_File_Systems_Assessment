
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ToolStatus(str, Enum):
    OK = "ok"
    INVALID = "invalid"
    DENIED = "denied"
    NOT_FOUND = "not_found"
    FAILED = "failed"
    REVIEW_REQUIRED = "review_required"


@dataclass(frozen=True)
class ToolSpec:
    name: str
    version: str
    description: str
    max_output_bytes: int


@dataclass
class ToolCall:
    run_id: str
    tool_name: str
    arguments: dict[str, Any]


@dataclass
class ToolResult:
    run_id: str
    status: ToolStatus
    data: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    events: list[dict[str, Any]] = field(default_factory=list)
