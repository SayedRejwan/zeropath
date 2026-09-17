from __future__ import annotations

import socket
from typing import Iterable


def quick_port_scan(host: str, ports: Iterable[int], timeout_s: float = 0.3) -> list[int]:
    """
    Minimal TCP connect scan intended for localhost demo environments only.
    """
    open_ports: list[int] = []
    for port in ports:
        try:
            with socket.create_connection((host, int(port)), timeout=timeout_s):
                open_ports.append(int(port))
        except OSError:
            continue
    return open_ports

