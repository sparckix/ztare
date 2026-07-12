"""Assumption-surfacing (COMPOUNDER, KERNEL). A document → bounded claims to TEST, each ANCHORED to a verbatim
span of the source.

WHAT'S NEW HERE vs the existing evidence compiler: this is a GATE, not an extractor. ZTARE's evidence compiler
(`workspace/compile_evidence.py`) already extracts `candidate_claims_to_test` from sources — but it does so by
TRUSTING THE LLM (no programmatic verbatim check). This module contributes only the piece the compiler lacks:
a DETERMINISTIC span-anchor gate — each candidate claim must carry a `span` that appears VERBATIM in the doc,
or it is dropped, fail-closed. So the PRIMARY intake path composes the compiler's already-extracted claims
(`claims_from_packet`) and gates them; the LLM `proposer` is only the FALLBACK for a raw doc with no compiled
packet. Never re-run the compiler's extraction where a packet exists. Deferred: multi-doc, PDF/table.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


def _norm(text: str) -> str:
    return " ".join((text or "").split())


@dataclass(frozen=True)
class SurfacedClaim:
    """A candidate claim extracted from a document, anchored to a verbatim source span."""
    text: str            # the bounded claim (proposer's phrasing) — a proposal to TEST, not an assertion
    span: str            # the verbatim quote from the doc that motivated it — GATED against the doc
    start: int = -1      # char offset in the doc (advisory)


@dataclass
class SurfaceResult:
    anchored: "list[SurfacedClaim]" = field(default_factory=list)
    rejected: "list[str]" = field(default_factory=list)   # proposals whose span is not verbatim in the doc


def surface_assumptions(doc: str, proposer: "Callable[[str], list[dict[str, Any]]]") -> SurfaceResult:
    """`proposer(doc)` returns `[{text, span}, ...]` candidate claims (the LLM — a plugin). The KERNEL keeps
    only those whose `span` appears VERBATIM (whitespace-normalized) in `doc`, dropping hallucinated anchors.
    Fail-closed: no span, or a span not in the doc ⇒ rejected."""
    doc_norm = _norm(doc)
    result = SurfaceResult()
    for candidate in (proposer(doc) or []):
        text = str(candidate.get("text", "")).strip()
        span = str(candidate.get("span", "")).strip()
        if not text or not span:
            result.rejected.append(f"empty text/span: {(text or span)[:60]}")
            continue
        if _norm(span) in doc_norm:
            result.anchored.append(SurfacedClaim(text=text, span=span, start=doc.find(span)))
        else:
            result.rejected.append(f"UNANCHORED (span not verbatim in doc): {span[:80]}")
    return result


def claims_from_packet(packet: "dict[str, Any]") -> "list[dict[str, str]]":
    """COMPOSE ZTARE's evidence compiler — do NOT re-extract. Reads `candidate_claims_to_test` (which
    `workspace/compile_evidence.py` already produced) into proposer shape, so `surface_assumptions` contributes
    ONLY its deterministic span-anchor gate on top. This is the primary intake when a compiled packet exists;
    `providers.llm_proposer` is the raw-doc fallback. A claim the compiler paraphrased (no verbatim span) is
    correctly gated out — the gate is the value we add, not a second extraction."""
    out: "list[dict[str, str]]" = []
    for candidate in (packet.get("candidate_claims_to_test") or []):
        if not isinstance(candidate, dict):
            continue
        claim = str(candidate.get("claim", "")).strip()
        if not claim:
            continue
        span = str(candidate.get("evidence_quote") or candidate.get("quote")
                   or candidate.get("source_excerpt") or claim).strip()
        out.append({"text": claim, "span": span})
    return out


def _selftest() -> int:
    fails: "list[str]" = []

    def ok(name: str, cond: bool) -> None:
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}")
        if not cond:
            fails.append(name)

    doc = ("The new checkout assumes users have a saved payment method. "
           "We expect a 20% conversion lift. Mobile is out of scope for v1.")

    def proposer(_doc: str) -> "list[dict[str, str]]":
        return [
            {"text": "Users already have a saved payment method", "span": "users have a saved payment method"},
            {"text": "Checkout lifts conversion ~20%", "span": "20% conversion lift"},
            {"text": "This will 10x revenue", "span": "guaranteed 10x revenue"},   # hallucinated anchor
        ]

    res = surface_assumptions(doc, proposer)
    ok("anchored claims are kept (span verbatim in doc)", len(res.anchored) == 2)
    ok("a hallucinated anchor is REJECTED (fail-closed)",
       len(res.rejected) == 1 and any("UNANCHORED" in m for m in res.rejected))
    ok("anchored claim carries its char offset", res.anchored[0].start >= 0)
    ok("empty proposer ⇒ nothing surfaced, no crash", surface_assumptions(doc, lambda _d: []).anchored == [])

    # composing the evidence compiler (NOT re-extracting) + the span-anchor gate on top.
    packet = {"candidate_claims_to_test": [
        {"claim": "Users have a saved payment method", "evidence_quote": "users have a saved payment method"},
        {"claim": "Paraphrased, no verbatim span", "evidence_quote": "this phrase is not in the doc"}]}
    composed = surface_assumptions(doc, lambda _d: claims_from_packet(packet))
    ok("compose compiler claims + gate: verbatim-span kept, paraphrase dropped", len(composed.anchored) == 1)

    print("SURFACING SELFTEST", "PASSED" if not fails else f"FAILED {fails}")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(_selftest())
