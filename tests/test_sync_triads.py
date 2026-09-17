from __future__ import annotations

from pathlib import Path

import yaml

from zeropath.db import KnowledgeBase
from zeropath.db.knowledge_base import KnowledgeBaseConfig
from zeropath.scrapers.sync_triads import sync_triads

from test_triad_schema import reviewed_payload


def test_sync_produces_sqlite_records_and_graph_edges(tmp_path: Path):
    source_dir = tmp_path / "triads"
    source_dir.mkdir()
    (source_dir / "t1190.yaml").write_text(
        yaml.safe_dump(reviewed_payload(), sort_keys=False), encoding="utf-8"
    )

    kb = KnowledgeBase(
        KnowledgeBaseConfig(sqlite_url=f"sqlite:///{tmp_path / 'triads.db'}", vector_dim=4)
    )
    synced = sync_triads(source_dir, kb=kb, catalog_path=tmp_path / "CATALOG.md")

    assert [triad.technique_id for triad in synced] == ["T1190"]
    stored = kb.get_triad("T1190")
    assert stored is not None
    assert stored["pentest_steps"][0]["command"].startswith("nuclei")

    relations = kb.sql.list_triad_relations("T1190")
    relation_types = {relation for relation, _ in relations}
    assert {"DETECTED_BY", "REMEDIATED_BY", "RELATED_TO"} <= relation_types
    assert kb.graph.edges(rel="DETECTED_BY")
    assert kb.graph.edges(rel="REMEDIATED_BY")


def test_sync_skips_valid_drafts(tmp_path: Path):
    payload = reviewed_payload()
    payload["status"] = "draft"
    payload["pentest_steps"] = []
    payload["evidence"] = []
    payload["detections"] = []
    payload["remedies"] = []
    source_dir = tmp_path / "triads"
    source_dir.mkdir()
    (source_dir / "draft.yaml").write_text(yaml.safe_dump(payload), encoding="utf-8")

    kb = KnowledgeBase(
        KnowledgeBaseConfig(sqlite_url=f"sqlite:///{tmp_path / 'draft.db'}", vector_dim=4)
    )
    assert sync_triads(source_dir, kb=kb, catalog_path=tmp_path / "CATALOG.md") == []
    assert kb.list_triads() == []

