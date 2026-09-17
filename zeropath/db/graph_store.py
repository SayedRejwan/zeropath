from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import networkx as nx


@dataclass(frozen=True)
class GraphPath:
    nodes: list[str]


class GraphStore:
    """
    Local-dev graph store using NetworkX.

    Node IDs are plain strings (e.g. technique names, host IDs).
    In production, this can be replaced with a Neo4j adapter.
    """

    def __init__(self) -> None:
        self._g = nx.DiGraph()

    def add_edge(self, src: str, dst: str, *, rel: str = "LEADS_TO") -> None:
        self._g.add_node(src)
        self._g.add_node(dst)
        self._g.add_edge(src, dst, rel=rel)

    def add_node(self, node_id: str, **attributes: object) -> None:
        self._g.add_node(node_id, **attributes)

    def edges(self, *, rel: Optional[str] = None) -> list[tuple[str, str, str]]:
        rows = [
            (str(src), str(dst), str(data.get("rel", "LEADS_TO")))
            for src, dst, data in self._g.edges(data=True)
        ]
        return [row for row in rows if rel is None or row[2] == rel]

    def shortest_path(self, src: str, dst: str) -> Optional[GraphPath]:
        if src not in self._g or dst not in self._g:
            return None
        try:
            nodes = nx.shortest_path(self._g, src, dst)
            return GraphPath(nodes=list(nodes))
        except nx.NetworkXNoPath:
            return None
