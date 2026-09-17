from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Iterable, Optional

from sqlalchemy import ForeignKey, String, Text, UniqueConstraint, create_engine, delete, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Room(Base):
    __tablename__ = "rooms"

    code: Mapped[str] = mapped_column(String(128), primary_key=True)
    title: Mapped[str] = mapped_column(String(512), default="")
    difficulty: Mapped[str] = mapped_column(String(32), default="")
    category: Mapped[str] = mapped_column(String(64), default="")

    techniques: Mapped[list["RoomTechnique"]] = relationship(
        back_populates="room", cascade="all, delete-orphan"
    )


class Technique(Base):
    __tablename__ = "techniques"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(256), unique=True, index=True)
    description: Mapped[str] = mapped_column(Text, default="")

    rooms: Mapped[list["RoomTechnique"]] = relationship(
        back_populates="technique", cascade="all, delete-orphan"
    )


class RoomTechnique(Base):
    __tablename__ = "room_techniques"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    room_code: Mapped[str] = mapped_column(ForeignKey("rooms.code", ondelete="CASCADE"))
    technique_id: Mapped[int] = mapped_column(
        ForeignKey("techniques.id", ondelete="CASCADE")
    )

    phase: Mapped[str] = mapped_column(String(64), default="unknown")
    order: Mapped[int] = mapped_column(default=0)
    notes: Mapped[str] = mapped_column(Text, default="")

    room: Mapped["Room"] = relationship(back_populates="techniques")
    technique: Mapped["Technique"] = relationship(back_populates="rooms")


class TriadRecord(Base):
    __tablename__ = "triad_records"

    technique_id: Mapped[str] = mapped_column(String(16), primary_key=True)
    name: Mapped[str] = mapped_column(String(256), index=True)
    description: Mapped[str] = mapped_column(Text)
    kill_chain_json: Mapped[str] = mapped_column(Text, default="[]")
    platforms_json: Mapped[str] = mapped_column(Text, default="[]")
    difficulty: Mapped[str] = mapped_column(String(16))
    status: Mapped[str] = mapped_column(String(16), index=True)
    payload_json: Mapped[str] = mapped_column(Text)


class TriadRelation(Base):
    __tablename__ = "triad_relations"
    __table_args__ = (
        UniqueConstraint("src", "dst", "relation", name="uq_triad_relation"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    src: Mapped[str] = mapped_column(String(256), index=True)
    dst: Mapped[str] = mapped_column(String(256), index=True)
    relation: Mapped[str] = mapped_column(String(64), index=True)


@dataclass(frozen=True)
class SqliteConfig:
    url: str = "sqlite:///./zeropath_local.db"


class SqliteStore:
    def __init__(self, config: SqliteConfig):
        self._engine = create_engine(config.url, future=True)

    def init_schema(self) -> None:
        Base.metadata.create_all(self._engine)

    def upsert_room(
        self, *, code: str, title: str = "", difficulty: str = "", category: str = ""
    ) -> None:
        with Session(self._engine) as session:
            room = session.get(Room, code)
            if room is None:
                room = Room(code=code)
                session.add(room)

            room.title = title
            room.difficulty = difficulty
            room.category = category
            session.commit()

    def get_room(self, code: str) -> Optional[Room]:
        with Session(self._engine) as session:
            return session.get(Room, code)

    def upsert_technique(self, *, name: str, description: str = "") -> int:
        with Session(self._engine) as session:
            existing = session.scalar(select(Technique).where(Technique.name == name))
            if existing is None:
                existing = Technique(name=name, description=description)
                session.add(existing)
                session.commit()
                session.refresh(existing)
                return existing.id

            existing.description = description or existing.description
            session.commit()
            return existing.id

    def link_room_technique(
        self,
        *,
        room_code: str,
        technique_name: str,
        phase: str,
        order: int,
        notes: str = "",
    ) -> None:
        with Session(self._engine) as session:
            room = session.get(Room, room_code)
            if room is None:
                raise ValueError(f"Room not found: {room_code}")

            tech = session.scalar(select(Technique).where(Technique.name == technique_name))
            if tech is None:
                tech = Technique(name=technique_name, description="")
                session.add(tech)
                session.flush()

            # Avoid duplicates for the same (room, technique, phase, order)
            existing = session.scalar(
                select(RoomTechnique).where(
                    RoomTechnique.room_code == room_code,
                    RoomTechnique.technique_id == tech.id,
                    RoomTechnique.phase == phase,
                    RoomTechnique.order == order,
                )
            )
            if existing is None:
                session.add(
                    RoomTechnique(
                        room_code=room_code,
                        technique_id=tech.id,
                        phase=phase,
                        order=order,
                        notes=notes,
                    )
                )
            else:
                existing.notes = notes or existing.notes

            session.commit()

    def list_room_techniques(self, room_code: str) -> list[tuple[str, str, int]]:
        """Return list of (technique_name, phase, order)."""
        with Session(self._engine) as session:
            rows: Iterable[tuple[str, str, int]] = session.execute(
                select(Technique.name, RoomTechnique.phase, RoomTechnique.order)
                .join(RoomTechnique, RoomTechnique.technique_id == Technique.id)
                .where(RoomTechnique.room_code == room_code)
                .order_by(RoomTechnique.order.asc())
            ).all()
            return [(name, phase, order) for (name, phase, order) in rows]

    def upsert_triad(self, payload: dict) -> None:
        technique_id = str(payload["technique_id"])
        with Session(self._engine) as session:
            record = session.get(TriadRecord, technique_id)
            if record is None:
                record = TriadRecord(
                    technique_id=technique_id,
                    name=str(payload["name"]),
                    description=str(payload["description"]),
                    difficulty=str(payload["difficulty"]),
                    status=str(payload["status"]),
                    payload_json="{}",
                )
                session.add(record)
            record.name = str(payload["name"])
            record.description = str(payload["description"])
            record.kill_chain_json = json.dumps(payload.get("kill_chain", []))
            record.platforms_json = json.dumps(payload.get("platforms", []))
            record.difficulty = str(payload["difficulty"])
            record.status = str(payload["status"])
            record.payload_json = json.dumps(payload, sort_keys=True)
            session.commit()

    def get_triad(self, technique_id: str) -> Optional[dict]:
        with Session(self._engine) as session:
            record = session.get(TriadRecord, technique_id)
            return json.loads(record.payload_json) if record else None

    def list_triads(self, *, status: Optional[str] = None) -> list[dict]:
        with Session(self._engine) as session:
            statement = select(TriadRecord).order_by(TriadRecord.technique_id.asc())
            if status:
                statement = statement.where(TriadRecord.status == status)
            records = session.scalars(statement).all()
            return [json.loads(record.payload_json) for record in records]

    def replace_triad_relations(self, technique_id: str, relations: list[tuple[str, str]]) -> None:
        with Session(self._engine) as session:
            session.execute(delete(TriadRelation).where(TriadRelation.src == technique_id))
            for relation, dst in relations:
                session.add(TriadRelation(src=technique_id, dst=dst, relation=relation))
            session.commit()

    def list_triad_relations(self, technique_id: str) -> list[tuple[str, str]]:
        with Session(self._engine) as session:
            rows = session.execute(
                select(TriadRelation.relation, TriadRelation.dst)
                .where(TriadRelation.src == technique_id)
                .order_by(TriadRelation.relation, TriadRelation.dst)
            ).all()
            return [(relation, dst) for relation, dst in rows]
