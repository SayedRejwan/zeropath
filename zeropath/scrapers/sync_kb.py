from __future__ import annotations

from pathlib import Path
from typing import Sequence
import yaml

from zeropath.db import KnowledgeBase
from .thm_scraper import THMRoomProfile


def ensure_data_dir() -> Path:
    out_dir = Path("data") / "thm_rooms"
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir


def save_room_yaml(profile: THMRoomProfile, base_dir: Path | None = None) -> Path:
    target_dir = base_dir or ensure_data_dir()
    file_path = target_dir / f"{profile.code}.yaml"
    with open(file_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(profile.to_dict(), f, sort_keys=False, allow_unicode=True)
    return file_path


def sync_room_to_kb(profile: THMRoomProfile, kb: KnowledgeBase | None = None) -> None:
    """Sync a parsed THM room profile into the KnowledgeBase SQLite & Graph stores."""
    if kb is None:
        kb = KnowledgeBase()
        kb.init()

    # 1. Upsert room
    kb.add_room(
        code=profile.code,
        title=profile.title,
        difficulty=profile.difficulty,
        category=profile.category,
    )

    # 2. Upsert techniques and link to room
    steps = profile.attack_chain
    for step in steps:
        kb.add_technique(name=step.technique, description=step.notes)
        kb.link_room_technique(
            room_code=profile.code,
            technique_name=step.technique,
            phase=step.phase,
            order=step.order,
            notes=f"Tools: {step.tool}. {step.notes}",
        )

    # 3. Add graph relationships (LEADS_TO edges) between consecutive techniques
    for i in range(len(steps) - 1):
        src = steps[i].technique
        dst = steps[i + 1].technique
        kb.link_technique_chain(src_technique=src, dst_technique=dst)


def save_room_catalog(profiles: Sequence[THMRoomProfile], base_dir: Path | None = None) -> Path:
    """Generate or update CATALOG.md summarizing all harvested TryHackMe rooms."""
    target_dir = base_dir or ensure_data_dir()
    catalog_path = target_dir / "CATALOG.md"

    lines = [
        "# TryHackMe Room Catalog & Attack Knowledge Base",
        "",
        "This catalog documents TryHackMe challenge rooms, attack chains, and techniques harvested from technical writeups and security articles for consumption by ZeroPath agents.",
        "",
        "| Room Code | Title | Difficulty | Category | Key Tools | Attack Sequence |",
        "|---|---|---|---|---|---|",
    ]

    for p in sorted(profiles, key=lambda x: (x.category, x.difficulty, x.code)):
        tools_str = ", ".join(p.tools[:4]) if p.tools else "-"
        chain_str = " → ".join(s.technique for s in p.attack_chain) if p.attack_chain else "-"
        lines.append(
            f"| [`{p.code}`]({p.code}.yaml) | {p.title} | {p.difficulty} | {p.category} | {tools_str} | {chain_str} |"
        )

    lines.append("")
    lines.append("## Usage in ZeroPath")
    lines.append("Rooms documented here are loaded into `zeropath_local.db` and can be queried by:")
    lines.append("- SQLite relational queries (e.g. `list_room_techniques(room_code)`)")
    lines.append("- Graph attack-path queries (`kb.graph.shortest_path(src, dst)`)")
    lines.append("")

    with open(catalog_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    return catalog_path
