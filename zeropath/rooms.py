from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from zeropath.config import RoomConfig, load_room_configs


@lru_cache(maxsize=1)
def rooms_dir() -> Path:
    return Path("configs") / "rooms"


@lru_cache(maxsize=1)
def all_rooms() -> dict[str, RoomConfig]:
    return load_room_configs(rooms_dir())


def get_room(room_id: str) -> RoomConfig:
    rooms = all_rooms()
    if room_id not in rooms:
        known = ", ".join(sorted(rooms.keys()))
        raise KeyError(f"Unknown room_id '{room_id}'. Known: {known}")
    return rooms[room_id]

