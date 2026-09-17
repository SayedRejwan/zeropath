from __future__ import annotations

import shutil
from pathlib import Path

from zeropath.envs.docker_lab import DockerLabEnv
from zeropath.envs.local_lab import LocalLabEnv


def create_lab_env(run_id: str, lab_dir: Path, backend: str = "auto"):
    if backend not in {"auto", "local", "docker"}:
        raise ValueError("Backend must be auto, local, or docker")
    if backend == "docker" or (backend == "auto" and shutil.which("docker")):
        return DockerLabEnv(run_id=run_id, lab_dir=lab_dir)
    return LocalLabEnv(run_id=run_id, lab_dir=lab_dir)

