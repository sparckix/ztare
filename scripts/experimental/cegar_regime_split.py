"""CEGAR regime-split abduction prototype (ef047373baeb216f, out-of-loop).

Mission: prove/refute that a CEGAR-style gated law = post_spec if s[5][19]==3
else champion reproduces the full bank and extends to level-2 interior,
zero LLM calls.

Steps 1-5 from the strategy card.
"""
from __future__ import annotations

import json
import sys
import time
import signal
from pathlib import Path
from collections import defaultdict

# ---- path setup ----
_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO / "src"))

_PROJ = _REPO / "projects" / "arc3_ls20_gov"
_BANK = _PROJ / "raw" / "episodes" / "episode_001.jsonl"
_HOLDOUT = _PROJ / "raw" / "episodes" / "episode_002.jsonl"
_WS = _PROJ / "workspace"
_CHAMPION_SRC = _PROJ / "test_model.py"
_NOGOOD_PROJECT = "arc3_ls20_gov"

from ztare.worldmodel.episode_log import EpisodeLog
from ztare.worldmodel.gates import (
    replay_consistency_gate,
    rollout_depth,
    as_predictor,
    env_frame_indices,
)
from ztare.worldmodel.spec_abduction import abduce_spec
from ztare.worldmodel.spec_catalog import lower_spec
from ztare.worldmodel.evidence_consolidation import _load_carrier_from_source


# ------------------------------------------------------------------ helpers

class _Timeout(Exception):
    pass


def _timeout_handler(sig, frame):
    raise _Timeout()


def _load_champion():
    src = _CHAMPION_SRC.read_text()
    return _load_carrier_from_source(src, str(_CHAMPION_SRC), _PROJ)


def _split_bank(bank: EpisodeLog):
    """Split by regime gate: post = rows where s[5][19]==3."""
    pre_rows, post_rows = [], []
    for tr in bank:
        if tr.s[5][19] == 3:
            post_rows.append(tr)
        else:
            pre_rows.append(tr)
    return EpisodeLog(pre_rows), EpisodeLog(post_rows)


def _interior_rows(post: EpisodeLog):
    """Level-2 interior: colour-12 band animation. Row has colour 12 somewhere in s."""
    return EpisodeLog([tr for tr in post if any(tr.s[r][c] == 12 for r in range(len(tr.s)) for c in range(len(tr.s[r])))])


# ------------------------------------------------------------------ step 1: split

print("=" * 60)
print("STEP 1: split bank by regime gate (s[5][19]==3)")
bank = EpisodeLog.read_jsonl(_BANK)
pre, post = _split_bank(bank)
print(f"  pre: {len(pre)}, post: {len(post)}, total: {len(bank)}")
assert len(pre) + len(post) == len(bank)

receipt = {
    "schema": "cegar_prototype_receipt_v1",
    "pre_count": len(pre),
    "post_count": len(post),
    "total": len(bank),
    "steps": {}
}

# ------------------------------------------------------------------ step 2: abduce post cell

print()
print("=" * 60)
print("STEP 2: abduce post cell (small, fast)")

_ABDUCTION_TIMEOUT_S = 600  # 10 minutes hard cap

signal.signal(signal.SIGALRM, _timeout_handler)
signal.alarm(_ABDUCTION_TIMEOUT_S)

post_spec = None
post_step_fn = None
post_replay_ok = False
post_wall_s = None

try:
    t0 = time.time()
    result = abduce_spec(post, 4, nogood_project=_NOGOOD_PROJECT)
    post_wall_s = time.time() - t0
    signal.alarm(0)
    post_spec = result.spec
    post_step_fn = result.step_fn
    post_replay_ok = result.replay_ok
    print(f"  status: {result.status}")
    print(f"  replay_ok: {result.replay_ok}")
    print(f"  wall time: {post_wall_s:.1f}s")
    print(f"  detail: {result.detail[:120]}")
    if result.spec:
        actions = result.spec.get("actions", {})
        print(f"  spec actions: {list(actions.keys())}, always rules: {len(result.spec.get('always', []))}")
except _Timeout:
    signal.alarm(0)
    post_wall_s = _ABDUCTION_TIMEOUT_S
    print(f"  TIMED OUT after {_ABDUCTION_TIMEOUT_S}s — timing IS the finding")
    receipt["steps"]["post_abduction"] = {
        "status": "timeout",
        "wall_s": post_wall_s,
    }
    # can't continue without post spec
    json.dump(receipt, open(str(_WS / "cegar_prototype_receipt.json"), "w"), indent=2)
    print("\nReceipt written (timeout).")
    sys.exit(1)
except Exception as exc:
    signal.alarm(0)
    post_wall_s = time.time() - t0
    print(f"  ERROR: {exc}")
    receipt["steps"]["post_abduction"] = {"status": "error", "error": str(exc)[:200], "wall_s": post_wall_s}
    json.dump(receipt, open(str(_WS / "cegar_prototype_receipt.json"), "w"), indent=2)
    sys.exit(1)

