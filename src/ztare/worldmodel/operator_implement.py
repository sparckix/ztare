"""Worldmodel INSTANCE of the kernel operator-implement contract (GP-250).

The kernel (``operator_proposal_contract.implement_and_validate``) orchestrates a
sealed leaf proposing a new operator and a substrate harness disposing it. This
module supplies the two grid-catalog plug-ins for the RULE-COUPLING family (the
ls20 residual: a color-11 timer whose tick is coupled to whether the mover
actually moved this step):

  * ``worldmodel_leaf_runner`` — prompts a sealed leaf (codex subscription CLI,
    per repo policy: leaf = codex CLI, never a metered API, never claude) for a
    GUARD/OPERATOR SPEC as strict JSON (name, semantics, catalog encoding sketch,
    planted-synthetic description) — a LAW SHAPE, never arbitrary code;
  * ``worldmodel_harness`` — the kernel gate: if the leaf names a fired-this-step
    coupling it is implemented as ``when_effect`` (already in the catalog) and
    accepted iff (a) a planted synthetic carrying that coupling recovers via
    ``abduce_spec`` with replay_ok, AND (b) replay on the real snapshot strictly
    improves once the coupling refine is enabled.

Leaf proposes the shape; the deterministic ``when_effect`` encoding + the gates
dispose. A leaf that returns junk or an uncoupled shape is rejected, not trusted.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from types import SimpleNamespace

from ztare.worldmodel.episode_log import EpisodeLog
from ztare.worldmodel.gates import env_frame_indices
from ztare.worldmodel.spec_abduction import abduce_spec
from ztare.worldmodel.spec_catalog import lower_spec, render_catalog_contract

REPO = Path(__file__).resolve().parents[3]

# Known-positive rule-coupling shape for harness tests and explicit debug runs.
# Production leaf dispatch must not silently substitute this for a failed leaf.
_CANNED_LEAF = {
    "name": "when_effect_rule_coupling",
    "semantics": ("One rule is suppressed/enabled iff ANOTHER rule fired this "
                  "step: the color-11 timer consume advances only on steps where "
                  "the mover translate did NOT move between docks. A mid-chain "
                  "fired-flag coupling, well-defined under deterministic dynamics."),
    "catalog_encoding": ("give the mover translate rule an \"id\" and gate the "
                         "consume_extremal with when_effect [id, false]"),
    "planted_synthetic": ("a two-colour mover on a floor corridor bounded by walls; "
                          "the color-11 timer consumes its leftmost cell iff the mover "
                          "was blocked (did not move) this step, so freeze steps still "
                          "change the grid and freeze positions vary — no fixed "
                          "positional or periodic guard separates the tick/pause split, "
                          "only the mover-fired coupling does"),
    "mover_colors": [9, 12], "timer_color": 11, "ticks_when_moved": False,
}


def _leaf_prompt(card: dict) -> str:
    wef = card.get("why_existing_ops_fail", {})
    return (
        "You are a sealed worker proposing ONE new world-model GUARD/OPERATOR as a "
        "LAW SHAPE — never code. The current operator catalog leaves a residual it "
        "cannot express; propose the guard/operator that closes it.\n\n"
        f"FAILURE FAMILY: {card.get('failure_family')}\n"
        f"WHY EVERY EXISTING OP FAILS:\n" +
        "".join(f"  - {fam}: {why}\n" for fam, why in wef.items()) +
        f"SPATIAL FOOTPRINT: {json.dumps(card.get('spatial_footprint', {}))}\n"
        f"EVIDENCE TRANSITION INDICES: {card.get('evidence_indices')}\n\n"
        f"CATALOG CONTRACT (you must encode within this vocabulary):\n"
        f"{render_catalog_contract()}\n\n"
        "Return STRICT JSON only, one object, with keys: "
        "\"name\", \"semantics\" (one paragraph), \"catalog_encoding\" (a sketch in "
        "the catalog vocabulary above), \"planted_synthetic\" (a description of a "
        "small synthetic log in which ONLY your proposed guard/operator explains all "
        "transitions). If the residual is a rule-coupling (a rule that fires iff "
        "another rule fired this step), say so and use when_effect.")


def worldmodel_leaf_runner(card: dict, provider: str = "codex") -> dict:
    """Dispatch the proposal prompt to a sealed leaf via the codex subscription
    CLI (repo policy). Returns the parsed JSON artifact tagged with the path that
    ran. Dispatch/parse failure returns a non-coupling artifact by default; the
    known-positive canned artifact is only available behind an explicit env flag."""
    prompt = _leaf_prompt(card)
    raw = ""
    try:
        from ztare.common.subscription_agent_runtime import (
            CODEX_SANDBOX_SEALED_COMPLETION,
            run_subscription_agent_with_recovery)
        run = run_subscription_agent_with_recovery(
            runtime=provider, prompt=prompt, agent_id="worldmodel::operator_implement",
            repo=REPO, session_state=None, timeout_seconds=180,
            codex_sandbox=CODEX_SANDBOX_SEALED_COMPLETION,
            claude_disallowed_tools=["WebSearch", "WebFetch"])
        raw = (getattr(getattr(run, "result", None), "stdout", "") or "") if run else ""
    except Exception:  # noqa: BLE001
        raw = ""
    m = re.search(r"\{.*\}", raw, re.S)
    if m:
        try:
            spec = json.loads(m.group(0))
            if isinstance(spec, dict) and spec:
                spec["_leaf_path"] = "codex_live"
                spec["_raw"] = raw
                return spec
        except Exception:  # noqa: BLE001
            pass
    if os.environ.get("ZTARE_WORLDMODEL_OPERATOR_ALLOW_CANNED_LEAF") == "1":
        out = dict(_CANNED_LEAF)
        out["_leaf_path"] = "canned_fallback_explicit"
        out["_raw"] = raw
        return out
    return {
        "name": "leaf_dispatch_or_parse_failed",
        "semantics": "no accepted operator proposal was produced by the sealed leaf",
        "catalog_encoding": "",
        "planted_synthetic": "",
        "_leaf_path": "dispatch_or_parse_failed",
        "_raw": raw,
    }


def _names_coupling(spec: dict) -> bool:
    """Does the leaf's shape name a fired-this-step (rule-coupling) law?"""
    blob = " ".join(str(spec.get(k, "")) for k in
                    ("name", "semantics", "catalog_encoding", "planted_synthetic")).lower()
    return ("when_effect" in blob or "fired this step" in blob
            or "rule-coupling" in blob or "rule coupling" in blob
            or bool(spec.get("mover_colors")) and "timer_color" in spec)


