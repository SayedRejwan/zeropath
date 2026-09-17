from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional
from urllib.parse import unquote, urlparse, urlsplit

import httpx

from zeropath.util import FLAG_REGEX, is_loopback_host


def _assert_loopback_url(url: str) -> None:
    p = urlparse(url)
    if p.scheme.lower() not in {"http", "https"} or not p.netloc:
        raise ValueError(f"Invalid URL: {url}")
    if p.username is not None or p.password is not None:
        raise ValueError("URL credentials are not allowed")
    host = p.hostname or ""
    if not is_loopback_host(host):
        raise ValueError(f"Blocked non-loopback target host: {host}")


@dataclass
class Memory:
    headers: dict[str, str] = field(default_factory=dict)
    basic_auth_user: Optional[str] = None
    basic_auth_pass: Optional[str] = None


class HttpTools:
    def __init__(
        self, base_url: str, timeout_s: float = 5.0, scope_prefix: str | None = None,
        *, transport: httpx.BaseTransport | None = None,
    ) -> None:
        _assert_loopback_url(base_url)
        parsed = httpx.URL(base_url)
        if parsed.query or parsed.fragment or parsed.path not in {"", "/"}:
            raise ValueError("Base URL must contain only an HTTP(S) origin")
        self.base_url = str(parsed).rstrip("/")
        self._origin = (parsed.scheme, parsed.host, parsed.port)
        self.scope_prefix = None
        if scope_prefix is not None:
            self._validate_path(scope_prefix)
            if urlsplit(scope_prefix).query or urlsplit(scope_prefix).fragment:
                raise ValueError("Scope prefix must be a path")
            self.scope_prefix = self._canonical_path(scope_prefix).rstrip("/") or "/"
        self.memory = Memory()
        self.client = httpx.Client(
            timeout=timeout_s, follow_redirects=True, trust_env=False, transport=transport,
            event_hooks={"request": [self._guard_request], "response": [self._guard_redirect]},
        )

    @staticmethod
    def _canonical_path(path: str) -> str:
        # Decode nested escapes before checking server-visible path boundaries.
        for _ in range(8):
            if re.search(r"%(?![0-9a-fA-F]{2})", path):
                raise ValueError("Malformed path encoding")
            decoded = unquote(path, errors="strict")
            if decoded == path:
                break
            path = decoded
        else:
            raise ValueError("Excessively encoded path")
        if "\\" in path or any(ord(c) < 32 or ord(c) == 127 for c in path):
            raise ValueError("Unsafe path characters")
        if any(part in {".", ".."} for part in path.split("/")):
            raise ValueError("Path traversal is not allowed")
        if "//" in path:
            raise ValueError("Ambiguous path separators")
        return path

    def _validate_path(self, path: str) -> None:
        if not isinstance(path, str) or not path.startswith("/") or path.startswith("//"):
            raise ValueError("Expected a root-relative path")
        if "\\" in path or any(ord(c) < 32 or ord(c) == 127 for c in path):
            raise ValueError("Unsafe path characters")
        parsed = urlsplit(path)
        if parsed.scheme or parsed.netloc or parsed.fragment:
            raise ValueError("Expected a root-relative path without fragment")
        canonical = self._canonical_path(parsed.path)
        prefix = self.scope_prefix
        if prefix and prefix != "/" and canonical != prefix and not canonical.startswith(prefix + "/"):
            raise ValueError("Request path is outside the selected room")

    def _guard_request(self, request: httpx.Request) -> None:
        _assert_loopback_url(str(request.url))
        if (request.url.scheme, request.url.host, request.url.port) != self._origin:
            raise ValueError("Request origin is outside the authorized target")
        self._validate_path(request.url.raw_path.decode("ascii"))

    def _guard_redirect(self, response: httpx.Response) -> None:
        if response.has_redirect_location:
            location = response.headers["location"]
            if "\\" in location or any(ord(c) < 32 or ord(c) == 127 for c in location):
                raise ValueError("Unsafe redirect location")
            # HTTPX normalizes literal dot segments before its next request hook.
            self._canonical_path(urlsplit(location).path)

    def close(self) -> None:
        self.client.close()

    def get(self, path: str) -> httpx.Response:
        self._validate_path(path)
        headers = dict(self.memory.headers)
        auth = None
        if self.memory.basic_auth_user is not None and self.memory.basic_auth_pass is not None:
            auth = (self.memory.basic_auth_user, self.memory.basic_auth_pass)
        return self.client.get(self.base_url + path, headers=headers, auth=auth)

    def get_json(self, path: str) -> dict:
        headers = {"Accept": "application/json", "X-Nightshift-Client": "agent"}
        resp = self.client.get(self.base_url + path, headers={**dict(self.memory.headers), **headers})
        resp.raise_for_status()
        return resp.json()

    def get_text(self, path: str) -> str:
        resp = self.client.get(self.base_url + path, headers=dict(self.memory.headers))
        resp.raise_for_status()
        return resp.text

    def post_json_agent(self, path: str, body: dict) -> httpx.Response:
        self._validate_path(path)
        return self.client.post(
            self.base_url + path,
            json=body,
            headers={**dict(self.memory.headers), "Content-Type": "application/json", "X-Nightshift-Client": "agent"},
        )

    def post_json(self, path: str, body: dict) -> httpx.Response:
        self._validate_path(path)
        return self.client.post(self.base_url + path, json=body, headers=dict(self.memory.headers))

    @staticmethod
    def extract_flag(text: str) -> Optional[str]:
        m = FLAG_REGEX.search(text or "")
        return m.group(0) if m else None

    @staticmethod
    def parse_robots_disallow(text: str) -> list[str]:
        out: list[str] = []
        for line in (text or "").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.lower().startswith("disallow:"):
                p = line.split(":", 1)[1].strip()
                if p and p.startswith("/"):
                    out.append(p)
        return out

    @staticmethod
    def parse_sitemap_locs(text: str) -> list[str]:
        # Minimal XML loc extraction without external deps.
        locs = re.findall(r"<loc>([^<]+)</loc>", text or "", flags=re.IGNORECASE)
        paths: list[str] = []
        for loc in locs:
            if loc.startswith("/"):
                paths.append(loc)
        return paths

    @staticmethod
    def parse_hint_header_key(html: str) -> Optional[str]:
        # Matches: <!-- hint: X-ZP-Key = value -->
        m = re.search(r"X-ZP-Key\s*=\s*([A-Za-z0-9_\-:.]+)", html or "", flags=re.IGNORECASE)
        return m.group(1) if m else None

