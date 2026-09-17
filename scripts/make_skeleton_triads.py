from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from zeropath.schemas.triad import Triad
from zeropath.paths import official_cache_dir, triads_dir


DEFAULT_ATTACK = official_cache_dir() / "attack_enterprise.json"
DEFAULT_OUTPUT = triads_dir()


def _attack_id(obj: dict) -> str | None:
    for ref in obj.get("external_references", []):
        external_id = str(ref.get("external_id", ""))
        if re.fullmatch(r"T\d{4}(?:\.\d{3})?", external_id):
            return external_id
    return None


def make_skeletons(attack_path: Path, output_dir: Path, *, limit: int = 50) -> list[Path]:
    bundle = json.loads(attack_path.read_text(encoding="utf-8"))
    techniques = []
    for obj in bundle.get("objects", []):
        if obj.get("type") != "attack-pattern" or obj.get("revoked") or obj.get("x_mitre_deprecated"):
            continue
        technique_id = _attack_id(obj)
        if not technique_id:
            continue
        phases = [phase.get("phase_name", "") for phase in obj.get("kill_chain_phases", [])]
        techniques.append((technique_id, obj, phases))

    output_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for technique_id, obj, phases in sorted(techniques)[:limit]:
        path = output_dir / f"{technique_id.lower().replace('.', '_')}.yaml"
        if path.exists():
            continue
        triad = Triad(
            technique_id=technique_id,
            name=obj.get("name", technique_id),
            description=(obj.get("description") or "Official ATT&CK technique awaiting enrichment.")[:4000],
            kill_chain=phases or ["unknown"],
            platforms=obj.get("x_mitre_platforms") or ["Unknown"],
            difficulty="medium",
            status="draft",
            sources=[
                {
                    "title": f"MITRE ATT&CK: {obj.get('name', technique_id)}",
                    "url": next(
                        (
                            ref.get("url")
                            for ref in obj.get("external_references", [])
                            if ref.get("url") and ref.get("external_id") == technique_id
                        ),
                        f"https://attack.mitre.org/techniques/{technique_id.replace('.', '/')}/",
                    ),
                    "source_type": "official",
                    "accessed": "generated-from-official-cache",
                }
            ],
        )
        path.write_text(
            yaml.safe_dump(triad.model_dump(mode="json"), sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )
        written.append(path)
    return written


def main() -> int:
    parser = argparse.ArgumentParser(description="Create draft triad YAMLs from ATT&CK STIX data.")
    parser.add_argument("--attack", type=Path, default=DEFAULT_ATTACK)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--limit", type=int, default=50)
    args = parser.parse_args()
    written = make_skeletons(args.attack, args.output, limit=args.limit)
    print(f"created {len(written)} draft triad(s) in {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

