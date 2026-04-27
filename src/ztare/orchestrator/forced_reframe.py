"""GP-168 — Forced REFRAME iter mechanism.

When the apparatus has been stagnated for N iters AND/OR refining the same
PARAMETRIC_FORM AST shape for M iters, force the next iter into a
mandatory-disjoint architecture: name the current family, ban it for that
iter, present alien-math framings as the only allowed starting points.

This is the forcing function ANALOGY currently lacks. The existing
ANALOGY mechanism surfaces cross-domain candidates as suggestions; the
mutator can ignore them. GP-168 makes them constraints — iter-N+1's
prompt explicitly forbids the architectural family iter-N used and
provides 3 alien-math framings as the only legal starts.

Design note (per GP-157 §3a): GP-168 ships as a Cage-routed gate with
`can_handle` predicate reading stagnation_count + AST-bucket-history.
The forcing-function effect lives in the iter-N+1 prompt provider, not
in autoresearch_loop direct-wire. Trigger conditions are detected by
the gate; the prompt rewrite happens in the briefing provider.

Trigger conditions (configurable via rubric):
  - `gp168_stagnation_threshold` (default 3): consecutive iters at score 0
  - `gp168_ast_bucket_threshold` (default 5): consecutive iters with the
    same PARAMETRIC_FORM AST hash bucket
  - `gp168_max_consecutive_fires` (default 2): after this many forced
    iters in a row without progress, downgrade to a softer "you've used
    your forcing budget" note. Prevents the apparatus locking the mutator
    into perpetual reframe loops.

Output: a `ForcedReframeDecision` consumed by the iter-N+1 prompt
builder.
"""
from __future__ import annotations

import ast
import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional


@dataclass
class ForcedReframeDecision:
    """Whether to force REFRAME on the next iter, and what to say if so."""
    should_force: bool = False
    trigger_reason: Optional[str] = None
    banned_family_description: Optional[str] = None
    seeded_alternatives: list[dict] = field(default_factory=list)
    consecutive_fires: int = 0
    # 2026-04-26: AST-distance enforcement. The bucket of the form that
    # triggered the reframe — submissions on the next iter whose AST
    # bucket equals this value get R1-rejected via the
    # check_forced_reframe_compliance hook in autoresearch_loop.
    banned_ast_bucket: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "should_force": self.should_force,
            "trigger_reason": self.trigger_reason,
            "banned_family_description": self.banned_family_description,
            "seeded_alternatives_count": len(self.seeded_alternatives),
            "consecutive_fires": self.consecutive_fires,
            "banned_ast_bucket": self.banned_ast_bucket,
        }


def extract_parametric_form_from_source(src: str) -> Optional[str]:
    """Pull the PARAMETRIC_FORM string literal out of a test_model.py source.

    Parses with `ast` so multi-line implicit-concatenation forms like
        PARAMETRIC_FORM = (
            "features['x'] / "
            "((1 - exp(-(...))))"
        )
    resolve to the single concatenated string Python sees at parse time.
    Replaces a previous regex-based extractor that captured the raw
    multi-line text and made AST-bucket detection bucket every form as
    `syntax_error` (false-positive REFRAME trigger across 5 consecutive
    iters in run_id 1777250273).

    Returns the form string, or None if the file does not declare
    PARAMETRIC_FORM with a literal-evaluable string value.
    """
    if not src:
        return None
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return None
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        if len(node.targets) != 1:
            continue
        tgt = node.targets[0]
        if not isinstance(tgt, ast.Name) or tgt.id != "PARAMETRIC_FORM":
            continue
        try:
            value = ast.literal_eval(node.value)
        except (ValueError, SyntaxError):
            return None
        if isinstance(value, str):
            return value
        return None
    return None


def parametric_form_ast_bucket(form_str: str) -> str:
    """Compute a stable AST-shape hash for a PARAMETRIC_FORM string.

    Two forms with the same AST shape (same operators, same nesting,
    different numeric constants and feature key strings) share a bucket.
    This is the signal that the mutator has been refining the same
    architectural family across iters.
    """
    if not form_str:
        return "empty"
    try:
        tree = ast.parse(form_str, mode="eval")
    except SyntaxError:
        return "syntax_error"
    # Walk the AST and emit a structural signature: node types + arity.
    # Skip Constant, Name, Subscript values — those are the variable
    # parts (numeric constants, feature keys, parameter keys).
    signature_parts: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.Constant, ast.Name)):
            continue
        if isinstance(node, ast.Subscript):
            signature_parts.append("Subscript")
            continue
        signature_parts.append(type(node).__name__)
    sig_str = "|".join(sorted(signature_parts))
    return hashlib.sha1(sig_str.encode()).hexdigest()[:12]


