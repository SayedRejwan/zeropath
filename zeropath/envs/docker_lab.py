from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from zeropath.util import find_free_tcp_port


@dataclass
class DockerLabInstance:
    run_id: str
    container_name: str
    network_name: str
    host_port: int
    base_url: str
    image_tag: str


class DockerLabEnv:
    """
    Local-only Docker lab runner.

    - Binds the lab service to 127.0.0.1:<random_port> (loopback only).
    - Uses container name namespaced by run_id for kill-switch cleanup.
    """

    def __init__(self, run_id: str, lab_dir: Path) -> None:
        self.run_id = run_id
        self.lab_dir = lab_dir
        self._instance: Optional[DockerLabInstance] = None

    @property
    def instance(self) -> DockerLabInstance:
        if not self._instance:
            raise RuntimeError("Environment not started.")
        return self._instance

    def _run(self, args: list[str]) -> str:
        p = subprocess.run(
            args,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            check=False,
        )
        if p.returncode != 0:
            raise RuntimeError(f"Command failed: {' '.join(args)}\n{p.stdout}")
        return p.stdout

    def logs(self, tail: int = 200) -> str:
        name = self.instance.container_name
        return self._run(["docker", "logs", "--tail", str(int(tail)), name])

    def exec(self, argv: list[str]) -> str:
        """
        Execute a command inside the lab container for diagnostics only.

        This is not used by the agent loop; it exists to satisfy the Phase 0/1
        environment abstraction and to help you debug the lab.
        """
        if not argv:
            raise ValueError("argv must be non-empty")
        allow = {"python", "python3", "ls", "cat", "env", "printenv"}
        if argv[0] not in allow:
            raise ValueError(f"Blocked docker exec command: {argv[0]}")
        name = self.instance.container_name
        return self._run(["docker", "exec", name, *argv])

    def build(self) -> str:
        dockerfile = self.lab_dir / "Dockerfile"
        if not dockerfile.exists():
            raise FileNotFoundError(f"Missing lab Dockerfile at {dockerfile}")

        tag = f"zeropath-lab:{self.run_id}"
        self._run(["docker", "build", "-t", tag, str(self.lab_dir)])
        return tag

    def start(self) -> DockerLabInstance:
        if self._instance:
            return self._instance

        tag = self.build()
        port = find_free_tcp_port()
        name = f"zeropath_lab_{self.run_id}"
        net = f"zeropath_net_{self.run_id}"

        # Per-run isolated network with no outbound connectivity.
        # Best-effort: if it already exists, creation will fail; clean it up first.
        subprocess.run(["docker", "network", "rm", net], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self._run(["docker", "network", "create", "--internal", net])

        # Bind to loopback only to reduce accidental exposure.
        self._run(
            [
                "docker",
                "run",
                "-d",
                "--rm",
                "--name",
                name,
                "--network",
                net,
                "-p",
                f"127.0.0.1:{port}:5000",
                tag,
            ]
        )

        inst = DockerLabInstance(
            run_id=self.run_id,
            container_name=name,
            network_name=net,
            host_port=port,
            base_url=f"http://127.0.0.1:{port}",
            image_tag=tag,
        )
        self._instance = inst
        return inst

    def stop(self) -> None:
        if not self._instance:
            return
        name = self._instance.container_name
        net = self._instance.network_name
        # Best-effort cleanup: ignore failures if already stopped.
        subprocess.run(["docker", "rm", "-f", name], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        subprocess.run(["docker", "network", "rm", net], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self._instance = None

    def inspect(self) -> dict:
        name = self.instance.container_name
        out = self._run(["docker", "inspect", name])
        arr = json.loads(out)
        return arr[0] if arr else {}

