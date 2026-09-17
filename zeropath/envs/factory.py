from __future__ import annotations

import shutil
from pathlib import Path

from zeropath.envs.docker_lab import DockerLabEnv
from zeropath.envs.local_lab import LocalLabEnv
from zeropath.envs.external_lab import ExternalLabEnv


def create_lab_env(run_id: str, lab_dir: Path, backend: str = "auto", target_url: str | None = None):
    if backend not in {"auto", "local", "docker", "external"}:
        raise ValueError("Backend must be auto, local, docker, or external")
    if backend == "external":
        if not target_url:
            raise ValueError("Backend 'external' requires --target http://127.0.0.1:PORT")
        return ExternalLabEnv(run_id=run_id, base_url=target_url, lab_dir=lab_dir)
    if backend == "docker" or (backend == "auto" and shutil.which("docker")):
        return DockerLabEnv(run_id=run_id, lab_dir=lab_dir)
    return LocalLabEnv(run_id=run_id, lab_dir=lab_dir)

