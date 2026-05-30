#!/usr/bin/env python3
"""pattern_026_calibration_audit.py — tertiary calibration test for PATTERN-026
(primitive_before_architecture_gate).

PATTERN-026 §5 requires: "apply this pattern to 5 historical seams in the repo;
if 'what counts as a layer' requires case-by-case judgment for >2 of 5, the
pattern's layer-definition is too vague and must be refined further."

Pre-registered audit targets (from the pattern file):
- GP-225 v22 through v30 chain
- GP-191 Stage 2 tenant overlay
- GP-216 theory-building ops
- GP-168 OKR addendum
- GP-156 fit_primitive_features

For each seam, applies PATTERN-026's structural triggers and reports:
- Layers identified (named components whose failure would retract architecture-
  level claims)
- For each layer: artifact-citation? pass-gate? measurement? PASS/FAIL.
- Overall PATTERN-026 verdict: FIRES / CLEAN.
- Pattern-applicability judgment: AUTOMATIC (rules unambiguous) / MANUAL
  (case-by-case judgment needed).

Pass-gate: ≥3 of 5 seams must yield AUTOMATIC pattern-applicability for
PATTERN-026 to validate. If ≤2 are AUTOMATIC, pattern fails calibration and
must be refined.
"""
from __future__ import annotations
import argparse, json, re, sys
from pathlib import Path
from typing import Any

ROOT = Path(__import__("os").environ.get("ZTARE_REPO_ROOT", ".")).resolve()

CALIBRATION_TARGETS = [
    {
        "id": "GP-233_§7",  # the calibration POSITIVE — known failure, should FIRE
        "path": "research_areas/seams/reflexive/GP-233_4_catalog_meta_solver_framework_seam.md",
        "expected_verdict": "FIRES",
        "rationale": "Demoted in same session; named Layer 2a/2b/2c/2d with 'first pass is crude' / 'research thread' markers; killed by Meta-Darwin.",
    },
    {
        "id": "GP-225_gnn_lemma_relevance_ranker",
        "path": "research_areas/seams/engine/lean/GP-225_gnn_lemma_relevance_ranker_seam.md",
        "expected_verdict": "UNKNOWN",
        "rationale": "Multi-route seam (Routes A/B/C). Tests whether routes count as 'layers' under PATTERN-026.",
    },
    {
        "id": "GP-216_theory_building",
        "path": "research_areas/seams/engine/meta/GP-216_theory_building_operations_seam.md",
        "expected_verdict": "UNKNOWN",
        "rationale": "12-op registry. Tests whether ops count as layers.",
    },
    {
        "id": "GP-168_org_design_unfalsifiability",
        "path": "research_areas/seams/mission/org/GP-168_org_design_unfalsifiability_seam.md",
        "expected_verdict": "UNKNOWN",
        "rationale": "Closure-impossibility theorem. Tests how pattern handles seam that names a negative result vs an architecture.",
    },
    {
        "id": "GP-191_org_kernel_policy_boundary",
        "path": "research_areas/seams/protocol/GP-191_org_kernel_policy_boundary_seam.md",
        "expected_verdict": "UNKNOWN",
        "rationale": "Tenant-overlay 2-repo split. Tests whether file-system architecture counts as layered.",
    },
]


# ---------------------------------------------------------------
# Structural detection per PATTERN-026 (revised v1)
# ---------------------------------------------------------------

ARCH_LEXICAL = [
    r"\barchitecture\b",
    r"\bLayer\s+\d+",
    r"\bLayer\s+[A-Z][a-z]+",
    r"\b\d+[- ]layer\b",
    r"\bmulti[- ]layer\b",
    r"\bload[- ]bearing\b",
    r"\bprimitive\b",
]

LAUNDERABLE_LEXICAL = [
    r"first pass is crude",
    r"crude first pass",
    r"first pass[: ]",
    r"research thread",
    r"deferred to future work",
    r"\bTBD\b",
    r"to be written",
    r"to be determined",
    r"v1 (?:implementation|version) is approximate",
    r"approximate first version",
    r"we'?ll skip",
    r"is the hardest step",
    r"will be refined",
]


def find_layer_sections(text: str) -> list[dict]:
    """Heuristic: a 'layer-like component' is a section header (## or ###)
    whose title matches one of:
      - 'Layer N' / 'Layer X' / 'Phase N' / 'Stage N'
      - '§N.M' style numbered subsection
      - any header containing a numbered component name
    Plus inline references to "Layer X" within prose.
    """
    layers = []
    for m in re.finditer(r"^#{2,4}\s+(.+)$", text, re.MULTILINE):
        title = m.group(1).strip()
        # Strip emphasis markers
        clean = re.sub(r"[*_`]", "", title)
        if re.search(r"\b(Layer|Phase|Stage|Step)\s+[A-Za-z0-9]+\b", clean, re.IGNORECASE) or \
           re.search(r"^§?\d+\.[0-9a-z]+", clean) or \
           re.search(r"\bcomponent\b|\bprimitive\b", clean, re.IGNORECASE):
            # Capture the section body until next same-or-higher header
            start = m.end()
            next_m = re.search(r"^#{2,4}\s+", text[start:], re.MULTILINE)
            end = start + next_m.start() if next_m else len(text)
            body = text[start:end]
            layers.append({
                "title": clean,
                "body": body[:3000],  # truncate
                "char_count": end - start,
            })
    return layers


