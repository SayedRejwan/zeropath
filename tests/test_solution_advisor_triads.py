from __future__ import annotations

from pathlib import Path

import yaml

from zeropath.agents.solution_advisor import SolutionAdvisor

from test_triad_schema import reviewed_payload


def test_advisor_returns_action_evidence_detection_and_remedy(tmp_path: Path):
    triad_dir = tmp_path / "triads"
    triad_dir.mkdir()
    payload = reviewed_payload()
    (triad_dir / "t1190.yaml").write_text(yaml.safe_dump(payload), encoding="utf-8")

    advisor = SolutionAdvisor(data_dir=tmp_path / "rooms", triad_dir=triad_dir)
    advice = advisor.get_tactical_advice(
        room_title="public-facing application exploit",
        start_path="/lab",
        last_obs="high severity web vulnerability",
    )

    assert "VALIDATED TRIAD T1190" in advice
    assert "nuclei -u http://127.0.0.1:8080" in advice
    assert "Evidence:" in advice
    assert "Detection" in advice
    assert "Remedy [P0]" in advice

