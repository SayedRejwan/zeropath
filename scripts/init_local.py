from __future__ import annotations

from zeropath.db import KnowledgeBase


def main() -> None:
    kb = KnowledgeBase()
    kb.init()
    print("OK: local SQLite schema initialized")


if __name__ == "__main__":
    main()
