from __future__ import annotations

import subprocess


def run_local_command(argv: list[str], timeout_s: float = 10.0) -> str:
    """
    Extremely constrained local command runner for diagnostics.

    This is NOT exposed to any autonomous agent logic in this prototype.
    """
    if not argv:
        raise ValueError("argv must be non-empty")

    allow = {
        "docker",
        "python",
        "python3",
    }
    if argv[0] not in allow:
        raise ValueError(f"Blocked local command: {argv[0]}")

    p = subprocess.run(
        argv,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=timeout_s,
        check=False,
    )
    if p.returncode != 0:
        raise RuntimeError(f"Command failed ({p.returncode}): {' '.join(argv)}\n{p.stdout}")
    return p.stdout

