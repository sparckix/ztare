#!/usr/bin/env python3
"""REPL↔substrate toolchain PARITY — mechanize the dead-instrument RCA fix so toolchain drift can't recur.

THE BUG THIS PREVENTS (root-caused 2026-06-09): the vendored Lean repl (`vendor/lean_repl`) can match only ONE
Lean toolchain. When a substrate (e.g. `ztare_proofs`) moves forward (v4.29 → v4.30) and the repl is NOT rebuilt,
the repl is ABI-dead over that substrate — `import Mathlib` silently returns an empty env, the warm-REPL compile
path falls back to a cold `lake env lean` reload per probe, and every hand-guessed timeout false-fails. The repl
was rebuilt BY HAND once; nothing kept it pinned, so a fresh box / the VPS would reproduce the drift. This makes
the rebuild a DEPLOY STEP: detect drift, rebuild the repl to the substrate's toolchain, verify it loads live.

The repl project has NO dependencies (standalone REPL, no Mathlib), so a rebuild is just `lake build` under the
substrate's toolchain — elan auto-selects it from `vendor/lean_repl/lean-toolchain`; NO Mathlib recompile. Cheap
and idempotent: a no-op when already matched. The authoritative liveness check is `PersistentLean.calibrate`
(actually loads Mathlib over the substrate through the repl) — it catches a STALE binary that the cheap
toolchain-file compare would miss.

  python3 repl_parity.py --substrate ztare_proofs [--check-only] [--no-verify-live] [--force] [--json]
  ZTARE_PREFLIGHT_REQUIRE=ztare_proofs python3 repl_parity.py     # substrate(s) from the env (comma-sep)

Exit 0 = parity (already, or achieved). Nonzero = drift unresolved (rebuild failed / --check-only found drift /
substrates demand conflicting toolchains / repl won't load live).
"""
from __future__ import annotations
import argparse, json, os, shutil, subprocess, sys, time
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO))

REPL_DIR = REPO / "vendor" / "lean_repl"
REPL_TOOLCHAIN_FILE = REPL_DIR / "lean-toolchain"
REPL_BIN = REPL_DIR / ".lake" / "build" / "bin" / "repl"

# `vendor/lean_repl` is gitignored + NOT in the VPS rsync allowlist (it's a local-only checkout), so a fresh box
# / the VPS has NO repl source to build. The deploy must FETCH it. Pin the exact upstream commit that builds
# clean at the substrate toolchain (v4.30) here — NOT HEAD, whose REPL.lean may assume a newer Lean and fail to
# build at the substrate's version. Re-pin (and re-verify locally) when the substrate's toolchain moves.
REPL_GIT_DEFAULT = "https://github.com/leanprover-community/repl"
REPL_PIN_DEFAULT = "495777293cb9cc3c62787a8c11393da1a9dd9505"  # tag v4.29.0 source; builds clean at v4.30.0-rc2


def _say(msg: str) -> None:
    print(f"[repl-parity] {msg}", flush=True)


def _find_lake() -> str | None:
    """Locate `lake` (elan shim). PATH first, then the standard elan bin dir."""
    found = shutil.which("lake")
    if found:
        return found
    for cand in (Path.home() / ".elan" / "bin" / "lake", Path("/root/.elan/bin/lake")):
        if cand.exists():
            return str(cand)
    return None


def _ensure_source(repl_git: str, repl_pin: str, timeout_s: int) -> tuple[bool, str]:
    """Fetch the vendored repl source if absent (the rsync allowlist does NOT ship vendor/lean_repl). Clones the
    PINNED commit — robust against upstream HEAD drifting past the substrate's Lean version. No-op when present."""
    if (REPL_DIR / "lakefile.toml").exists():
        return True, "repl source already present (no clone)"
    git = shutil.which("git")
    if git is None:
        return False, "git not found — cannot fetch the repl source"
    if REPL_DIR.exists() and any(REPL_DIR.iterdir()):
        return False, f"{REPL_DIR} exists, is non-empty, and has no lakefile.toml (corrupt) — clear it and retry"
    REPL_DIR.parent.mkdir(parents=True, exist_ok=True)
    _say(f"repl source absent — cloning {repl_git} @ {repl_pin[:12]} → {REPL_DIR.relative_to(REPO)}")
    try:
        c = subprocess.run([git, "clone", repl_git, str(REPL_DIR)], capture_output=True, text=True, timeout=timeout_s)
        if c.returncode != 0:
            return False, f"git clone failed (rc={c.returncode}): {(c.stderr or '').strip()[-300:]}"
        if repl_pin:
            co = subprocess.run([git, "-C", str(REPL_DIR), "checkout", "--quiet", repl_pin],
                                capture_output=True, text=True, timeout=120)
            if co.returncode != 0:
                return False, f"git checkout {repl_pin[:12]} failed: {(co.stderr or '').strip()[-200:]}"
    except subprocess.TimeoutExpired:
        return False, f"git clone/checkout timed out after {timeout_s}s"
    if not (REPL_DIR / "lakefile.toml").exists():
        return False, "clone returned 0 but lakefile.toml is absent"
    return True, f"cloned {repl_git} @ {repl_pin[:12]}"


