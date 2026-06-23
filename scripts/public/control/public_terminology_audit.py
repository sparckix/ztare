#!/usr/bin/env python3
"""Audit front-door public docs for reader-facing internal shorthand.

This is intentionally narrower than a repo-wide GP/seam scan. Historical ids
are valid provenance in specs, seams, code comments, tests, and research logs.
The front-door docs should lead with understandable names and keep ids as
secondary provenance.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Iterable


REPO = Path(__file__).resolve().parents[3]

TARGETS = [
    REPO / "pyproject.toml",
    REPO / "CITATION.cff",
    REPO / "README.md",
    REPO / "PRINCIPLES.md",
    REPO / "CONTRIBUTING.md",
    REPO / "SECURITY.md",
    REPO / "CHANGELOG.md",
    REPO / "RELEASE_CHECKLIST.md",
    REPO / "priority_roadmap.md",
    REPO / "docs/README.md",
    REPO / "docs/gaming_behavior_catalog.md",
    REPO / "docs/concepts/agent_agnostic_recursive_gain.md",
    REPO / "docs/concepts/agentic_engineering_patterns.md",
    REPO / "docs/concepts/capabilities.md",
    REPO / "docs/concepts/cognitive_gym.md",
    REPO / "docs/concepts/epistemic_principles.md",
    REPO / "docs/concepts/forensic_workbench_interface.md",
    REPO / "docs/concepts/glossary.md",
    REPO / "docs/concepts/goodhart_at_every_layer.md",
    REPO / "docs/concepts/problem_class_taxonomy.md",
    REPO / "docs/concepts/reflexive_engineering.md",
    REPO / "docs/concepts/reflexive_mining_methodology.md",
    REPO / "docs/concepts/rubric_specification.md",
    REPO / "docs/concepts/system_position_and_module_map.md",
    REPO / "docs/multi_substrate_validation.md",
    REPO / "docs/guides/README.md",
    REPO / "docs/guides/quickstart.md",
    REPO / "docs/guides/first-30-minutes.md",
    REPO / "docs/guides/cli.md",
    REPO / "docs/guides/experiment_cookbook.md",
    REPO / "docs/guides/for_researchers.md",
    REPO / "docs/guides/manual_console.md",
    REPO / "docs/guides/runtime_smoke_test.md",
    REPO / "docs/guides/workflow.md",
    REPO / "docs/guides/agent-prompts.md",
    REPO / "docs/landings/README.md",
    REPO / "docs/reference/make_targets.md",
    REPO / "docs/evidence_atlas/README.md",
    REPO / "docs/evidence_atlas/executable_review_pack.md",
    REPO / "docs/evidence_atlas/packet_coverage.md",
    REPO / "docs/evidence_atlas/packets/README.md",
    REPO / "docs/evidence_atlas/packets/anti_laundering_catches.md",
    REPO / "docs/evidence_atlas/packets/evaluator_hardening.md",
    REPO / "docs/evidence_atlas/packets/forecast_calibration.md",
    REPO / "docs/evidence_atlas/packets/gaming_catalog.md",
    REPO / "docs/evidence_atlas/packets/governed_autoformalization.md",
    REPO / "docs/evidence_atlas/packets/leanmill_apn_audit.md",
    REPO / "docs/evidence_atlas/packets/public_claim_governance.md",
    REPO / "docs/evidence_atlas/packets/reflexive_primitive_promotion.md",
    REPO / "docs/evidence_atlas/packets/transport_to_decidability.md",
    REPO / "docs/evidence_atlas/packets/validator_source_preflight.md",
    REPO / "docs/reference/autoresearch_state_carrier.md",
    REPO / "docs/sprint_70day_journey.md",
    REPO / "examples/README.md",
    REPO / "examples/project_packets/README.md",
    REPO / "examples/substrate_packets/README.md",
    REPO / "scripts/public/control/README.md",
    REPO / "src/ztare/cli.py",
]

COMMAND_SURFACES = {
    "make help": ["make", "help"],
    "ztare --help": [sys.executable, "-m", "src.ztare.cli", "--help"],
}

FORBIDDEN_TERMS = [
    (re.compile(r"\bapparatus-lift\b", re.IGNORECASE), "use measured proof-search lift"),
    (re.compile(r"\bapparatus evidence\b", re.IGNORECASE), "use existing evidence"),
    (re.compile(r"\bapparatus deployment\b", re.IGNORECASE), "use workbench deployment"),
    (re.compile(r"\bautonomous research engine\b", re.IGNORECASE), "use autonomous research system"),
    (re.compile(r"\bcurrent-engine\b", re.IGNORECASE), "use current or workbench"),
    (re.compile(r"docs/internal", re.IGNORECASE), "do not point public entry docs at maintainer-only paths"),
    (re.compile(r"\bevidence[- ]packets?\b", re.IGNORECASE), "use audit trails or review packets as public labels"),
    (re.compile(r"\bepistemic engine\b", re.IGNORECASE), "use zero-trust workbench or claim-auditing workbench"),
    (re.compile(r"\bgeneral-purpose engine users\b", re.IGNORECASE), "use project users"),
    (re.compile(r"\bgp_example\b", re.IGNORECASE), "use a neutral example slug in public docs"),
    (re.compile(r"\bkernel[-/ ]entry\b", re.IGNORECASE), "use run readiness"),
    (re.compile(r"\bdogfood(?:ed|ing|s)?\b", re.IGNORECASE), "use self-applied, exercised locally, or tested"),
    (
        re.compile(r"--project\s+[a-z0-9]+(?:_[a-z0-9]+)*_\d{4}\b", re.IGNORECASE),
        "keep dated project-specific examples out of public entry docs",
    ),
    (re.compile(r"\bmoat\b", re.IGNORECASE), "use strategic advantage or claim advantage"),
    (re.compile(r"\bload[- ]bearing\b", re.IGNORECASE), "use core, required, or central"),
    (re.compile(r"\bprincipal-orchestrator\b", re.IGNORECASE), "use cross-domain orchestration"),
    (re.compile(r"\bresearch operating system\b", re.IGNORECASE), "use research workbench"),
    (re.compile(r"research_areas/private", re.IGNORECASE), "do not point public entry docs at maintainer-only paths"),
    (re.compile(r"\breal work\b", re.IGNORECASE), "use the specific task or artifact"),
    (re.compile(r"\bresearch-engineer\b", re.IGNORECASE), "use research engineering"),
    (re.compile(r"\bsubstrate packet intake\b", re.IGNORECASE), "use project intake"),
    (re.compile(r"\bsubstrate prep ledger\b", re.IGNORECASE), "use project/data prep ledger"),
    (re.compile(r"\bsubstrate-prober\b", re.IGNORECASE), "use in-loop autoresearch or project intake"),
    (re.compile(r"\bworkbench workflow\b", re.IGNORECASE), "use out-of-loop research operations"),
    (re.compile(r"\bprepare the packet\b", re.IGNORECASE), "use prepare project intake"),
    (
        re.compile(r"\bwhat can this review packet actually answer\b", re.IGNORECASE),
        "use bounded claim and evidence surface for in-loop route language",
    ),
    (
        re.compile(r"\bbounded review packet\b", re.IGNORECASE),
        "use bounded intake/evidence surface unless referring to an evidence-atlas review packet",
    ),
    (
        re.compile(r"\bonce the packet exists\b", re.IGNORECASE),
        "use once intake and evidence surfaces exist",
    ),
    (re.compile(r"\bpacket is stable\b", re.IGNORECASE), "use boundary object is stable"),
    (re.compile(r"\bT" r"MLR\b", re.IGNORECASE), "use neutral submission package wording"),
    (re.compile(r"\blands hard\b", re.IGNORECASE), "state the concrete effect"),
    (re.compile(r"\bworld[- ]class\b", re.IGNORECASE), "state the concrete quality bar"),
    (
        re.compile(r"\bcheating catalog\b", re.IGNORECASE),
        "use gaming behavior catalog in public-facing docs",
    ),
    (
        re.compile(r"\badversarial[- ]reasoning engine\b", re.IGNORECASE),
        "use zero-trust workbench in public-facing docs",
    ),
    (
        re.compile(r"\badversarial[- ]reasoning\b", re.IGNORECASE),
        "use zero-trust workbench or attack/defense pressure in public-facing docs",
    ),
    (
        re.compile(r"\boperator[- ]console\b", re.IGNORECASE),
        "use manual console for the public-facing surface",
    ),
    (
        re.compile(r"\bresearch-engine\b", re.IGNORECASE),
        "use research workbench or claim-auditing workbench in package metadata",
    ),
    (
        re.compile(
            r"\b(?:technical|independent technical|policy/strategy|human)\s+operators?\b",
            re.IGNORECASE,
        ),
        "use reviewer, maintainer, person, or accountable human",
    ),
    (
        re.compile(
            r"\boperator[- ]facing\b|\bagent/operator\b|\boperator\s+rule\b|"
            r"\boperators?'?s?\s+(?:judgment|posterior|role|job|discipline)\b|"
            r"\boperator[- ]patch\b|"
            r"\b(?:single|second|different)[- ]operator\b|"
            r"\boperator[- ](?:committed|curated|authored|mandated|side|enforced)\b|"
            r"\boperator\s+(?:input|guidance|state|notes|audit|action|"
            r"decides|reviews|wants|authorizes|treats|runs|opts|path|clarity|catch|remains)\b",
            re.IGNORECASE,
        ),
        "use reviewer, maintainer, person, or accountable human",
    ),
]

BARE_GP_LABEL = re.compile(
    r"^\s*(?:[-*]\s+|\|[^|]*\|\s*)"
    r"(?:\*\*)?(?:\[)?GP-\d{3}[a-z]?(?:/[A-Z0-9-]+)?(?:\]\([^)]+\)|\])?(?:\*\*)?"
    r"(?:\s|[:|—-])",
    re.IGNORECASE,
)

BARE_GP_HEADING = re.compile(
    r"^\s*#{1,6}\s+(?:\d+(?:\.\d+)*[a-z]?\s+)?"
    r"(?:\*\*)?(?:\[)?GP-\d{3}[a-z]?(?:/[A-Z0-9-]+)?(?:\]\([^)]+\)|\])?(?:\*\*)?"
    r"(?:\s|[:|—-])",
    re.IGNORECASE,
)

ADJECTIVAL_GP_ID = re.compile(
    r"\bGP-\d{3}[a-z]?\s+"
    r"(?:rubric|sandbox|forecast|contract|commit|membrane|pattern|primitive|"
    r"gate|protocol|discipline|review|vocabulary|operation|ops|row|surface)\b",
    re.IGNORECASE,
)

GP_LINK_AS_LABEL = re.compile(
    r"(?:^\s*(?:[-*]\s+)?|\|\s*)"
    r"(?:\*\*)?\[GP-\d{3}[a-z]?(?:/[A-Z0-9-]+)?\]\([^)]+\)(?:\*\*)?\s+"
    r"(?:[A-Z][A-Za-z0-9-]*|[a-z][a-z0-9-]*(?:[-_][a-z0-9]+)*)",
    re.IGNORECASE,
)

GP_LINK_CELL_AS_LABEL = re.compile(
    r"\|\s*(?:\*\*)?\[GP-\d{3}[a-z]?(?:/[A-Z0-9-]+)?\]\([^)]+\)(?:\*\*)?\s*[:;,)-]",
    re.IGNORECASE,
)

BARE_GP_CELL_LABEL = re.compile(
    r"\|\s*GP-\d{3}[a-z]?(?:/[A-Z0-9-]+)?\s*[:;,)-]",
    re.IGNORECASE,
)

RAW_ID_LINK_LABEL = re.compile(
    r"\[[^\]]*(?:projects/gp\d{3}[a-z]?[a-z0-9_-]*|"
    r"research_areas/[^\]]*GP-\d{3}[a-z]?|"
    r"/gp\d{3}[a-z]?[a-z0-9_-]*|"
    r"/GP-\d{3}[a-z]?)[^\]]*\]\([^)]+\)",
    re.IGNORECASE,
)


def iter_existing_targets() -> Iterable[Path]:
    for target in TARGETS:
        if target.exists():
            yield target


def classify_line(path: Path, line_no: int, text: str) -> list[dict[str, object]]:
    findings: list[dict[str, object]] = []
    for pattern, replacement in FORBIDDEN_TERMS:
        if pattern.search(text):
            findings.append(
                {
                    "path": str(path.relative_to(REPO)),
                    "line": line_no,
                    "kind": "forbidden_term",
                    "term": pattern.pattern,
                    "suggestion": replacement,
                    "text": text.strip(),
                }
            )

    if BARE_GP_LABEL.search(text):
        findings.append(
            {
                "path": str(path.relative_to(REPO)),
                "line": line_no,
                "kind": "bare_gp_label",
                "suggestion": "lead with a plain capability name; keep GP id as provenance",
                "text": text.strip(),
            }
        )
    if BARE_GP_HEADING.search(text):
        findings.append(
            {
                "path": str(path.relative_to(REPO)),
                "line": line_no,
                "kind": "bare_gp_heading",
                "suggestion": "lead headings with the capability name; keep GP id as provenance",
                "text": text.strip(),
            }
        )
    if ADJECTIVAL_GP_ID.search(text):
        findings.append(
            {
                "path": str(path.relative_to(REPO)),
                "line": line_no,
                "kind": "adjectival_gp_id",
                "suggestion": "name the capability first; put the GP id after it as provenance",
                "text": text.strip(),
            }
        )
    if GP_LINK_AS_LABEL.search(text):
        findings.append(
            {
                "path": str(path.relative_to(REPO)),
                "line": line_no,
                "kind": "gp_link_as_label",
                "suggestion": "name the capability first; put the GP id after it as provenance",
                "text": text.strip(),
            }
        )
    if GP_LINK_CELL_AS_LABEL.search(text) or BARE_GP_CELL_LABEL.search(text):
        findings.append(
            {
                "path": str(path.relative_to(REPO)),
                "line": line_no,
                "kind": "gp_cell_label",
                "suggestion": "start the table cell with a plain capability name; put the GP id after it as provenance",
                "text": text.strip(),
            }
        )
    if RAW_ID_LINK_LABEL.search(text):
        findings.append(
            {
                "path": str(path.relative_to(REPO)),
                "line": line_no,
                "kind": "raw_id_link_label",
                "suggestion": "make markdown link text human-readable; keep the raw id only in the URL target",
                "text": text.strip(),
            }
        )
    return findings


def classify_forbidden_terms(surface: str, line_no: int, text: str) -> list[dict[str, object]]:
    findings: list[dict[str, object]] = []
    for pattern, replacement in FORBIDDEN_TERMS:
        if pattern.search(text):
            findings.append(
                {
                    "path": surface,
                    "line": line_no,
                    "kind": "forbidden_term",
                    "term": pattern.pattern,
                    "suggestion": replacement,
                    "text": text.strip(),
                }
            )
    return findings


def command_output(name: str, args: list[str]) -> str:
    result = subprocess.run(
        args,
        cwd=REPO,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return result.stdout


def main() -> int:
    findings: list[dict[str, object]] = []
    checked: list[str] = []
    for path in iter_existing_targets():
        checked.append(str(path.relative_to(REPO)))
        for idx, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            findings.extend(classify_line(path, idx, line))
    for surface, args in COMMAND_SURFACES.items():
        checked.append(surface)
        for idx, line in enumerate(command_output(surface, args).splitlines(), start=1):
            findings.extend(classify_forbidden_terms(surface, idx, line))

    payload = {
        "ok": not findings,
        "checked_files": checked,
        "finding_count": len(findings),
        "findings": findings,
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    if findings:
        raise SystemExit("public terminology audit failed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
