import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from ztare.workspace.compile_evidence import ROOT_DIR, read_text, write_json, write_text


DEBATE_SCORE_RE = re.compile(r"# Final Score:\s*(\d+)")
WEAKEST_POINT_RE = re.compile(r"\*\*Weakest Point:\*\*\s*(.+)")
ITERATION_RE = re.compile(r"iter[_-]?(\d+)|debate_log_iter_(\d+)")


RULES: List[Dict[str, Any]] = [
    {
        "primitive_key": "cooked_books",
        "pattern_label": "Step-Index Leakage / Cooked Books / Parametric Rigging",
        "keywords": [r"Step-Index Leakage", r"Data Dependence Break", r"Cooked Book RNG", r"Cooked Books?", r"cooked book", r"hardcoded favorable", r"parametric grounding", r"Parameter Overfitting", r"Parameter Provenance Break", r"Gravity Constant"],
        "classification": "epistemic_failure",
        "epistemic_role_guess": "attack_template",
        "severity": "high",
    },
    {
        "primitive_key": "assert_narrowing",
        "pattern_label": "Claim-Test Mismatch",
        "keywords": [r"Claim-Test Mismatch", r"Claim-Test Equivalence Break", r"Assert Narrowing", r"assertion range", r"exactly match", r"threshold fitting"],
        "classification": "epistemic_failure",
        "epistemic_role_guess": "attack_template",
        "severity": "high",
    },
    {
        "primitive_key": "silent_injection",
        "pattern_label": "Silent Injection / Hidden Upstream Assumption",
        "keywords": [r"Silent Injection", r"hidden upstream", r"silently set to 100%", r"never named in decision-critical", r"assumed at 100%", r"hardcoded to True"],
        "classification": "epistemic_failure",
        "epistemic_role_guess": "attack_template",
        "severity": "high",
    },
    {
        "primitive_key": "straw_man_design",
        "pattern_label": "Weak Baseline",
        "keywords": [r"Weak Baseline", r"Comparator Fairness Break", r"Straw Man", r"manufactured gap", r"engineer(?:ed)? Design A to fail", r"comparison rigg"],
        "classification": "epistemic_failure",
        "epistemic_role_guess": "attack_template",
        "severity": "high",
    },
    {
        "primitive_key": "float_masking",
        "pattern_label": "Tolerance Abuse / Precision Hiding",
        "keywords": [r"Tolerance Abuse", r"Precision Invariance Break", r"Float Masking", r"round\(", r"precision", r"destroy precision"],
        "classification": "epistemic_failure",
        "epistemic_role_guess": "attack_template",
        "severity": "medium",
    },
    {
        "primitive_key": "fake_autodiff",
        "pattern_label": "Stubbed Implementation / Named Mechanism Without Real Mechanism",
        "keywords": [r"Stubbed Implementation", r"Mechanism Responsiveness Break", r"Fake AutoDiff", r"hardcoded dict", r"named after mechanism"],
        "classification": "epistemic_failure",
        "epistemic_role_guess": "attack_template",
        "severity": "high",
    },
    {
        "primitive_key": "dimensional_error",
        "pattern_label": "Fudge-Factor Patching / Dimensional Error",
        "keywords": [r"Fudge-Factor Patching", r"Dimensional Invariance Break", r"Dimensional Factor", r"Dimensional", r"unit dimensionality", r"dimensionally inconsistent", r"Category Error", r"pint"],
        "classification": "epistemic_failure",
        "epistemic_role_guess": "test_template",
        "severity": "high",
    },
    {
        "primitive_key": "unidirectional_decay",
        "pattern_label": "Partial-Domain Miscalibration",
        "keywords": [r"Partial-Domain Miscalibration", r"Probability-Bounds Break", r"Impossible Probability", r"unidirectional decay", r"cannot increase probability", r"confidence degrader", r"Bayesian Updater"],
        "classification": "epistemic_failure",
        "epistemic_role_guess": "failure_pattern",
        "severity": "high",
    },
    {
        "primitive_key": "domain_leakage",
        "pattern_label": "Domain Leakage Into Architectural Proof",
        "keywords": [r"ABSTRACTION MANDATE", r"domain-specific variable names", r"domain context", r"architecture wearing"],
        "classification": "epistemic_failure",
        "epistemic_role_guess": "failure_pattern",
        "severity": "medium",
    },
    {
        "primitive_key": "perfect_mirroring_simulation",
        "pattern_label": "Perfectly Mirrored Simulation",
        "keywords": [r"artificially easy", r"perfectly mirroring", r"perfectly discoverable", r"simulated reality"],
        "classification": "epistemic_failure",
        "epistemic_role_guess": "failure_pattern",
        "severity": "medium",
    },
    {
        "primitive_key": "post_hoc_rescue_variable",
        "pattern_label": "Post-Hoc Rescue Variable",
        "keywords": [r"post-hoc", r"introduced after the model failed", r"free variable", r"unfalsifiable rescue"],
        "classification": "epistemic_failure",
        "epistemic_role_guess": "failure_pattern",
        "severity": "high",
    },
    {
        "primitive_key": "small_n_base_rate_trap",
        "pattern_label": "Small-N Base-Rate Trap",
        "keywords": [r"coin flip", r"base rates are low", r"variance swallows the signal", r"statistically indistinguishable", r"small pilot"],
        "classification": "epistemic_failure",
        "epistemic_role_guess": "test_template",
        "severity": "high",
    },
    {
        "primitive_key": "missing_falsification_suite",
        "pattern_label": "Missing Falsification Suite",
        "keywords": [r"No falsification suite", r"test_model\.py\) found"],
        "classification": "process_failure",
        "epistemic_role_guess": "failure_pattern",
        "severity": "medium",
    },
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extract reusable primitive incidents from project runs.")
    parser.add_argument(
        "--project",
        action="append",
        help="Project directory name under projects/. Repeatable. If omitted, scan all projects.",
    )
    parser.add_argument(
        "--output-jsonl",
        help="Output JSONL path. Defaults to global_primitives/incidents/primitive_incidents.jsonl.",
    )
    parser.add_argument(
        "--output-summary",
        help="Output summary JSON path. Defaults to global_primitives/incidents/primitive_incident_summary.json.",
    )
    return parser.parse_args()


def resolve_projects(project_args: Optional[List[str]]) -> List[Path]:
    projects_root = ROOT_DIR / "projects"
    if not project_args:
        return sorted([path for path in projects_root.iterdir() if path.is_dir()])
    resolved = []
    for project_arg in project_args:
        candidate = projects_root / project_arg
        if candidate.exists():
            resolved.append(candidate)
    return sorted(resolved)


def artifact_paths(project_dir: Path) -> Iterable[Path]:
    for path in sorted(project_dir.glob("debate_log_iter_*.md")):
        yield path
    history_dir = project_dir / "history"
    if history_dir.exists():
        for path in sorted(history_dir.glob("*.md")):
            yield path
    path = project_dir / "test_model.py"
    if path.exists():
        yield path


def artifact_type_for_path(path: Path) -> str:
    if path.name.startswith("debate_log_iter_"):
        return "debate_log"
    if "history" in path.parts:
        return "history"
    if path.name == "test_model.py":
        return "test_model"
    if path.name == "thesis.md":
        return "thesis"
    if path.name == "current_iteration.md":
        return "current_iteration"
    return "artifact"


def parse_score(text: str) -> Optional[int]:
    match = DEBATE_SCORE_RE.search(text)
    return int(match.group(1)) if match else None


def parse_weakest_point(text: str) -> Optional[str]:
    match = WEAKEST_POINT_RE.search(text)
    return match.group(1).strip() if match else None


def parse_iteration_hint(path: Path) -> Optional[str]:
    match = ITERATION_RE.search(path.name)
    if not match:
        return None
    return next((group for group in match.groups() if group), None)


def excerpt_for_match(text: str, pattern: str, radius: int = 280) -> Optional[str]:
    match = re.search(pattern, text, re.IGNORECASE)
    if not match:
        return None
    start = max(0, match.start() - radius)
    end = min(len(text), match.end() + radius)
    excerpt = text[start:end].strip()
    return " ".join(excerpt.split())


def extract_rule_hit(text: str, rule: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    hits: List[str] = []
    excerpt: Optional[str] = None
    for pattern in rule["keywords"]:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            hits.append(match.group(0))
            if excerpt is None:
                excerpt = excerpt_for_match(text, pattern)
    if not hits:
        return None
    return {
        "keyword_hits": sorted(set(hits)),
        "signal_excerpt": excerpt or "",
    }


def build_incident(project_dir: Path, path: Path, text: str, rule: Dict[str, Any], hit: Dict[str, Any]) -> Dict[str, Any]:
    rel_path = str(path.relative_to(ROOT_DIR))
    artifact_type = artifact_type_for_path(path)
    iteration_hint = parse_iteration_hint(path)
    score = parse_score(text)
    weakest_point = parse_weakest_point(text)
    incident_id = f"{project_dir.name}:{artifact_type}:{path.stem}:{rule['primitive_key']}"
    summary_bits = [rule["pattern_label"], f"detected in {artifact_type}"]
    if score is not None:
        summary_bits.append(f"score={score}")
    summary = " | ".join(summary_bits)
    return {
        "incident_id": incident_id,
        "primitive_key": rule["primitive_key"],
        "pattern_label": rule["pattern_label"],
        "project": project_dir.name,
        "artifact_path": rel_path,
        "artifact_type": artifact_type,
        "iteration_hint": iteration_hint,
        "final_score": score,
        "classification": rule["classification"],
        "epistemic_role_guess": rule["epistemic_role_guess"],
        "severity": rule["severity"],
        "summary": summary,
        "weakest_point": weakest_point,
        "signal_excerpt": hit["signal_excerpt"],
        "keyword_hits": hit["keyword_hits"],
        "source_meta": {
            "path_name": path.name,
        },
    }


def scan_project(project_dir: Path) -> List[Dict[str, Any]]:
    incidents: List[Dict[str, Any]] = []
    for path in artifact_paths(project_dir):
        text = read_text(path)
        for rule in RULES:
            hit = extract_rule_hit(text, rule)
            if not hit:
                continue
            incidents.append(build_incident(project_dir, path, text, rule, hit))
    return incidents


def dedupe_incidents(incidents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = set()
    out = []
    for incident in incidents:
        key = incident["incident_id"]
        if key in seen:
            continue
        seen.add(key)
        out.append(incident)
    return out


def write_jsonl(path: Path, rows: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    content = "\n".join(json.dumps(row, sort_keys=True) for row in rows) + ("\n" if rows else "")
    write_text(path, content)


def main() -> int:
    args = parse_args()
    projects = resolve_projects(args.project)
    if not projects:
        raise SystemExit("No projects found to scan.")

    incidents: List[Dict[str, Any]] = []
    for project_dir in projects:
        incidents.extend(scan_project(project_dir))
    incidents = dedupe_incidents(incidents)
    incidents.sort(key=lambda item: (item["primitive_key"], item["project"], item["artifact_path"]))

    output_jsonl = (
        Path(args.output_jsonl).resolve()
        if args.output_jsonl
        else (ROOT_DIR / "global_primitives" / "incidents" / "primitive_incidents.jsonl")
    )
    output_summary = (
        Path(args.output_summary).resolve()
        if args.output_summary
        else (ROOT_DIR / "global_primitives" / "incidents" / "primitive_incident_summary.json")
    )

    write_jsonl(output_jsonl, incidents)

    by_key = Counter(item["primitive_key"] for item in incidents)
    by_project = Counter(item["project"] for item in incidents)
    by_classification = Counter(item["classification"] for item in incidents)
    sample_by_key: Dict[str, Dict[str, Any]] = {}
    for incident in incidents:
        sample_by_key.setdefault(incident["primitive_key"], incident)

    summary = {
        "project_count": len(projects),
        "incident_count": len(incidents),
        "by_primitive_key": dict(sorted(by_key.items())),
        "by_project": dict(sorted(by_project.items())),
        "by_classification": dict(sorted(by_classification.items())),
        "samples": {key: sample_by_key[key] for key in sorted(sample_by_key)},
    }
    write_json(output_summary, summary)

    print(f"Incidents: {output_jsonl}")
    print(f"Summary: {output_summary}")
    print(f"Incident count: {len(incidents)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
