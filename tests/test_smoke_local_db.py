from __future__ import annotations

from zeropath.db import KnowledgeBase


def test_smoke_local_kb(tmp_path):
    db_path = tmp_path / "kb.db"
    kb = KnowledgeBase(
        config=type(
            "Cfg",
            (),
            {"sqlite_url": f"sqlite:///{db_path}", "vector_dim": 4},
        )()
    )
    kb.init()

    kb.add_room(code="colddbox", title="ColddBox", difficulty="Easy", category="Web")

    kb.add_technique(name="Local_File_Inclusion", description="Read arbitrary files via include/path traversal.")
    kb.add_technique(name="Sudo_Abuse_Vim", description="Privilege escalation via sudo vim shell escape.")

    kb.link_room_technique(room_code="colddbox", technique_name="Local_File_Inclusion", phase="initial_access", order=1)
    kb.link_room_technique(room_code="colddbox", technique_name="Sudo_Abuse_Vim", phase="privilege_escalation", order=2)

    kb.link_technique_chain(src_technique="Local_File_Inclusion", dst_technique="Sudo_Abuse_Vim")
    path = kb.graph.shortest_path("Local_File_Inclusion", "Sudo_Abuse_Vim")
    assert path is not None
    assert path.nodes == ["Local_File_Inclusion", "Sudo_Abuse_Vim"]

    kb.upsert_technique_embedding(
        vec_id="colddbox_Local_File_Inclusion",
        vector=[1.0, 0.0, 0.0, 0.0],
        metadata={"room_code": "colddbox", "technique": "Local_File_Inclusion"},
    )
    kb.upsert_technique_embedding(
        vec_id="colddbox_Sudo_Abuse_Vim",
        vector=[0.9, 0.1, 0.0, 0.0],
        metadata={"room_code": "colddbox", "technique": "Sudo_Abuse_Vim"},
    )

    matches = kb.query_similar(vector=[1.0, 0.0, 0.0, 0.0], top_k=2)
    assert len(matches) == 2
    assert matches[0].id == "colddbox_Local_File_Inclusion"
    assert matches[0].score >= matches[1].score
