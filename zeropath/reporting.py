from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import TYPE_CHECKING

from zeropath.util import write_json

if TYPE_CHECKING:
    from zeropath.config import RoomConfig
    from zeropath.orchestrator import RunResult


def write_run_report(directory: Path, result: RunResult, room: RoomConfig, evidence: list[dict]) -> None:
    """Write measured lab evidence without inventing ATT&CK or financial impact."""
    report = {
        "schema_version": "1.0", "scope": "synthetic_local_lab",
        "result": asdict(result), "objective": room.description,
        "success_regex": room.success_regex, "http_evidence": evidence,
        "limitations": ["Synthetic training task, not a production vulnerability assessment.",
                        "No human timing baseline or live LLM performance established.",
                        "HTTP body hashes are fingerprints; logs are not tamper-proof.",
                        "No detection or remediation effectiveness inferred from a captured flag."],
    }
    write_json(directory / "report.json", report)
    lines = [f"# ZeroPath: {room.title}", "", f"I measured **{'PASS' if result.ok else 'FAIL'}** in the synthetic local lab.",
             f"I recorded {result.steps} attempts in {result.duration_s:.3f}s using {result.agent} / {result.backend}.",
             "", f"Objective: {room.description}", f"Result evidence: {result.flag or result.error}", "",
             "| Attempt | Tool | Path | HTTP status |", "|---|---|---|---|"]
    lines += [f"| {e['n']} | {e['tool']} | {str(e['path']).replace('|', '%7C')} | {e['status']} |" for e in evidence]
    lines += ["", "I retain response hashes and URLs in report.json and the event sequence in events.jsonl.", ""]
    lines += [f"- {item}" for item in report["limitations"]]
    (directory / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
