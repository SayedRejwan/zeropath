from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Optional
import yaml

from zeropath.db import KnowledgeBase
from zeropath.schemas.triad import Triad, load_triad


class SolutionAdvisor:
    """
    Knowledge retrieval & solution advisor that queries harvested TryHackMe rooms,
    attack paths, and techniques to recommend actionable solutions to ZeroPath agents.
    """

    def __init__(
        self,
        data_dir: Optional[Path] = None,
        kb: Optional[KnowledgeBase] = None,
        triad_dir: Optional[Path] = None,
    ) -> None:
        self.data_dir = data_dir or (Path("data") / "thm_rooms")
        self.triad_dir = triad_dir or (Path("data") / "triads" / "techniques")
        self.kb = kb or KnowledgeBase()
        try:
            self.kb.init()
        except Exception:
            pass
        self._cache: list[dict[str, Any]] = []
        self._triads: list[Triad] = []
        self._load_cached_rooms()
        self._load_triads()

    def _load_cached_rooms(self) -> None:
        self._cache = []
        if not self.data_dir.exists():
            return
        for f in self.data_dir.glob("*.yaml"):
            try:
                with open(f, "r", encoding="utf-8") as fp:
                    data = yaml.safe_load(fp)
                    if isinstance(data, dict):
                        self._cache.append(data)
            except Exception:
                continue

    def reload(self) -> None:
        self._load_cached_rooms()
        self._load_triads()

    def _load_triads(self) -> None:
        self._triads = []
        if not self.triad_dir.exists():
            return
        for path in sorted(self.triad_dir.glob("*.yaml")):
            try:
                triad = load_triad(path)
            except Exception:
                continue
            non_ai_sources = [source for source in triad.sources if source.source_type != "ai"]
            if triad.status == "reviewed" and len(non_ai_sources) >= 2:
                self._triads.append(triad)

    def find_relevant_triads(
        self,
        *,
        goal: str = "",
        path: str = "",
        observation: str = "",
        top_k: int = 3,
    ) -> list[Triad]:
        combined = f"{goal} {path} {observation}".lower()
        requested_ids = {
            value.upper() for value in re.findall(r"\bT\d{4}(?:\.\d{3})?\b", combined, re.IGNORECASE)
        }
        if requested_ids:
            return [triad for triad in self._triads if triad.technique_id in requested_ids][:top_k]
        words = set(re.findall(r"[a-z0-9_.-]{4,}", combined))
        scored: list[tuple[float, Triad]] = []
        for triad in self._triads:
            haystack = " ".join(
                [
                    triad.technique_id,
                    triad.name,
                    triad.description,
                    *triad.kill_chain,
                    *triad.platforms,
                    *(step.tool for step in triad.pentest_steps),
                ]
            ).lower()
            score = 8.0 if triad.technique_id.lower() in combined else 0.0
            score += sum(1.0 for word in words if word in haystack)
            if score:
                scored.append((score, triad))
        scored.sort(key=lambda item: (-item[0], item[1].technique_id))
        return [triad for _, triad in scored[:top_k]]

    @staticmethod
    def _format_triad_advice(triad: Triad) -> list[str]:
        first_step = triad.pentest_steps[0]
        first_evidence = triad.evidence[0]
        first_detection = triad.detections[0]
        first_remedy = triad.remedies[0]
        return [
            f"VALIDATED TRIAD {triad.technique_id}: {triad.name}",
            f"- Authorized-lab action ({first_step.tool}): {first_step.command}",
            f"- Expected result: {first_step.expected_result}",
            f"- Evidence: {first_evidence.location} -> {first_evidence.sample}",
            f"- Detection ({first_detection.data_source}): {first_detection.strategy}",
            f"- Remedy [{first_remedy.priority}]: {first_remedy.action}",
            f"- Verify remedy: {first_remedy.verification}",
        ]

    def find_relevant_solutions(
        self,
        *,
        goal: str = "",
        path: str = "",
        observation: str = "",
        top_k: int = 3,
    ) -> list[dict[str, Any]]:
        """
        Match current agent context against harvested rooms and techniques.
        """
        combined_text = f"{goal} {path} {observation}".lower()
        scored: list[tuple[float, dict[str, Any]]] = []

        for room in self._cache:
            score = 0.0
            category = str(room.get("category", "")).lower()
            title = str(room.get("title", "")).lower()
            code = str(room.get("code", "")).lower()
            tools = [t.lower() for t in room.get("tools", [])]
            tags = [t.lower() for t in room.get("tags", [])]

            # Matching patterns
            if "robots" in combined_text and ("robots" in code or "robots" in tags):
                score += 5.0
            if "dirbust" in combined_text or "admin" in combined_text:
                if any(t in ["ffuf", "gobuster", "dirsearch"] for t in tools):
                    score += 4.0
            if "auth" in combined_text or "401" in combined_text or "login" in combined_text:
                if "hydra" in tools or "basic" in code or "auth" in tags:
                    score += 4.0
            if "cookie" in combined_text or "session" in combined_text:
                if "web" in category or "cookie" in tags:
                    score += 3.0
            if "header" in combined_text:
                if "web" in category:
                    score += 2.0
            if "query" in combined_text or "puzzle" in combined_text or "parameter" in combined_text:
                score += 2.0

            # General keyword match
            for word in set(re.findall(r"\w{4,}", combined_text)):
                if word in title or word in code:
                    score += 1.5
                if word in tags:
                    score += 1.0

            if score > 0:
                scored.append((score, room))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [item[1] for item in scored[:top_k]]

    def get_tactical_advice(
        self,
        *,
        room_title: str = "",
        start_path: str = "",
        last_obs: str = "",
        status_code: int = 200,
    ) -> str:
        """
        Generate tactical prompt guidance for the agent using learned THM writeups.
        """
        relevant = self.find_relevant_solutions(
            goal=room_title, path=start_path, observation=last_obs, top_k=2
        )
        triads = self.find_relevant_triads(
            goal=room_title, path=start_path, observation=last_obs, top_k=2
        )

        advice_lines: list[str] = []

        for triad in triads:
            advice_lines.extend(self._format_triad_advice(triad))

        # 1. Specialized tactic rules derived from harvested writeup patterns
        obs_lower = last_obs.lower()
        if "disallow:" in obs_lower or start_path.endswith("robots.txt"):
            advice_lines.append(
                "LEARNED FROM WRITEUPS: Robots.txt reveals hidden, restricted directories. Immediately request the Disallowed path + '/flag'."
            )
        elif "sitemap" in start_path or "<loc>" in obs_lower:
            advice_lines.append(
                "LEARNED FROM WRITEUPS: Sitemap manifests expose unlinked endpoints (e.g., /debug or /api). Query exposed debug paths to uncover credentials."
            )
        elif status_code == 401 or "basic auth" in room_title.lower() or "service_user" in obs_lower:
            advice_lines.append(
                "LEARNED FROM WRITEUPS: Basic Auth gate detected. Use harvested credentials or extracted service_user/service_pass to authenticate against /flag."
            )
        elif "cookie" in room_title.lower() or "login" in start_path or "session" in obs_lower:
            advice_lines.append(
                "LEARNED FROM WRITEUPS: Cookie gate detected. Submit credentials to /login to establish session cookie, then fetch /flag."
            )
        elif "x-zp-key" in obs_lower or "header" in room_title.lower() or "header key" in obs_lower:
            advice_lines.append(
                "LEARNED FROM WRITEUPS: Custom header required. Parse comment or hint for key name/token and supply it in HTTP headers."
            )
        elif "answer is" in obs_lower or "query" in room_title.lower() or "puzzle" in obs_lower:
            advice_lines.append(
                "LEARNED FROM WRITEUPS: Query parameter puzzle. Compute the arithmetic or format puzzle answer and append '?answer=<val>' to /flag."
            )
        else:
            advice_lines.append(
                "LEARNED FROM WRITEUPS: Enumerate standard paths (/admin, /hidden, /robots.txt, /login, /flag) using dirbust techniques."
            )

        # 2. Add references from similar harvested rooms
        if relevant:
            advice_lines.append("SIMILAR HARVESTED THM ROOMS:")
            for r in relevant:
                chain = " -> ".join(s.get("technique", "") for s in r.get("attack_chain", []))
                tools = ", ".join(r.get("tools", []))
                advice_lines.append(f"- [{r.get('code')}] ({r.get('category')}): {chain} (Tools: {tools})")

        return "\n".join(advice_lines)
