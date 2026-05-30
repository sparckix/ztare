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
    enable_qualitative_stagnation: bool = False,
    qualitative_stagnation_threshold: int = 3,
    qualitative_plateau_threshold: int = 5,
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
        # Guard (2026-05-02 pm): "empty" and "syntax_error" buckets must
        # NOT trip Trigger 2. Qualitative substrates (no PARAMETRIC_FORM)
        # would otherwise auto-fire Trigger 2 with bucket="empty" after
        # ast_bucket_threshold iters, even when no real architectural
        # stagnation has occurred. Mirrors the guard in
        # cold_llm_seed_requery.detect_stagnation. This is a regression
        # fix — was not present originally. No effect on numerical
        # substrates (their buckets are real AST hashes, never "empty").
        if (recent_buckets
                and recent_buckets[0] not in ("empty", "syntax_error")
                and all(b == recent_buckets[0] for b in recent_buckets)):
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

    # Trigger 3 — capped-stagnation detection (2026-04-27): consecutive iters
    # where the apparatus capped the judge's raw score (raw > capped) with
    # identical capped value. Catches gp163d's path-a-stuck-at-cap pattern:
    # bridge skeleton variants score raw 100 but get capped to 50 by
    # R20+R21+R24+R22. Pure zero-score and same-AST-bucket detectors miss
    # this because (a) capped score is never 0 and (b) different bridge
    # variants (with/without screening, hardcoded vs fitted sigmoid centers)
    # produce different AST buckets despite all being path-a.
    if len(iter_history) >= stagnation_threshold:
        recent = iter_history[-stagnation_threshold:]
        capped_streak = 0
        for e in recent:
            s = e.get("score")
            r = e.get("raw_judge_score")
            if (
                s is not None and r is not None
                and isinstance(s, (int, float)) and isinstance(r, (int, float))
                and r > s
                and s == recent[-1].get("score")
            ):
                capped_streak += 1
        if capped_streak >= stagnation_threshold:
            decision.should_force = True
            last_form = iter_history[-1].get("parametric_form", "")
            decision.banned_ast_bucket = parametric_form_ast_bucket(last_form)
            decision.trigger_reason = (
                f"capped_stagnation: {stagnation_threshold} consecutive iters "
                f"capped at score={recent[-1].get('score')} by structural detectors "
                f"(raw_judge_score > capped, indicating path-a parameter laundering)"
            )
            decision.banned_family_description = (
                f"the path-a parametric family that the apparatus has capped at "
                f"score={recent[-1].get('score')} for {stagnation_threshold} consecutive iters. "
                f"R20/R21/R24/R22 detected hardcoded structural constants masquerading "
                f"as fitted parameters. Submit a Lagrangian-derived form (chameleon, AQUAL, "
                f"MOG, f(R)) per evidence Set I — not another bridge skeleton variant."
            )
            return decision

    # Trigger 4 — qualitative-substrate stagnation (2026-05-02). Triggers 1-3
    # all assume a numerical substrate: score==0 hard-rejects, PARAMETRIC_FORM
    # AST drift, or capped-stagnation with raw_judge_score. None of those
    # apply to qualitative_thesis substrates (gp168 v3, gp169) where the
    # judge produces nonzero prose-thesis scores and there is no
    # PARAMETRIC_FORM. The qualitative trigger uses (a) repeated weakest_point
    # gate-name fingerprints across consecutive iters AND (b) sub-baseline
    # score drift — exactly the gp168 v3 pattern (6 iters scored 13-71,
    # all citing the same v3 hard-gate failures, never below the iter-0
    # baseline of 93 from the inherited v2 champion).
    #
    # OPT-IN: only fires when rubric sets enable_qualitative_stagnation_detection=true.
    # Numerical substrates do NOT set this flag, so Trigger 4 never reaches
    # them — no regression risk for the science branch (gp163d, gp161, etc.).
    if not enable_qualitative_stagnation:
        return decision
    qual_thresh = qualitative_stagnation_threshold
    if len(iter_history) >= qual_thresh:
        recent = iter_history[-qual_thresh:]
        gate_buckets = [_weakest_point_gate_bucket(e) for e in recent]
        if gate_buckets and all(b is not None and b == gate_buckets[0]
                                for b in gate_buckets):
            # All three iters cite the same hard-gate failure.
            # Sub-baseline drift check: are recent scores below iter-0?
            iter_0 = next((e.get("score") for e in iter_history
                           if e.get("iter_index") in (0, "0")), None)
            if iter_0 is None:
                iter_0 = iter_history[0].get("score")
            recent_scores_qual = [e.get("score", 0) for e in recent]
            sub_baseline = (
                iter_0 is not None
                and all(isinstance(s, (int, float)) and s < iter_0
                        for s in recent_scores_qual)
            )
            if sub_baseline:
                decision.should_force = True
                decision.banned_ast_bucket = f"qual_gate:{gate_buckets[0]}"
                decision.trigger_reason = (
                    f"qualitative_gate_lock: {qual_thresh} consecutive iters "
                    f"failing the same weakest-point gate ('{gate_buckets[0]}') "
                    f"with all scores below iter-0 baseline ({iter_0})"
                )
                decision.banned_family_description = (
                    f"the thesis-axis that has been failing gate '{gate_buckets[0]}' "
                    f"for {qual_thresh} consecutive iters. The mutator is iterating "
                    f"on the wrong axis — propose a structurally disjoint thesis "
                    f"family per the charter's mandatory hypothesis space, not "
                    f"another refinement of the failing axis."
                )
                return decision

    # Trigger 5 — flat-plateau qualitative stagnation (2026-05-02 pm).
    # Trigger 4 catches sub-baseline drift (gp168 v3 pattern: 93→71→26
    # below baseline). Trigger 5 catches the OPPOSITE flat-plateau
    # pattern (gp169 v2: 70→98→91→94→67 — high but no improvement past
    # the iter-1 champion). The mutator can't beat its own champion;
    # without intervention it will keep refining the wrong axis or
    # produce over-extensions like iter-4=67. Same reframe target —
    # propose a structurally disjoint thesis spine — but the trigger
    # condition is "no champion improvement over N iters" rather than
    # "scores below baseline."
    #
    # Fires when: (a) qualitative-stagnation enabled (same opt-in as T4)
    # AND (b) ≥ qual_thresh iters AFTER the current champion AND
    # (c) none of those iters beat the champion's score AND
    # (d) the recent iter weakest-points share a gate bucket.
    plateau_thresh = qualitative_plateau_threshold
    if len(iter_history) >= plateau_thresh + 1:
        scores = [e.get("score") for e in iter_history
                  if isinstance(e.get("score"), (int, float))]
        if scores:
            champ_score = max(scores)
            champ_idx = scores.index(champ_score)
            iters_after_champ = iter_history[champ_idx + 1:]
            if len(iters_after_champ) >= plateau_thresh:
                recent_after_champ = iters_after_champ[-plateau_thresh:]
                no_new_champ = all(
                    isinstance(e.get("score"), (int, float))
                    and e.get("score") < champ_score
                    for e in recent_after_champ
                )
                gate_buckets_pl = [_weakest_point_gate_bucket(e)
                                   for e in recent_after_champ]
                # Trigger 5 looseness (2026-05-02 pm): fire on plateau alone,
                # WITHOUT requiring same gate. The same-gate constraint was
                # too strict — gp169 v2 plateau iters cited different gates
                # (certificate_partition then fail_closed_blindness) which IS
                # stagnation from the user's perspective even though the
                # apparatus thinks it's exploring different angles.
                # Same-gate is now a *bonus signal* for the trigger reason
                # text but no longer required for firing.
                same_gate = (
                    gate_buckets_pl
                    and all(b is not None and b == gate_buckets_pl[0]
                            for b in gate_buckets_pl)
                )
                if no_new_champ:
                    decision.should_force = True
                    bucket_label = gate_buckets_pl[0] if same_gate else "varied"
                    decision.banned_ast_bucket = f"qual_plateau:{bucket_label}"
                    same_gate_note = (
                        f" AND all citing the same gate ('{gate_buckets_pl[0]}')"
                        if same_gate else
                        f" (gates varied: {gate_buckets_pl} — apparatus "
                        f"explored different angles but none beat the champion)"
                    )
                    decision.trigger_reason = (
                        f"qualitative_flat_plateau: {plateau_thresh} consecutive "
                        f"post-champion iters all below champion score "
                        f"({champ_score}){same_gate_note}. The mutator cannot "
                        f"beat its own champion."
                    )
                    decision.banned_family_description = (
                        f"the thesis-axis around the iter-{champ_idx} champion "
                        f"(score {champ_score}). {plateau_thresh} subsequent iters "
                        f"failed to improve while citing the same weakest-point "
                        f"gate ('{gate_buckets_pl[0]}'). Propose a structurally "
                        f"disjoint thesis spine, not another refinement of the "
                        f"champion."
                    )
                    return decision

    return decision


