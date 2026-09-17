from __future__ import annotations

import re
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator, model_validator


ATTACK_ID_RE = re.compile(r"^T\d{4}(?:\.\d{3})?$")


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class SourceReference(StrictModel):
    title: str = Field(min_length=3)
    url: HttpUrl
    source_type: Literal["official", "vendor", "research", "community", "ai"]
    accessed: str = Field(min_length=4)


class PentestStep(StrictModel):
    order: int = Field(ge=1)
    name: str = Field(min_length=3)
    tool: str = Field(min_length=1)
    command: str = Field(min_length=3)
    prerequisite: str = Field(min_length=3)
    expected_result: str = Field(min_length=3)
    safety: str = Field(
        min_length=8,
        description="Authorization, scope, and containment condition for this command.",
    )


class Evidence(StrictModel):
    name: str = Field(min_length=3)
    artifact_type: Literal[
        "process", "file", "registry", "network", "authentication", "application", "cloud", "other"
    ]
    location: str = Field(min_length=2)
    sample: str = Field(min_length=3)


class Detection(StrictModel):
    name: str = Field(min_length=3)
    data_source: str = Field(min_length=3)
    query: str = Field(min_length=3)
    strategy: str = Field(min_length=8)
    d3fend: list[str] = Field(default_factory=list)


class Remedy(StrictModel):
    name: str = Field(min_length=3)
    priority: Literal["P0", "P1", "P2", "P3"]
    action: str = Field(min_length=8)
    verification: str = Field(min_length=8)


class Triad(StrictModel):
    schema_version: Literal["1.0"] = "1.0"
    technique_id: str
    name: str = Field(min_length=3)
    description: str = Field(min_length=12)
    kill_chain: list[str] = Field(min_length=1)
    platforms: list[str] = Field(min_length=1)
    difficulty: Literal["low", "medium", "high"]
    status: Literal["draft", "reviewed"] = "draft"
    prerequisites: list[str] = Field(default_factory=list)
    room_refs: list[str] = Field(default_factory=list)
    pentest_steps: list[PentestStep] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)
    detections: list[Detection] = Field(default_factory=list)
    remedies: list[Remedy] = Field(default_factory=list)
    cve_refs: list[str] = Field(default_factory=list)
    related_techniques: list[str] = Field(default_factory=list)
    sources: list[SourceReference] = Field(default_factory=list)

    @field_validator("technique_id")
    @classmethod
    def valid_technique_id(cls, value: str) -> str:
        if not ATTACK_ID_RE.fullmatch(value):
            raise ValueError("technique_id must match T#### or T####.###")
        return value

    @field_validator("related_techniques")
    @classmethod
    def valid_related_ids(cls, values: list[str]) -> list[str]:
        invalid = [value for value in values if not ATTACK_ID_RE.fullmatch(value)]
        if invalid:
            raise ValueError(f"invalid related technique IDs: {invalid}")
        return values

    @field_validator("cve_refs")
    @classmethod
    def valid_cves(cls, values: list[str]) -> list[str]:
        invalid = [value for value in values if not re.fullmatch(r"CVE-\d{4}-\d{4,}", value)]
        if invalid:
            raise ValueError(f"invalid CVE identifiers: {invalid}")
        return values

    @model_validator(mode="after")
    def reviewed_records_are_complete(self) -> "Triad":
        if self.status != "reviewed":
            return self
        missing = []
        if not self.pentest_steps:
            missing.append("pentest_steps")
        if not self.evidence:
            missing.append("evidence")
        if not self.detections:
            missing.append("detections")
        if not self.remedies:
            missing.append("remedies")
        if missing:
            raise ValueError(f"reviewed triad missing: {', '.join(missing)}")
        return self


def load_triad(path: Path) -> Triad:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return Triad.model_validate(data)