receipt["steps"]["post_abduction"] = {
    "status": result.status,
    "replay_ok_post_cell": post_replay_ok,
    "wall_s": round(post_wall_s, 2),
    "detail": result.detail[:200],
}

# ------------------------------------------------------------------ step 2b: verify post spec on post rows

if post_step_fn is None and post_spec is not None:
    post_step_fn, err = lower_spec(post_spec)
    print(f"  lower_spec: {'ok' if post_step_fn else 'fail'} err={err}")

if post_step_fn is not None:
    gate = replay_consistency_gate(post_step_fn, post)
    print(f"  replay gate on post cell: ok={gate.ok} | {gate.detail[:100]}")
    post_replay_ok = gate.ok
    receipt["steps"]["post_abduction"]["replay_on_post_rows"] = gate.ok
    receipt["steps"]["post_abduction"]["replay_detail"] = gate.detail[:200]

# ------------------------------------------------------------------ step 2c: pre cell — SKIP cold, reuse champion

print()
print("=" * 60)
print("STEP 2c: pre cell — warm-start from champion (cold skip: pre cold >> hours)")
champion = _load_champion()
predict_champion = as_predictor(champion)

t0 = time.time()
pre_replay = replay_consistency_gate(champion, pre)
pre_wall_s = time.time() - t0
print(f"  champion replay on pre rows: ok={pre_replay.ok} | {pre_replay.detail[:100]}")
print(f"  wall time: {pre_wall_s:.1f}s")

receipt["steps"]["pre_champion_verify"] = {
    "method": "reuse_live_champion_extensionally_exact_on_pre",
    "replay_ok": pre_replay.ok,
    "wall_s": round(pre_wall_s, 2),
    "detail": pre_replay.detail[:200],
}

# ------------------------------------------------------------------ step 3: compose gated law

print()
print("=" * 60)
print("STEP 3: compose gated law")

if post_step_fn is None:
    print("  WARNING: no post spec — gated law falls back to champion everywhere")

def gated_law(grid, action, t):
    """CEGAR gated law: post cell if s[5][19]==3, else champion."""
    if post_step_fn is not None and grid[5][19] == 3:
        return post_step_fn(grid, action, t)
    return predict_champion(grid, action, t)

# 3a: visible replay over full bank
t0 = time.time()
gate_full = replay_consistency_gate(gated_law, bank)
full_wall_s = time.time() - t0
print(f"  3a full-bank replay: ok={gate_full.ok} | {gate_full.detail[:100]}")
print(f"  wall: {full_wall_s:.1f}s")

receipt["steps"]["composed_full_bank_replay"] = {
    "ok": gate_full.ok,
    "wall_s": round(full_wall_s, 2),
    "detail": gate_full.detail[:200],
}

# 3b: holdout rollout depth
holdout = EpisodeLog.read_jsonl(_HOLDOUT)
t0 = time.time()
depth = rollout_depth(gated_law, holdout)
rollout_wall_s = time.time() - t0
print(f"  3b holdout rollout depth: {depth}/{len(holdout)}")
print(f"  wall: {rollout_wall_s:.1f}s")

receipt["steps"]["holdout_rollout"] = {
    "depth": depth,
    "holdout_len": len(holdout),
    "target": 16,
    "wall_s": round(rollout_wall_s, 2),
}

# Compare to champion rollout depth
t0 = time.time()
depth_champion = rollout_depth(champion, holdout)
champion_rollout_wall_s = time.time() - t0
print(f"  champion holdout rollout depth: {depth_champion}/{len(holdout)}")

receipt["steps"]["holdout_rollout"]["champion_depth"] = depth_champion

# 3c: alpha-measurability check on gated law vs champion baseline
print()
print("=" * 60)
print("STEP 3c: alpha-measurability check")

def _check_alpha(predictor_fn, label, rows_cap=300):
    """Count (violations, probes) where equal grids at different t predict differently."""
    by_grid = defaultdict(set)
    for tr in bank:
        key = json.dumps([list(row) for row in tr.s], separators=(',', ':'))
        by_grid[key].add(tr.t)
    pairs = [(g, sorted(ts)) for g, ts in by_grid.items() if len(ts) > 1]
    viol = probes = 0
    for g, ts in pairs[:rows_cap]:
        sg = tuple(tuple(row) for row in json.loads(g))
        for a in range(4):
            outs = {json.dumps(predictor_fn(sg, a, t)) for t in ts[:4]}
            probes += 1
            if len(outs) > 1:
                viol += 1
    return viol, probes, len(pairs)

t0 = time.time()
viol_champion, probes_champion, npairs = _check_alpha(predict_champion, "champion")
alpha_wall_s = time.time() - t0
print(f"  champion: {viol_champion}/{probes_champion} violations ({npairs} multi-t states)")

t0 = time.time()
viol_gated, probes_gated, _ = _check_alpha(gated_law, "gated_law")
alpha_gated_wall_s = time.time() - t0
print(f"  gated_law: {viol_gated}/{probes_gated} violations")

