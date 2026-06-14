"""BRIDGE-1 — Substrate-recommender.

Spec: research_areas/private/specs/active/engine/GP-213_BRIDGE1_substrate_recommender_spec.md

Operator-confirmed only in v0. No auto-launch. Outputs a markdown
recommendation file dropped into ztare_workspace/inbox/substrate_recommendations/.

Two modes:

  cold      — no constraints; propose top-N candidate next substrates from
              the corpus. Useful for "what should I work on next?" runs.

  branch    — input is a named branch grid (JSON file); recommend one
              substrate per branch. Useful for routing across a known
              falsification grid (e.g. NS Track B's seven branches).

The cross-LLM audit (GP-149 §10) found classifier labels disagree at 0.42
three-way. v0 therefore disables auto-classification of substrate class;
predicted class is shown with an explicit confidence band and the audit
verdict is disclosed in every recommendation footer.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import textwrap
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_TRACK_RECORD = REPO_ROOT / "research_areas" / "EXPERIMENT_TRACK_RECORD.md"
DEFAULT_INSIGHTS = REPO_ROOT / "research_areas" / "private" / "insights_ledger.md"
DEFAULT_ARCHIVE = REPO_ROOT / "analytics" / "trajectory_archive_enriched.jsonl"
DEFAULT_INBOX = REPO_ROOT / "ztare_workspace" / "inbox" / "substrate_recommendations"
DEFAULT_BRANCH_GRID_DIR = REPO_ROOT / "src" / "ztare" / "research_director" / "branch_grids"
DEFAULT_MODEL = "gemini-2.5-flash"

CROSS_LLM_DISCLOSURE = (
    "Cross-LLM agreement on classifier labels (May 4 2026 audit, GP-149 §10): "
    "42% three-way (verdict band: FAILS_cross_llm_validation < 0.60). The "
    "predicted_class field below is operator-supplied or shown as a hedge; "
    "auto-routing on classifier labels is deferred until cross-LLM stability "
    "lifts above 0.60."
)


# ---------- input gathering ------------------------------------------------ #


def existing_substrate_names(track_record_path: Path, archive_path: Path) -> set[str]:
    names: set[str] = set()
    if track_record_path.exists():
        text = track_record_path.read_text()
        # E-row tags include the substrate slug after `E-GPxxx-`. Pull all
        # tokens that look like a substrate slug (gpNNN_..., ns_..., ztare_...).
        for m in re.finditer(r"`(gp\d+_[a-z0-9_]+|ns_[a-z0-9_]+|ztare_[a-z0-9_]+|sandbox_[a-z0-9_]+|monotone_[a-z0-9_]+|seattle_[a-z0-9_]+|riemann_[a-z0-9_]+|stieltjes_[a-z0-9_]+|oeis_[a-z0-9_]+|central_[a-z0-9_]+)`", text):
            names.add(m.group(1))
    if archive_path.exists():
        with archive_path.open() as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    proj = json.loads(line).get("project")
                except Exception:
                    continue
                if proj:
                    names.add(proj)
    return names


def load_track_record_tail(path: Path, n_chars: int = 30000) -> str:
    if not path.exists():
        return ""
    text = path.read_text()
    return text[-n_chars:]


def load_insights_tail(path: Path, n_chars: int = 30000) -> str:
    if not path.exists():
        return ""
    text = path.read_text()
    return text[-n_chars:]


def load_branch_grid(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


# ---------- prompts ------------------------------------------------------- #


def cold_prompt(
    n_candidates: int,
    track_record_tail: str,
    insights_tail: str,
    operator_class: str | None,
    operator_substrate_class: str | None,
    existing_names: set[str],
) -> str:
    class_clause = (
        f"OPERATOR-SUPPLIED CLASS (treat as ground truth): {operator_class}\n"
        if operator_class
        else "No operator class supplied; hedge across the top-N classes you observe in the track record.\n"
    )
    substrate_clause = (
        f"OPERATOR-SUPPLIED SUBSTRATE CLASS HINT: {operator_substrate_class}\n"
        if operator_substrate_class
        else ""
    )
    return f"""You are BRIDGE-1, a substrate-recommender for the ZTARE adversarial-verification engine.

Your job: propose {n_candidates} candidate next substrates for the operator. Each must cite specific findings from the artifacts below and propose a charter sketch a human could lift directly into a project.

