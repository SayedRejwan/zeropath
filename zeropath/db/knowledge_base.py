from __future__ import annotations

from dataclasses import dataclass

from .graph_store import GraphStore
from .sqlite_store import SqliteConfig, SqliteStore
from .vector_store import InMemoryVectorStore, VectorMatch


@dataclass(frozen=True)
class KnowledgeBaseConfig:
    sqlite_url: str = "sqlite:///./zeropath_local.db"
    vector_dim: int = 8  # small by default so smoke tests are fast


class KnowledgeBase:
    """
    Minimal knowledge base wiring:
    - SQLite: rooms + techniques + room-technique links
    - Graph: technique chaining / attack paths
    - Vectors: similarity search over technique text embeddings (local stub)
    """

    def __init__(self, config: KnowledgeBaseConfig = KnowledgeBaseConfig()):
        self.sql = SqliteStore(SqliteConfig(url=config.sqlite_url))
        self.graph = GraphStore()
        self.vectors = InMemoryVectorStore(dim=config.vector_dim)

    def init(self) -> None:
        self.sql.init_schema()

    # --- Relational helpers ---
    def add_room(self, *, code: str, title: str = "", difficulty: str = "", category: str = "") -> None:
        self.sql.upsert_room(code=code, title=title, difficulty=difficulty, category=category)

    def add_technique(self, *, name: str, description: str = "") -> int:
        return self.sql.upsert_technique(name=name, description=description)

    def link_room_technique(
        self, *, room_code: str, technique_name: str, phase: str, order: int, notes: str = ""
    ) -> None:
        self.sql.link_room_technique(
            room_code=room_code,
            technique_name=technique_name,
            phase=phase,
            order=order,
            notes=notes,
        )

    # --- Graph helpers ---
    def link_technique_chain(self, *, src_technique: str, dst_technique: str) -> None:
        self.graph.add_edge(src_technique, dst_technique, rel="LEADS_TO")

    def upsert_triad(self, payload: dict) -> None:
        self.sql.upsert_triad(payload)
        technique_id = str(payload["technique_id"])
        self.graph.add_node(technique_id, kind="technique", name=payload["name"])

        relations: list[tuple[str, str]] = []
        for detection in payload.get("detections", []):
            node_id = f"detection:{detection['name']}"
            self.graph.add_node(node_id, kind="detection", **detection)
            self.graph.add_edge(technique_id, node_id, rel="DETECTED_BY")
            relations.append(("DETECTED_BY", node_id))
        for remedy in payload.get("remedies", []):
            node_id = f"remedy:{remedy['name']}"
            self.graph.add_node(node_id, kind="remedy", **remedy)
            self.graph.add_edge(technique_id, node_id, rel="REMEDIATED_BY")
            relations.append(("REMEDIATED_BY", node_id))
        for related in payload.get("related_techniques", []):
            self.graph.add_edge(technique_id, related, rel="RELATED_TO")
            relations.append(("RELATED_TO", related))
        self.sql.replace_triad_relations(technique_id, relations)

    def get_triad(self, technique_id: str) -> dict | None:
        return self.sql.get_triad(technique_id)

    def list_triads(self, *, status: str | None = None) -> list[dict]:
        return self.sql.list_triads(status=status)

    # --- Vector helpers ---
    def upsert_technique_embedding(self, *, vec_id: str, vector: list[float], metadata: dict) -> None:
        self.vectors.upsert(vec_id=vec_id, vector=vector, metadata=metadata)

    def query_similar(self, *, vector: list[float], top_k: int = 5) -> list[VectorMatch]:
        return self.vectors.query(vector=vector, top_k=top_k)
