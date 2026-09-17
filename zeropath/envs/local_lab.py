from __future__ import annotations

import os
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from zeropath.util import find_free_tcp_port, runs_dir


@dataclass
class LocalLabInstance:
    run_id: str
    host_port: int
    base_url: str
    pid: int
    log_path: Path


class LocalLabEnv:
    """
    Fallback lab runner when Docker is unavailable.

    Starts the lab Flask app as a local subprocess bound to 127.0.0.1:<random_port>.
    """

    def __init__(self, run_id: str, lab_dir: Path) -> None:
        self.run_id = run_id
        self.lab_dir = lab_dir
        self._p: Optional[subprocess.Popen] = None
        self._inst: Optional[LocalLabInstance] = None

    @property
    def instance(self) -> LocalLabInstance:
        if not self._inst:
            raise RuntimeError("Environment not started.")
        return self._inst

    def start(self) -> LocalLabInstance:
        if self._inst:
            return self._inst

        port = find_free_tcp_port()
        log_path = runs_dir() / self.run_id / "lab_stdout.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)

        env = dict(os.environ)
        env["HOST"] = "127.0.0.1"
        env["PORT"] = str(port)

        with log_path.open("w", encoding="utf-8") as f:
            p = subprocess.Popen(
                [sys.executable, str((self.lab_dir / "app.py").resolve())],
                cwd=str(self.lab_dir),
                env=env,
                stdout=f,
                stderr=subprocess.STDOUT,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
        self._p = p

        # Wait briefly for the server to come up.
        deadline = time.time() + 10.0
        last_err: Optional[Exception] = None
        import socket

        while time.time() < deadline:
            if p.poll() is not None:
                self.stop()
                raise RuntimeError("Local lab exited before becoming ready; see lab_stdout.log")
            try:
                with socket.create_connection(("127.0.0.1", port), timeout=0.2):
                    last_err = None
                    break
            except OSError as e:
                last_err = e
                time.sleep(0.1)

        if last_err is not None:
            self.stop()
            raise RuntimeError(f"Local lab did not start: {last_err}")

        inst = LocalLabInstance(
            run_id=self.run_id,
            host_port=port,
            base_url=f"http://127.0.0.1:{port}",
            pid=p.pid,
            log_path=log_path,
        )
        self._inst = inst
        return inst

    def stop(self) -> None:
        if self._p is not None:
            self._p.terminate()
            try:
                self._p.wait(timeout=5.0)
            except subprocess.TimeoutExpired:
                self._p.kill()
                self._p.wait(timeout=5.0)
        self._p = None
        self._inst = None

    def logs(self, tail: int = 200) -> str:
        p = self.instance.log_path
        if not p.exists():
            return ""
        lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
        return "\n".join(lines[-int(tail) :])

