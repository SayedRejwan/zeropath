from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from zeropath.util import append_jsonl, ensure_dir, utc_ms, write_json


@dataclass
class RunPaths:
    run_dir: Path
    events_jsonl: Path
    summary_json: Path


class Logbook:
    def __init__(self, run_id: str, base_dir: Path) -> None:
        self.run_id = run_id
        self.paths = RunPaths(
            run_dir=base_dir / run_id,
            events_jsonl=base_dir / run_id / "events.jsonl",
            summary_json=base_dir / run_id / "summary.json",
        )
        ensure_dir(self.paths.run_dir)

    def event(self, kind: str, data: dict[str, Any]) -> None:
        append_jsonl(
            self.paths.events_jsonl,
            {
                "ts_ms": utc_ms(),
                "run_id": self.run_id,
                "kind": kind,
                "data": data,
            },
        )

    def summary(
        self,
        *,
        ok: bool,
        room_id: str,
        base_url: str,
        start_url: str,
        flag: Optional[str],
        steps: int,
        error: Optional[str] = None,
    ) -> None:
        write_json(
            self.paths.summary_json,
            {
                "run_id": self.run_id,
                "ok": ok,
                "room_id": room_id,
                "base_url": base_url,
                "start_url": start_url,
                "flag": flag,
                "steps": steps,
                "error": error,
            },
        )

