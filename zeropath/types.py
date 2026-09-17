from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


Phase = Literal["INIT", "RECON", "ENUM", "ACCESS", "FLAG_HUNT", "DONE", "FAILED"]


@dataclass(frozen=True)
class ToolCall:
    tool: str
    args: dict


@dataclass(frozen=True)
class ToolResult:
    ok: bool
    tool: str
    output: str
    meta: dict

