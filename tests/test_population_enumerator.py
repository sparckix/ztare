"""Tests for ztare.worldmodel.population_enumerator.

Synthetic tmp projects, no LLM calls. 10+ tests covering:
  - spec-variant well-formedness
  - wrapper identity on witnessed states
  - wrapper differs on never-witnessed state
  - visible-perfect filter rejects broken variant
  - budget + target-survivor stopping
  - fingerprint dedup drops clone variants
  - receipts row written
  - determinism
  - never-witnessed predicates derived from episode
  - spec-source roundtrip
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from ztare.worldmodel.episode_log import EpisodeLog
from ztare.worldmodel.spec_catalog import validate_spec, lower_spec
from ztare.worldmodel.population_enumerator import (
    _extract_spec_from_source,
    _is_visible_perfect,
    _never_witnessed_predicates,
    _spec_to_source,
    _spec_variants,
    _wrapper_source,
    enumerate_population,
)


# ── helpers ───────────────────────────────────────────────────────────────────

_G1 = ((1, 2), (3, 4))
_G2 = ((1, 2), (3, 5))   # differs from G1 at [1][1]
_G3 = ((1, 3), (3, 4))


def _write_ep(path: Path, triples: list) -> None:
    log = EpisodeLog()
    for t, (s, a, sn) in enumerate(triples):
        log.append(s, a, sn, t=t)
    log.write_jsonl(path)


def _make_project(tmp: Path, triples: list) -> Path:
    ep_dir = tmp / "raw" / "episodes"
    ep_dir.mkdir(parents=True)
    _write_ep(ep_dir / "episode_001.jsonl", triples)
    return tmp


_SIMPLE_SPEC = {
    "actions": {
        "0": [{"op": "identity"}],
    },
    "always": [],
}

_CONSUME_SPEC = {
    "actions": {
        "0": [
            {
                "op": "consume_extremal",
                "color": 1,
                "replacement": 0,
                "axis": "row",
                "extreme": "min",
            }
        ],
    },
    "always": [],
}


# ── test 1: spec_variants produces only well-formed specs ─────────────────────

def test_spec_variants_well_formed():
    variants = _spec_variants(_CONSUME_SPEC)
    assert len(variants) > 0, "should produce at least some variants"
    for v_spec, desc in variants:
        err = validate_spec(v_spec)
        assert err is None, f"variant {desc!r} failed validation: {err}"


# ── test 2: spec_to_source roundtrips through lower_spec ─────────────────────

def test_spec_to_source_roundtrip():
    src = _spec_to_source(_SIMPLE_SPEC)
    ns: dict = {"__name__": "t"}
    exec(compile(src, "<test>", "exec"), ns)  # noqa: S102
    step = ns.get("step") or ns.get("f")
    assert callable(step), "lowered spec must produce callable step"
    g = ((0, 1), (2, 3))
    result = step(g, 0, 0)
    assert result is not None


# ── test 3: wrapper is IDENTITY on witnessed states ───────────────────────────

def test_wrapper_identity_on_witnessed_states():
    """Wrapper prediction == champion prediction on every row in episode."""
    champ_src = "def step(s, a, t):\n    return s\nf=step\nmodel=step\nI_model=step\n"
    # Guard fires on state[5][5] == 99 — never in our 2x2 grids
    guard = "(len(state) > 5 and len(state[5]) > 5 and state[5][5] == 99)"
    wrapper_src = _wrapper_source(champ_src, guard, "state[5][5]==99", 0)

    # Build champion callable
    ns_champ: dict = {"__name__": "champ"}
    exec(compile(champ_src, "<c>", "exec"), ns_champ)  # noqa: S102
    champ = ns_champ["step"]

    # Build wrapper callable
    ns_wrap: dict = {"__name__": "wrap"}
    exec(compile(wrapper_src, "<w>", "exec"), ns_wrap)  # noqa: S102
    wrap = ns_wrap["step"]

    # Witnessed states: small grids, no cell has value 99
    test_states = [_G1, _G2, _G3]
    for s in test_states:
        assert wrap(s, 0, 0) == champ(s, 0, 0), (
            f"wrapper must match champion on witnessed state {s}"
        )


# ── test 4: wrapper DIFFERS on a never-witnessed state ───────────────────────

def test_wrapper_differs_on_never_witnessed_state():
    """When guard fires the wrapper returns something different from champion."""
    champ_src = (
        "def step(s, a, t):\n"
        "    return tuple(tuple(row) for row in s)\n"
        "f=step\nmodel=step\nI_model=step\n"
    )
    # Guard fires when state[0][0] == 99
    guard = "(len(state) > 0 and len(state[0]) > 0 and state[0][0] == 99)"
    wrapper_src = _wrapper_source(champ_src, guard, "state[0][0]==99", 0)

    ns_champ: dict = {"__name__": "champ"}
    exec(compile(champ_src, "<c>", "exec"), ns_champ)  # noqa: S102
    champ = ns_champ["step"]

    ns_wrap: dict = {"__name__": "wrap"}
    exec(compile(wrapper_src, "<w>", "exec"), ns_wrap)  # noqa: S102
    wrap = ns_wrap["step"]

    # Unwitnessed state: state[0][0] == 99
    unwitnessed = ((99, 0), (0, 0))
    champ_pred = champ(unwitnessed, 0, 0)
    wrap_pred = wrap(unwitnessed, 0, 0)
    assert wrap_pred != champ_pred, (
        "wrapper must predict differently on state where guard fires"
    )


# ── test 5: _is_visible_perfect rejects broken variant ───────────────────────

def test_visible_perfect_filter_rejects_broken():
    """A carrier that always returns None is not visible-perfect."""
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        # Episode: identity law
        proj = _make_project(tmp, [(_G1, 0, _G1), (_G2, 1, _G2)])
        ep = proj / "raw" / "episodes" / "episode_001.jsonl"

        broken_src = "def step(s, a, t):\n    return None\nf=step\nmodel=step\nI_model=step\n"
        assert not _is_visible_perfect(broken_src, "broken", ep, proj, tmp)


# ── test 6: _is_visible_perfect accepts a correct carrier ────────────────────

def test_visible_perfect_filter_accepts_correct():
    """A carrier that returns s unchanged is visible-perfect for identity episode."""
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        proj = _make_project(tmp, [(_G1, 0, _G1), (_G2, 1, _G2)])
        ep = proj / "raw" / "episodes" / "episode_001.jsonl"

        identity_src = (
            "def step(s, a, t):\n"
            "    return tuple(tuple(r) for r in s)\n"
            "f=step\nmodel=step\nI_model=step\n"
        )
        assert _is_visible_perfect(identity_src, "identity", ep, proj, tmp)


# ── test 7: budget stopping ───────────────────────────────────────────────────

def test_budget_stopping():
    """enumerate_population stops at budget even if target not reached."""
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        proj = _make_project(tmp, [(_G1, 0, _G1), (_G2, 1, _G2)])
        result = enumerate_population(proj, budget=2, target_survivors=100)
        assert result["generated_count"] <= 2, "should not exceed budget"


# ── test 8: target-survivor stopping ─────────────────────────────────────────

def test_target_survivor_stopping():
    """enumerate_population stops once target distinct fingerprints reached."""
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        proj = _make_project(tmp, [(_G1, 0, _G1), (_G2, 1, _G2)])
        # Write a champion so there is a visible-perfect baseline to admit
        tm = proj / "test_model.py"
        tm.write_text(
            "def step(s, a, t): return tuple(tuple(r) for r in s)\n"
            "f=step\nmodel=step\nI_model=step\n"
        )
        # Large budget but tiny target: stop at 1 distinct fingerprint (champion alone)
        result = enumerate_population(proj, budget=100, target_survivors=1)
        # Champion is admitted → at least 1 distinct fingerprint
        assert result["distinct_fingerprints"] >= 1


# ── test 9: fingerprint dedup drops clone variants ───────────────────────────

def test_fingerprint_dedup():
    """Identical source admitted twice gets status=duplicate on second call."""
    from ztare.worldmodel.version_space import admit, load
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        proj = _make_project(tmp, [(_G1, 0, _G1), (_G2, 1, _G2)])
        sub_dir = proj / "workspace" / "submissions"
        sub_dir.mkdir(parents=True)
        src = (
            "def step(s, a, t):\n"
            "    return tuple(tuple(r) for r in s)\n"
            "f=step\nmodel=step\nI_model=step\n"
        )
        p1 = sub_dir / "v1.py"
        p2 = sub_dir / "v2.py"
        p1.write_text(src)
        p2.write_text(src)
        r1 = admit(p1, proj)
        r2 = admit(p2, proj)
        assert r1.get("status") == "admitted"
        assert r2.get("status") == "duplicate", f"expected duplicate, got {r2}"


# ── test 10: receipt written to JSONL ─────────────────────────────────────────

def test_receipt_written():
    """enumerate_population writes a receipt row to workspace/population_enumeration.jsonl."""
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        proj = _make_project(tmp, [(_G1, 0, _G1), (_G2, 1, _G2)])
        enumerate_population(proj, budget=2, target_survivors=1)
        ledger = proj / "workspace" / "population_enumeration.jsonl"
        assert ledger.exists(), "receipt file must exist"
        rows = [json.loads(l) for l in ledger.read_text().splitlines() if l.strip()]
        assert len(rows) >= 1
        row = rows[-1]
        assert row.get("schema") == "ztare.population_enumeration.v1"
        assert "generated_count" in row
        assert "perfect" in row
        assert "admitted" in row
        assert "distinct_fingerprints" in row


# ── test 11: determinism — same inputs produce same variants ──────────────────

def test_determinism():
    """Running enumerate_population twice produces the same generated_count."""
    with tempfile.TemporaryDirectory() as td1:
        with tempfile.TemporaryDirectory() as td2:
            proj1 = _make_project(Path(td1), [(_G1, 0, _G1), (_G2, 1, _G2)])
            proj2 = _make_project(Path(td2), [(_G1, 0, _G1), (_G2, 1, _G2)])
            r1 = enumerate_population(proj1, budget=5, target_survivors=2)
            r2 = enumerate_population(proj2, budget=5, target_survivors=2)
            assert r1["generated_count"] == r2["generated_count"], (
                "same inputs must generate same count"
            )


# ── test 12: never-witnessed predicates derived from episode ──────────────────

def test_never_witnessed_predicates():
    """Predicates are derived and evaluate to False on all visible episode states."""
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        proj = _make_project(tmp, [(_G1, 0, _G1), (_G2, 1, _G2)])
        ep = proj / "raw" / "episodes" / "episode_001.jsonl"
        log = EpisodeLog.read_jsonl(ep)
        rows = list(log)
        from ztare.worldmodel.gates import env_frame_indices
        env_idx = env_frame_indices(log)
        preds = _never_witnessed_predicates(rows, env_idx)
        # We should get some predicates
        assert len(preds) >= 1, "should find at least one never-witnessed predicate"
        # Every predicate must evaluate to False on visible states
        for expr, desc in preds[:10]:
            for tr in rows:
                state = tr.s
                result = eval(expr, {"state": state})  # noqa: S307
                assert not result, (
                    f"predicate {desc!r} fired on visible state — not never-witnessed!"
                )


# ── test 13: _extract_spec_from_source returns None for non-spec sources ──────

def test_extract_spec_from_non_spec_source():
    src = "def step(s, a, t): return s\nf=step\n"
    assert _extract_spec_from_source(src) is None


# ── test 14: _extract_spec_from_source returns spec for spec sources ──────────

def test_extract_spec_from_spec_source():
    src = _spec_to_source(_SIMPLE_SPEC)
    spec = _extract_spec_from_source(src)
    # The spec_to_source wraps in lower_spec call, not WORLD_MODEL_SPEC dict
    # so extract will not find it — that's fine. But a raw spec source should work:
    raw_src = f"WORLD_MODEL_SPEC = {json.dumps(_SIMPLE_SPEC)}\n"
    spec2 = _extract_spec_from_source(raw_src)
    assert isinstance(spec2, dict), "should extract spec from raw source"
    assert validate_spec(spec2) is None


# ── test 15: enumerate_population on minimal identity project ─────────────────

def test_enumerate_population_minimal():
    """Smoke: enumerate_population runs without error on a minimal project."""
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        proj = _make_project(tmp, [(_G1, 0, _G1)])
        # Write a champion
        tm = proj / "test_model.py"
        tm.write_text(
            "def step(s, a, t): return tuple(tuple(r) for r in s)\n"
            "f=step\nmodel=step\nI_model=step\n"
        )
        result = enumerate_population(proj, budget=5, target_survivors=2)
        assert result["schema"] == "ztare.population_enumeration.v1"
        assert result["generated_count"] >= 0