def detect_forced_reframe_trigger(
    iter_history: list[dict],
    *,
    stagnation_threshold: int = 3,
    ast_bucket_threshold: int = 5,
    max_consecutive_fires: int = 2,
) -> ForcedReframeDecision:
    """Inspect iter_history and decide whether to force REFRAME on the
    next iter.

    Args:
        iter_history: list of dicts with at least keys
            {"iter_index", "score", "parametric_form", "forced_reframe_fired"}.
            Most-recent iter last.
        stagnation_threshold: consecutive zero-score iters that triggers.
        ast_bucket_threshold: consecutive same-AST-bucket iters that triggers.
        max_consecutive_fires: limits how many GP-168 iters fire in a row.
    """
    decision = ForcedReframeDecision()
    if not iter_history:
        return decision

    # Count consecutive forced-reframe fires (including current run-up)
    consec_fires = 0
    for entry in reversed(iter_history):
        if entry.get("forced_reframe_fired"):
            consec_fires += 1
        else:
            break
    decision.consecutive_fires = consec_fires

    if consec_fires >= max_consecutive_fires:
        return decision  # forcing budget exhausted; let normal flow proceed

    # Trigger 1: consecutive zero scores
    recent_scores = [e.get("score") for e in iter_history[-stagnation_threshold:]]
    if (len(recent_scores) >= stagnation_threshold
            and all(s == 0 for s in recent_scores)):
        decision.should_force = True
        decision.trigger_reason = (
            f"stagnation: {stagnation_threshold} consecutive iters at score=0"
        )
        last_form = iter_history[-1].get("parametric_form", "")
        last_bucket = parametric_form_ast_bucket(last_form)
        decision.banned_ast_bucket = last_bucket
        decision.banned_family_description = (
            f"the architectural family of iter-{iter_history[-1].get('iter_index', '?')} "
            f"with PARAMETRIC_FORM AST bucket {last_bucket} "
            f"(last form: {last_form[:200]}...)"
        )
        return decision

    # Trigger 2: same AST bucket for ast_bucket_threshold consecutive iters
    if len(iter_history) >= ast_bucket_threshold:
        recent_buckets = [
            parametric_form_ast_bucket(e.get("parametric_form", ""))
            for e in iter_history[-ast_bucket_threshold:]
        ]
        if recent_buckets and all(b == recent_buckets[0] for b in recent_buckets):
            decision.should_force = True
            decision.banned_ast_bucket = recent_buckets[0]
            decision.trigger_reason = (
                f"ast_bucket_lock: {ast_bucket_threshold} consecutive iters "
                f"with PARAMETRIC_FORM AST bucket {recent_buckets[0]}"
            )
            decision.banned_family_description = (
                f"the architectural family with AST bucket {recent_buckets[0]} "
                f"that has been refined for the last {ast_bucket_threshold} iters "
                f"without breakthrough"
            )
            return decision

    return decision


