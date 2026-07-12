"""The round-trip demo — the anti-Frankenstein coherence proof AND the "forged edit" moment, fully
DETERMINISTIC (no LLM anywhere). It runs the whole compiler-for-arguments motion on ZTARE's OWN code:

    a claim a doc makes about the code  →  bound to a VERBATIM source excerpt (evidence-binding gate)
    →  a governed graph  →  a governed memo (every sentence traces to source)
    →  a plausible FORGED edit  →  the re-ingest gate catches it, with receipts.

Every tool helps you *generate* plausible prose; this is the only one that *catches* a forged one. Run:
    PYTHONPATH=src python -m ztare.scenarios.demo_roundtrip
"""
from __future__ import annotations

from ztare.scenarios.artifacts import (
    GovernedEdge,
    GovernedElement,
    GovernedState,
    assemble_verdict,
    decision_memo,
    reingest_gate,
    render,
)
from ztare.scenarios.evidence_binding import bind_evidence


def _bound_claim(rel_path: str, needle: str, claim_text: str, cid: str) -> "tuple[GovernedElement, GovernedElement, GovernedEdge] | None":
    """A doc CLAIM about the code, bound to the verbatim source line that exhibits it (deterministic gate)."""
    from ztare.common.paths import REPO_ROOT

    content = (REPO_ROOT / rel_path).read_text(encoding="utf-8")
    excerpt = next((line.strip() for line in content.splitlines() if needle in line), "")
    binding = bind_evidence(rel_path, content, excerpt)
    if binding is None:
        return None
    claim = GovernedElement(f"claim.{cid}", "claim", claim_text)
    evidence = GovernedElement(f"ev.{cid}", "evidence", f"{binding.excerpt}   [{rel_path} @ {binding.content_sha256[:8]}]")
    return claim, evidence, GovernedEdge(evidence.id, "SUPPORTS", claim.id)


def build_governed() -> GovernedState:
    elements: "list[GovernedElement]" = []
    edges: "list[GovernedEdge]" = []
    for rel_path, needle, claim_text, cid in [
        ("src/ztare/scenarios/artifacts.py", "PARAPHRASE DRIFT",
         "The provenance firewall rejects a slot whose text is not verbatim to its governed element.", "firewall"),
        ("src/ztare/scenarios/artifacts.py", 'UNLICENSED RELATION',
         "A relation in a deliverable is rejected unless a governed edge licenses it.", "relations"),
    ]:
        bound = _bound_claim(rel_path, needle, claim_text, cid)
        if bound:
            claim, evidence, edge = bound
            elements += [claim, evidence]
            edges.append(edge)
    return GovernedState(elements, edges)


def main() -> int:
    governed = build_governed()
    if not governed.elements:
        print("demo: could not bind excerpts (source moved?) — nothing to show")
        return 1

    memo = decision_memo(governed)
    print("=" * 78)
    print("1. GOVERNED MEMO — every sentence traces to a verbatim source excerpt")
    print("=" * 78)
    print(render(memo, governed))
    print(f"verdict: {assemble_verdict(governed).status}\n")

    rendered = render(memo, governed)
    forged = rendered.replace("rejects", "silently ignores")   # plausible, well-written, and FALSE
    print("=" * 78)
    print("2. FORGED EDIT — 'rejects' → 'silently ignores' (exactly what a polish-AI would produce)")
    print("=" * 78)
    verdict = reingest_gate(forged, governed)
    if verdict.ok:
        print("re-ingest: GOVERNED (nothing caught) — demo failed to forge\n")
        return 1
    print(f"re-ingest: CAUGHT — {len(verdict.violations)} ungoverned sentence(s), deterministic, no LLM judge:")
    for violation in verdict.violations:
        print(f"   ✗ {violation}")
    print("\nThe governed original is licensed by a hash-bound source line; the forgery is not. Receipts, not vibes.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
