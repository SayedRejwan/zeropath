from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

from zeropath.tools.http_tools import HttpTools


COMMON_PATHS = [
    "/robots.txt",
    "/sitemap.xml",
    "/debug",
    "/admin",
    "/admin/flag",
    "/hidden",
    "/hidden/flag",
    "/flag",
    "/flag.txt",
    "/login",
]


@dataclass
class AgentContext:
    room_prefix: str
    queue: list[str]
    visited: set[str] = field(default_factory=set)
    notes: dict[str, str] = field(default_factory=dict)


class HeuristicAgent:
    """
    Deterministic agent meant to prove the end-to-end loop without requiring an LLM.
    It only uses loopback HTTP requests (enforced by HttpTools).
    """

    def __init__(self, http: HttpTools) -> None:
        self.http = http

    def init_context(self, start_path: str) -> AgentContext:
        room_prefix = "/" + start_path.strip("/").split("/", 1)[0]
        q = [start_path]
        # Seed common endpoints under the same room prefix for lightweight dirbust.
        for p in COMMON_PATHS:
            if p.startswith("/"):
                q.append(room_prefix + p)
        return AgentContext(room_prefix=room_prefix, queue=q)

    def next_path(self, ctx: AgentContext) -> Optional[str]:
        while ctx.queue:
            p = ctx.queue.pop(0)
            if not p.startswith("/"):
                continue
            if p in ctx.visited:
                continue
            ctx.visited.add(p)
            return p
        return None

    def observe_and_expand(self, ctx: AgentContext, path: str, status_code: int, body_text: str) -> None:
        # robots.txt → disallow paths
        if path.endswith("robots.txt"):
            for dis in self.http.parse_robots_disallow(body_text):
                ctx.queue.append(dis)
                ctx.queue.append(dis.rstrip("/") + "/flag")

        # sitemap.xml → locs
        if path.endswith("sitemap.xml"):
            for loc in self.http.parse_sitemap_locs(body_text):
                ctx.queue.append(loc)
                ctx.queue.append(loc.rstrip("/") + "/flag")

        # HTML hints
        header_key = self.http.parse_hint_header_key(body_text)
        if header_key:
            self.http.memory.headers["X-ZP-Key"] = header_key
            ctx.notes["header_key"] = header_key

        # creds hint: "creds user/pass"
        m = re.search(r"creds\s+([A-Za-z0-9_\-]+)\s*/\s*([A-Za-z0-9_\-]+)", body_text, flags=re.IGNORECASE)
        if m:
            ctx.notes["user"] = m.group(1)
            ctx.notes["pass"] = m.group(2)

        # JSON creds (room03/debug returns JSON)
        # We avoid strict JSON parsing to keep deps minimal; use regex extraction.
        jm_u = re.search(r'"service_user"\s*:\s*"([^"]+)"', body_text)
        jm_p = re.search(r'"service_pass"\s*:\s*"([^"]+)"', body_text)
        if jm_u and jm_p:
            self.http.memory.basic_auth_user = jm_u.group(1)
            self.http.memory.basic_auth_pass = jm_p.group(1)
            ctx.notes["basic_auth_user"] = jm_u.group(1)

        # Query puzzle: "answer is 6*7"
        qm = re.search(r"answer\s+is\s+(\d+)\s*\*\s*(\d+)", body_text, flags=re.IGNORECASE)
        if qm:
            a = int(qm.group(1)) * int(qm.group(2))
            ctx.queue.append(ctx.room_prefix + f"/flag?answer={a}")

        # If we see explicit /flag references, enqueue them.
        for ref in re.findall(r"(/room\d{2}/[A-Za-z0-9_\-./?=]+)", body_text):
            if ref.startswith(ctx.room_prefix):
                ctx.queue.append(ref)

        # Opportunistic: if forbidden, try /flag anyway after setting hints.
        if status_code in (401, 403):
            ctx.queue.append(ctx.room_prefix + "/flag")
            ctx.queue.append(ctx.room_prefix + "/admin/flag")

    def maybe_login(self, ctx: AgentContext) -> bool:
        if ctx.room_prefix != "/room04":
            return False
        user = ctx.notes.get("user")
        password = ctx.notes.get("pass")
        if not user or not password:
            return False
        r = self.http.post_json("/room04/login", {"user": user, "password": password})
        return r.status_code == 200

