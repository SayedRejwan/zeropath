from __future__ import annotations

import subprocess


def kill_run(run_id: str) -> None:
    name = f"zeropath_lab_{run_id}"
    subprocess.run(["docker", "rm", "-f", name], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

