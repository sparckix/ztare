"""Audience shaping for governed deliverables.

The model may organize, never rewrite: it proposes a title, headings, and a
permutation of governed slot IDs. The deterministic gate requires every slot
exactly once and renders the authoritative wording from the governed state.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Callable

from ztare.scenarios.governed_types import Deliverable, GovernedState, _EDGE_CONNECTIVE
from ztare.scenarios.roundtrip import open_reingest_session


EDITORIAL_DRAFT_SCHEMA = "ztare-editorial-draft-v1"
ALLOWED_HEADINGS = (
    "Decision", "Decision boundary", "Essential claims", "Backing", "Supporting evidence",
    "Constraints", "Vulnerabilities", "Risks and open questions", "Open questions", "Falsifiers",
    "Trade-offs", "Revisit triggers", "Decision tests", "Settlement conditions", "Dependencies",
)


def _prompt(deliverable: Deliverable) -> str:
    slots = [
        {"id": slot.element_id, "current_section": slot.label, "text": slot.text}
        for slot in deliverable.slots
    ]
    return "\n\n".join([
        "You are organizing a checked decision document for its recipient.",
        "Return JSON only: {\"sections\": "
        "[{\"heading\": string, \"mode\": \"body\"|\"appendix\", \"ids\": [string]}]}.",
        "Use every supplied id exactly once. Do not add ids. Do not rewrite, summarize, or quote the text. "
        "Your only editorial choices are a controlled section heading, grouping, reading order, and whether a "
        "section belongs in the main body or the collapsed supporting appendix. Keep the decision and its few "
        "essential reasons in the body; put detailed evidence, provenance, and exhaustive risks in the appendix.",
        f"Recipient: {deliverable.audience or 'Decision reader'}",
        f"Editorial direction: {deliverable.presentation_brief or 'Lead with the decision, then backing and open questions.'}",
        "Allowed section headings (copy one exactly; do not invent a factual heading): " + json.dumps(ALLOWED_HEADINGS),
        "Governed slots JSON:",
        json.dumps(slots, ensure_ascii=False, indent=2),
    ])


def _json_object(raw: str) -> dict:
    text = str(raw or "").strip()
    fence = re.search(r"```(?:json)?\s*(.+?)```", text, re.DOTALL)
    if fence:
        text = fence.group(1).strip()
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end < start:
        raise ValueError("editorial model did not return a JSON object")
    payload = json.loads(text[start:end + 1])
    if not isinstance(payload, dict):
        raise ValueError("editorial plan must be an object")
    return payload


def validate_plan(raw: str, deliverable: Deliverable) -> dict:
    payload = _json_object(raw)
    available = [slot.element_id for slot in deliverable.slots]
    sections = payload.get("sections") if isinstance(payload.get("sections"), list) else []
    clean_sections: list[dict] = []
    ordered: list[str] = []
    for row in sections:
        if not isinstance(row, dict):
            continue
        heading = str(row.get("heading") or "").strip()
        if heading not in ALLOWED_HEADINGS:
            raise ValueError(f"editorial heading must be one of {list(ALLOWED_HEADINGS)}")
        ids = [str(value).strip() for value in row.get("ids", []) if str(value).strip()] \
            if isinstance(row.get("ids"), list) else []
        mode = str(row.get("mode") or "body").strip().lower()
        if mode not in {"body", "appendix"}:
            raise ValueError("editorial section mode must be body or appendix")
        if heading and ids:
            clean_sections.append({"heading": heading[:120], "mode": mode, "ids": ids})
            ordered.extend(ids)
    if not clean_sections:
        raise ValueError("editorial plan has no sections")
    if len(ordered) != len(set(ordered)):
        raise ValueError("editorial plan repeats a governed slot")
    if set(ordered) != set(available) or len(ordered) != len(available):
        missing = sorted(set(available) - set(ordered))
        unknown = sorted(set(ordered) - set(available))
        raise ValueError(f"editorial plan must use every governed slot exactly once; missing={missing[:5]} unknown={unknown[:5]}")
    return {"title": str(deliverable.label or deliverable.name).strip()[:140],
            "sections": clean_sections}


def render_plan(deliverable: Deliverable, governed: GovernedState, plan: dict) -> str:
    slots = {slot.element_id: slot for slot in deliverable.slots}
    lines = [f"# {plan['title'] or deliverable.label or deliverable.name}", ""]
    if deliverable.audience:
        lines += [f"_For: {deliverable.audience}_", ""]
    body_sections = [section for section in plan["sections"] if section.get("mode") != "appendix"]
    appendix_sections = [section for section in plan["sections"] if section.get("mode") == "appendix"]

    def render_sections(sections: list[dict]) -> list[str]:
        rendered: list[str] = []
        for section in sections:
            rendered += [f"## {section['heading']}", ""]
            for element_id in section["ids"]:
                slot = slots[element_id]
                rendered += [slot.text, f"<sub>← governed:{element_id}</sub>", ""]
        return rendered

    lines += render_sections(body_sections)
    if appendix_sections:
        lines += ["<details>", "<summary>Supporting record</summary>", ""]
        lines += render_sections(appendix_sections)
        lines += ["</details>", ""]
    if deliverable.relations:
        lines += ["<details>", "<summary>Evidence trail</summary>", ""]
        for relation in deliverable.relations:
            src, dst = governed.by_id(relation.src_id), governed.by_id(relation.dst_id)
            connective = _EDGE_CONNECTIVE.get(relation.kind, relation.kind)
            lines += [
                f"- {src.text if src else relation.src_id} **{connective}** {dst.text if dst else relation.dst_id} "
                f"<sub>← governed-edge:{relation.src_id}-{relation.kind}-{relation.dst_id}</sub>"
            ]
        lines += ["", "</details>", ""]
    return "\n".join(lines) + "\n"


def create_editorial_draft(deliverable: Deliverable, governed: GovernedState, *,
                           call: Callable[[str], str], out_path: Path) -> dict:
    raw = call(_prompt(deliverable))
    plan = validate_plan(raw, deliverable)
    text = render_plan(deliverable, governed, plan)
    session = open_reingest_session("", text, governed)
    if not session.promotable:
        raise ValueError(f"editorial rendering lost provenance: {session.diff.ungoverned[:3]}")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(text, encoding="utf-8")
    receipt = {
        "schema": EDITORIAL_DRAFT_SCHEMA,
        "source_deliverable": deliverable.name,
        "base_hash": session.base_hash,
        "traced_claims": session.diff.traced_claims,
        "dropped_claims": session.diff.dropped_claims,
        "presentation_brief_sha256": hashlib.sha256(
            str(deliverable.presentation_brief or "").encode("utf-8")
        ).hexdigest(),
        "plan": plan,
    }
    receipt_path = out_path.with_suffix(".editorial.json")
    receipt_path.write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return {"ok": True, "path": str(out_path), "receipt_path": str(receipt_path),
            "base_hash": session.base_hash, "traced_claims": session.diff.traced_claims,
            "dropped_claims": session.diff.dropped_claims}


def _selftest() -> int:
    from tempfile import TemporaryDirectory
    from ztare.scenarios.governed_types import GovernedElement, Slot

    governed = GovernedState(elements=[
        GovernedElement("t", "thesis", "Use the staged rollout."),
        GovernedElement("e", "evidence", "The pilot reduced failures by 20%."),
    ])
    deliverable = Deliverable("brief", slots=[
        Slot("Decision", "t", governed.by_id("t").text),
        Slot("Backing", "e", governed.by_id("e").text),
    ], audience="Leadership", presentation_brief="Lead with the decision.")
    raw = '{"sections":[{"heading":"Decision","mode":"body","ids":["t"]},{"heading":"Supporting evidence","mode":"appendix","ids":["e"]}]}'
    with TemporaryDirectory() as tmp:
        result = create_editorial_draft(deliverable, governed, call=lambda _prompt: raw,
                                        out_path=Path(tmp) / "brief.editorial-draft.md")
        assert result["ok"] and Path(result["path"]).is_file()
        assert open_reingest_session("", Path(result["path"]).read_text(), governed).promotable
    try:
        validate_plan('{"sections":[{"heading":"Call","ids":["t"]}]}', deliverable)
    except ValueError:
        pass
    else:
        raise AssertionError("a plan that drops a governed slot must fail")
    print("EDITORIAL SELFTEST PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(_selftest())