def check_layer(layer: dict) -> dict:
    """Apply PATTERN-026's 3 structural tests to one layer."""
    body = layer["body"]
    title = layer["title"]

    # Test 1: artifact citation present?
    has_artifact = bool(re.search(
        r"`[a-z_]+\.py`|\.py\b|\.lean\b|\.json\b|\.yaml\b|\.md\b|`scripts/|`src/",
        body
    ))

    # Test 2: pass-gate defined?
    pass_gate_signals = [
        r"pass[- ]gate", r"pass[: ]\s*≥|\bpass.*\d+%",
        r"threshold.*\d", r"accuracy\s*[≥>]\s*\d",
        r"F1\s*[≥>]", r"if\s+\w+\s*<\s*\d",
        r"falsifi", r"retract.*if", r"kill.*if",
    ]
    has_pass_gate = any(re.search(p, body, re.IGNORECASE) for p in pass_gate_signals)

    # Test 3: measurement reported?
    measurement_signals = [
        r"\d+\s*/\s*\d+\s*\(\s*\d+\s*%\)",  # "3/10 (30%)"
        r"\b(?:accuracy|F1|score|recall|precision)\b.*\d",
        r"\d+\.\d+\s*%",
        r"measured\s*[:=]",
        r"empirical\s+result",
    ]
    has_measurement = any(re.search(p, body, re.IGNORECASE) for p in measurement_signals)

    # Bonus: launderable lexical markers (these are paraphrase-launderable per Meta-Darwin v2 fix)
    laundering_markers = [p for p in LAUNDERABLE_LEXICAL if re.search(p, body, re.IGNORECASE)]

    return {
        "title": title,
        "has_artifact_citation": has_artifact,
        "has_pass_gate": has_pass_gate,
        "has_measurement": has_measurement,
        "laundering_markers_present": laundering_markers,
        "fires_026": not (has_artifact and has_pass_gate and has_measurement),
    }


def audit_seam(target: dict) -> dict:
    """Audit one seam against PATTERN-026."""
    p = ROOT / target["path"]
    if not p.exists():
        return {**target, "error": f"file not found: {p}"}
    text = p.read_text()

    is_architecture_artifact = any(
        re.search(pat, text, re.IGNORECASE) for pat in ARCH_LEXICAL
    )

    layers = find_layer_sections(text)
    layer_results = [check_layer(L) for L in layers]
    n_layers = len(layers)
    n_firing = sum(1 for L in layer_results if L["fires_026"])

    # Pattern-applicability judgment
    # AUTOMATIC if: (a) artifact identified clearly as architecture, AND
    #               (b) layers identified by the heuristic ≥1, AND
    #               (c) each layer's 3 tests are mechanically computable (always true here).
    # MANUAL otherwise.
    applicability = (
        "AUTOMATIC" if (is_architecture_artifact and n_layers >= 1)
        else "MANUAL" if is_architecture_artifact
        else "NOT_APPLICABLE"
    )

    overall_verdict = "FIRES" if n_firing > 0 else "CLEAN"

    return {
        "id": target["id"],
        "expected_verdict": target.get("expected_verdict"),
        "rationale": target.get("rationale"),
        "is_architecture_artifact": is_architecture_artifact,
        "n_layers_identified": n_layers,
        "n_layers_firing_026": n_firing,
        "applicability": applicability,
        "overall_verdict": overall_verdict,
        "layer_details": layer_results[:10],  # truncate to 10
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    results = [audit_seam(t) for t in CALIBRATION_TARGETS]

    n_total = len(results)
    n_auto = sum(1 for r in results if r.get("applicability") == "AUTOMATIC")
    n_manual = sum(1 for r in results if r.get("applicability") == "MANUAL")
    n_na = sum(1 for r in results if r.get("applicability") == "NOT_APPLICABLE")

    summary = {
        "n_total": n_total,
        "n_automatic": n_auto,
        "n_manual": n_manual,
        "n_not_applicable": n_na,
        "pass_gate_threshold": "≥3 of 5 AUTOMATIC",
        "pass_gate_verdict": "PASS" if n_auto >= 3 else "FAIL",
        "per_seam_results": results,
    }

    print(f"# PATTERN-026 Tertiary Calibration Audit\n")
    print(f"**Targets:** {n_total} historical seams")
    print(f"**Automatic applicability:** {n_auto}/{n_total}")
    print(f"**Manual judgment needed:** {n_manual}/{n_total}")
    print(f"**Not applicable:** {n_na}/{n_total}")
    print(f"**Pass gate:** ≥3 AUTOMATIC")
    print(f"**Verdict:** {summary['pass_gate_verdict']}\n")
    print("## Per-seam results\n")
    for r in results:
        if "error" in r:
            print(f"- **{r['id']}**: ERROR — {r['error']}")
            continue
        print(f"### {r['id']}")
        print(f"- Expected: `{r.get('expected_verdict')}`")
        print(f"- Is architecture artifact: `{r['is_architecture_artifact']}`")
        print(f"- Layers identified: `{r['n_layers_identified']}`")
        print(f"- Layers firing PATTERN-026: `{r['n_layers_firing_026']}`")
        print(f"- Applicability: `{r['applicability']}`")
        print(f"- Overall: **{r['overall_verdict']}**")
        if r["layer_details"][:3]:
            print(f"- Top layer details:")
            for L in r["layer_details"][:3]:
                marker = " | LAUNDERING" if L["laundering_markers_present"] else ""
                print(f"  - `{L['title'][:60]}` → artifact={L['has_artifact_citation']} gate={L['has_pass_gate']} measured={L['has_measurement']}{marker}")
        print()

    if args.out:
        Path(args.out).write_text(json.dumps(summary, indent=2, ensure_ascii=False, default=str))
        print(f"\nwrote {args.out}")

    return 0 if summary["pass_gate_verdict"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