def _weakest_point_gate_bucket(entry: dict) -> Optional[str]:
    """Extract a stable gate-name fingerprint from an iter entry's
    weakest_point critique. Two iters that fail the same gate produce the
    same bucket; this is the qualitative analog of parametric_form_ast_bucket.

    Heuristic: scan the weakest_point text for known v3 gate phrases (≥3
    disjoint families, substrate-prior diversity, substrate-paraphrase,
    no-tautology, exogenous-pressure, second-order adaptation, asymmetry
    stress test). Returns the matched gate label, or a fallback hash of
    the first 80 chars if no known phrase matches. Returns None if the
    entry has no weakest_point string.
    """
    wp = entry.get("weakest_point") or entry.get("weakest_point_text") or ""
    if not isinstance(wp, str) or not wp.strip():
        return None
    wp_lower = wp.lower()
    # Ordered known gates — first match wins.
    known_gates = [
        # gp168 v3 (org topology) gate phrases
        ("disjoint_families",
         ["disjoint construct famil", "three disjoint famil", "≥3 disjoint",
          "comparative evaluation of at least three", "minimum disjoint famil",
          "multi-family hypothesis"]),
        ("substrate_prior_diversity",
         ["substrate prior", "substrate-prior", "substrate priors",
          "marine/ecological", "intellectual tradition"]),
        ("substrate_paraphrase",
         ["paraphrase", "substrate-paraphrase", "substrate-leak",
          "substrate leak"]),
        ("no_tautology",
         ["tautolog", "circular", "defines its own success",
          "vacuous", "unfalsifiable"]),
        ("exogenous_pressure",
         ["exogenous pressure", "exogenous resource", "closure clock",
          "exogenous-pressure"]),
        ("second_order_adaptation",
         ["second-order", "covert fusion", "biosocial", "co-evolution",
          "ecological adaptation", "jacobi inversion"]),
        ("asymmetry_stress_test",
         ["asymmetry", "edge case", "dementia", "philosophizing llm",
          "locked-in", "anesthet"]),
        ("compensation_axis",
         ["compensation", "compensatory", "weakest-link", "convex compensat",
          "hard ceiling"]),
        ("worked_mechanism",
         ["worked mechanism", "by mechanism", "not by assertion",
          "mechanism vs assertion"]),
        # gp169 v2 (consciousness audit) gate phrases — added 2026-05-02 pm.
        # Without these, gp169-v2-shaped weakest_points fall through to the
        # prose-hash fallback and same-gate detection misses the actual
        # repeated failure mode.
        ("alien_statability",
         ["alien-statable", "alien-statability", "first-person presupposition",
          "first-person anchor", "anthropic leakage", "anthropic-leak",
          "non-anthropic"]),
        ("no_citation_recapitulation",
         ["no-citation", "school recovery", "training-corpus consensus",
          "recapitulat", "thesaurus substitut"]),
        ("endogenous_closure",
         ["endogenous closure", "endogenous-closure", "internal coherence",
          "fixed point under substrate-paraphrase"]),
        ("certificate_partition",
         ["translation-admissibility", "tau(d)", "τ(d)", "certificate",
          "preserved-analog", "severed-analog", "partition not crisp",
          "partition operator"]),
        ("fail_closed_blindness",
         ["fail-closed", "structural blindness", "structural blind spot",
          "positive recognition blocked", "pyrrhic", "absence of evidence",
          "systematic blindness", "blocked selector"]),
        ("non_applicability_admission",
         ["non-applicability", "bounded domain", "universal-applicability"]),
    ]
    for label, phrases in known_gates:
        if any(p in wp_lower for p in phrases):
            return label
    # Fallback: hash first 80 chars so prose-distinct critiques don't
    # collide on the same bucket.
    return f"prose:{hashlib.sha1(wp_lower[:80].encode()).hexdigest()[:8]}"


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
