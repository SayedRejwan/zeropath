from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Optional

import httpx

from zeropath.types import ToolCall


@dataclass
class LLMConfig:
    api_key: str
    model: str
    base_url: str = "https://api.openai.com/v1"


class LLMAgent:
    """
    LLM-driven decision layer for the local lab, augmented with
    harvested TryHackMe intelligence & solution advice.
    """

    def __init__(self, config: LLMConfig, advisor: Optional[Any] = None) -> None:
        self.config = config
        self.advisor = advisor
        self.client = httpx.Client(
            base_url=self.config.base_url.rstrip("/"),
            headers={"Authorization": f"Bearer {self.config.api_key}"},
            timeout=20.0,
        )

    @staticmethod
    def from_env(advisor: Optional[Any] = None) -> "LLMAgent":
        key = os.getenv("OPENAI_API_KEY", "").strip()
        if not key:
            raise RuntimeError("OPENAI_API_KEY is not set.")
        model = os.getenv("ZEROPATH_OPENAI_MODEL", "gpt-4o-mini").strip()
        base_url = os.getenv("ZEROPATH_OPENAI_BASE_URL", "https://api.openai.com/v1").strip()
        return LLMAgent(LLMConfig(api_key=key, model=model, base_url=base_url), advisor=advisor)

    def close(self) -> None:
        self.client.close()

    def decide(
        self,
        *,
        phase: str,
        goal: str,
        base_url: str,
        visited: list[str],
        queue: list[str],
        last_observation: str,
    ) -> ToolCall:
        tactical_advice = ""
        if self.advisor:
            try:
                curr_path = queue[0] if queue else (visited[-1] if visited else "")
                tactical_advice = self.advisor.get_tactical_advice(
                    room_title=goal,
                    start_path=curr_path,
                    last_obs=last_observation,
                )
            except Exception:
                pass

        sys = (
            "You are a security validation agent operating ONLY against a local training lab on localhost.\n"
            "You must choose exactly one action as strict JSON.\n"
            "Allowed tools:\n"
            '  - {"tool":"http_get","args":{"path":"/path"}}\n'
            '  - {"tool":"http_post_json","args":{"path":"/path","body":{...}}}\n'
            "Rules:\n"
            "- Only use paths that start with '/'.\n"
            "- Prefer exploring queued paths first.\n"
            "- Try to obtain the flag string matching FLAG{...}.\n"
        )
        if tactical_advice:
            sys += f"\nTactical Intelligence from harvested writeups:\n{tactical_advice}\n"

        user = {
            "phase": phase,
            "goal": goal,
            "base_url": base_url,
            "visited_count": len(visited),
            "next_queue": queue[:8],
            "last_observation": last_observation[:1200],
        }
        if tactical_advice:
            user["intelligence_recommendations"] = tactical_advice

        resp = self.client.post(
            "/chat/completions",
            json={
                "model": self.config.model,
                "messages": [
                    {"role": "system", "content": sys},
                    {"role": "user", "content": json.dumps(user)},
                ],
                "temperature": 0.2,
            },
        )
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]

        try:
            obj = json.loads(content)
        except json.JSONDecodeError:
            # Try to extract the first JSON object if the model wrapped it.
            start = content.find("{")
            end = content.rfind("}")
            if start == -1 or end == -1 or end <= start:
                raise RuntimeError(f"LLM did not return JSON: {content[:400]}")
            obj = json.loads(content[start : end + 1])

        tool = str(obj.get("tool", "")).strip()
        args = obj.get("args") or {}
        if tool not in {"http_get", "http_post_json"}:
            raise RuntimeError(f"LLM chose unsupported tool: {tool}")
        if not isinstance(args, dict):
            raise RuntimeError("LLM args must be an object.")
        path = args.get("path")
        if not isinstance(path, str) or not path.startswith("/"):
            raise RuntimeError("LLM must provide args.path starting with '/'.")
        return ToolCall(tool=tool, args=args)

