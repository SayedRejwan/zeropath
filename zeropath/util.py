from __future__ import annotations

import json
import os
import re
import socket
import time
import uuid
from pathlib import Path
from typing import Any


FLAG_REGEX = re.compile(r"FLAG\{[A-Za-z0-9_\-:.]{6,128}\}")


def new_run_id() -> str:
    return uuid.uuid4().hex[:12]


def utc_ms() -> int:
    return int(time.time() * 1000)


def runs_dir() -> Path:
    return Path(os.getenv("ZEROPATH_RUNS_DIR", "runs")).resolve()


def ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def write_json(path: Path, obj: Any) -> None:
    path.write_text(json.dumps(obj, indent=2, sort_keys=True), encoding="utf-8")


def append_jsonl(path: Path, obj: Any) -> None:
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, sort_keys=True))
        f.write("\n")


def find_free_tcp_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def is_loopback_host(host: str) -> bool:
    host = host.strip().lower()
    return host in {"127.0.0.1", "localhost"}


