from __future__ import annotations

import re
from typing import Any
import httpx


COMMUNITY_INDEX_SOURCES = [
    # Cajac collections (275+ rooms)
    {
        "index_url": "https://raw.githubusercontent.com/Cajac/TryHackMe-Writeups/master/Walkthroughs/Easy/README.md",
        "base_url": "https://raw.githubusercontent.com/Cajac/TryHackMe-Writeups/master/Walkthroughs/Easy/",
        "default_diff": "Easy",
        "default_cat": "Walkthrough",
    },
    {
        "index_url": "https://raw.githubusercontent.com/Cajac/TryHackMe-Writeups/master/Walkthroughs/Medium/README.md",
        "base_url": "https://raw.githubusercontent.com/Cajac/TryHackMe-Writeups/master/Walkthroughs/Medium/",
        "default_diff": "Medium",
        "default_cat": "Walkthrough",
    },
    {
        "index_url": "https://raw.githubusercontent.com/Cajac/TryHackMe-Writeups/master/Challenges/Easy/README.md",
        "base_url": "https://raw.githubusercontent.com/Cajac/TryHackMe-Writeups/master/Challenges/Easy/",
        "default_diff": "Easy",
        "default_cat": "Challenge",
    },
    {
        "index_url": "https://raw.githubusercontent.com/Cajac/TryHackMe-Writeups/master/Challenges/Medium/README.md",
        "base_url": "https://raw.githubusercontent.com/Cajac/TryHackMe-Writeups/master/Challenges/Medium/",
        "default_diff": "Medium",
        "default_cat": "Challenge",
    },
    # Esther7171 Walkthroughs (105 rooms)
    {
        "index_url": "https://raw.githubusercontent.com/Esther7171/TryHackMe-Walkthroughs/main/README.md",
        "base_url": "https://raw.githubusercontent.com/Esther7171/TryHackMe-Walkthroughs/main/Room/",
        "is_esther": True,
        "default_diff": "Easy",
        "default_cat": "Walkthrough",
    },
    # Noraj multi-blog index (73 rooms)
    {
        "index_url": "https://raw.githubusercontent.com/noraj/tryhackme-writeups/master/README.md",
        "is_noraj": True,
        "default_diff": "Easy",
        "default_cat": "Walkthrough",
    },
]


def harvest_all_repository_targets(max_per_source: int = 40) -> list[dict[str, Any]]:
    """
    Crawls open-source TryHackMe writeup indices to harvest hundreds of verified room writeup URLs.
    """
    all_targets: list[dict[str, Any]] = []
    seen_codes: set[str] = set()

    for src in COMMUNITY_INDEX_SOURCES:
        index_url = src["index_url"]
        try:
            with httpx.Client(timeout=12.0) as client:
                resp = client.get(index_url)
                if resp.status_code != 200:
                    continue
                text = resp.text

                # Esther format: [Blue](./Room/Blue/readme.md)
                if src.get("is_esther"):
                    matches = re.findall(r"\[([^\]]+)\]\(\./Room/([^\)]+)\)", text)
                    count = 0
                    for title, path_suffix in matches:
                        clean_code = re.sub(r"[^a-zA-Z0-9_]", "_", title.lower().replace(" ", "_")).strip("_")
                        if clean_code in seen_codes:
                            continue
                        seen_codes.add(clean_code)
                        file_url = f"https://raw.githubusercontent.com/Esther7171/TryHackMe-Walkthroughs/main/Room/{path_suffix}"
                        all_targets.append({
                            "name": title,
                            "code": clean_code,
                            "url": file_url,
                            "difficulty": src.get("default_diff", "Easy"),
                            "category": src.get("default_cat", "Walkthrough"),
                        })
                        count += 1
                        if count >= max_per_source:
                            break

                # Noraj format: [noraj-tag]: url
                elif src.get("is_noraj"):
                    matches = re.findall(r"\[([^\]]+)\]:\s*(https?://[^\s]+)", text)
                    count = 0
                    for tag, url in matches:
                        if "tryhackme.com/p/" in url:
                            continue
                        title = tag.replace("noraj-", "").replace("-", " ").title()
                        clean_code = tag.replace("noraj-", "").replace("-", "_").lower()
                        if clean_code in seen_codes:
                            continue
                        seen_codes.add(clean_code)
                        all_targets.append({
                            "name": title,
                            "code": clean_code,
                            "url": url,
                            "difficulty": src.get("default_diff", "Easy"),
                            "category": src.get("default_cat", "Walkthrough"),
                        })
                        count += 1
                        if count >= max_per_source:
                            break

                # Cajac format: [Title](filename.md)
                else:
                    base_url = src["base_url"]
                    matches = re.findall(r"\[([^\]]+)\]\(([^\)]+\.md)\)", text)
                    count = 0
                    for title, filename in matches:
                        if "README.md" in filename:
                            continue
                        clean_code = re.sub(r"[^a-zA-Z0-9_]", "_", title.lower().replace(" ", "_")).strip("_")
                        if clean_code in seen_codes:
                            continue
                        seen_codes.add(clean_code)
                        file_url = f"{base_url.rstrip('/')}/{filename.lstrip('/')}"
                        all_targets.append({
                            "name": title,
                            "code": clean_code,
                            "url": file_url,
                            "difficulty": src.get("default_diff", "Easy"),
                            "category": src.get("default_cat", "Challenge"),
                        })
                        count += 1
                        if count >= max_per_source:
                            break
        except Exception as exc:
            print(f"[!] Warning: could not process index {index_url}: {exc}")

    return all_targets
