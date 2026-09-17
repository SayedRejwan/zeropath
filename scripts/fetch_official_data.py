from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from zeropath.paths import official_cache_dir

DEFAULT_OUTPUT = official_cache_dir()

FEEDS = {
    "attack_enterprise.json": "https://raw.githubusercontent.com/mitre-attack/attack-stix-data/master/enterprise-attack/enterprise-attack.json",
    "d3fend_ontology.json": "https://next.d3fend.mitre.org/ontologies/d3fend.json",
    "d3fend_full_mappings.json": "https://next.d3fend.mitre.org/api/ontology/inference/d3fend-full-mappings.json",
}
NVD_API = "https://services.nvd.nist.gov/rest/json/cves/2.0"


def _download_json(client: httpx.Client, url: str, destination: Path) -> dict:
    response = client.get(url)
    response.raise_for_status()
    payload = response.json()
    destination.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


def fetch_official_data(output_dir: Path, *, refresh: bool = False, include_nvd: bool = True) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    status: dict[str, str] = {}
    headers = {"User-Agent": "ZeroPath-Knowledge-Builder/0.2 (+authorized research)"}
    nvd_key = os.getenv("NVD_API_KEY", "").strip()
    if nvd_key:
        headers["apiKey"] = nvd_key

    with httpx.Client(timeout=120.0, follow_redirects=True, headers=headers) as client:
        for filename, url in FEEDS.items():
            destination = output_dir / filename
            if destination.exists() and not refresh:
                status[filename] = "cached"
                continue
            _download_json(client, url, destination)
            status[filename] = "refreshed"

        if include_nvd:
            destination = output_dir / "nvd_recent.json"
            if destination.exists() and not refresh:
                status[destination.name] = "cached"
            else:
                end = datetime.now(timezone.utc)
                start = end - timedelta(days=7)
                params = {
                    "resultsPerPage": 200,
                    "pubStartDate": start.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
                    "pubEndDate": end.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
                }
                response = client.get(NVD_API, params=params)
                response.raise_for_status()
                destination.write_text(json.dumps(response.json(), indent=2), encoding="utf-8")
                status[destination.name] = "refreshed"

    manifest = {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "feeds": FEEDS,
        "nvd_api": NVD_API if include_nvd else None,
        "files": status,
    }
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return status


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch official ATT&CK, D3FEND, and NVD data.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument("--skip-nvd", action="store_true", help="Skip the rate-limited NVD API feed.")
    args = parser.parse_args()
    for filename, state in fetch_official_data(
        args.output, refresh=args.refresh, include_nvd=not args.skip_nvd
    ).items():
        print(f"{state:9} {filename}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
