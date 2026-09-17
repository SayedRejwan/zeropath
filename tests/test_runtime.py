from __future__ import annotations

import importlib
import json
import socket
from pathlib import Path
from urllib.parse import urlparse

import pytest

from zeropath.config import load_room_configs
from zeropath.orchestrator import Orchestrator
from zeropath.paths import lab_dir, rooms_dir
from zeropath.types import ToolCall


ROOT = Path(__file__).resolve().parents[1]
ROOMS = list(load_room_configs(rooms_dir()).values())


@pytest.fixture
def isolated_runs(tmp_path, monkeypatch):
    directory = tmp_path / "runs"
    for module in ("zeropath.orchestrator", "zeropath.envs.local_lab", "zeropath.benchmark"):
        monkeypatch.setattr(importlib.import_module(module), "runs_dir", lambda: directory)
    return directory


def assert_stopped(orch, result):
    assert orch.env._p is None
    assert orch.env._inst is None
    if result.base_url:
        parsed = urlparse(result.base_url)
        with socket.socket() as connection:
            connection.settimeout(0.2)
            assert connection.connect_ex((parsed.hostname, parsed.port)) != 0


@pytest.mark.parametrize("room", ROOMS, ids=lambda room: room.room_id)
def test_local_rooms_capture_evidence_and_cleanup(room, isolated_runs):
    orch = Orchestrator(room.room_id, room, lab_dir(), backend="local")
    result = orch.run()
    assert result.ok, result.error
    assert result.duration_s > 0
    report_dir = isolated_runs / result.run_id
    report = json.loads((report_dir / "report.json").read_text())
    events = [json.loads(line) for line in (report_dir / "events.jsonl").read_text().splitlines()]
    requests = report["http_evidence"]
    assert len(requests) == result.steps
    assert [item["n"] for item in requests] == list(range(1, result.steps + 1))
    assert all(len(item["sha256"]) == 64 for item in requests)
    assert requests[-1]["status"] == 200
    assert report["result"]["flag"] == result.flag
    assert report["scope"] == "synthetic_local_lab"
    assert (report_dir / "report.md").exists()
    assert sum(event["kind"] == "env_stopped" for event in events) == 1
    if room.start_path.startswith("/room04"):
        logins = [item for item in requests if item["tool"] == "http_post_json"]
        assert len(logins) == 1
        assert logins[0]["path"] == "/room04/login"
    assert_stopped(orch, result)


def test_startup_failure_is_reported_and_cleaned(isolated_runs, tmp_path):
    lab = tmp_path / "broken_lab"
    lab.mkdir()
    (lab / "app.py").write_text("raise RuntimeError('intentional startup failure')\n")
    orch = Orchestrator("startup-failure", ROOMS[0], lab, backend="local")
    result = orch.run()
    assert not result.ok
    assert "run_error" in result.error
    assert result.steps == 0
    assert json.loads((isolated_runs / result.run_id / "report.json").read_text())["http_evidence"] == []
    assert_stopped(orch, result)


def test_step_budget_has_explicit_failure(isolated_runs):
    room = ROOMS[0].model_copy(update={"max_steps": 1})
    orch = Orchestrator("budget", room, lab_dir(), backend="local")
    result = orch.run()
    assert not result.ok
    assert result.steps == 1
    assert result.error.startswith("max_steps_exceeded")
    assert_stopped(orch, result)


def test_success_uses_configured_regex_not_any_flag(isolated_runs):
    room = ROOMS[1].model_copy(update={"success_regex": r"FLAG\{ONLY_THIS_ROOM_IS_VALID\}"})
    orch = Orchestrator("wrong-flag", room, lab_dir(), backend="local")
    result = orch.run()
    assert not result.ok
    assert result.flag is None
    report = json.loads((isolated_runs / result.run_id / "report.json").read_text())
    assert any(item["path"].endswith("/admin/flag") and item["status"] == 200 for item in report["http_evidence"])
    assert_stopped(orch, result)


