"""Live assumption-proposer (PLUGIN, boundary — the intake funnel). Extracts candidate claims + their verbatim
source spans from a document via an LLM, so nobody hand-authors a claim graph — you paste a doc.

Moat-preserving by construction: the LLM is a PROPOSER, never trusted. `surface_assumptions` (kernel) gates
every returned span against the doc and drops hallucinated anchors, so a fabricated claim can't enter. The LLM
call is INJECTED (`call=`) — swappable between ZTARE's own runtime and a cognitive-firm MCP adapter at the
boundary; the kernel takes no hard live dependency and functions without any of this.
"""
from __future__ import annotations

import json
import re
from typing import Any, Callable, Optional

_EXTRACTION_PROMPT = (
    "You extract the ASSUMPTIONS a document makes — the load-bearing claims it takes for granted.\n"
    "For each, return an object with:\n"
    '  "text": the assumption as a bounded, testable claim (your phrasing), and\n'
    '  "span": a VERBATIM quote from the document (copy exact characters) that the assumption rests on.\n'
    "Return ONLY a JSON array of such objects. The span MUST be copied verbatim from the document — do not "
    "paraphrase it; a span that is not verbatim will be discarded.\n\nDOCUMENT:\n{doc}\n"
)


def _parse_candidates(raw: str) -> "list[dict[str, str]]":
    """Tolerant parse of the LLM's JSON array (strips code fences / prose around it). A malformed reply yields
    [] — the kernel then surfaces nothing, never a crash and never an ungated guess."""
    text = str(raw or "").strip()
    fence = re.search(r"```(?:json)?\s*(.+?)```", text, re.DOTALL)
    if fence:
        text = fence.group(1).strip()
    start, end = text.find("["), text.rfind("]")
    if start == -1 or end == -1 or end < start:
        return []
    try:
        data = json.loads(text[start:end + 1])
    except Exception:  # noqa: BLE001 — a malformed proposal is dropped, not guessed at
        return []
    out: "list[dict[str, str]]" = []
    for item in data if isinstance(data, list) else []:
        if isinstance(item, dict) and str(item.get("text", "")).strip() and str(item.get("span", "")).strip():
            out.append({"text": str(item["text"]).strip(), "span": str(item["span"]).strip()})
    return out


def _ztare_runtime_call(model: str) -> "Callable[[str], str]":
    """Default LLM call via ZTARE's own runtime (lazy import so importing this module is free and the kernel
    keeps no hard dependency). Short timeout + no retries/fallback: this is a UI-facing intake call, so a
    dead/slow model should fail fast (the caller degrades to map-only), not hang. Swap for a cognitive-firm MCP
    adapter by passing `call=` instead."""
    def _call(prompt: str) -> str:
        from ztare.common.llm_runtime import LLMRuntime, pick_model_for_tier, resolve_model_id
        model_id = resolve_model_id(model) if model else pick_model_for_tier("cheap")
        if not model_id:
            raise RuntimeError("no model available (set --model or configure a provider key)")
        resp = LLMRuntime().call_text(prompt, model_id=model_id, timeout_seconds=60,
                                      retries=0, fallback_model_ids=())
        return str(getattr(resp, "text", "") or "")
    return _call


def llm_proposer(doc: str, *, model: str = "", call: "Optional[Callable[[str], str]]" = None) -> "list[dict[str, Any]]":
    """Return `[{text, span}, ...]` candidate assumptions for `doc`. `call(prompt)->str` is the LLM (injected
    for tests / for a cognitive-firm MCP adapter); defaults to ZTARE's runtime. This is the PROPOSER — pass it
    to `surfacing.surface_assumptions(doc, proposer)`, which gates each span against the doc (fail-closed)."""
    llm = call if call is not None else _ztare_runtime_call(model)
    return _parse_candidates(llm(_EXTRACTION_PROMPT.format(doc=doc)))


def _selftest() -> int:
    from ztare.scenarios.surfacing import surface_assumptions

    fails: "list[str]" = []

    def ok(name: str, cond: bool) -> None:
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}")
        if not cond:
            fails.append(name)

    doc = "The rollout assumes every user has a saved card. We expect a 20% lift."

    # a stubbed LLM (injected `call`) — one good candidate, one with a hallucinated span, wrapped in a fence.
    def stub_call(_prompt: str) -> str:
        return ('```json\n[{"text":"Every user has a saved card","span":"every user has a saved card"},'
                '{"text":"Guaranteed 10x","span":"guaranteed 10x revenue"}]\n```')

    proposed = llm_proposer(doc, call=stub_call)
    ok("proposer parses fenced JSON into candidates", len(proposed) == 2)
    gated = surface_assumptions(doc, lambda _d: proposed)
    ok("kernel gate keeps the anchored claim, drops the hallucinated span",
       len(gated.anchored) == 1 and len(gated.rejected) == 1)
    ok("malformed LLM reply → no candidates, no crash", llm_proposer(doc, call=lambda _p: "sorry, no.") == [])

    print("LLM-PROPOSER SELFTEST", "PASSED" if not fails else f"FAILED {fails}")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(_selftest())