{class_clause}{substrate_clause}

EXISTING SUBSTRATE NAMES (do not reuse, even with a renaming wrapper):
{sorted(existing_names)}

EXPERIMENT TRACK RECORD (tail; most recent rows are most relevant):
---
{track_record_tail}
---

INSIGHTS LEDGER (tail):
---
{insights_tail}
---

Output strict JSON, no markdown fences, no prose outside the object:

{{
  "candidates": [
    {{
      "name": "<short slug, snake_case, must NOT match any existing name above>",
      "predicted_class": "<class name from the track record OR 'unknown'>",
      "confidence": "<high|medium|low>",
      "mining_basis": "<one line: what N from how many projects supports this; or 'novel' if no mining hits>",
      "rationale": "<1 paragraph; MUST cite at least 2 specific findings by F-row id (e.g. F-GP186-NS-PHASE5CH-01) or by insights_ledger section heading. Do not cite by vocabulary — cite by id.>",
      "charter_sketch": "<300-word charter sketch with target, falsification criterion, gate package>",
      "what_changes_if_succeeds": "<1 paragraph; min 100 chars; describes the structural question this substrate would answer>"
    }}
  ]
}}

Output the JSON now.
"""


def branch_prompt(
    grid: dict[str, Any],
    track_record_tail: str,
    insights_tail: str,
    existing_names: set[str],
) -> str:
    branches_block = "\n".join(
        f"- branch_id: {b['id']}\n  name: {b['name']}\n  obligation: {b['obligation']}\n  evidence_anchors: {b.get('evidence_anchors', [])}"
        for b in grid["branches"]
    )
    lean_targets = "\n".join(f"- {p}" for p in grid.get("lean_targets", []))
    return f"""You are BRIDGE-1, a substrate-recommender for the ZTARE adversarial-verification engine.

You are operating in BRANCH-ROUTED mode. The operator has supplied a named falsification grid; you must propose ONE substrate per branch.

GRID NAME: {grid['name']}
GRID DESCRIPTION: {grid['description']}
GRID SOURCE: {grid.get('source', '(unspecified)')}

LEAN TARGETS ALREADY IN PLACE:
{lean_targets}

BRANCHES (one substrate per branch; same order in your output):
{branches_block}

EXISTING SUBSTRATE NAMES (do not reuse, even with a renaming wrapper):
{sorted(existing_names)}

EXPERIMENT TRACK RECORD (tail):
---
{track_record_tail}
---

INSIGHTS LEDGER (tail):
---
{insights_tail}
---

Per the parent spec, each branch substrate MUST:

1. Have a name that does not collide with existing substrate names.
2. Have a falsification criterion that is one of: (a) close the branch's Lean obligation, OR (b) construct a deterministic Python audit that exhibits the analytic failure inside the branch.
3. Cite the branch obligation by branch_id AND cite at least one F-row from the track record OR one section of the insights ledger.
4. State explicitly what would change if the substrate succeeds (close vs falsify the branch).
5. Charter sketch must include a gate package — at least one deterministic test (PSD, finite-prefix, certificate-pass) and at least one Lean target.

Output strict JSON, no markdown fences, no prose outside the object:

{{
  "grid_name": "{grid['name']}",
  "candidates": [
    {{
      "branch_id": "<from grid; one entry per branch, same order>",
      "name": "<snake_case substrate slug>",
      "predicted_class": "formal_proof_lean | qualitative_thesis_governance | numerical_obstruction_audit | structural_diagnostic | quantitative_law_discovery | cross_domain_methodology",
      "confidence": "<high|medium|low>",
      "rationale": "<1 paragraph citing branch_id, plus at least one F-row id or insights_ledger section>",
      "falsification_criterion": "<one of: 'lean_target_close: <obligation>' | 'python_audit_falsify: <obligation>' | 'both'>",
      "charter_sketch": "<300-word charter; must include declared Leray observable, the gate package (deterministic + Lean), iteration cap (recommend 8), and the precise success/failure criterion>",
      "what_changes_if_succeeds": "<1 paragraph, min 100 chars>",
      "anti_tautology_check": {{
        "no_name_reuse": true,
        "branch_id_cited": true,
        "fixes_one_obligation_only": true
      }}
    }}
  ]
}}

