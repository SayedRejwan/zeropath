from __future__ import annotations

from copy import deepcopy

import pytest
from pydantic import ValidationError

from zeropath.schemas.triad import Triad


def reviewed_payload() -> dict:
    return {
        "schema_version": "1.0",
        "technique_id": "T1190",
        "name": "Exploit Public-Facing Application",
        "description": "Exploit an exposed application in an explicitly authorized local lab.",
        "kill_chain": ["initial-access"],
        "platforms": ["Linux"],
        "difficulty": "high",
        "status": "reviewed",
        "prerequisites": ["Local vulnerable application"],
        "room_refs": ["vulnversity"],
        "pentest_steps": [
            {
                "order": 1,
                "name": "Run a focused local scan",
                "tool": "Nuclei",
                "command": "nuclei -u http://127.0.0.1:8080 -severity high",
                "prerequisite": "The lab service is bound to loopback.",
                "expected_result": "The scanner records a matched local template.",
                "safety": "Use only the disposable loopback lab and non-destructive templates.",
            }
        ],
        "evidence": [
            {
                "name": "Web request",
                "artifact_type": "application",
                "location": "reverse proxy log",
                "sample": "127.0.0.1 POST /lab status=500",
            }
        ],
        "detections": [
            {
                "name": "Exploit request burst",
                "data_source": "reverse proxy log",
                "query": "count(high_severity_signature) > 3",
                "strategy": "Correlate exploit signatures with abnormal server errors.",
                "d3fend": ["D3-NTA"],
            }
        ],
        "remedies": [
            {
                "name": "Patch exposed component",
                "priority": "P0",
                "action": "Deploy the fixed build and disable the vulnerable route.",
                "verification": "Repeat the exact test and confirm no template match.",
            }
        ],
        "cve_refs": [],
        "related_techniques": ["T1595.002"],
        "sources": [
            {
                "title": "MITRE ATT&CK T1190",
                "url": "https://attack.mitre.org/techniques/T1190/",
                "source_type": "official",
                "accessed": "2026-09-17",
            },
            {
                "title": "CISA KEV Catalog",
                "url": "https://www.cisa.gov/known-exploited-vulnerabilities-catalog",
                "source_type": "official",
                "accessed": "2026-09-17",
            },
        ],
    }


def test_reviewed_triad_schema_accepts_complete_record():
    triad = Triad.model_validate(reviewed_payload())
    assert triad.technique_id == "T1190"
    assert triad.pentest_steps[0].tool == "Nuclei"


def test_bad_attack_identifier_is_rejected():
    payload = deepcopy(reviewed_payload())
    payload["technique_id"] = "ATTACK-1190"
    with pytest.raises(ValidationError):
        Triad.model_validate(payload)


def test_reviewed_triad_requires_all_three_operational_sides():
    payload = deepcopy(reviewed_payload())
    payload["detections"] = []
    with pytest.raises(ValidationError):
        Triad.model_validate(payload)

