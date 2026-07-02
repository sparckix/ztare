"""Draft a project's mandate from a raw document — kills the blank page (Activation lever).

Reads a memo / paper / brief and drafts the four fields the create flow otherwise makes you author from
scratch, grounded in the document:

  task            the single pivotal question the project should answer
  bounded_claim   a tight, falsifiable thesis — one declarative sentence that could be shown false
  next_falsifier  the specific finding that would force you to drop or rewrite the thesis
  non_claims      2-3 scope guards — what the thesis deliberately does NOT assert

One model call, structured output. ADVISORY: the model drafts, you review and edit every field before
creating — nothing is committed here. CLI is master; the workbench pre-fills the create form with this.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

_SYSTEM = (
    "You help a researcher turn a raw document into a TESTABLE research project. Read the document and "
    "draft, grounded strictly in it:\n"
    "- task: the single pivotal question the project should answer (one sentence).\n"
    "- bounded_claim: a tight, falsifiable thesis — one declarative sentence that could be shown false. "
    "Not a topic, not a question: a claim.\n"
    "- next_falsifier: the specific finding that would force the researcher to drop or rewrite the thesis.\n"
    "- non_claims: 2-3 scope guards — things the thesis deliberately does NOT assert.\n"
    "Be concrete and specific to the document; never hedge into generality. Output ONLY a JSON object with "
    "keys task, bounded_claim, next_falsifier, non_claims (non_claims is an array of strings)."
)


def _parse_draft(text: str) -> dict[str, Any]:
    """Extract + normalise the four fields from the model's response (robust to fences / trailing prose)."""
    match = re.search(r"\{.*\}", str(text or ""), re.S)
    data = {}
    if match:
        try:
            data = json.loads(match.group(0))
        except json.JSONDecodeError:
            data = {}
    if not isinstance(data, dict):
        data = {}
    non_claims = data.get("non_claims")
    if isinstance(non_claims, str):
        non_claims = [non_claims]
    if not isinstance(non_claims, list):
        non_claims = []
    task = str(data.get("task", "")).strip()
    bounded_claim = str(data.get("bounded_claim", "")).strip()
    return {
        "ok": bool(task or bounded_claim),
        "task": task,
        "bounded_claim": bounded_claim,
        "next_falsifier": str(data.get("next_falsifier", "")).strip(),
        "non_claims": [str(x).strip() for x in non_claims if str(x).strip()][:5],
    }


def draft_project(doc_text: str, model: str = "") -> dict[str, Any]:
    """Draft the mandate fields from a document via one model call. Returns _parse_draft's shape + model."""
    from ztare.common.llm_runtime import LLMRuntime, pick_default_model_id_for_scripts, resolve_model_id
    from ztare.common.dispatch_model import dispatch_call_text

    chosen = model or pick_default_model_id_for_scripts()
    try:
        chosen = resolve_model_id(chosen)
    except Exception:  # noqa: BLE001 — an unknown label falls through to call_text as-is
        pass
    runtime = LLMRuntime()
    prompt = f"{_SYSTEM}\n\n## Document\n\n{str(doc_text or '')[:12000]}\n\n## Output\nJSON only."
    resp = dispatch_call_text(
        "project_draft",
        prompt,
        llm_response_call=lambda p: runtime.call_text(p, model_id=chosen, max_tokens=1200, request_label="project_draft"),
        timeout_seconds=180,
    )
    text = resp.text if hasattr(resp, "text") else str(resp)
    result = _parse_draft(text)
    result["model"] = chosen
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="ztare project draft",
                                     description="Draft the project mandate (question/thesis/falsifier/non-claims) from a document.")
    parser.add_argument("--doc", required=True, help="Path to the document (memo/paper/brief) to draft from.")
    parser.add_argument("--model", default="", help="Model label (default: the script default).")
    parser.add_argument("--json", action="store_true", help="Emit the drafted fields as JSON (for the workbench).")
    args = parser.parse_args(argv)
    doc = Path(args.doc)
    if not doc.exists():
        payload = {"ok": False, "error": f"document not found: {args.doc}"}
        print(json.dumps(payload) if args.json else payload["error"])
        return 2
    result = draft_project(doc.read_text(encoding="utf-8", errors="replace"), args.model)
    if args.json:
        print(json.dumps(result))
        return 0
    print(f"Task: {result['task']}")
    print(f"Thesis: {result['bounded_claim']}")
    print(f"Falsifier: {result['next_falsifier']}")
    for nc in result["non_claims"]:
        print(f"  not: {nc}")
    return 0


def _selfcheck() -> None:
    good = 'prose... {"task": "Does X cause Y?", "bounded_claim": "X causes Y.", "next_falsifier": "No effect in an RCT.", "non_claims": ["not about Z"]} trailing'
    p = _parse_draft(good)
    assert p["ok"] and p["task"] == "Does X cause Y?" and p["bounded_claim"] == "X causes Y." and p["non_claims"] == ["not about Z"], p
    assert _parse_draft("no json here")["ok"] is False
    assert _parse_draft('{"task":"Q","non_claims":"one guard"}')["non_claims"] == ["one guard"]  # string → list
    print("draft_project selfcheck: OK")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--selfcheck":
        _selfcheck()
    else:
        raise SystemExit(main())
