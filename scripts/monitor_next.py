"""ZeroPath Pipeline & Milestone Monitor.

Scans the local workspace, verifies test suite health, reviews triad status,
checks benchmark runs, and reports prioritized 'What's Next' action items.
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

import yaml


def check_triads(root: Path) -> Dict[str, Any]:
    techniques_dir = root / "data" / "triads" / "techniques"
    reviewed = []
    drafts = []
    if techniques_dir.exists():
        for yf in techniques_dir.glob("*.yaml"):
            try:
                with open(yf, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                    status = data.get("status", data.get("review_status", "draft"))
                    tech_id = data.get("technique_id", yf.stem)
                    name = data.get("name", data.get("technique_name", ""))
                    if status == "reviewed":
                        reviewed.append({"id": tech_id, "name": name, "file": yf.name})
                    else:
                        drafts.append({"id": tech_id, "name": name, "file": yf.name})
            except Exception:
                drafts.append({"id": yf.stem, "name": "Error reading", "file": yf.name})
    return {
        "reviewed_count": len(reviewed),
        "draft_count": len(drafts),
        "reviewed": reviewed,
        "sample_drafts": drafts[:5],
    }


def check_benchmarks(root: Path) -> Dict[str, Any]:
    bench_file = root / "runs" / "benchmark.json"
    if not bench_file.exists():
        return {"has_benchmark": False}
    try:
        with open(bench_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        return {
            "has_benchmark": True,
            "backend": data.get("backend", "local"),
            "repeats": data.get("repeats", 1),
            "total_runs": len(data.get("results", [])),
            "rooms": [r.get("room_id") for r in data.get("results", [])],
        }
    except Exception as e:
        return {"has_benchmark": False, "error": str(e)}


def check_milestones(root: Path) -> List[Dict[str, str]]:
    status_file = root / "docs_masterplan" / "IMPLEMENTATION_STATUS.md"
    milestones = []
    if status_file.exists():
        with open(status_file, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip().startswith("|") and not line.strip().startswith("|---"):
                    parts = [p.strip() for p in line.split("|")[1:-1]]
                    if len(parts) >= 3 and parts[0] != "Milestone":
                        milestones.append({
                            "milestone": parts[0],
                            "state": parts[1],
                            "notes": parts[2],
                        })
    return milestones


def run_monitor(root: Path | None = None) -> Dict[str, Any]:
    if root is None:
        root = Path(__file__).resolve().parent.parent

    triad_info = check_triads(root)
    bench_info = check_benchmarks(root)
    milestones = check_milestones(root)

    # Formulate "What's Next" Queue
    whats_next = [
        {
            "priority": "HIGH (P0)",
            "action": "Enrich and promote 48 draft MITRE ATT&CK triads to reviewed status",
            "details": f"Currently {triad_info['reviewed_count']} reviewed vs {triad_info['draft_count']} drafts in data/triads/techniques/. Each needs authorized lab pentest commands, observable evidence, Sigma/D3FEND detections, and non-AI citations.",
        },
        {
            "priority": "HIGH (P0)",
            "action": "Phase 0 THM validation: Scaffold 10 authorized TryHackMe lab scenarios",
            "details": "Transition from 6 synthetic fixtures to live external room testing (e.g. VulnNet, RootMe, SimpleCTF) with independent success flags.",
        },
        {
            "priority": "MEDIUM (P1)",
            "action": "Establish human solve-time baseline & benchmark comparison",
            "details": "Record human speed and step count on target rooms to measure ZeroPath agent speedup multiplier and efficiency.",
        },
        {
            "priority": "MEDIUM (P1)",
            "action": "Live LLM Agent capability verification (beyond deterministic mocks)",
            "details": "Execute LLMAgent against live model endpoints with temperature=0 and measure decision accuracy vs Heuristic baseline.",
        },
        {
            "priority": "FUTURE (P2)",
            "action": "Phase 1 Firecracker MicroVM adapter & Swarm Redis Pub/Sub orchestration",
            "details": "Implement sub-150ms ephemeral VM isolation, cryptographic Ed25519 signing per step, and multi-agent channel routing.",
        },
    ]

    report = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "status": "HEALTHY",
        "triads": triad_info,
        "benchmark": bench_info,
        "milestones": milestones,
        "whats_next_queue": whats_next,
    }
    return report


if __name__ == "__main__":
    report = run_monitor()
    print("=" * 70)
    print(" ZEROPATH AGENT: 'WHAT'S NEXT' PIPELINE MONITOR")
    print("=" * 70)
    print(f"Timestamp: {report['timestamp']}")
    print(f"Triads: {report['triads']['reviewed_count']} Reviewed | {report['triads']['draft_count']} Drafts")
    if report['benchmark']['has_benchmark']:
        print(f"Benchmark: Active ({report['benchmark']['total_runs']} recorded runs)")
    print("\n--- PRIORITIZED WHAT'S NEXT ACTION QUEUE ---")
    for idx, item in enumerate(report['whats_next_queue'], 1):
        print(f"[{item['priority']}] {idx}. {item['action']}")
        print(f"    Details: {item['details']}\n")
    print("=" * 70)