def build_coupling_synthetic(mover_colors=(9, 12), timer_color: int = 11,
                             ticks_when_moved: bool = False) -> EpisodeLog:
    """A planted ls20-shaped coupling log: a two-colour mover slides on floor(3)
    in a corridor bounded by walls(7); the timer consumes its leftmost cell iff
    the mover's move-status matches ``ticks_when_moved``. Freeze steps still
    change the grid (the timer) and freeze positions vary — so no fixed
    positional/periodic guard separates the tick/pause split, ONLY the coupling."""
    mc = list(mover_colors)
    a, b = (mc + mc)[0], (mc + mc)[1]
    truth, err = lower_spec({
        "actions": {"0": [{"op": "translate_block", "id": "m", "match_colors": mc,
                           "dy": 0, "dx": 1, "require_dest_colors": [3],
                           "fill_color": 3, "component_min_colors": len(set(mc))}],
                    "1": [{"op": "translate_block", "id": "m", "match_colors": mc,
                           "dy": 0, "dx": -1, "require_dest_colors": [3],
                           "fill_color": 3, "component_min_colors": len(set(mc))}]},
        "always": [{"op": "consume_extremal", "color": timer_color, "replacement": 3,
                    "axis": "row", "extreme": "min",
                    "when_effect": ["m", bool(ticks_when_moved)]}]})
    if truth is None:
        raise ValueError(f"canonical coupling spec failed to lower: {err}")
    g = ((7, 3, 3, a, b, 3, 3, 7),
         (7, 3, 3, 3, 3, 3, 3, 7),
         tuple([timer_color] * 6 + [3, 3]))
    log = EpisodeLog()
    s = g
    for act in (0, 0, 0, 0, 1, 0, 1, 1, 1, 1, 1, 0, 0, 0, 0, 1):
        s2 = truth(s, act, 0)
        log.append(s, act, s2, t=0)
        s = s2
    return log