def _read_tc(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8").strip()
    except Exception:  # noqa: BLE001
        return ""


def _substrates_from_args(a) -> list[Path]:
    raw: list[str] = list(a.substrate or [])
    if not raw and os.environ.get("ZTARE_PREFLIGHT_REQUIRE"):
        raw = [s for s in os.environ["ZTARE_PREFLIGHT_REQUIRE"].replace(",", " ").split() if s]
    if not raw:
        raw = ["ztare_proofs"]                       # the default active substrate (overridable; not hardcoded logic)
    out: list[Path] = []
    for s in raw:
        p = Path(s) if Path(s).is_absolute() else (REPO / s)
        out.append(p)
    return out


def _target_toolchain(substrates: list[Path]) -> tuple[str, list[str]]:
    """Resolve the single toolchain the repl must be built at. Fail loud if the required substrates demand
    DIFFERENT toolchains (one vendored repl cannot satisfy both — that needs separate repls / a per-substrate
    binary, a decision the operator must make)."""
    from ztare.formal.substrate_liveness import toolchain_of
    tcs: dict[str, str] = {}
    notes: list[str] = []
    for s in substrates:
        tc = toolchain_of(s)
        if not tc:
            notes.append(f"substrate {s} has no lean-toolchain (skipped)")
            continue
        tcs[str(s)] = tc
    distinct = set(tcs.values())
    if len(distinct) > 1:
        raise SystemExit(
            "[repl-parity] CONFLICT: required substrates demand different toolchains "
            f"{tcs} — a single vendored repl cannot match all. Build a per-substrate repl or narrow "
            "ZTARE_PREFLIGHT_REQUIRE.")
    if not distinct:
        raise SystemExit(f"[repl-parity] no substrate toolchain found among {[str(s) for s in substrates]}")
    return distinct.pop(), notes


def _rebuild(target_tc: str, timeout_s: int) -> tuple[bool, str]:
    lake = _find_lake()
    if lake is None:
        return False, "lake not found (elan not installed / not on PATH)"
    REPL_TOOLCHAIN_FILE.write_text(target_tc + "\n", encoding="utf-8")  # pin → elan auto-selects on build
    _say(f"pinned {REPL_TOOLCHAIN_FILE.relative_to(REPO)} → {target_tc}; building (lake build, no deps)…")
    env = dict(os.environ)
    elan_bin = str(Path(lake).parent)
    if elan_bin not in env.get("PATH", ""):
        env["PATH"] = elan_bin + os.pathsep + env.get("PATH", "")
    t0 = time.time()
    try:
        proc = subprocess.run([lake, "build"], cwd=str(REPL_DIR), env=env,
                              capture_output=True, text=True, timeout=timeout_s)
    except subprocess.TimeoutExpired:
        return False, f"lake build timed out after {timeout_s}s"
    dt = time.time() - t0
    if proc.returncode != 0:
        tail = (proc.stderr or proc.stdout or "").strip()[-800:]
        return False, f"lake build failed (rc={proc.returncode}, {dt:.0f}s): {tail}"
    if not REPL_BIN.exists():
        return False, f"lake build returned 0 but {REPL_BIN} is absent"
    return True, f"rebuilt at {target_tc} in {dt:.0f}s"


def _verify_live(substrate: Path) -> tuple[bool, str]:
    """The authoritative check: does the (rebuilt) repl actually load Mathlib over the substrate? Catches a
    stale binary the toolchain-file compare can't. Reuses the canonical path EXACTLY as node_preflight:
    open a PersistentLean (defaults to the rebuilt DEFAULT_REPL_BIN) and run substrate_liveness.calibrate,
    which RAISES SubstrateDeadError unless every positive/negative/sorry control passes."""
    try:
        from ztare.formal.lean_persistent import PersistentLean
        from ztare.formal.substrate_liveness import calibrate, SubstrateDeadError
    except Exception as exc:  # noqa: BLE001
        return False, f"cannot import PersistentLean/calibrate: {exc!r}"
    try:
        with PersistentLean(project_dir=str(substrate)) as pl:
            rep = calibrate(pl)
        return True, "live — " + rep.banner()
    except SubstrateDeadError as e:
        return False, f"substrate DEAD over the rebuilt repl: {str(e)[:300]}"
    except Exception as exc:  # noqa: BLE001 — missing repl / import failure / process death
        return False, f"calibrate raised {type(exc).__name__}: {str(exc)[:200]}"


def main() -> int:
    ap = argparse.ArgumentParser(description="REPL↔substrate toolchain parity (rebuild on drift).")
    ap.add_argument("--substrate", action="append", help="substrate project dir (repeatable); "
                    "default ZTARE_PREFLIGHT_REQUIRE or ztare_proofs")
    ap.add_argument("--check-only", action="store_true", help="report drift, do NOT rebuild (nonzero exit on drift)")
    ap.add_argument("--no-verify-live", action="store_true", help="skip the PersistentLean live check (toolchain-file compare only)")
    ap.add_argument("--force", action="store_true", help="rebuild even if the toolchain already matches")
    ap.add_argument("--no-ensure-source", action="store_true",
                    help="do NOT clone the repl source when absent (default: clone the pinned commit)")
    ap.add_argument("--repl-git", default=REPL_GIT_DEFAULT, help="upstream repl git URL (clone-when-absent)")
    ap.add_argument("--repl-pin", default=REPL_PIN_DEFAULT, help="repl commit to check out (substrate-compatible)")
    ap.add_argument("--build-timeout", type=int, default=900)
    ap.add_argument("--clone-timeout", type=int, default=300)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    substrates = _substrates_from_args(a)
    target_tc, notes = _target_toolchain(substrates)
    for n in notes:
        _say(n)

    report: dict = {"substrates": [str(s) for s in substrates], "target_toolchain": target_tc,
                    "source_ensured": None, "rebuilt": False, "live": None}

    # SETUP: fetch the repl source if absent (the VPS rsync allowlist does NOT ship it). Skipped for --check-only
    # (a read-only probe) and --no-ensure-source. This is what makes the deploy set up the repl from nothing.
    if not a.check_only and not a.no_ensure_source:
        sok, smsg = _ensure_source(a.repl_git, a.repl_pin, a.clone_timeout)
        report["source_ensured"] = sok
        report["source_msg"] = smsg
        _say(("SOURCE: " if sok else "SOURCE FAILED: ") + smsg)
        if not sok:
            if a.json:
                print(json.dumps(report, indent=2))
            return 4

    repl_pin = _read_tc(REPL_TOOLCHAIN_FILE)
    binary_present = REPL_BIN.exists()
    drift = (repl_pin != target_tc) or (not binary_present)
    report.update({"repl_toolchain_pin": repl_pin, "binary_present": binary_present, "drift": drift})
    _say(f"substrate target = {target_tc} | repl pin = {repl_pin or '<none>'} | binary = "
         f"{'present' if binary_present else 'ABSENT'} | drift = {drift}")

    if a.check_only:
        report["verdict"] = "drift" if drift else "parity"
        if a.json:
            print(json.dumps(report, indent=2))
        return 1 if drift else 0

    if drift or a.force:
        ok, msg = _rebuild(target_tc, a.build_timeout)
        report["rebuilt"] = ok
        report["rebuild_msg"] = msg
        _say(("REBUILD OK: " if ok else "REBUILD FAILED: ") + msg)
        if not ok:
            if a.json:
                print(json.dumps(report, indent=2))
            return 2
    else:
        _say("already at parity (toolchain pin matches; binary present) — no rebuild")

    if not a.no_verify_live:
        live, lmsg = _verify_live(substrates[0])
        report["live"] = live
        report["live_msg"] = lmsg
        _say(("LIVE: " if live else "NOT LIVE: ") + lmsg)
        if not live:
            if a.json:
                print(json.dumps(report, indent=2))
            return 3

    report["verdict"] = "parity"
    if a.json:
        print(json.dumps(report, indent=2))
    _say("✅ parity")
    return 0


def _selftest() -> int:
    """Non-building unit checks: arg/env substrate resolution, conflict detection, drift logic."""
    fails = []

    def ok(n, c):
        print(f"  [{'PASS' if c else 'FAIL'}] {n}")
        if not c:
            fails.append(n)

    class A:  # minimal args stand-in
        substrate = None
    os.environ.pop("ZTARE_PREFLIGHT_REQUIRE", None)
    ok("default substrate = ztare_proofs", [p.name for p in _substrates_from_args(A())] == ["ztare_proofs"])
    os.environ["ZTARE_PREFLIGHT_REQUIRE"] = "ztare_proofs, atlas_lean_2026_05_29"
    names = {p.name for p in _substrates_from_args(A())}
    ok("env ZTARE_PREFLIGHT_REQUIRE parsed (comma-sep)", names == {"ztare_proofs", "atlas_lean_2026_05_29"})
    os.environ.pop("ZTARE_PREFLIGHT_REQUIRE", None)
    ok("repl paths resolve under vendor/lean_repl",
       REPL_TOOLCHAIN_FILE.parent.name == "lean_repl" and REPL_BIN.name == "repl")
    ok("_find_lake returns a path or None (no crash)", _find_lake() is None or Path(_find_lake()).name == "lake")
    # conflict detection: two substrates at different toolchains must raise
    try:
        from ztare.formal import substrate_liveness as _sl
        _orig = _sl.toolchain_of
        _sl.toolchain_of = lambda p: "v4.29" if "a" in str(p) else "v4.30"  # type: ignore
        try:
            _target_toolchain([Path("/x/a"), Path("/x/b")])
            ok("conflicting toolchains raise SystemExit", False)
        except SystemExit:
            ok("conflicting toolchains raise SystemExit", True)
        finally:
            _sl.toolchain_of = _orig
    except Exception as exc:  # noqa: BLE001
        ok(f"conflict-detection harness ({exc!r})", False)
    print("SELFTEST", "PASSED" if not fails else f"FAILED: {fails}")
    return 0 if not fails else 1


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        raise SystemExit(_selftest())
    raise SystemExit(main())
