from __future__ import annotations

import hashlib
import re
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional

from zeropath.agents.heuristic_agent import HeuristicAgent
from zeropath.agents.llm_agent import LLMAgent
from zeropath.config import RoomConfig
from zeropath.envs.factory import create_lab_env
from zeropath.logbook import Logbook
from zeropath.tools.http_tools import HttpTools
from zeropath.util import runs_dir, write_json


@dataclass
class RunResult:
    ok: bool
    run_id: str
    room_id: str
    flag: Optional[str]
    steps: int
    base_url: str
    start_url: str
    error: Optional[str] = None
    duration_s: float = 0.0
    agent: str = "heuristic"
    backend: str = "auto"


class Orchestrator:
    def __init__(self, run_id: str, room: RoomConfig, lab_dir: Path, backend: str = "auto") -> None:
        self.run_id = run_id
        self.room = room
        self.env = create_lab_env(run_id=run_id, lab_dir=lab_dir, backend=backend)
        self.log = Logbook(run_id=run_id, base_dir=runs_dir())

    def run(self, agent_name: str = "heuristic", on_update=None, keep_env: bool = False) -> RunResult:
        started = time.monotonic()
        http = llm = None
        base_url = start_url = ""
        steps = 0
        flag = None
        error = None
        evidence = []
        try:
            if agent_name not in {"heuristic", "llm"}:
                raise ValueError("Unsupported agent. Use 'heuristic' or 'llm'.")
            success = re.compile(self.room.success_regex)
            if success.search(""):
                raise ValueError("Success regex must not match empty text")
            if agent_name == "llm":
                from zeropath.agents.solution_advisor import SolutionAdvisor
                llm = LLMAgent.from_env(advisor=SolutionAdvisor())
            inst = self.env.start()
            base_url = inst.base_url
            start_url = base_url + self.room.start_path
            prefix = "/" + self.room.start_path.strip("/").split("/", 1)[0]
            http = HttpTools(base_url=base_url, scope_prefix=prefix)
            self.log.event("env_started", {"base_url": base_url, "start_path": self.room.start_path,
                                         "backend": type(self.env).__name__})
            agent = HeuristicAgent(http=http)
            ctx = agent.init_context(self.room.start_path)
            last_obs = ""
            phase = "RECON"
            while steps < self.room.max_steps:
                steps += 1
                tool, path, body = "http_get", "", None
                try:
                    # Login is an explicit, budgeted and audited action.
                    if (ctx.room_prefix == "/room04" and "login_attempted" not in ctx.notes
                            and ctx.notes.get("user") and ctx.notes.get("pass")):
                        ctx.notes["login_attempted"] = "1"
                        tool, path = "http_post_json", "/room04/login"
                        body = {"user": ctx.notes["user"], "password": ctx.notes["pass"]}
                    elif llm is None:
                        path = agent.next_path(ctx) or ""
                        if not path:
                            steps -= 1
                            error = "queue_exhausted"
                            break
                    else:
                        call = llm.decide(phase=phase,
                            goal=f"{self.room.title}: {self.room.description}", base_url=base_url,
                            visited=sorted(ctx.visited), queue=list(ctx.queue), last_observation=last_obs)
                        tool, path = call.tool, str(call.args.get("path", ""))
                        body = call.args.get("body", {})
                        if tool not in {"http_get", "http_post_json"}:
                            raise ValueError("Unsupported tool")
                        ctx.visited.add(path)
                        ctx.queue = [p for p in ctx.queue if p != path]
                    self.log.event("step", {"n": steps, "phase": phase, "tool": tool, "path": path})
                    if tool == "http_post_json":
                        if not isinstance(body, dict):
                            raise ValueError("http_post_json body must be an object")
                        response = http.post_json(path, body)
                    else:
                        response = http.get(path)
                except Exception as exc:
                    # Decision errors also consume the bounded attempt budget.
                    error = f"step_error: {type(exc).__name__}: {exc}"
                    self.log.event("step_result", {"n": steps, "ok": False, "error": error})
                    if on_update:
                        on_update({"step": steps, "phase": phase, "tool": tool, "path": path, "error": error})
                    continue
                text = response.text or ""
                item = {"n": steps, "tool": tool, "path": path, "url": str(response.url),
                        "status": response.status_code, "len": len(response.content),
                        "sha256": hashlib.sha256(response.content).hexdigest()}
                evidence.append(item)
                self.log.event("http_response", item)
                last_obs = f"{tool.upper()} {path} -> {response.status_code}\n{text[:800]}"
                if on_update:
                    on_update({"step": steps, "phase": phase, "tool": tool, "path": path,
                               "status": response.status_code})
                match = success.search(text) if 200 <= response.status_code < 300 else None
                if match:
                    flag = match.group(0)
                    error = None
                    self.log.event("flag_found", {"n": steps, "path": path, "flag": flag})
                    if on_update:
                        on_update({"step": steps, "phase": phase, "flag": flag})
                    break
                agent.observe_and_expand(ctx, path=path, status_code=response.status_code, body_text=text)
                if tool == "http_post_json" and path == "/room04/login" and response.status_code == 200:
                    ctx.visited.discard("/room04/flag")
                    ctx.queue.insert(0, "/room04/flag")
                phase = "ACCESS" if response.status_code in (401, 403) or "/login" in path else "ENUM"
            if not flag and steps >= self.room.max_steps:
                error = "max_steps_exceeded" + (f"; {error}" if error else "")
        except Exception as exc:
            error = f"run_error: {type(exc).__name__}: {exc}"
            self.log.event("run_error", {"error": error})
        finally:
            cleanup = []
            if http is not None:
                cleanup.append(http.close)
            if llm is not None:
                cleanup.append(llm.close)
            if not keep_env:
                cleanup.append(self.kill)
            for close in cleanup:
                try:
                    close()
                except Exception as exc:
                    error = f"cleanup_error: {type(exc).__name__}: {exc}"
                    self.log.event("cleanup_error", {"error": error})
        result = RunResult(ok=flag is not None and error is None,
            run_id=self.run_id, room_id=self.room.room_id, flag=flag, steps=steps,
            base_url=base_url, start_url=start_url, error=error,
            duration_s=round(time.monotonic() - started, 4), agent=agent_name, backend=type(self.env).__name__)
        write_json(self.log.paths.summary_json, asdict(result))
        from zeropath.reporting import write_run_report
        write_run_report(self.log.paths.run_dir, result, self.room, evidence)
        return result

    def kill(self) -> None:
        self.env.stop()
        self.log.event("env_stopped", {"run_id": self.run_id})
