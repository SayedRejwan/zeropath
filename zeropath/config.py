from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, field_validator


class RoomConfig(BaseModel):
    room_id: str
    title: str
    description: str
    docker: dict[str, Any] = Field(default_factory=dict)
    start_path: str
    success_regex: str = r"FLAG\{[A-Za-z0-9_\-:.]{6,128}\}"
    max_steps: int = Field(default=30, ge=1, le=10000)

    @field_validator("success_regex")
    @classmethod
    def valid_success_regex(cls, value: str) -> str:
        try:
            pattern = re.compile(value)
        except re.error as exc:
            raise ValueError("Invalid success regex") from exc
        if pattern.search(""):
            raise ValueError("Success regex cannot match empty text")
        return value


def load_room_configs(config_dir: Path) -> dict[str, RoomConfig]:
    configs: dict[str, RoomConfig] = {}
    for p in sorted(config_dir.glob("*.yaml")):
        data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
        cfg = RoomConfig.model_validate(data)
        configs[cfg.room_id] = cfg
    return configs

