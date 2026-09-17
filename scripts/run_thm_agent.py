#!/usr/bin/env python3
"""
Autonomous TryHackMe Harvesting Agent
Crawls the web (blogs, Medium, community repos) and local RedTeam directories
to extract structured room knowledge, attack chains, and techniques for ZeroPath agents.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# Add project root to sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import httpx
from zeropath.db import KnowledgeBase
from zeropath.scrapers.thm_scraper import THMScraper, THMRoomProfile
from zeropath.scrapers.sync_kb import save_room_yaml, sync_room_to_kb, save_room_catalog, ensure_data_dir
from zeropath.scrapers.local_ingest import ingest_local_redteam_rooms
from zeropath.agents.solution_advisor import SolutionAdvisor

# Curated seed list of high-value, foundational TryHackMe rooms with public writeups on blogs and GitHub
DEFAULT_TARGET_ROOMS = [
    {
        "name": "Pickle Rick",
        "code": "picklerick",
        "difficulty": "Easy",
        "category": "Web",
        "url": "https://raw.githubusercontent.com/rohitdeshmukh27/TryHackMe-Pickle-Rick-Writeups/main/README.md",
    },
    {
        "name": "Basic Pentesting",
        "code": "basic_pentesting",
        "difficulty": "Easy",
        "category": "Web",
        "url": "https://blog.raw.pm/en/TryHackMe-Basic-Pentesting-write-up/",
    },
    {
        "name": "ColddBox: Easy",
        "code": "colddbox",
        "difficulty": "Easy",
        "category": "Web",
        "url": "https://blog.raw.pm/en/TryHackMe-ColddBox-Easy-write-up/",
    },
    {
        "name": "Blue",
        "code": "blue",
        "difficulty": "Easy",
        "category": "Windows",
        "url": "https://blog.raw.pm/en/TryHackMe-Blue-write-up/",
    },
    {
        "name": "Bounty Hacker",
        "code": "bountyhacker",
        "difficulty": "Easy",
        "category": "Linux",
        "url": "https://blog.raw.pm/en/TryHackMe-Bounty-Hacker-write-up/",
    },
    {
        "name": "Bolt",
        "code": "bolt",
        "difficulty": "Easy",
        "category": "Web",
        "url": "https://blog.raw.pm/en/TryHackMe-Bolt-write-up/",
    },
    {
        "name": "Daily Bugle",
        "code": "dailybugle",
        "difficulty": "Medium",
        "category": "Web",
        "url": "https://blog.raw.pm/en/TryHackMe-Daily-Bugle-write-up/",
    },
    {
        "name": "Ignite",
        "code": "ignite",
        "difficulty": "Easy",
        "category": "Web",
        "url": "https://blog.raw.pm/en/TryHackMe-Ignite-write-up/",
    },
    {
        "name": "Inclusion",
        "code": "inclusion",
        "difficulty": "Easy",
        "category": "Web",
        "url": "https://blog.raw.pm/en/TryHackMe-Inclusion-write-up/",
    },
    {
        "name": "Ice",
        "code": "ice",
        "difficulty": "Easy",
        "category": "Windows",
        "url": "https://blog.raw.pm/en/TryHackMe-Ice-write-up/",
    },
    {
        "name": "Agent Sudo",
        "code": "agentsudo",
        "difficulty": "Easy",
        "category": "Linux",
        "url": "https://blog.raw.pm/en/TryHackMe-Agent-Sudo-write-up/",
    },
    {
        "name": "Archangel",
        "code": "archangel",
        "difficulty": "Easy",
        "category": "Web",
        "url": "https://blog.raw.pm/en/TryHackMe-Archangel-write-up/",
    },
    {
        "name": "All in One",
        "code": "allinone",
        "difficulty": "Easy",
        "category": "Linux",
        "url": "https://blog.raw.pm/en/TryHackMe-All-in-One-write-up/",
    },
    {
        "name": "Baron Samedit",
        "code": "baronsamedit",
        "difficulty": "Easy",
        "category": "Linux",
        "url": "https://blog.raw.pm/en/TryHackMe-Baron-Samedit-write-up/",
    },
    {
        "name": "Biohazard",
        "code": "biohazard",
        "difficulty": "Medium",
        "category": "Web",
        "url": "https://blog.raw.pm/en/TryHackMe-Biohazard-write-up/",
    },
    {
        "name": "Chocolate Factory",
        "code": "chocolatefactory",
        "difficulty": "Easy",
        "category": "Linux",
        "url": "https://blog.raw.pm/en/TryHackMe-Chocolate-Factory-write-up/",
    },
]


def discover_web_writeups(max_items: int = 50) -> list[dict]:
    """Fetch live community writeups index from GitHub/blogs."""
    discovered: list[dict] = []
    try:
        resp = httpx.get("https://raw.githubusercontent.com/noraj/tryhackme-writeups/master/README.md", timeout=12)
        if resp.status_code == 200:
            links = re.findall(r"\[([^\]]+)\]:\s*(https?://[^\s]+)", resp.text)
            for tag, url in links:
                if "tryhackme.com/p/" in url:
                    continue
                name = tag.replace("noraj-", "").replace("-", " ").title()
                code = tag.replace("noraj-", "").replace("-", "_").lower()
                discovered.append({"name": name, "code": code, "url": url})
                if len(discovered) >= max_items:
                    break
    except Exception as exc:
        print(f"[!] Note: web discovery index notice: {exc}")
    return discovered


from zeropath.scrapers.repo_harvester import harvest_all_repository_targets


def run_agent(
    targets: list[dict] | None = None,
    single_url: str | None = None,
    limit: int = 60,
    include_local: bool = True,
    local_dir: str = r"F:\04_Cybersecurity_RedTeam\Try hack me Rooms",
) -> list[THMRoomProfile]:
    scraper = THMScraper()
    kb = KnowledgeBase()
    kb.init()

    collected_profiles: list[THMRoomProfile] = []

    # 1. Ingest user local RedTeam directory if present
    if include_local and Path(local_dir).exists():
        print(f"[*] Ingesting user's local RedTeam directory: {local_dir}")
        local_profs = ingest_local_redteam_rooms(base_dir=local_dir, kb=kb)
        collected_profiles.extend(local_profs)
        print(f"[OK] Ingested {len(local_profs)} local rooms.")

    # 2. Build target list from curated seeds + repository harvester
    if single_url:
        items_to_process = [{"name": "Custom Target", "code": "", "url": single_url}]
    else:
        seeds = list(DEFAULT_TARGET_ROOMS)
        web_targets = harvest_all_repository_targets(max_per_source=25)
        seen_urls = {s["url"] for s in seeds}
        for wt in web_targets:
            if wt["url"] not in seen_urls:
                seeds.append(wt)
                seen_urls.add(wt["url"])
        items_to_process = seeds[:limit]

    print(f"\n[*] Starting Bulk Harvesting Agent: processing {len(items_to_process)} target writeups across the web...")

    for item in items_to_process:
        url = item.get("url", "")
        hint_name = item.get("name", "")
        hint_code = item.get("code", "")
        hint_diff = item.get("difficulty", "")
        hint_cat = item.get("category", "")

        print(f"\n[+] Fetching & analyzing writeup: {hint_name or url}")
        print(f"    Source URL: {url}")

        try:
            profile = scraper.scrape_and_parse(url, room_hint=hint_name)

            if hint_code and (not profile.code or profile.code.startswith("thm_room_")):
                profile.code = hint_code
            elif hint_code:
                profile.code = hint_code

            if hint_diff:
                profile.difficulty = hint_diff
            if hint_cat:
                profile.category = hint_cat

            # Save to YAML
            yaml_path = save_room_yaml(profile)
            print(f"    -> Saved YAML: {yaml_path}")

            # Ingest into SQLite + NetworkX Graph
            sync_room_to_kb(profile, kb)
            print(f"    -> Synced into KnowledgeBase (room: {profile.code}, {len(profile.attack_chain)} attack steps)")

            collected_profiles.append(profile)
        except Exception as exc:
            print(f"    [!] Warning: failed to parse {url}: {exc}")

    # Update master catalog
    catalog_path = save_room_catalog(collected_profiles)
    print(f"\n[OK] Completed harvest! Master catalog updated at: {catalog_path}")
    print(f"[OK] ZeroPath Knowledge Base populated with {len(collected_profiles)} TryHackMe rooms.")

    # Reload advisor
    advisor = SolutionAdvisor(kb=kb)
    advisor.reload()
    print("[OK] SolutionAdvisor reloaded with new intelligence.")

    return collected_profiles


def main() -> None:
    parser = argparse.ArgumentParser(description="ZeroPath TryHackMe Ingestion Agent")
    parser.add_argument("--url", help="Direct URL of a writeup/article to scrape and parse.")
    parser.add_argument("--limit", type=int, default=20, help="Max rooms to process.")
    parser.add_argument("--no-local", action="store_true", help="Skip local RedTeam folder ingestion.")
    args = parser.parse_args()

    run_agent(single_url=args.url, limit=args.limit, include_local=not args.no_local)


if __name__ == "__main__":
    main()
