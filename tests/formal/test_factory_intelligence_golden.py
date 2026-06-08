#!/usr/bin/env python3
"""Golden-master regression for `factory_intelligence` — the SAFETY NET for the Action-4 refactor.

Locks the recommendation contract — the sorted `(class, priority)` list `build()` emits on a FIXED,
fully-absent input fixture — which is EXACTLY the surface `24x7_runner` keys self-correction off. Any
refactor (the `_dict_field` safe-getter dedup, the `_recommendations` rule-table conversion, a package
split) must keep this byte-identical; this test fails loudly if it drifts.

Determinism: `_now()` is frozen to a constant and every file input points at an absent tempdir path
(so each read-model takes its deterministic missing-path). The volatile `move_space_yield` pane (it
reads the live attempts DB) is excluded — it is display-only and drives no recommendation. The test
also builds TWICE and asserts the two recommendation lists are identical, so the locked hash is trusted.

Run: `python3 tests/formal/test_factory_intelligence_golden.py`  (records the golden on first run).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tempfile
from pathlib import Path

_HERE = Path(__file__).resolve()
_REPO = _HERE.parents[2]
_FI_DIR = _REPO / "scripts" / "public" / "control" / "leanmill"
sys.path.insert(0, str(_FI_DIR))
sys.path.insert(0, str(_REPO / "src"))

import factory_intelligence as fi  # noqa: E402
import work_queue  # noqa: E402  (resolved via _FI_DIR on sys.path, same as the module itself)

_GOLDEN = _HERE.parent / "factory_intelligence_recs.golden.json"
_FROZEN_NOW = 1_700_000_000  # any fixed epoch; kills _now() timestamp volatility
_SCALAR_ARGS = {"event_tail", "window_s", "integration_receipt_limit",
                "worker_heartbeat_stale_s", "policy_profile", "self_test"}


def _deterministic_args(tmp: Path) -> argparse.Namespace:
    """Reuse the module's REAL parser (so the arg surface can never drift from the test), then redirect
    every input at an absent tempdir path + neutralize outputs."""
    args = fi._build_arg_parser().parse_args([])
    for name in vars(args):
        if name in _SCALAR_ARGS:
            continue
        if name in ("out", "md"):
            setattr(args, name, None)  # guarded in build(); skip writing artifacts
        elif name == "queue_db":
            setattr(args, name, str(tmp / "empty.sqlite"))
        else:
            setattr(args, name, str(tmp / f"absent__{name}"))
    work_queue.connect(str(tmp / "empty.sqlite"))  # create the empty queue schema build() reads
    return args


def _recommendation_contract() -> list[list]:
    orig_now = fi._now
    fi._now = lambda: _FROZEN_NOW  # type: ignore[assignment]
    try:
        with tempfile.TemporaryDirectory(prefix="fi_golden_") as td:
            payload = fi.build(_deterministic_args(Path(td)))
    finally:
        fi._now = orig_now  # type: ignore[assignment]
    recs = payload.get("recommendations") or []
    return sorted([str(r.get("class")), int(r.get("priority"))] for r in recs)


def main() -> int:
    contract_a = _recommendation_contract()
    contract_b = _recommendation_contract()
    if contract_a != contract_b:
        print("[FAIL] non-deterministic: two builds produced different recommendation contracts")
        return 1
    blob = json.dumps(contract_a, sort_keys=True)
    digest = hashlib.sha256(blob.encode()).hexdigest()
    if not _GOLDEN.exists():
        _GOLDEN.write_text(json.dumps({"sha256": digest, "contract": contract_a}, indent=2) + "\n")
        print(f"[RECORDED] golden master: {len(contract_a)} recommendations, sha256={digest[:16]}…")
        print(f"           -> {_GOLDEN}")
        return 0
    want = json.loads(_GOLDEN.read_text())
    if digest == want.get("sha256"):
        print(f"[PASS] golden match: {len(contract_a)} recommendations, sha256={digest[:16]}…")
        return 0
    print(f"[FAIL] recommendation contract changed!\n  expected sha256={want.get('sha256')}\n  got      sha256={digest}")
    have = {tuple(x) for x in contract_a}
    had = {tuple(x) for x in want.get("contract", [])}
    for added in sorted(have - had):
        print(f"    + {added}")
    for removed in sorted(had - have):
        print(f"    - {removed}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
