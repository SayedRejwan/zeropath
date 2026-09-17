"""Package-internal path resolution.

All bundled assets (room configs, knowledge YAML, the local lab app) live inside
the ``zeropath`` package, so they resolve identically from a source checkout and
from an installed wheel. Output state (runs, SQLite DB) stays relative to the
user's working directory.

Env overrides:
- ZEROPATH_ROOMS_DIR   -> room config directory
- ZEROPATH_DATA_DIR    -> bundled data root (thm_rooms, triads)
- ZEROPATH_LAB_DIR     -> local lab app directory
- ZEROPATH_RUNS_DIR    -> run evidence output directory (CWD-relative default)
"""

from __future__ import annotations

import os
from pathlib import Path

_PACKAGE_ROOT = Path(__file__).resolve().parent


def _override(env_var: str, default: Path) -> Path:
    value = os.getenv(env_var, "").strip()
    return Path(value).expanduser().resolve() if value else default


def package_root() -> Path:
    return _PACKAGE_ROOT


def rooms_dir() -> Path:
    return _override("ZEROPATH_ROOMS_DIR", _PACKAGE_ROOT / "configs" / "rooms")


def data_dir() -> Path:
    return _override("ZEROPATH_DATA_DIR", _PACKAGE_ROOT / "data")


def thm_rooms_dir() -> Path:
    return data_dir() / "thm_rooms"


def triads_dir() -> Path:
    return data_dir() / "triads" / "techniques"


def triads_catalog_path() -> Path:
    return data_dir() / "triads" / "CATALOG.md"


def official_cache_dir() -> Path:
    return data_dir() / "triads" / "_official"


def lab_dir() -> Path:
    return _override("ZEROPATH_LAB_DIR", _PACKAGE_ROOT / "lab")