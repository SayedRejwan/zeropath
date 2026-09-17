from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
import time

from zeropath.config import RoomConfig
from zeropath.orchestrator import Orchestrator
from zeropath.util import new_run_id, runs_dir, write_json


def benchmark(rooms: list[RoomConfig], *, lab_dir: Path, agent: str = "heuristic",
              backend: str = "local", repeats: int = 1, output: Path | None = None) -> dict:
    if not rooms or repeats < 1:
        raise ValueError("Benchmark requires rooms and at least one repetition")
    started = time.monotonic()
    rows = []
    for repeat in range(1, repeats + 1):
        for room in rooms:
            run_id = new_run_id()
            try:
                orch = Orchestrator(run_id, room, lab_dir, backend=backend)
                result = orch.run(agent_name=agent)
                row = asdict(result)
            except Exception as exc:
                row = {"run_id": run_id, "room_id": room.room_id, "ok": False,
                       "steps": 0, "duration_s": 0, "error": f"{type(exc).__name__}: {exc}"}
            row.update(repeat=repeat, report=str(runs_dir() / run_id / "report.json"))
            rows.append(row)
    passed = sum(row["ok"] for row in rows)
    payload = {"schema_version": "1.0", "scope": "synthetic_local_lab", "agent": agent,
               "backend": backend, "room_count": len(rooms), "repeats": repeats,
               "total": len(rows), "passed": passed, "failed": len(rows) - passed,
               "success_rate": passed / len(rows), "duration_s": round(time.monotonic() - started, 4),
               "local_80_percent_threshold_met": passed / len(rows) >= 0.8,
               "masterplan_phase0_complete": False,
               "limitations": ["Six synthetic fixtures do not establish ten TryHackMe room capability.",
                               "Human solve-time comparison is unmeasured.",
                               "Heuristic success does not establish live LLM performance."], "runs": rows}
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        write_json(output, payload)
    return payload
