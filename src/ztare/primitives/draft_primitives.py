import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List

from src.ztare.common import utils
from src.ztare.common.paths import GLOBAL_PRIMITIVES_DIR, PROMPTS_DIR, REPO_ROOT
from src.ztare.workspace.compile_evidence import LLMClient, write_json, write_text


ROOT_DIR = REPO_ROOT
REVIEW_DIR = GLOBAL_PRIMITIVES_DIR / "review"
INCIDENTS_JSONL = GLOBAL_PRIMITIVES_DIR / "incidents" / "primitive_incidents.jsonl"
INDEX_JSON = REVIEW_DIR / "index.json"


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def load_prompt(name: str) -> str:
    return read_text(PROMPTS_DIR / name).strip()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Draft candidate primitive cards from extracted incident records.")
    parser.add_argument("--model", default="gemini", choices=["gemini", "gemini-pro", "claude", "claude-opus", "gpt4o", "gpt4.1", "gpt4.1-mini"])
    parser.add_argument("--incidents", help="Path to primitive_incidents.jsonl. Defaults to global_primitives/incidents/primitive_incidents.jsonl.")
    parser.add_argument("--min-incidents", type=int, default=2, help="Minimum incidents required to draft a candidate.")
    parser.add_argument("--primitive-key", action="append", help="Restrict drafting to one or more primitive keys.")
    parser.add_argument("--skip-existing", action="store_true", help="Skip primitive keys that already have review JSON files.")
    return parser.parse_args()


def load_incidents(path: Path) -> List[Dict[str, Any]]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


def candidate_shape_ok(candidate: Dict[str, Any]) -> None:
    required = [
        "primitive_id",
        "title",
        "primitive_key",
        "primitive_type",
        "status",
        "summary",
        "mechanism",
        "epistemic_role",
        "scope_conditions",
        "non_transfer_cases",
        "required_transfer_test",
        "mutator_guidance",
        "firing_squad_attack",
        "judge_penalty_condition",
        "source_projects",
        "source_incident_ids",
        "evidence_summary",
        "tags",
        "confidence",
        "promotion_note",
    ]
    missing = [key for key in required if key not in candidate]
    if missing:
        raise ValueError(f"Primitive candidate missing required keys: {', '.join(missing)}")


def build_prompt(primitive_key: str, incidents: List[Dict[str, Any]]) -> str:
    incident_payload = {
        "primitive_key": primitive_key,
        "incident_count": len(incidents),
        "projects": sorted({incident["project"] for incident in incidents}),
        "classifications": sorted({incident["classification"] for incident in incidents}),
        "incidents": incidents,
    }
    return "\n\n".join(
        [
            load_prompt("draft_primitive.md"),
            f"Primitive key: {primitive_key}",
            "Incident bundle:",
            json.dumps(incident_payload, indent=2, sort_keys=True),
        ]
    )


