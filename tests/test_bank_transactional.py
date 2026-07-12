"""Transactional substrate edits: a FAILED bank leaves the theory file byte-identical (no corruption / no
half-reverted residue), a SUCCESSFUL bank appends atomically, and neither litters a temp file. This is the
invariant behind the 2026-07-02 median-voter substrate-corruption fix (in-place `open("a")` → atomic `os.replace`).

Runnable: `python tests/test_bank_transactional.py`. Hermetic — injects reverify_fn, no Lean.
"""
import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
from ztare.leanmill.solver import family_lemma_library as fll  # noqa: E402
from ztare.leanmill.solver.family_lemma_library import bank, bank_decl_to_env, _atomic_write, _default_reverify  # noqa: E402

_BASE = "import Mathlib\n\ntheorem base : True := trivial\n"
_RUNG = "theorem foo : True := trivial\n"


def test_failed_bank_is_byte_identical():
    d = tempfile.mkdtemp()
    ctx = pathlib.Path(d) / "theory.lean"
    ctx.write_text(_BASE, encoding="utf-8")
    before = ctx.read_text(encoding="utf-8")
    # realistic non-porting rung: the appended file fails reverify, the reverted clean file passes → the classifier
    # sees a known-good `before` and reports `reverted_noncompile` (not the dead-instrument branch).
    rv = lambda pth, _root: "foo" not in pathlib.Path(pth).read_text(encoding="utf-8")
    r = bank_decl_to_env(ctx, "foo", _RUNG, d, reverify_fn=rv)
    assert r["banked_as"] is None and r["reason"] == "reverted_noncompile", r
    assert ctx.read_text(encoding="utf-8") == before, "FAILED bank changed the substrate (corruption class)"
    assert not list(pathlib.Path(d).glob("*.tmp")), "left an atomic-write temp behind"
    print("OK: failed bank leaves substrate byte-identical, no temp litter")


def test_success_bank_appends_atomically():
    d = tempfile.mkdtemp()
    ctx = pathlib.Path(d) / "theory.lean"
    ctx.write_text(_BASE, encoding="utf-8")
    r = bank_decl_to_env(ctx, "foo", _RUNG, d, reverify_fn=lambda _p, _root: True)  # porting rung
    assert r["banked_as"] and "foo" in r["banked_as"], r
    text = ctx.read_text(encoding="utf-8")
    assert text.startswith(_BASE.rstrip("\n")), "append clobbered the existing content"
    assert "foo" in text and "base" in text
    assert not list(pathlib.Path(d).glob("*.tmp"))
    print("OK: successful bank appends atomically, existing content intact")


def test_failed_bank_reverifies_candidate_before_live_swap():
    d = tempfile.mkdtemp()
    ctx = pathlib.Path(d) / "theory.lean"
    ctx.write_text(_BASE, encoding="utf-8")
    before = ctx.read_text(encoding="utf-8")
    candidate_seen = []

    def rv(pth, _root):
        path = pathlib.Path(pth)
        if path.resolve() != ctx.resolve():
            candidate_seen.append(path)
            assert ctx.read_text(encoding="utf-8") == before, "candidate reverify mutated live substrate"
            assert "foo" in path.read_text(encoding="utf-8")
            return False
        assert ctx.read_text(encoding="utf-8") == before
        return True

    r = bank_decl_to_env(ctx, "foo", _RUNG, d, reverify_fn=rv)
    assert r["banked_as"] is None and r["reason"] == "reverted_noncompile", r
    assert candidate_seen, "reverify should inspect a sibling candidate file before live swap"
    assert ctx.read_text(encoding="utf-8") == before
    assert not list(pathlib.Path(d).glob("*.candidate.*.lean"))
    print("OK: failed bank verifies candidate bytes before live swap")


def test_atomic_write_no_partial_and_no_litter():
    d = tempfile.mkdtemp()
    f = pathlib.Path(d) / "x.lean"
    import ztare.formal.repl_compile as rc
    rc._FILE_ENV_CACHE[str(f.resolve())] = (0.0, 0, "old", 123)
    _atomic_write(f, "hello\n")
    assert str(f.resolve()) not in rc._FILE_ENV_CACHE
    _atomic_write(f, "world\n")            # overwrite is a clean replace
    assert f.read_text(encoding="utf-8") == "world\n"
    assert not list(pathlib.Path(d).glob("*.tmp"))
    print("OK: _atomic_write replaces cleanly, no temp litter, invalidates warm env cache")