Output the JSON now.
"""


# ---------- LLM call ------------------------------------------------------- #


def _call_gemini_api(prompt: str, model: str = DEFAULT_MODEL) -> str:
    import google.generativeai as genai  # type: ignore

    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY (or GOOGLE_API_KEY) must be set to call Gemini.")
    genai.configure(api_key=api_key)
    m = genai.GenerativeModel(
        model,
        generation_config={
            "temperature": 0.4,
            "response_mime_type": "application/json",
        },
    )
    res = m.generate_content(prompt)
    return res.text


def call_recommender_model(prompt: str, model: str = DEFAULT_MODEL) -> str:
    from src.ztare.common.dispatch_model import dispatch_call_text

    response = dispatch_call_text(
        "substrate_recommender",
        prompt,
        llm_response_call=lambda p: _call_gemini_api(p, model=model),
        timeout_seconds=int(os.environ.get("ZTARE_AUTORESEARCH_AGENT_TIMEOUT_SECONDS", "300")),
    )
    return response.text


# ---------- Literature-transfer integration: G5 stall extraction + matcher pairing ----- #
#
# Per the panel-reviewed contract additions (GP-215 second-pass section), the
# stall description fed to the matcher must come ONLY from a candidate's
# falsification_criterion + cited F-rows — not from charter prose, not from
# predicted_class. This prevents the matcher from optimizing its retrieval
# against text the LLM wrote freely about the substrate's intent.


_F_ROW_PATTERN = re.compile(r"\b(F-GP\d+(?:-[A-Z0-9]+)*(?:-\d+)?)\b")
_INS_PATTERN = re.compile(r"\b(INS-\d+)\b")
_PHASE_PATTERN = re.compile(r"\bPhase\s?5[A-Z]+\b", re.IGNORECASE)


def g5_stall_from_proposal(candidate: dict[str, Any]) -> tuple[str, list[str]]:
    """G5 — extract a stall description from a BRIDGE-1 candidate using ONLY
    the falsification_criterion and the F-row / INS-id / Phase citations
    embedded in the rationale. Charter prose, predicted_class, and
    what_changes_if_succeeds are excluded.

    Returns (stall_text, cited_anchors)."""
    falsif = (candidate.get("falsification_criterion") or "").strip()
    rationale = candidate.get("rationale") or ""
    f_rows = _F_ROW_PATTERN.findall(rationale)
    ins_ids = _INS_PATTERN.findall(rationale)
    phases = [m.group(0) for m in _PHASE_PATTERN.finditer(rationale)]
    anchors = sorted(set(f_rows + ins_ids + phases))
    pieces = [f"Open obligation: {falsif}." if falsif else ""]
    if anchors:
        pieces.append(f"Cited prior findings: {', '.join(anchors)}.")
    pieces.append(
        "The current arc is stalled at this obligation; the question is what shape "
        "of work would close it."
    )
    return " ".join(p for p in pieces if p), anchors


def attach_meta_arc_recommendations(
    payload: dict[str, Any],
    *,
    catalog_substrate: str = "all",
    top_k: int = 3,
) -> dict[str, Any]:
    """Run the matcher against each candidate's G5-extracted stall and attach
    a `meta_arc_recommendation` block to each candidate. Catches matcher
    failures inline (matcher is advisory; per-candidate failure should not
    kill the whole BRIDGE-1 run)."""
    from ztare.research_director.meta_arc_matcher import (
        load_catalog,
        match_stall,
    )

    moves = load_catalog(catalog_substrate)
    cands = payload.get("candidates", [])
    for c in cands:
        stall_text, anchors = g5_stall_from_proposal(c)
        if not stall_text:
            c["meta_arc_recommendation"] = {
                "skipped": True,
                "reason": "no falsification_criterion or cited anchors; G5 cannot extract stall",
            }
            continue
        try:
            result = match_stall(
                stall_text,
                moves=moves,
                substrate=catalog_substrate,
                top_k=top_k,
            )
            result["g5_stall_text"] = stall_text
            result["g5_cited_anchors"] = anchors
            result["advisory_only"] = True
            c["meta_arc_recommendation"] = result
        except Exception as e:
            c["meta_arc_recommendation"] = {
                "error": f"matcher failed: {e}",
                "advisory_only": True,
            }
    return payload


# ---------- validators ---------------------------------------------------- #


def _validate_meta_arc(c: dict[str, Any], prefix: str) -> list[str]:
    """V6 + V8 validators on the matcher block when present.

    V6 — proof_object_delta path-existence: the top-1 match's `object_created`
         field references a real artifact in the repo (Lean file, gate file,
         audit doc), or the field is honestly empty. Hallucinated paths
         caught here.
    V8 — stall-anchor existence: g5_cited_anchors must be non-empty AND must
         match the rationale's anchors (G5 must have extracted, not invented).
    """
    errs: list[str] = []
    rec = c.get("meta_arc_recommendation")
    if not rec or not isinstance(rec, dict):
        return errs  # matcher is advisory; absence is allowed
    if rec.get("skipped") or rec.get("error"):
        return errs

    # V8 — stall anchors non-empty (we extracted from rationale's F-row/INS/Phase)
    anchors = rec.get("g5_cited_anchors") or []
    if not anchors:
        rationale = c.get("rationale", "")
        if (
            re.search(r"\bF-GP\d+", rationale)
            or re.search(r"\bINS-\d+", rationale)
            or re.search(r"\bPhase\s?5", rationale, re.IGNORECASE)
        ):
            errs.append(
                f"{prefix}: V8 — g5_cited_anchors empty but rationale contains F-row/INS/Phase markers; G5 extractor failed"
            )

    # V6 — top-1 object_created should be inspectable. We don't enforce the path exists
    # in the live repo (paths in catalog entries are historical), but we do require
    # the field to be non-empty and reference a recognizable artifact shape.
    ranked = rec.get("ranked", [])
    if ranked:
        top1 = ranked[0]
        obj = top1.get("object_created", "")
        if not obj or len(obj) < 8:
            errs.append(f"{prefix}: V6 — top-1 object_created field empty or trivially short")
    return errs


def validate_cold(payload: dict[str, Any], existing_names: set[str]) -> list[str]:
    errs: list[str] = []
    cands = payload.get("candidates", [])
    if not isinstance(cands, list) or not cands:
        return ["payload.candidates is missing or empty"]
    seen: set[str] = set()
    for i, c in enumerate(cands):
        prefix = f"candidate[{i}]"
        nm = c.get("name", "")
        if not nm:
            errs.append(f"{prefix}: missing name")
            continue
        if nm in existing_names:
            errs.append(f"{prefix}: name '{nm}' collides with existing substrate")
        if nm in seen:
            errs.append(f"{prefix}: name '{nm}' repeated within candidate set")
        seen.add(nm)
        rat = c.get("rationale", "")
        if len(rat) < 50:
            errs.append(f"{prefix}: rationale shorter than 50 chars")
        if not (re.search(r"\bF-GP\d+", rat) or re.search(r"\bINS-\d+", rat) or re.search(r"###", rat)):
            errs.append(f"{prefix}: rationale lacks F-row/INS-id/heading citation")
        wc = c.get("what_changes_if_succeeds", "")
        if len(wc) < 100:
            errs.append(f"{prefix}: what_changes_if_succeeds shorter than 100 chars")
        ch = c.get("charter_sketch", "")
        if len(ch) < 200:
            errs.append(f"{prefix}: charter_sketch shorter than 200 chars")
        errs.extend(_validate_meta_arc(c, prefix))
    return errs


def validate_branch(payload: dict[str, Any], grid: dict[str, Any], existing_names: set[str]) -> list[str]:
    errs: list[str] = []
    cands = payload.get("candidates", [])
    if not isinstance(cands, list):
        return ["payload.candidates is not a list"]
    expected_ids = [b["id"] for b in grid["branches"]]
    got_ids = [c.get("branch_id") for c in cands]
    if got_ids != expected_ids:
        errs.append(f"branch_id sequence mismatch: expected {expected_ids}, got {got_ids}")
    seen: set[str] = set()
    for i, c in enumerate(cands):
        prefix = f"candidate[{i}] (branch={c.get('branch_id')})"
        nm = c.get("name", "")
        if not nm:
            errs.append(f"{prefix}: missing name")
            continue
        if nm in existing_names:
            errs.append(f"{prefix}: name '{nm}' collides with existing substrate")
        if nm in seen:
            errs.append(f"{prefix}: name '{nm}' repeated within candidate set")
        seen.add(nm)
        rat = c.get("rationale", "")
        bid = c.get("branch_id", "")
        if bid and bid not in rat:
            errs.append(f"{prefix}: rationale does not cite branch_id '{bid}'")
        if not (re.search(r"\bF-GP\d+", rat) or re.search(r"\bINS-\d+", rat) or re.search(r"Phase\s?5\w+", rat)):
            errs.append(f"{prefix}: rationale lacks F-row/INS-id/Phase-citation")
        ch = c.get("charter_sketch", "")
        if len(ch) < 200:
            errs.append(f"{prefix}: charter_sketch shorter than 200 chars")
        wc = c.get("what_changes_if_succeeds", "")
        if len(wc) < 100:
            errs.append(f"{prefix}: what_changes_if_succeeds shorter than 100 chars")
        if "lean_target_close" not in str(c.get("falsification_criterion", "")) and "python_audit_falsify" not in str(c.get("falsification_criterion", "")):
            errs.append(f"{prefix}: falsification_criterion not in expected shape")
        errs.extend(_validate_meta_arc(c, prefix))
    return errs


# ---------- rendering ----------------------------------------------------- #


def _render_meta_arc_block(c: dict[str, Any]) -> list[str]:
    """Operator-facing markdown for the matcher block. G1 — ordinal rank
    only, no cosines. G4 — adversary surfaced inline. Catalog-limits
    disclosure baked into the footer."""
    rec = c.get("meta_arc_recommendation")
    if not rec or not isinstance(rec, dict):
        return []
    out: list[str] = []
    out.append("**Meta-arc lens (advisory; predicted_class wins for routing):**")
    out.append("")
    if rec.get("skipped"):
        out.append(f"- Matcher skipped — {rec.get('reason','no reason given')}")
        return out
    if "error" in rec:
        out.append(f"- Matcher failed — {rec['error']}")
        return out
    if rec.get("saturation_flag"):
        out.append("- ⚠ **Catalog saturated for this candidate's stall** — matcher refuses to recommend; the move-class your stall most resembles is the dominant move-class. Consider this signal as 'don't do more of the modal move'; the closing move likely belongs to a class with no in-distribution exemplar.")
        out.append(f"- {rec.get('saturation_reason', '')}")
        # surface non-modal seeds as inspiration
        modal_id = rec.get("modal_cluster")
        rare = [r for r in rec.get("ranked", []) if r.get("cluster_id") != modal_id]
        if rare:
            out.append("- Structurally-rare seeds (inspiration only):")
            for r in rare[:3]:
                out.append(f"  - top-{r['rank']} `{r['source_substrate']}/{r['source_cycle']}` **{r['move_name']}** — {r['object_created'][:80]}")
        return out
    ranked = rec.get("ranked", [])
    if ranked:
        out.append("- Top matches (ordinal rank only — cosines in JSON, not here per panel clause G1):")
        for r in ranked[:3]:
            out.append(f"  - top-{r['rank']} `{r['source_substrate']}/{r['source_cycle']}` **{r['move_name']}** — {r['object_created'][:80]}")
    adv = rec.get("adversary_move") or {}
    if "move_id" in adv:
        out.append(f"- **Adversary** (different substrate AND cluster, panel clause G4): `{adv['source_substrate']}/{adv['source_cycle']}` **{adv['move_name']}** — {adv['object_created'][:80]}")
    elif "reason" in adv:
        out.append(f"- ⚠ {adv['reason']}")
    anchors = rec.get("g5_cited_anchors") or []
    if anchors:
        out.append(f"- Stall anchored on: {', '.join(anchors[:6])}")
    return out


def _catalog_disclosure() -> str:
    return (
        "Catalog: NS Track B (22 cycles, 4 sub-clusters of cluster_6 + 5 singletons) + "
        "AQUAL gp163d (9 cycles) + Neural gp140 (9 cycles) = 40 cycles. "
        "**NS-heavy; cross-substrate transfer evidence is partial.** "
        "Treat matcher recommendations as advisory annotations on BRIDGE-1's rationale; "
        "do not promote a substrate solely because the matcher endorses it."
    )


def render_cold(payload: dict[str, Any], timestamp: str, model: str, validation_errors: list[str]) -> str:
    lines: list[str] = []
    lines.append(f"# Substrate recommendation — cold mode — {timestamp}")
    lines.append("")
    if validation_errors:
        lines.append("## ⚠ Anti-tautology validation errors")
        lines.append("")
        for e in validation_errors:
            lines.append(f"- {e}")
        lines.append("")
        lines.append("**Operator must address these before promoting any candidate.**")
        lines.append("")
    lines.append("## Top candidates")
    lines.append("")
    for i, c in enumerate(payload.get("candidates", []), 1):
        lines.append(f"### Candidate {i}: `{c.get('name', '?')}`")
        lines.append("")
        lines.append(f"- **Predicted class:** {c.get('predicted_class', 'unknown')}  ")
        lines.append(f"- **Confidence:** {c.get('confidence', 'unknown')}  ")
        lines.append(f"- **Mining basis:** {c.get('mining_basis', '—')}")
        lines.append("")
        lines.append("**Rationale:**")
        lines.append("")
        lines.append(c.get("rationale", ""))
        lines.append("")
        lines.append("**Charter sketch:**")
        lines.append("")
        lines.append(c.get("charter_sketch", ""))
        lines.append("")
        lines.append("**What changes if it succeeds:**")
        lines.append("")
        lines.append(c.get("what_changes_if_succeeds", ""))
        lines.append("")
        meta_block = _render_meta_arc_block(c)
        if meta_block:
            lines.extend(meta_block)
            lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("**Recommender metadata**")
    lines.append("")
    lines.append(f"- Run timestamp: `{timestamp}`")
    lines.append(f"- LLM model: `{model}`")
    lines.append(f"- {CROSS_LLM_DISCLOSURE}")
    lines.append(f"- {_catalog_disclosure()}")
    return "\n".join(lines)


def render_branch(payload: dict[str, Any], grid: dict[str, Any], timestamp: str, model: str, validation_errors: list[str]) -> str:
    lines: list[str] = []
    lines.append(f"# Substrate recommendation — branch mode — {timestamp}")
    lines.append("")
    lines.append(f"**Grid:** `{grid['name']}`  ")
    lines.append(f"**Source:** `{grid.get('source', '—')}`  ")
    lines.append(f"**Description:** {grid['description']}")
    lines.append("")
    if validation_errors:
        lines.append("## ⚠ Anti-tautology validation errors")
        lines.append("")
        for e in validation_errors:
            lines.append(f"- {e}")
        lines.append("")
        lines.append("**Operator must address these before promoting any candidate.**")
        lines.append("")
    lines.append("## Per-branch candidates")
    lines.append("")
    for i, c in enumerate(payload.get("candidates", []), 1):
        bid = c.get("branch_id", "?")
        lines.append(f"### Branch {i}: `{bid}` → `{c.get('name', '?')}`")
        lines.append("")
        lines.append(f"- **Predicted class:** {c.get('predicted_class', 'unknown')}  ")
        lines.append(f"- **Confidence:** {c.get('confidence', 'unknown')}  ")
        lines.append(f"- **Falsification criterion:** {c.get('falsification_criterion', '—')}")
        lines.append("")
        lines.append("**Rationale:**")
        lines.append("")
        lines.append(c.get("rationale", ""))
        lines.append("")
        lines.append("**Charter sketch:**")
        lines.append("")
        lines.append(c.get("charter_sketch", ""))
        lines.append("")
        lines.append("**What changes if it succeeds:**")
        lines.append("")
        lines.append(c.get("what_changes_if_succeeds", ""))
        lines.append("")
        meta_block = _render_meta_arc_block(c)
        if meta_block:
            lines.extend(meta_block)
            lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("**Recommender metadata**")
    lines.append("")
    lines.append(f"- Run timestamp: `{timestamp}`")
    lines.append(f"- LLM model: `{model}`")
    lines.append(f"- Grid: `{grid['name']}`  ({len(grid['branches'])} branches)")
    lines.append(f"- {CROSS_LLM_DISCLOSURE}")
    lines.append(f"- {_catalog_disclosure()}")
    return "\n".join(lines)


# ---------- entry --------------------------------------------------------- #


def run(
    *,
    mode: str,
    n_candidates: int,
    operator_class: str | None,
    operator_substrate_class: str | None,
    branch_grid_path: Path | None,
    track_record_path: Path,
    insights_path: Path,
    archive_path: Path,
    inbox_path: Path,
    model: str,
    prompt_only: bool,
    skip_llm: bool,
    raw_payload: Path | None,
) -> tuple[str, Path | None]:
    existing = existing_substrate_names(track_record_path, archive_path)
    track_tail = load_track_record_tail(track_record_path)
    insights_tail = load_insights_tail(insights_path)

    if mode == "cold":
        prompt = cold_prompt(
            n_candidates=n_candidates,
            track_record_tail=track_tail,
            insights_tail=insights_tail,
            operator_class=operator_class,
            operator_substrate_class=operator_substrate_class,
            existing_names=existing,
        )
        grid = None
    elif mode == "branch":
        if not branch_grid_path:
            raise SystemExit("branch mode requires --branch-grid")
        grid = load_branch_grid(branch_grid_path)
        prompt = branch_prompt(grid, track_tail, insights_tail, existing)
    else:
        raise SystemExit(f"unknown mode: {mode}")

    if prompt_only:
        return prompt, None

    if raw_payload is not None:
        text = raw_payload.read_text()
    elif skip_llm:
        # write the prompt next to the inbox for operator manual run
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        inbox_path.mkdir(parents=True, exist_ok=True)
        out = inbox_path / f"{timestamp}_{mode}_PROMPT.md"
        out.write_text("# Recommender prompt (operator runs this manually)\n\n" + prompt)
        return prompt, out
    else:
        text = call_recommender_model(prompt, model=model)

    payload = json.loads(text)

    # Literature-transfer integration: attach meta-arc recommendations to each candidate.
    # Advisory only — predicted_class still wins for routing; the matcher's
    # role is to surface adversary moves and stall-anchor matches at the
    # operator decision moment.
    if not skip_llm:
        try:
            payload = attach_meta_arc_recommendations(payload, catalog_substrate="all", top_k=3)
        except Exception as e:
            print(f"[meta-arc] attach failed (non-fatal): {e}")

    if mode == "cold":
        errors = validate_cold(payload, existing)
        md = render_cold(payload, datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"), model, errors)
    else:
        errors = validate_branch(payload, grid, existing)  # type: ignore[arg-type]
        md = render_branch(payload, grid, datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"), model, errors)  # type: ignore[arg-type]

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    inbox_path.mkdir(parents=True, exist_ok=True)
    label = mode if mode != "branch" else f"branch_{(grid or {}).get('name', 'unknown')}"
    out = inbox_path / f"{timestamp}_{label}.md"
    out.write_text(md)
    # also persist the raw JSON next to it for replay
    out_json = out.with_suffix(".json")
    out_json.write_text(json.dumps(payload, indent=2))
    return md, out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="ztare.research_director.substrate_recommender")
    parser.add_argument("--mode", choices=["cold", "branch"], default="cold")
    parser.add_argument("--n", type=int, default=3, dest="n_candidates")
    parser.add_argument("--class", dest="operator_class", default=None)
    parser.add_argument("--substrate-class", dest="operator_substrate_class", default=None)
    parser.add_argument("--branch-grid", type=Path, default=None)
    parser.add_argument("--track-record", type=Path, default=DEFAULT_TRACK_RECORD)
    parser.add_argument("--insights", type=Path, default=DEFAULT_INSIGHTS)
    parser.add_argument("--archive", type=Path, default=DEFAULT_ARCHIVE)
    parser.add_argument("--inbox", type=Path, default=DEFAULT_INBOX)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--prompt-only", action="store_true", help="emit prompt to stdout and exit (no LLM call)")
    parser.add_argument("--skip-llm", action="store_true", help="write prompt to inbox for operator manual LLM run")
    parser.add_argument("--raw-payload", type=Path, default=None, help="JSON file with a precomputed payload to render (skips LLM call)")
    args = parser.parse_args(argv)

    if args.mode == "branch" and args.branch_grid is None:
        # convenience default: current NS Track B paraproduct grid
        args.branch_grid = DEFAULT_BRANCH_GRID_DIR / "ns_track_b_paraproduct_2026-05-04.json"

    md, path = run(
        mode=args.mode,
        n_candidates=args.n_candidates,
        operator_class=args.operator_class,
        operator_substrate_class=args.operator_substrate_class,
        branch_grid_path=args.branch_grid,
        track_record_path=args.track_record,
        insights_path=args.insights,
        archive_path=args.archive,
        inbox_path=args.inbox,
        model=args.model,
        prompt_only=args.prompt_only,
        skip_llm=args.skip_llm,
        raw_payload=args.raw_payload,
    )
    if args.prompt_only:
        print(md)
    else:
        print(f"wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