def render_candidate_markdown(candidate: Dict[str, Any]) -> str:
    lines = [
        f"# {candidate.get('title', '').strip()}",
        "",
        f"- Primitive ID: `{candidate.get('primitive_id', '').strip()}`",
        f"- Primitive Key: `{candidate.get('primitive_key', '').strip()}`",
        f"- Type: `{candidate.get('primitive_type', '').strip()}`",
        f"- Status: `{candidate.get('status', '').strip()}`",
        f"- Epistemic Role: `{candidate.get('epistemic_role', '').strip()}`",
        f"- Confidence: `{candidate.get('confidence', '').strip()}`",
        "",
        "## Summary",
        candidate.get("summary", "").strip(),
        "",
        "## Mechanism",
        candidate.get("mechanism", "").strip(),
        "",
        "## Scope Conditions",
    ]
    scope_conditions = candidate.get("scope_conditions", [])
    if scope_conditions:
        lines.extend(f"- {item}" for item in scope_conditions)
    else:
        lines.append("- None specified.")

    lines.extend(["", "## Non-Transfer Cases"])
    non_transfer_cases = candidate.get("non_transfer_cases", [])
    if non_transfer_cases:
        lines.extend(f"- {item}" for item in non_transfer_cases)
    else:
        lines.append("- None specified.")

    lines.extend(
        [
            "",
            "## Required Transfer Test",
            candidate.get("required_transfer_test", "").strip(),
            "",
            "## Mutator Guidance",
            candidate.get("mutator_guidance", "").strip(),
            "",
            "## Firing Squad Attack",
            candidate.get("firing_squad_attack", "").strip(),
            "",
            "## Judge Penalty Condition",
            candidate.get("judge_penalty_condition", "").strip(),
            "",
            "## Evidence Summary",
            candidate.get("evidence_summary", "").strip(),
            "",
            "## Source Projects",
        ]
    )

    source_projects = candidate.get("source_projects", [])
    if source_projects:
        lines.extend(f"- {item}" for item in source_projects)
    else:
        lines.append("- None listed.")

    lines.extend(["", "## Source Incident IDs"])
    source_incident_ids = candidate.get("source_incident_ids", [])
    if source_incident_ids:
        lines.extend(f"- `{item}`" for item in source_incident_ids)
    else:
        lines.append("- None listed.")

    lines.extend(["", "## Tags"])
    tags = candidate.get("tags", [])
    if tags:
        lines.extend(f"- `{item}`" for item in tags)
    else:
        lines.append("- None listed.")

    lines.extend(["", "## Promotion Note", candidate.get("promotion_note", "").strip(), ""])
    return "\n".join(lines)


def write_index(index: List[Dict[str, Any]], drafted: int) -> None:
    write_json(INDEX_JSON, {"drafted": drafted, "items": index})


def main() -> int:
    args = parse_args()
    incidents_path = Path(args.incidents).resolve() if args.incidents else INCIDENTS_JSONL
    if not incidents_path.exists():
        raise SystemExit(f"Incident file not found: {incidents_path}")

    incidents = load_incidents(incidents_path)
    if not incidents:
        raise SystemExit("No incidents found.")

    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for incident in incidents:
        grouped[incident["primitive_key"]].append(incident)

    REVIEW_DIR.mkdir(parents=True, exist_ok=True)
    llm = LLMClient(args.model)

    allowed_keys = set(args.primitive_key or [])
    index: List[Dict[str, Any]] = []
    drafted = 0

    for primitive_key in sorted(grouped):
        if allowed_keys and primitive_key not in allowed_keys:
            continue
        incident_group = grouped[primitive_key]
        if len(incident_group) < args.min_incidents:
            continue

        json_path = REVIEW_DIR / f"{primitive_key}.json"
        md_path = REVIEW_DIR / f"{primitive_key}.md"
        if args.skip_existing and json_path.exists():
            candidate = json.loads(json_path.read_text(encoding="utf-8"))
            index.append(
                {
                    "primitive_key": primitive_key,
                    "incident_count": len(incident_group),
                    "json_path": str(json_path.relative_to(ROOT_DIR)),
                    "markdown_path": str(md_path.relative_to(ROOT_DIR)),
                    "title": candidate.get("title", ""),
                    "confidence": candidate.get("confidence", ""),
                    "status": candidate.get("status", ""),
                }
            )
            continue

        prompt = build_prompt(primitive_key, incident_group)
        raw_response = llm.call(prompt)
        candidate = utils.parse_llm_json(raw_response)
        candidate_shape_ok(candidate)

        write_json(json_path, candidate)
        write_text(md_path, render_candidate_markdown(candidate))

        index.append(
            {
                "primitive_key": primitive_key,
                "incident_count": len(incident_group),
                "json_path": str(json_path.relative_to(ROOT_DIR)),
                "markdown_path": str(md_path.relative_to(ROOT_DIR)),
                "title": candidate.get("title", ""),
                "confidence": candidate.get("confidence", ""),
                "status": candidate.get("status", ""),
            }
        )
        drafted += 1
        write_index(index, drafted)

    write_index(index, drafted)

    print(f"Review index: {INDEX_JSON}")
    print(f"Drafted candidates: {drafted}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
