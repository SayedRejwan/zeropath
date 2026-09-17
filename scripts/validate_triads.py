from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from zeropath.schemas.triad import Triad, load_triad


DEFAULT_DIR = ROOT / "data" / "triads" / "techniques"
TEMPLATE_MARKERS = re.compile(
    r"\b(todo|tbd|lorem ipsum|fill me|replace me|example only|generated placeholder)\b|<[^>]+>",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class ValidationIssue:
    path: Path
    message: str


def quality_issues(triad: Triad, path: Path, *, require_reviewed: bool = False) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    if triad.status != "reviewed":
        if require_reviewed:
            issues.append(ValidationIssue(path, "status must be reviewed before knowledge-base sync"))
        return issues

    non_ai_sources = [source for source in triad.sources if source.source_type != "ai"]
    if len(non_ai_sources) < 2:
        issues.append(ValidationIssue(path, "reviewed triad requires at least 2 non-AI sources"))

    seen_orders: set[int] = set()
    for step in triad.pentest_steps:
        if step.order in seen_orders:
            issues.append(ValidationIssue(path, f"duplicate pentest step order: {step.order}"))
        seen_orders.add(step.order)
        for label, value in {
            "command": step.command,
            "prerequisite": step.prerequisite,
            "expected_result": step.expected_result,
            "safety": step.safety,
        }.items():
            if TEMPLATE_MARKERS.search(value):
                issues.append(ValidationIssue(path, f"template marker in pentest_steps[{step.order}].{label}"))

    serialized_sections = [
        *(item.model_dump_json() for item in triad.evidence),
        *(item.model_dump_json() for item in triad.detections),
        *(item.model_dump_json() for item in triad.remedies),
    ]
    if any(TEMPLATE_MARKERS.search(value) for value in serialized_sections):
        issues.append(ValidationIssue(path, "template marker in evidence, detection, or remedy"))
    return issues


def validate_directory(base_dir: Path, *, require_reviewed: bool = False) -> tuple[list[Triad], list[ValidationIssue]]:
    triads: list[Triad] = []
    issues: list[ValidationIssue] = []
    seen_ids: dict[str, Path] = {}

    paths = sorted(base_dir.glob("*.yaml")) if base_dir.exists() else []
    if not paths:
        return [], [ValidationIssue(base_dir, "no triad YAML files found")]

    for path in paths:
        try:
            triad = load_triad(path)
        except Exception as exc:
            issues.append(ValidationIssue(path, f"schema validation failed: {exc}"))
            continue

        previous = seen_ids.get(triad.technique_id)
        if previous:
            issues.append(
                ValidationIssue(path, f"duplicate technique_id {triad.technique_id}; first seen in {previous.name}")
            )
            continue
        seen_ids[triad.technique_id] = path
        triads.append(triad)
        issues.extend(quality_issues(triad, path, require_reviewed=require_reviewed))

    return triads, issues


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate ZeroPath triad YAML files.")
    parser.add_argument("path", nargs="?", type=Path, default=DEFAULT_DIR)
    parser.add_argument("--require-reviewed", action="store_true", help="Fail if any record is still a draft.")
    args = parser.parse_args()

    triads, issues = validate_directory(args.path, require_reviewed=args.require_reviewed)
    if issues:
        for issue in issues:
            print(f"ERROR {issue.path}: {issue.message}")
        print(f"FAILED: {len(issues)} issue(s), {len(triads)} parseable triad(s)")
        return 1

    reviewed = sum(1 for triad in triads if triad.status == "reviewed")
    drafts = len(triads) - reviewed
    print(f"PASS: {len(triads)} triad(s) ({reviewed} reviewed, {drafts} draft), 0 quality issues")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