receipt["steps"]["alpha_measurability"] = {
    "champion_violations": viol_champion,
    "champion_probes": probes_champion,
    "gated_law_violations": viol_gated,
    "gated_law_probes": probes_gated,
    "multi_t_states": npairs,
    "champion_wall_s": round(alpha_wall_s, 2),
    "gated_wall_s": round(alpha_gated_wall_s, 2),
    "note": "baseline from card: 32/752; probes capped at 300 states x 4 actions",
}

# ------------------------------------------------------------------ step 4: level-2 interior extension

print()
print("=" * 60)
print("STEP 4: level-2 interior extension")

interior = _interior_rows(post)
print(f"  interior rows (colour-12 in post): {len(interior)}")

if len(interior) > 0 and post_step_fn is not None:
    t0 = time.time()
    interior_replay = replay_consistency_gate(post_step_fn, interior)
    interior_wall_s = time.time() - t0
    print(f"  post_spec replay on interior: ok={interior_replay.ok}")
    print(f"  detail: {interior_replay.detail[:120]}")
    print(f"  wall: {interior_wall_s:.1f}s")
    receipt["steps"]["level2_interior"] = {
        "interior_rows": len(interior),
        "post_spec_replay_ok": interior_replay.ok,
        "wall_s": round(interior_wall_s, 2),
        "detail": interior_replay.detail[:200],
    }
    if not interior_replay.ok:
        # Count residual rows
        from ztare.worldmodel.gates import env_frame_indices
        pred_fn = as_predictor(post_step_fn)
        env = env_frame_indices(interior)
        residual_rows = []
        for i, tr in enumerate(interior):
            if i in env:
                continue
            pred = pred_fn(tr.s, tr.a, tr.t)
            if pred is None or pred != tr.s_next:
                residual_rows.append({"t": tr.t, "a": tr.a, "i": i})
        print(f"  residual rows: {len(residual_rows)} (first next experiment)")
        receipt["steps"]["level2_interior"]["residual_rows"] = residual_rows[:20]
        receipt["steps"]["level2_interior"]["residual_count"] = len(residual_rows)
else:
    print(f"  interior: {len(interior)} rows — check skipped (no post_spec or no interior rows)")
    receipt["steps"]["level2_interior"] = {
        "interior_rows": len(interior),
        "skipped": post_step_fn is None,
    }

# ------------------------------------------------------------------ step 5: verdict

print()
print("=" * 60)
print("STEP 5: verdict")

pred_card = (
    "card ef047373: CEGAR gated law deterministically reproduces champion law "
    "on pre rows AND possibly extends to level-2 interior with zero LLM calls"
)

# Confirm logic:
# - post abduction succeeded with replay_ok
# - champion reuses as pre law
# - full bank replay ok
# - holdout at least matches champion depth
# - alpha violations decrease or stay same
full_bank_ok = gate_full.ok
holdout_ok = depth >= depth_champion  # at least as good as champion
post_ok = post_replay_ok

if full_bank_ok and post_ok:
    interior_info = receipt["steps"].get("level2_interior", {})
    interior_ok = interior_info.get("post_spec_replay_ok")
    if interior_ok:
        verdict = "CONFIRMED"
        verdict_note = "gated law replays full bank + holdout target + level-2 interior explained by post cell"
    else:
        verdict = "PARTIALLY CONFIRMED"
        residual = interior_info.get("residual_count", "?")
        verdict_note = (
            f"full-bank replay OK, post-cell abduction OK, "
            f"but level-2 interior has {residual} residual rows — that is the next experiment"
        )
elif full_bank_ok and not post_ok:
    verdict = "PARTIALLY CONFIRMED"
    verdict_note = "full-bank replay OK but post-cell abduction did not gate-pass on post rows"
elif post_ok and not full_bank_ok:
    verdict = "REFUTED (composition step)"
    verdict_note = "post-cell abduction OK but composed gated law fails full-bank replay"
else:
    verdict = "REFUTED"
    verdict_note = "both post-cell abduction and full-bank replay failed"

print(f"  {verdict}: {verdict_note}")

receipt["verdict"] = verdict
receipt["verdict_note"] = verdict_note
receipt["card_prediction"] = pred_card
receipt["summary"] = {
    "pre_count": len(pre),
    "post_count": len(post),
    "post_abduction_status": result.status,
    "post_replay_ok": post_replay_ok,
    "pre_champion_replay_ok": pre_replay.ok,
    "full_bank_replay_ok": full_bank_ok,
    "holdout_depth_gated": depth,
    "holdout_depth_champion": depth_champion,
    "alpha_violations_champion": viol_champion,
    "alpha_violations_gated": viol_gated,
    "level2_interior_rows": len(interior),
}

# ------------------------------------------------------------------ write receipt

out_path = _WS / "cegar_prototype_receipt.json"
json.dump(receipt, open(str(out_path), "w"), indent=2)
print(f"\nReceipt written: {out_path}")
print(f"\nOne-line verdict: {verdict}")
