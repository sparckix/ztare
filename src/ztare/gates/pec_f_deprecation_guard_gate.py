"""G-PEC-F-DEPRECATION-GUARD — flag legacy pec_f tagging in advisor channels.

GP-219 Phase 3 cross-paper test (2026-05-06) confirmed pec_f
("Proof-Surface Compression") is NS-substrate-specific: appears in
0 of 3 fresh PDE papers (quasilinear elliptic, kinetic Boltzmann,
dispersive Ricci soliton). The proto-op is demoted to substrate-
management metadata.

This gate scans advisor channel turns / F-rows / closure docs for
references to `pec_f` or "Proof-Surface Compression" and emits an
advisory warning suggesting re-tagging as `pec_b` (Regime/Class
Scoping) for the scoping-flavored aspect.

Severity: advisory. Catches drift where Director tags work with the
demoted op without acknowledging the Phase 3 demotion.

# When this gate fires

  Per closure-attempt review (per RD mandate v1.22+). Run on the
  current advisor channel + recent F-rows for the substrate.
"""
from __future__ import annotations

from pathlib import Path
import re
from typing import Any

GATE_ID = "G-PEC-F-DEPRECATION-GUARD"
PRODUCER = "phase3_pde_estimate_craft_validation"
RELIABILITY_NOTE = (
    "Advisory only. Phase 3 evidence: pec_f appears in 0 of 3 PDE papers "
    "outside the NS+analysis_pde Phase 1+2 corpus. Demotion is empirical "
    "but small-N (3 papers); a future Phase 4 with larger corpus could "
    "rehabilitate the op if it surfaces broadly."
)

PEC_F_PATTERNS = [
    re.compile(r"\bpec_f\b", re.IGNORECASE),
    re.compile(r"Proof[-\s]Surface\s+Compression", re.IGNORECASE),
]

ACKNOWLEDGED_DEMOTION_PATTERNS = [
    re.compile(r"demot", re.IGNORECASE),
    re.compile(r"subordinate", re.IGNORECASE),
    re.compile(r"substrate[-\s]specific", re.IGNORECASE),
    re.compile(r"substrate[-\s]management", re.IGNORECASE),
    re.compile(r"not\s+generic", re.IGNORECASE),
    re.compile(r"NS[-\s]heavy", re.IGNORECASE),
    re.compile(r"provisional", re.IGNORECASE),
    re.compile(r"Phase\s+3", re.IGNORECASE),
]


def scan_text_for_pec_f(text: str) -> list[dict]:
    """Find lines that reference pec_f or its long name."""
    lines = text.splitlines()
    hits = []
    for line_no, line in enumerate(lines, 1):
        for pat in PEC_F_PATTERNS:
            m = pat.search(line)
            if m:
                context_window = " ".join(
                    lines[max(0, line_no - 2):min(len(lines), line_no + 1)]
                )
                hits.append({
                    "line": line_no,
                    "matched": m.group(0),
                    "context": line.strip()[:160],
                    "acknowledged_demotion": any(
                        ack.search(context_window)
                        for ack in ACKNOWLEDGED_DEMOTION_PATTERNS
                    ),
                })
                break
    return hits


def run_gate(target_files: list[Path]) -> dict[str, Any]:
    """Scan provided files, return advisory result."""
    all_hits: list[dict] = []
    for path in target_files:
        if not path.exists():
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        file_hits = scan_text_for_pec_f(text)
        for h in file_hits:
            h["file"] = str(path)
        all_hits.extend(file_hits)

    actionable_hits = [
        h for h in all_hits if not h.get("acknowledged_demotion")
    ]
    n_demoted_refs = len(actionable_hits)
    n_acknowledged = len(all_hits) - n_demoted_refs
    return {
        "name": GATE_ID,
        "passed": True,  # advisory; never blocks
        "actual": n_demoted_refs,
        "threshold": 0,
        "reason": (f"found {n_demoted_refs} reference(s) to demoted op pec_f. "
                   f"Phase 3 (2026-05-06) confirmed NS-substrate-specific. "
                   f"Consider re-tagging as pec_b (Regime/Class Scoping) or "
                   f"as substrate-management metadata, not generic PDE op."
                   if n_demoted_refs else
                   f"no unacknowledged references to demoted pec_f "
                   f"({n_acknowledged} acknowledged reference(s))"),
        "penalty": 0,
        "hard_fail": False,
        "severity": "advisory",
        "source": PRODUCER,
        "extra": {
            "demoted_op": "pec_f",
            "phase3_evidence": "0 of 3 PDE papers; quasilinear elliptic, kinetic Boltzmann, dispersive Ricci soliton",
            "suggested_replacement": "pec_b (Regime/Class Scoping) for scoping-flavored aspect",
            "hits": actionable_hits[:25],  # cap output
            "acknowledged_hits": [
                h for h in all_hits if h.get("acknowledged_demotion")
            ][:25],
            "RELIABILITY_NOTE": RELIABILITY_NOTE,
        },
    }


def can_handle(substrate: Any, candidate: Any) -> tuple[bool, str]:
    """Engages whenever closure-attempt review runs."""
    return True, "always-on advisory; runs per closure-attempt review"


if __name__ == "__main__":
    import sys
    REPO = Path(__file__).resolve().parents[3]
    DEFAULT_TARGETS = [
        REPO / "projects" / "ns_millennium_hunt" / "workspace" / "advisor_channel.md",
        REPO / "research_areas" / "EXPERIMENT_TRACK_RECORD.md",
    ]
    targets = ([Path(p) for p in sys.argv[1:]] if len(sys.argv) > 1
               else DEFAULT_TARGETS)
    result = run_gate(targets)
    print(f"=== {GATE_ID} ===")
    print(f"  result: {result['reason']}")
    if result["actual"]:
        for h in result["extra"]["hits"][:10]:
            print(f"    {h['file']}:{h['line']}  {h['matched']}: {h['context']}")
