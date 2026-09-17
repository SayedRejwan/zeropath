"""Attach to an already-running external loopback lab (no subprocess management).

Used when a room server is already live (e.g. a hand-crafted room07 instance
started outside ZeroPath). The guard rules stay identical: loopback-only,
room-scoped. ZeroPath never starts or stops anything here.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from zeropath.envs.local_lab import LocalLabInstance


@dataclass
class ExternalLabInstance(LocalLabInstance):
    pid: int = 0
    log_path: Path = None  # type: ignore[assignment]

    @property
    def managed(self) -> bool:
        return False


class ExternalLabEnv:
    """Attach to an external lab; lifecycle is owned by the operator."""

    def __init__(self, run_id: str, base_url: str, lab_dir: Path) -> None:
        self.run_id = run_id
        self.base_url = base_url.rstrip("/")
        self.lab_dir = lab_dir

    def start(self) -> LocalLabInstance:
        # Probe once so a dead target fails fast with a clear error.
        import httpx

        try:
            r = httpx.get(self.base_url, timeout=5.0, trust_env=False)
        except httpx.HTTPError as exc:
            raise RuntimeError(
                f"External lab is not reachable at {self.base_url}: {exc}"
            ) from exc
        return ExternalLabInstance(
            run_id=self.run_id,
            host_port=0,
            base_url=self.base_url,
            pid=0,
        )

    def stop(self) -> None:
        # External lab: never kill anything we did not start.
        pass