def test_default_reverify_rejects_warm_ok_cold_broken():
    """A warm env load is not enough to persist a substrate mutation; cold file compile is the ground truth."""
    import ztare.formal.repl_compile as rc
    d = tempfile.mkdtemp()
    ctx = pathlib.Path(d) / "theory.lean"
    ctx.write_text(_BASE, encoding="utf-8")
    old_env, old_cold, old_cache = rc.campaign_file_env, rc._substrate_cold_compiles, dict(rc._FILE_ENV_CACHE)
    try:
        warm_calls = []
        rc.campaign_file_env = lambda *_a, **_k: warm_calls.append(True) or object()
        rc._substrate_cold_compiles = lambda *_a, **_k: False
        assert _default_reverify(ctx, d) is False
        assert warm_calls == [], "cold-broken source must not be rescued by a cached warm env"
        rc._substrate_cold_compiles = lambda *_a, **_k: True
        assert _default_reverify(ctx, d) is True
        assert warm_calls == [True]
    finally:
        rc.campaign_file_env, rc._substrate_cold_compiles = old_env, old_cold
        rc._FILE_ENV_CACHE.clear()
        rc._FILE_ENV_CACHE.update(old_cache)
    print("OK: default bank reverify requires cold file compile, not warm-only acceptance")


def test_bank_reverts_when_reorder_and_eof_fallback_both_fail():
    d = tempfile.mkdtemp()
    ctx = pathlib.Path(d) / "theory.lean"
    before = (
        "import Mathlib\n\n"
        "namespace N\n"
        "variable {A : Type}\n\n"
        "theorem open_work_item : True := by\n"
        "  sorry\n"
        "\nend N\n"
    )
    ctx.write_text(before, encoding="utf-8")
    proof = "theorem helper_for_open_work_item : 1 = 1 := by rfl\n"
    seen = []

    def rv(pth):
        seen.append(pathlib.Path(pth).read_text(encoding="utf-8"))
        return False

    assert bank(ctx, proof, reverify=rv) == []
    assert len(seen) >= 1, "regression must exercise the compile-arbitrated bank path"
    assert ctx.read_text(encoding="utf-8") == before
    print("OK: failed reorder+EOF fallback restores the original substrate bytes")


def test_bank_decl_caches_unavailable_reverify_for_same_substrate_sha():
    d = tempfile.mkdtemp()
    ctx = pathlib.Path(d) / "theory.lean"
    before = (
        "import Mathlib\n\n"
        "theorem open_work_item : True := by\n"
        "  sorry\n"
    )
    ctx.write_text(before, encoding="utf-8")
    proof = "theorem foo : True := by trivial\n"
    calls = []

    old_rv = fll._default_reverify
    old_cache = set(fll._REVERIFY_UNAVAILABLE_SHA)

    def rv(pth, _root):
        calls.append(pathlib.Path(pth).read_text(encoding="utf-8"))
        return False

    try:
        fll._REVERIFY_UNAVAILABLE_SHA.clear()
        fll._default_reverify = rv
        r = bank_decl_to_env(ctx, "foo", proof, d)
        assert r["banked_as"] is None and r["reason"] == "reverify_unavailable", r
        assert len(calls) == 2, "first failure still classifies candidate vs restored substrate"
        assert ctx.read_text(encoding="utf-8") == before
        r2 = bank_decl_to_env(ctx, "foo", proof, d)
        assert r2["banked_as"] is None and r2["reason"] == "reverify_unavailable", r2
        assert len(calls) == 2, "second attempt on same substrate SHA must use unavailable-cache, not cold compile"
    finally:
        fll._default_reverify = old_rv
        fll._REVERIFY_UNAVAILABLE_SHA.clear()
        fll._REVERIFY_UNAVAILABLE_SHA.update(old_cache)
    print("OK: bank_decl_to_env caches unavailable reverify for unchanged substrate SHA")


def test_campaign_file_env_cache_key_includes_content_identity():
    import ztare.formal.repl_compile as rc
    d = tempfile.mkdtemp()
    ctx = pathlib.Path(d) / "theory.lean"
    ctx.write_text("theorem a : True := trivial\n", encoding="utf-8")
    key = str(ctx.resolve())
    rc._FILE_ENV_CACHE[key] = (ctx.stat().st_mtime, ctx.stat().st_size, "wrongsha", 777)
    old_toolchain, old_get = rc._toolchain_ok, rc._get_repl
    try:
        rc._toolchain_ok = lambda _project: False
        rc._get_repl = lambda _project: (_ for _ in ()).throw(AssertionError("stale cache was used"))
        assert rc.campaign_file_env(str(ctx), d) is None
    finally:
        rc._toolchain_ok, rc._get_repl = old_toolchain, old_get
        rc._FILE_ENV_CACHE.pop(key, None)
    print("OK: campaign_file_env cache is content-keyed, not mtime-only")


if __name__ == "__main__":
    test_failed_bank_is_byte_identical()
    test_success_bank_appends_atomically()
    test_failed_bank_reverifies_candidate_before_live_swap()
    test_atomic_write_no_partial_and_no_litter()
    test_default_reverify_rejects_warm_ok_cold_broken()
    test_bank_reverts_when_reorder_and_eof_fallback_both_fail()
    test_bank_decl_caches_unavailable_reverify_for_same_substrate_sha()
    test_campaign_file_env_cache_key_includes_content_identity()