def test_llm_consumes_queue_and_tracks_visited_without_network(isolated_runs, monkeypatch):
    agent_module = importlib.import_module("zeropath.orchestrator")
    advisor_module = importlib.import_module("zeropath.agents.solution_advisor")

    class FakeLLM:
        closed = False

        def __init__(self):
            self.observations = []

        def decide(self, **kwargs):
            self.observations.append(kwargs)
            return ToolCall("http_get", {"path": kwargs["queue"][0]})

        def close(self):
            self.closed = True

    llm = FakeLLM()
    monkeypatch.setattr(advisor_module, "SolutionAdvisor", lambda: object())
    monkeypatch.setattr(agent_module.LLMAgent, "from_env", lambda **kwargs: llm)
    room = ROOMS[1]
    orch = Orchestrator("llm-mock", room, lab_dir(), backend="local")
    result = orch.run(agent_name="llm")
    assert result.ok, result.error
    assert llm.closed
    assert room.title in llm.observations[0]["goal"]
    for previous, current in zip(llm.observations, llm.observations[1:]):
        consumed = previous["queue"][0]
        assert consumed in current["visited"]
        assert consumed not in current["queue"]
    assert_stopped(orch, result)


def test_benchmark_continues_after_failure_and_saves_measurements(isolated_runs, tmp_path):
    benchmark_module = importlib.import_module("zeropath.benchmark")
    failing = ROOMS[0].model_copy(update={"max_steps": 1})
    output = tmp_path / "benchmark.json"
    payload = benchmark_module.benchmark([failing, ROOMS[1]], lab_dir=lab_dir(), output=output)
    assert payload["total"] == 2
    assert payload["passed"] == payload["failed"] == 1
    assert payload["success_rate"] == 0.5
    assert not payload["masterplan_phase0_complete"]
    assert payload["runs"][1]["ok"]
    assert all(Path(row["report"]).exists() for row in payload["runs"])
    assert json.loads(output.read_text()) == payload


def test_invalid_llm_actions_exhaust_budget_and_cleanup(isolated_runs, monkeypatch):
    module = importlib.import_module("zeropath.orchestrator")
    advisor = importlib.import_module("zeropath.agents.solution_advisor")

    class InvalidLLM:
        def decide(self, **kwargs):
            return ToolCall("shell", {"path": "/room02/"})

        def close(self):
            pass

    monkeypatch.setattr(advisor, "SolutionAdvisor", lambda: object())
    monkeypatch.setattr(module.LLMAgent, "from_env", lambda **kwargs: InvalidLLM())
    room = ROOMS[1].model_copy(update={"max_steps": 2})
    orch = Orchestrator("invalid-llm", room, lab_dir(), backend="local")
    result = orch.run(agent_name="llm")
    assert not result.ok
    assert result.steps == 2
    assert "Unsupported tool" in result.error
    assert_stopped(orch, result)


def test_client_close_failure_still_stops_lab(isolated_runs, monkeypatch):
    module = importlib.import_module("zeropath.orchestrator")
    original = module.HttpTools.close

    def failing_close(self):
        original(self)
        raise RuntimeError("close failed")

    monkeypatch.setattr(module.HttpTools, "close", failing_close)
    orch = Orchestrator("close-failure", ROOMS[1], lab_dir(), backend="local")
    result = orch.run()
    assert not result.ok
    assert result.flag is not None
    assert "cleanup_error" in result.error
    assert_stopped(orch, result)


def test_cli_returns_failure_for_failed_run(isolated_runs, monkeypatch):
    from typer.testing import CliRunner
    from zeropath import cli

    room = ROOMS[0].model_copy(update={"max_steps": 1})
    monkeypatch.setattr(cli, "get_room", lambda room_id: room)
    result = CliRunner().invoke(cli.app, ["run", room.room_id, "--backend", "local", "--no-live"])
    assert result.exit_code == 1
    assert "FAILED" in result.output
