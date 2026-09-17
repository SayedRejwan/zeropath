from __future__ import annotations

from pathlib import Path
from typing import Iterable

from zeropath.db import KnowledgeBase
from zeropath.paths import triads_catalog_path, triads_dir
from zeropath.schemas.triad import Triad, load_triad
from scripts.validate_triads import quality_issues


DEFAULT_TRIAD_DIR = triads_dir()
DEFAULT_CATALOG = triads_catalog_path()


def iter_reviewed_triads(base_dir: Path = DEFAULT_TRIAD_DIR) -> Iterable[tuple[Path, Triad]]:
    for path in sorted(base_dir.glob("*.yaml")):
        triad = load_triad(path)
        if triad.status != "reviewed":
            continue
        issues = quality_issues(triad, path)
        if issues:
            messages = "; ".join(issue.message for issue in issues)
            raise ValueError(f"triad is not sync-ready: {path}: {messages}")
        yield path, triad


def sync_triads(
    base_dir: Path = DEFAULT_TRIAD_DIR,
    *,
    kb: KnowledgeBase | None = None,
    catalog_path: Path = DEFAULT_CATALOG,
) -> list[Triad]:
    kb = kb or KnowledgeBase()
    kb.init()
    synced: list[Triad] = []
    for _, triad in iter_reviewed_triads(base_dir):
        kb.upsert_triad(triad.model_dump(mode="json"))
        synced.append(triad)
    save_triad_catalog(synced, catalog_path)
    return synced


def save_triad_catalog(triads: list[Triad], path: Path = DEFAULT_CATALOG) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# ZeroPath Triad Knowledge Base",
        "",
        "Reviewed YAML is the source of truth. SQLite and NetworkX are derived indexes.",
        "",
        "| ATT&CK ID | Technique | Kill Chain | Platforms | Pentest Steps | Detections | Remedies |",
        "|---|---|---|---|---:|---:|---:|",
    ]
    for triad in sorted(triads, key=lambda item: item.technique_id):
        filename = f"techniques/{triad.technique_id.lower().replace('.', '_')}.yaml"
        lines.append(
            f"| [{triad.technique_id}]({filename}) | {triad.name} | "
            f"{', '.join(triad.kill_chain)} | {', '.join(triad.platforms)} | "
            f"{len(triad.pentest_steps)} | {len(triad.detections)} | {len(triad.remedies)} |"
        )
    lines.extend(["", f"Total reviewed triads: **{len(triads)}**", ""])
    path.write_text("\n".join(lines), encoding="utf-8")
    return path
