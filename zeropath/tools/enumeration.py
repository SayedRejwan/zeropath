from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from zeropath.tools.http_tools import HttpTools


@dataclass(frozen=True)
class DirBustHit:
    path: str
    status_code: int
    length: int


def dir_bust(http: HttpTools, base_path: str, words: Iterable[str]) -> list[DirBustHit]:
    """
    Tiny, safe dir-buster for localhost lab targets.
    """
    hits: list[DirBustHit] = []
    base_path = "/" + base_path.strip("/")
    for w in words:
        w = str(w).strip().strip("/")
        if not w:
            continue
        p = base_path + "/" + w
        r = http.get(p)
        if r.status_code < 400:
            hits.append(DirBustHit(path=p, status_code=r.status_code, length=len(r.text or "")))
    return hits