def _replay_count(spec_or_result, log, env) -> int:
    step = spec_or_result.step_fn
    if step is None:
        return 0
    return sum(1 for i, tr in enumerate(log)
               if i not in env and step(tr.s, tr.a, tr.t) == tr.s_next)


def _slice_log(log, indices) -> "EpisodeLog":
    out = EpisodeLog()
    rows = list(log)
    seen = set()
    for raw in indices or []:
        try:
            i = int(raw)
        except Exception:
            continue
        if i in seen or i < 0 or i >= len(rows):
            continue
        seen.add(i)
        tr = rows[i]
        out.append(tr.s, tr.a, tr.s_next, t=tr.t)
    return out


def worldmodel_harness(spec_json, real_log: "EpisodeLog | None" = None) -> dict:
    """Kernel gate — two admission branches, SAME strict evidence criteria:

    Branch A (rule-coupling): leaf names a fired-this-step coupling.
      Accepts iff (a) a planted synthetic recovers via abduce_spec with
      replay_ok and a when_effect rule, AND (b) real_log replay strictly
      improves once the coupling refine is enabled.

    Branch B (spec-patch): leaf returns a spec-patch shape (not a coupling).
      Routed to _spec_patch_house_verdict — accepts iff the candidate step
      strictly improves on the baseline with no regressions.

    Gate-widening in admissible FORMS only; evidence criteria are not loosened.
    Each rejection names which branch evaluated and why.
    """
    spec = spec_json if isinstance(spec_json, dict) else {}
    if isinstance(spec_json, str):
        m = re.search(r"\{.*\}", spec_json, re.S)
        if m:
            try:
                spec = json.loads(m.group(0))
            except Exception:  # noqa: BLE001
                spec = {}
    if not _names_coupling(spec):
        # Branch B: non-coupling shape — route to spec-patch arbiter if real_log present.
        # The card's proposed_operator_sketch is used as the spec-patch source when the
        # leaf artifact itself is not a fully-lowerable spec (the leaf may embed the patch
        # inside "spec_patch" or "proposed_spec" keys).
        if real_log is None:
            return {"accepted": False, "receipt": "",
                    "branch": "spec_patch",
                    "counterexample": "branch=spec_patch: no real_log supplied; cannot evaluate"}
        # Prefer an explicit spec_patch key, else treat the whole artifact as the patch.
        spec_patch = spec.get("spec_patch") or spec.get("proposed_spec") or spec
        if not isinstance(spec_patch, dict) or not spec_patch:
            return {"accepted": False, "receipt": "",
                    "branch": "spec_patch",
                    "counterexample": "branch=spec_patch: no usable spec_patch in leaf artifact"}
        # Build a stub ab_result so _spec_patch_house_verdict can load the baseline.
        _baseline_spec = (spec_json.get("_baseline") or {}).get("spec") if isinstance(spec_json, dict) else None
        from types import SimpleNamespace as _SN
        _ab_stub = _SN(spec=_baseline_spec, step_fn=None)
        from ztare.worldmodel.grammar_reflex import _spec_patch_house_verdict
        verdict = _spec_patch_house_verdict(real_log, _ab_stub, spec_patch)
        if verdict.get("accepted"):
            return {"accepted": True,
                    "branch": "spec_patch",
                    "receipt": f"spec_patch branch: {verdict}",
                    "counterexample": None}
        return {"accepted": False,
                "branch": "spec_patch",
                "receipt": "",
                "counterexample": f"branch=spec_patch rejected: {verdict.get('reason')} — {verdict}"}

    # (a) planted-synthetic recovery
    syn = build_coupling_synthetic(
        mover_colors=spec.get("mover_colors", (9, 12)),
        timer_color=int(spec.get("timer_color", 11)),
        ticks_when_moved=bool(spec.get("ticks_when_moved", False)))
    syn_env = env_frame_indices(syn)
    syn_r = abduce_spec(syn, 2, _effect_refine=True)
    syn_has_we = any("when_effect" in r for r in (syn_r.spec or {}).get("always", [])) or \
        any("when_effect" in r for rules in (syn_r.spec or {}).get("actions", {}).values()
            for r in rules)
    if not (syn_r.replay_ok and syn_has_we):
        return {"accepted": False, "receipt": "",
                "counterexample": "planted synthetic did not recover with when_effect "
                                  f"(replay_ok={syn_r.replay_ok}, has_when_effect={syn_has_we})"}

    # (b) real snapshot: strict improvement from the coupling refine
    if real_log is None:
        return {"accepted": False, "receipt": "",
                "counterexample": "no real log supplied for the strict-improvement leg"}
    real_indices = spec.get("_real_indices") if isinstance(spec, dict) else None
    score_log = _slice_log(real_log, real_indices) if real_indices else real_log
    if not len(score_log):
        score_log = real_log
    env = env_frame_indices(score_log)
    total = len(list(score_log)) - len(env)
    arity = max((tr.a for tr in real_log), default=0) + 1
    # PROPORTIONALITY (2026-07-05, py-spy verdict): use the residual slice as a
    # fast rejection gate, then run the house arbiter on the full log. Local
    # improvement is never enough for adoption because writes can regress away
    # from the card evidence.
    baseline = spec_json.get("_baseline") if isinstance(spec_json, dict) else None
    import os as _os
    _old_ladder = _os.environ.get("ZTARE_REFINE_LADDER")
    _os.environ["ZTARE_REFINE_LADDER"] = "0"
    try:
        if baseline and baseline.get("spec") is not None:
            base_ab = abduce_spec(score_log, arity, _effect_refine=False,
                                  prior_spec=baseline["spec"])
        else:
            base_ab = abduce_spec(score_log, arity, _effect_refine=False)
        base = _replay_count(base_ab, score_log, env)
        impr_ab = abduce_spec(score_log, arity, _effect_refine=True,
                              prior_spec=getattr(base_ab, "spec", None))
        impr = _replay_count(impr_ab, score_log, env)
    finally:
        if _old_ladder is None:
            _os.environ.pop("ZTARE_REFINE_LADDER", None)
        else:
            _os.environ["ZTARE_REFINE_LADDER"] = _old_ladder
    if impr <= base:
        return {"accepted": False, "receipt": "",
                "counterexample": f"real replay did not strictly improve "
                                  f"(baseline {base}/{total}, with coupling {impr}/{total})"}
    full_env = env_frame_indices(real_log)
    full_total = len(list(real_log)) - len(full_env)
    base_full_step = getattr(base_ab, "step_fn", None)
    if baseline and baseline.get("spec") is not None:
        base_full_step, _err = lower_spec(baseline["spec"])
    if base_full_step is None:
        base_full_step = getattr(base_ab, "step_fn", None)
    base_full = _replay_count(SimpleNamespace(step_fn=base_full_step),
                              real_log, full_env)
    impr_full = _replay_count(impr_ab, real_log, full_env)
    if impr_full <= base_full:
        return {"accepted": False, "receipt": "",
                "counterexample": "full replay did not strictly improve after "
                                  "slice gate "
                                  f"(slice {base}/{total}->{impr}/{total}; "
                                  f"full {base_full}/{full_total}->{impr_full}/{full_total})"}
    return {"accepted": True,
            "receipt": f"when_effect coupling: synthetic recovers (replay_ok); real replay "
                       f"slice {base}/{total} -> {impr}/{total}; full "
                       f"{base_full}/{full_total} -> {impr_full}/{full_total} "
                       "(strict improvement)",
            "counterexample": None}
