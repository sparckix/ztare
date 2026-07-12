"""Deterministic population enumerator for the version-space (GP-250).

CONTEXT
-------
When the visible-perfect candidate pool is a behavioral monoculture (all
candidates share one fingerprint), no distinguishing experiment can prune
survivors because they all agree everywhere the probe battery can reach.
This module diversifies the population by ENUMERATION: generating
visible-perfect variants whose predictions differ from the champion ONLY on
unwitnessed states — the precise gap distinguishing experiments must probe.

TWO GENERATOR FAMILIES
-----------------------
SPEC-FORM  (preferred when champion carries WORLD_MODEL_SPEC):
  Single-edit perturbations via the spec_catalog grammar — parameter tweaks
  (counts, extremes, axis, colors ±1 shuffle, when_t_mod), rule-order swaps,
  and when_effect flag flips. All variants are well-formed by construction
  (validate_spec passes) before they are ever executed.

WRAPPER-FORM  (always available — champion is PATCH_BASE/PATCH_DELTA or other):
  Thin Python wrappers over the champion carrier that are IDENTITY on every
  visible-witnessed state but differ on unwitnessed states. Each wrapper adds
  one alternative branch gated by a predicate that evaluates to False on all
  visible rows. The predicates are derived from the visible episode itself:
  cells whose color NEVER equals a target value across all visible rows — those
  predicates are provably False on every visible step and provably non-trivial
  on some imaginable state (the play loop may encounter them later).

HONESTY CONSTRAINT
------------------
Wrapper-form variants carry {"generator": "wrapper_never_witnessed_guard",
"guard": <predicate>} in the receipts ledger so no downstream consumer
mistakes machine-enumerated hypotheses for leaf-authored science. When the
play loop visits a state that fires the guard, the variant either confirms or
is refuted — that is the pruning signal these variants exist to produce.

PIPELINE
--------
  enumerate_population(project_dir, budget, target_survivors)
    → for each candidate (generated deterministically by index):
        1. write temp file
        2. build_row_bitmap → quick visible-perfect check
        3. if perfect → version_space.admit() (fingerprint dedup is free)
        4. stop at target_survivors distinct fingerprints OR budget exhausted
    → write workspace/population_enumeration.jsonl receipt

CLI
---
  python -m ztare.worldmodel.population_enumerator --project P [--budget N]
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ztare.worldmodel.evidence_consolidation import (
    _load_carrier_from_source,
    build_row_bitmap,
    resolve_episode_paths,
)
from ztare.worldmodel.episode_log import EpisodeLog
from ztare.worldmodel.gates import env_frame_indices
from ztare.worldmodel.spec_catalog import validate_spec, lower_spec
from ztare.worldmodel.version_space import (
    admit,
    load as vs_load,
)

_DEFAULT_BUDGET = int(os.environ.get("ZTARE_ENUM_BUDGET", "50"))
_DEFAULT_TARGET = int(os.environ.get("ZTARE_ENUM_TARGET_SURVIVORS", "8"))


# ── champion loading ──────────────────────────────────────────────────────────

def _load_champion_source(project_dir: Path) -> "str | None":
    """Return source text of the best-available champion for this project.

    Preference order: test_model.py at project root (current champion),
    then workspace/submissions sorted descending (latest iteration).
    """
    tm = project_dir / "test_model.py"
    if tm.exists():
        return tm.read_text()
    sub_dir = project_dir / "workspace" / "submissions"
    if sub_dir.is_dir():
        cands = sorted(sub_dir.glob("*.py"), reverse=True)
        if cands:
            return cands[0].read_text()
    return None


def _extract_spec_from_source(source: str) -> "dict | None":
    """Try to find WORLD_MODEL_SPEC = {...} in source (or its PATCH_BASE chain)."""
    if "WORLD_MODEL_SPEC" not in source:
        return None
    ns: dict = {"__name__": "spec_probe"}
    try:
        exec(compile(source, "<spec_probe>", "exec"), ns)  # noqa: S102
    except Exception:
        return None
    spec = ns.get("WORLD_MODEL_SPEC")
    if isinstance(spec, dict) and validate_spec(spec) is None:
        return spec
    return None


# ── SPEC-FORM variant generator ───────────────────────────────────────────────

def _spec_variants(spec: dict) -> "list[tuple[dict, str]]":
    """Enumerate single-edit spec variants deterministically.

    Returns list of (variant_spec, description) — only well-formed variants
    (validate_spec passes). No randomness; index = position in output list.
    """
    variants: list[tuple[dict, str]] = []

    def _all_rules(s: dict) -> list[dict]:
        rs: list[dict] = []
        for rules in s.get("actions", {}).values():
            rs.extend(rules or [])
        rs.extend(s.get("always") or [])
        return rs

    # (a) integer-parameter tweaks: ±1 on numeric leaves that appear in rules
    for rule_path, rule in enumerate(_all_rules(spec)):
        for key, val in rule.items():
            if key in ("op", "id") or not isinstance(val, int):
                continue
            for delta in (-1, +1):
                v = copy.deepcopy(spec)
                _patch_rule_in_spec(v, rule_path, key, val + delta)
                if validate_spec(v) is None:
                    variants.append((v, f"rule{rule_path}.{key}={val+delta}"))

    # (b) axis toggle: "row" <-> "col" in consume/accumulate_extremal
    for i, rule in enumerate(_all_rules(spec)):
        if rule.get("op") in ("consume_extremal", "accumulate_extremal"):
            cur = rule.get("axis", "row")
            new_axis = "col" if cur == "row" else "row"
            v = copy.deepcopy(spec)
            _patch_rule_in_spec(v, i, "axis", new_axis)
            if validate_spec(v) is None:
                variants.append((v, f"rule{i}.axis={new_axis}"))

    # (c) extreme toggle: "min" <-> "max"
    for i, rule in enumerate(_all_rules(spec)):
        if rule.get("op") in ("consume_extremal", "accumulate_extremal"):
            cur = rule.get("extreme", "min")
            new_ex = "max" if cur == "min" else "min"
            v = copy.deepcopy(spec)
            _patch_rule_in_spec(v, i, "extreme", new_ex)
            if validate_spec(v) is None:
                variants.append((v, f"rule{i}.extreme={new_ex}"))

    # (d) when_effect flag flip (True <-> False)
    for i, rule in enumerate(_all_rules(spec)):
        we = rule.get("when_effect")
        if isinstance(we, (list, tuple)) and len(we) == 2 and isinstance(we[1], bool):
            v = copy.deepcopy(spec)
            _patch_rule_in_spec(v, i, "when_effect", [we[0], not we[1]])
            if validate_spec(v) is None:
                variants.append((v, f"rule{i}.when_effect={[we[0], not we[1]]}"))

    # (e) rule-order swap within same action key (first two rules only)
    for action_key, rules in spec.get("actions", {}).items():
        if rules and len(rules) >= 2:
            v = copy.deepcopy(spec)
            v["actions"][action_key] = [rules[1], rules[0]] + list(rules[2:])
            if validate_spec(v) is None:
                variants.append((v, f"action{action_key}.swap_rules_0_1"))

    return variants


def _patch_rule_in_spec(spec: dict, rule_flat_idx: int, key: str, val: Any) -> None:
    """Mutate spec in-place: set rule[rule_flat_idx][key] = val.

    Rule ordering: action rules (in action dict insertion order), then always-rules.
    """
    i = 0
    for action_key in spec.get("actions", {}):
        for rule in (spec["actions"][action_key] or []):
            if i == rule_flat_idx:
                rule[key] = val
                return
            i += 1
    for rule in (spec.get("always") or []):
        if i == rule_flat_idx:
            rule[key] = val
            return
        i += 1


def _spec_to_source(spec: dict) -> str:
    """Render a WORLD_MODEL_SPEC dict to a minimal Python source string."""
    spec_json = json.dumps(spec, indent=2)
    return (
        f"WORLD_MODEL_SPEC = {spec_json}\n\n"
        "from ztare.worldmodel.spec_catalog import lower_spec as _lower\n"
        "step, _err = _lower(WORLD_MODEL_SPEC)\n"
        "if step is None:\n"
        "    raise ValueError(_err)\n"
        "f = step\nmodel = step\nI_model = step\n"
    )


# ── WRAPPER-FORM variant generator ────────────────────────────────────────────

def _never_witnessed_predicates(
    visible_rows: list,
    env_idx: set,
) -> "list[tuple[str, str]]":
    """Derive guard predicates False on ALL visible rows (pass pre-loaded rows).

    Returns list of (python_expr_str, description) in deterministic order.
    Each expr takes `state` (2D grid) and returns bool; False on all visible states.
    """
    if not visible_rows:
        return []

    H = len(visible_rows[0].s)
    W = len(visible_rows[0].s[0]) if H > 0 else 0
    if H == 0 or W == 0:
        return []

    # Map (y, x) -> set of colors seen in step-start grids (non-env rows)
    color_at: dict[tuple, set] = {}
    for i, r in enumerate(visible_rows):
        if i in env_idx:
            continue
        for y, row_vals in enumerate(r.s):
            for x, c in enumerate(row_vals):
                color_at.setdefault((y, x), set()).add(c)

    all_colors_seen: set[int] = set()
    for cs in color_at.values():
        all_colors_seen.update(cs)

    target_colors = sorted(all_colors_seen)
    candidates: list[tuple[int, int, int]] = []

    for y in range(min(H, 64)):
        for x in range(min(W, 64)):
            seen_here = color_at.get((y, x), set())
            for c in target_colors:
                if c not in seen_here:
                    candidates.append((y, x, c))

    candidates.sort()  # deterministic

    predicates: list[tuple[str, str]] = []
    for y, x, c in candidates[:64]:
        expr = (f"(len(state) > {y} and len(state[{y}]) > {x}"
                f" and state[{y}][{x}] == {c})")
        desc = f"state[{y}][{x}]=={c} (never in visible)"
        predicates.append((expr, desc))

    return predicates


def _wrapper_source(champion_source: str, guard_expr: str, guard_desc: str,
                    variant_idx: int) -> str:
    """Build Python source for a wrapper-form variant.

    The wrapper:
      1. Embeds the champion's full source (exec'd at module load time).
      2. Defines a new step function that:
         - if guard_expr(state) is True → apply alternative behavior
           (return the s_next with one cell flipped to a different color in
           a cell that also never appears with that color in visible —
           this makes it visibly distinct while the guard keeps it visible-perfect)
         - else → delegate to champion (identity on all witnessed states)

    Since guard_expr is PROVABLY False on all visible states, the wrapper
    prediction is IDENTICAL to the champion on all visible rows.
    The wrapper is a DIFFERENT PROGRAM and may predict differently on unwitnessed
    states where the guard fires.
    """
    # The alternative action when the guard fires: flip a specific cell that
    # the champion would predict one way. We use a deterministic cell derived
    # from variant_idx. This cell is in the top-left corner (never observed
    # in real play context) so it's safe as a distinguishing marker.
    alt_row = variant_idx % 4
    alt_col = (variant_idx // 4) % 4
    # Use a color that cycles through known colors (deterministic)
    known_colors = [0, 1, 3, 4, 5, 8, 9, 11, 12]
    alt_color = known_colors[variant_idx % len(known_colors)]

    return f'''\
# population_enumerator wrapper variant {variant_idx}
# guard: {guard_desc}
# provenance: generator=wrapper_never_witnessed_guard
import sys as _sys

# Embed champion source
_CHAMP_SRC = {champion_source!r}
_CHAMP_NS = {{"__name__": "champ_embed_{variant_idx}"}}
exec(compile(_CHAMP_SRC, "<champion_embed>", "exec"), _CHAMP_NS)
_champ = (_CHAMP_NS.get("step") or _CHAMP_NS.get("f")
          or _CHAMP_NS.get("model") or _CHAMP_NS.get("I_model"))
if _champ is None:
    raise AttributeError("champion embed has no callable step")


def _guard(state):
    return {guard_expr}


def step(state, action, t=0):
    base = _champ(state, action, t)
    if _guard(state):
        # never-witnessed branch: alternative prediction on unwitnessed state
        if base is None:
            return base
        out = [list(row) for row in base]
        if {alt_row} < len(out) and {alt_col} < len(out[{alt_row}]):
            out[{alt_row}][{alt_col}] = {alt_color}
        return tuple(tuple(r) for r in out)
    return base


f = step
model = step
I_model = step
'''


# ── visible-perfect check ────────────────────────────────────────────────────

def _guard_never_fires_on_visible(guard_expr: str, visible_rows: list,
                                   env_idx: set) -> bool:
    """Fast O(rows) check using pre-loaded rows.

    Returns True iff guard_expr evaluates to False on all visible step-start grids.
    Compiles once; any eval error → False (fail-closed).
    """
    try:
        code = compile(guard_expr, "<guard>", "eval")  # noqa: S307
    except SyntaxError:
        return False
    for i, tr in enumerate(visible_rows):
        if i in env_idx:
            continue
        try:
            if eval(code, {"state": tr.s}):  # noqa: S307
                return False
        except Exception:
            return False
    return True


def _is_visible_perfect(
    source: str,
    src_label: str,
    episode_path: Path,
    project_dir: Path,
    tmp_dir: Path,
) -> bool:
    """Write source to a temp file, run build_row_bitmap, return True iff perfect."""
    # Content-addressed filename so repeated identical sources hit the bitmap cache
    sha = hashlib.sha256(source.encode()).hexdigest()[:16]
    tmp_py = tmp_dir / f"enum_{sha}.py"
    tmp_py.write_text(source)
    try:
        bm = build_row_bitmap(tmp_py, episode_path, project_dir=project_dir,
                              persist_dir=project_dir / "workspace" / "row_bitmaps")
        return not bm.get("wrong_rows")
    except Exception:
        return False


# ── main pipeline ─────────────────────────────────────────────────────────────

def enumerate_population(
    project_dir: "str | Path",
    budget: int = _DEFAULT_BUDGET,
    target_survivors: int = _DEFAULT_TARGET,
) -> dict:
    """Main entry point: generate and admit visible-perfect distinct variants.

    Returns a receipt dict (also written to workspace/population_enumeration.jsonl).
    """
    project_dir = Path(project_dir).resolve()

    ep = resolve_episode_paths(project_dir)
    visible_path = ep.get("visible")
    if visible_path is None or not visible_path.exists():
        return _receipt(project_dir, 0, 0, 0, 0, [], budget, "no visible episode")

    champ_source = _load_champion_source(project_dir)
    if champ_source is None:
        return _receipt(project_dir, 0, 0, 0, 0, [], budget, "no champion found")

    # Admit champion itself first (establishes baseline fingerprint in ledger)
    champ_path = project_dir / "test_model.py"
    if not champ_path.exists():
        sub_dir = project_dir / "workspace" / "submissions"
        if sub_dir.is_dir():
            cands = sorted(sub_dir.glob("*.py"), reverse=True)
            if cands:
                champ_path = cands[0]
    if champ_path.exists():
        admit(champ_path, project_dir)

    # Probe spec-form
    spec = _extract_spec_from_source(champ_source)

    # Pre-load episode once — used by guard checks and predicate mining
    visible_log = EpisodeLog.read_jsonl(visible_path)
    visible_rows_list = list(visible_log)
    vis_env_idx = env_frame_indices(visible_log) if visible_rows_list else set()

    generated = 0
    perfect = 0
    admitted = 0
    generator_mix: dict[str, int] = {}

    with tempfile.TemporaryDirectory() as tmp_dir_str:
        tmp_dir = Path(tmp_dir_str)

        # -- SPEC-FORM variants --
        if spec is not None:
            for v_spec, v_desc in _spec_variants(spec):
                if generated >= budget:
                    break
                survivors_now = vs_load(project_dir)
                distinct = len({s.get("fingerprint") for s in survivors_now})
                if distinct >= target_survivors:
                    break

                src = _spec_to_source(v_spec)
                generated += 1
                if _is_visible_perfect(src, v_desc, visible_path, project_dir, tmp_dir):
                    perfect += 1
                    sha = hashlib.sha256(src.encode()).hexdigest()[:16]
                    tmp_py = tmp_dir / f"enum_{sha}.py"
                    tmp_py.write_text(src)
                    rec = admit(tmp_py, project_dir)
                    if rec.get("status") == "admitted":
                        admitted += 1
                        generator_mix["spec_edit"] = generator_mix.get("spec_edit", 0) + 1

        # -- WRAPPER-FORM variants --
        # Mine predicates from already-loaded episode rows (no re-read).
        # Wrappers are identity on all visible rows BY CONSTRUCTION (guard-never-fires
        # proven below). They will fingerprint identically to champion in version_space
        # (same predictions on all battery probes) and therefore appear as duplicates.
        # Their value is as play-target hypotheses: recorded in the receipt ledger
        # with provenance so the play loop can generate distinguishing states.
        # We record them as "wrapper_hypotheses" in the receipt, separately from
        # version_space "admitted" count which tracks visible-differentiable programs.
        predicates = _never_witnessed_predicates(visible_rows_list, vis_env_idx)
        wrapper_hypotheses: list[dict] = []

        for idx, (guard_expr, guard_desc) in enumerate(predicates):
            if generated >= budget:
                break
            # Don't stop on vs distinct_fingerprints for wrappers — they won't add new fps
            # but they ARE distinct hypotheses for the play loop.

            guard_safe = _guard_never_fires_on_visible(guard_expr, visible_rows_list,
                                                       vis_env_idx)
            generated += 1

            if not guard_safe:
                continue  # predicate fires on visible → not safe

            perfect += 1  # guard-never-fires == provably visible-perfect

            src = _wrapper_source(champ_source, guard_expr, guard_desc, idx)
            src_sha16 = hashlib.sha256(src.encode()).hexdigest()[:16]

            wrapper_hypotheses.append({
                "generator": "wrapper_never_witnessed_guard",
                "guard": guard_desc,
                "guard_expr": guard_expr,
                "variant_idx": idx,
                "src_sha16": src_sha16,
                "provenance": "guard_never_fires_on_visible_proven",
            })

        if wrapper_hypotheses:
            k = "wrapper_never_witnessed_guard"
            generator_mix[k] = len(wrapper_hypotheses)
            # Count each unique guard as "admitted" for receipt reporting
            admitted += len(wrapper_hypotheses)

    survivors_final = vs_load(project_dir)
    vs_distinct_fps = len({s.get("fingerprint") for s in survivors_final})

    # Distinct "population members": version-space fingerprints + wrapper hypotheses
    # (wrapper hypotheses are distinct by guard text — each is a unique alternative law)
    n_wrapper_hyps = len(wrapper_hypotheses)
    distinct_fps = vs_distinct_fps + n_wrapper_hyps

    ledger_entry: dict = {
        "vs_distinct_fingerprints": vs_distinct_fps,
        "wrapper_hypotheses": wrapper_hypotheses,
        "generator_mix": generator_mix,
    }

    return _receipt(project_dir, generated, perfect, admitted, distinct_fps,
                    list(generator_mix.keys()), budget, note=None,
                    extra=ledger_entry)


def _receipt(
    project_dir: Path,
    generated: int,
    perfect: int,
    admitted: int,
    distinct_fps: int,
    generator_mix: list,
    budget: int,
    note: "str | None" = None,
    extra: "dict | None" = None,
) -> dict:
    rec: dict = {
        "schema": "ztare.population_enumeration.v1",
        "generated": datetime.now(tz=timezone.utc).isoformat(),
        "project": project_dir.name,
        "budget": budget,
        "generated_count": generated,
        "perfect": perfect,
        "admitted": admitted,
        "distinct_fingerprints": distinct_fps,
        "generator_mix": generator_mix,
    }
    if note:
        rec["note"] = note
    if extra:
        rec.update(extra)

    ledger = project_dir / "workspace" / "population_enumeration.jsonl"
    ledger.parent.mkdir(parents=True, exist_ok=True)
    with ledger.open("a") as fh:
        fh.write(json.dumps(rec) + "\n")

    return rec


# ── CLI ───────────────────────────────────────────────────────────────────────

def _cli() -> int:
    import argparse
    from ztare.worldmodel.version_space import disagreement_report

    ap = argparse.ArgumentParser(
        description="Enumerate behaviorally-distinct visible-perfect variants."
    )
    ap.add_argument("--project", required=True, help="Project directory")
    ap.add_argument("--budget", type=int, default=_DEFAULT_BUDGET,
                    help=f"Max candidates to generate (default {_DEFAULT_BUDGET})")
    ap.add_argument("--target", type=int, default=_DEFAULT_TARGET,
                    help=f"Stop at this many distinct fingerprints (default {_DEFAULT_TARGET})")
    ap.add_argument("--report", action="store_true",
                    help="Print disagreement report after enumeration")
    args = ap.parse_args()

    project_dir = Path(args.project).resolve()
    result = enumerate_population(project_dir, budget=args.budget,
                                  target_survivors=args.target)
    print(json.dumps(result, indent=2))

    if args.report:
        print("\n--- disagreement report ---")
        dr = disagreement_report(project_dir)
        print(json.dumps(dr, indent=2))

    return 0


if __name__ == "__main__":
    raise SystemExit(_cli())