def build_forced_reframe_briefing_block(
    decision: ForcedReframeDecision,
    seeded_alternatives: list[dict],
) -> str:
    """Render the forced-reframe block for inclusion in the next iter's
    mutator briefing. The block opens with the trigger reason, names
    the banned family, and presents the alternatives as the only legal
    starting points.

    Args:
        decision: the ForcedReframeDecision from detect_forced_reframe_trigger
        seeded_alternatives: list of dicts with keys
            {"name", "form", "field_of_origin", "what_it_captures"}
            from GP-164 alien-math framings or GP-169 cold-LLM seed.
    """
    if not decision.should_force:
        return ""
    parts = [
        "## ⚠️  FORCED REFRAME (GP-168)",
        "",
        f"**Trigger**: {decision.trigger_reason}",
        "",
        f"**Banned for this iter**: {decision.banned_family_description}",
        "",
        "The current architectural family has been refined sufficiently. ",
        "This iter MUST commit to a structurally-disjoint architecture from ",
        "one of the alternatives below, OR provide a one-paragraph prose ",
        "justification why none of the alternatives apply (such submissions ",
        "go to the judge with a prominent note that the mutator declined the ",
        "forced reframe; the judge will weigh that in scoring).",
        "",
        "### Mandatory architectural alternatives",
        "",
    ]
    for i, alt in enumerate(seeded_alternatives, 1):
        parts.append(f"#### Alternative {i}: {alt.get('name', f'Framing {i}')}")
        if alt.get("field_of_origin"):
            parts.append(f"**Field of origin**: {alt['field_of_origin']}")
        if alt.get("what_it_captures"):
            parts.append(f"**Captures**: {alt['what_it_captures']}")
        if alt.get("form"):
            parts.append("```python")
            parts.append(str(alt["form"]).strip())
            parts.append("```")
        parts.append("")
    parts.extend([
        "### Adherence requirement",
        "",
        "Iter submissions that copy the banned family's AST shape — same",
        "operators in the same nesting — will be R1-rejected by the apparatus",
        "as a forced-reframe-violation. Pick one of the alternatives, modify",
        "one (e.g. swap features, add a parameter, change a primitive), or",
        "explicitly justify rejection in thesis prose.",
        "",
    ])
    return "\n".join(parts)


def write_forced_reframe_decision(
    workspace_dir: Path,
    iter_index: int,
    decision: ForcedReframeDecision,
) -> Path:
    """Persist the decision so iter_history can read forced_reframe_fired
    flags on subsequent iters."""
    out_path = workspace_dir / f"forced_reframe_iter_{iter_index:03d}.json"
    out_path.write_text(json.dumps(decision.to_dict(), indent=2), encoding="utf-8")
    return out_path


def check_forced_reframe_compliance(
    workspace_dir: Path,
    iter_index: int,
    submitted_form: str,
) -> Optional[str]:
    """R1-side check (2026-04-26): when Forced-REFRAME has fired for the
    CURRENT iter (i.e., banning the previous iter's family), the
    mutator's new submission MUST belong to a different AST bucket.

    Returns:
        None if compliant (no forced-reframe in effect, or the form's
        AST bucket differs from the banned bucket).
        A non-empty error string when non-compliant — the caller
        (autoresearch_loop's R1 retry path) raises ValueError with this
        message so the mutator gets the feedback and one free retry.

    Looks at the most recent forced_reframe_iter_NNN.json file in the
    workspace where NNN <= iter_index. If decision.should_force is True
    and decision.banned_ast_bucket is set, the submission's bucket is
    compared.
    """
    if not submitted_form:
        return None
    # Find the most recent forced-reframe decision file with iter <= iter_index
    candidates: list[tuple[int, Path]] = []
    if workspace_dir.is_dir():
        for p in workspace_dir.glob("forced_reframe_iter_*.json"):
            try:
                idx = int(p.stem.split("_")[-1])
            except ValueError:
                continue
            if idx <= iter_index:
                candidates.append((idx, p))
    if not candidates:
        return None
    candidates.sort(key=lambda t: t[0])
    latest_idx, latest_path = candidates[-1]
    try:
        decision = json.loads(latest_path.read_text(encoding="utf-8"))
    except Exception:
        return None
    if not decision.get("should_force"):
        return None
    banned = decision.get("banned_ast_bucket")
    if not banned:
        return None
    submitted_bucket = parametric_form_ast_bucket(submitted_form)
    if submitted_bucket == banned:
        return (
            f"FORCED-REFRAME violation: this iter's PARAMETRIC_FORM has AST bucket "
            f"'{submitted_bucket}' which equals the banned bucket from "
            f"forced_reframe_iter_{latest_idx:03d}.json (trigger: "
            f"'{decision.get('trigger_reason', '?')}'). The apparatus has formally "
            f"flagged this architectural family as stagnant. Pick a structurally "
            f"different form from the Forced-REFRAME briefing alternatives "
            f"(F1 RG-flow / F2 modular / F3 multifractal) or from the cold-LLM "
            f"Erdős seed candidates. The form MUST have a different AST shape — "
            f"swap operators, change nesting, drop the McGaugh interpolation "
            f"family, or pick from the briefing's mandatory alternatives. "
            f"Refining the same family with renamed parameters does NOT count as "
            f"structurally different."
        )
    return None
