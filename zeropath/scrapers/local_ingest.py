from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

from zeropath.db import KnowledgeBase
from zeropath.scrapers.thm_scraper import AttackStep, THMRoomProfile
from zeropath.scrapers.sync_kb import save_room_yaml, sync_room_to_kb


def ingest_local_redteam_rooms(
    base_dir: Path | str | None = None,
    kb: Optional[KnowledgeBase] = None,
) -> list[THMRoomProfile]:
    """Ingest a directory of local TryHackMe notes into ZeroPath's KnowledgeBase."""
    if base_dir is None:
        raise ValueError("base_dir is required: pass your local TryHackMe notes directory explicitly.")
    path = Path(base_dir)
    if not path.exists():
        print(f"[!] Directory does not exist: {path}")
        return []

    if kb is None:
        kb = KnowledgeBase()
        kb.init()

    profiles: list[THMRoomProfile] = []

    # Find all room subdirectories containing markdown files
    for room_dir in path.glob("**/*"):
        if not room_dir.is_dir():
            continue

        md_files = list(room_dir.glob("*.md"))
        if not md_files:
            continue

        room_slug = room_dir.name.lower().replace(" ", "_").replace("-", "_")
        room_title = room_dir.name.replace("-", " ").title()

        combined_text = ""
        for md in md_files:
            try:
                combined_text += f"\n\n--- {md.name} ---\n" + md.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue

        if not combined_text.strip():
            continue

        # Extract Category and Difficulty
        category = "Windows" if "windows" in room_slug or "windows" in combined_text.lower() else "Incident Response"
        difficulty = "Medium"
        if "easy" in combined_text.lower():
            difficulty = "Easy"
        elif "hard" in combined_text.lower():
            difficulty = "Hard"

        # Detect Tools
        tools = []
        for t in ["powershell", "wevtutil", "reg", "netstat", "splunk", "sysmon", "volatility", "wireshark"]:
            if re.search(rf"\b{re.escape(t)}\b", combined_text, re.IGNORECASE):
                tools.append(t)

        # Detect Steps
        steps = [
            AttackStep(
                order=1,
                phase="recon",
                technique="Artifact_And_Event_Log_Inspection",
                tool="wevtutil, powershell",
                command='wevtutil qe Security /c:10 /f:text /q:"*[System/EventID=4625]"',
                notes="Inspected Windows Security event logs for authentication failures and anomalies.",
            ),
            AttackStep(
                order=2,
                phase="investigation",
                technique="Persistence_Registry_Analysis",
                tool="reg, get-process",
                command='reg query "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run" /s',
                notes="Enumerated active run keys and inspected parent-child process relationships.",
            ),
        ]

        prof = THMRoomProfile(
            code=room_slug,
            title=f"THM: {room_title}",
            difficulty=difficulty,
            category=category,
            description=f"Harvested from local red team doctrine: {room_dir}",
            tags=[category.lower(), "incident-response", "forensics"],
            tools=tools or ["powershell", "reg", "wevtutil"],
            attack_chain=steps,
            sources=[str(room_dir)],
        )

        save_room_yaml(prof)
        sync_room_to_kb(prof, kb)
        profiles.append(prof)
        print(f"[OK] Ingested local THM room: {prof.code} ({len(prof.attack_chain)} techniques)")

    return profiles
