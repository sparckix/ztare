#!/usr/bin/env python3
"""Node preflight — fail-loud calibration of a (new) node's proof-search instruments.

RCA mechanization (2026-06-02): the dead-REPL episode was a DEPLOY-TIME misconfiguration —
the vendored Lean repl binary and a project's Mathlib oleans were built at different Lean
toolchains, so `import Mathlib` silently returned an empty env and every probe falsely
"failed". Nothing checked this at provisioning, so a new node would reproduce it. This
preflight runs ALL the instrument positive controls the session hardened, so a misconfigured
node FAILS LOUD at bring-up instead of silently emitting false negatives during runs.

HARD checks (nonzero exit ⇒ node not proof-ready, abort provisioning):
  1. Toolchain match: the repl binary's lean-toolchain == at least one Mathlib-built project's.
  2. Substrate liveness: PersistentLean over a matched project actually loads Mathlib
     (substrate_liveness.calibrate: positive controls + verifier false-accept + sorry-gate).
SOFT checks (warn, don't abort — degrade gracefully but visibly):
  3. Embedder liveness (the amnesia firewall's semantic layer — a dead embedder silently
     green-lights re-derivation).
  4. Provider availability (codex/claude on subscription; deepseek/gemini via API).

  python3 node_preflight.py [--project-dir <dir>] [--json] [--soft-ok]
"""
from __future__ import annotations
import argparse, json, os, subprocess, sys, time
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
# both REPO and REPO/src so `ztare.*` AND any `src.ztare.*`-style imports resolve regardless
# of how the preflight is invoked (a path gap here would falsely report a SOFT instrument dead)
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO))


def _candidate_projects(explicit: str | None) -> list[Path]:
    if explicit:
        p = (REPO / explicit) if not Path(explicit).is_absolute() else Path(explicit)
        return [p]
    out = []
    for tc in REPO.rglob("lean-toolchain"):
        d = tc.parent
        if "/.lake/" in str(d) or "/_archive/" in str(d):
            continue
        if list(d.glob(".lake/packages/mathlib/.lake/build/lib/lean/Mathlib.olean")) \
           or (d / ".lake/build/lib/lean").exists():
            out.append(d)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project-dir", default=None, help="lean project to calibrate (default: auto-discover Mathlib-built projects)")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--soft-ok", action="store_true", help="exit 0 even if SOFT checks fail (still aborts on HARD)")
    a = ap.parse_args()
    from ztare.formal.lean_persistent import PersistentLean, DEFAULT_REPL_BIN
    from ztare.formal.substrate_liveness import toolchain_match, repl_toolchain, toolchain_of, calibrate, SubstrateDeadError

    report = {"hard_ok": False, "soft": {}, "repl_bin": str(DEFAULT_REPL_BIN),
              "repl_toolchain": repl_toolchain(DEFAULT_REPL_BIN), "projects": []}
    log = (lambda *x: None) if a.json else (lambda *x: print(*x, flush=True))

    # ── HARD 1+2: toolchain match + substrate liveness over a matched project ──
    projects = _candidate_projects(a.project_dir)
    live_pair = None
    for proj in projects:
        m, rtc, ptc = toolchain_match(DEFAULT_REPL_BIN, proj)
        entry = {"project": str(proj), "toolchain": ptc, "match": m, "substrate_live": None}
        if m:
            try:
                with PersistentLean(project_dir=str(proj)) as pl:
                    rep = calibrate(pl)
                    entry["substrate_live"] = True
                    live_pair = (str(proj), rep.banner())
            except (SubstrateDeadError, RuntimeError) as e:
                entry["substrate_live"] = False
                entry["substrate_err"] = str(e)[:160]
        report["projects"].append(entry)
        log(f"[preflight] project {Path(proj).name}: toolchain={ptc} match={'Y' if m else 'N'} "
            f"substrate_live={entry['substrate_live']}")
        if live_pair:
            break
    # ── HARD: leanmill SUITE import-smoke ─────────────────────────────────────
    # The suite was silently broken on a cleanup branch (a renamed sibling shim
    # left `from leanmill_paths import …` unresolvable for ~46 scripts incl.
    # governance), and nothing caught it until governance was needed. Import the
    # governance triangle (+ a sample of workers) so a broken suite fails LOUD at
    # bring-up, not when a proof needs auditing.
    control = REPO / "scripts/public/control"
    leanmill_dir = control / "leanmill"
    env2 = dict(os.environ)
    env2["PYTHONPATH"] = f"{REPO}:{REPO}/src:{control}:{leanmill_dir}:{env2.get('PYTHONPATH','')}"
    # COMPREHENSIVE: import EVERY leanmill control script (not a sample) so ANY broken
    # importer — e.g. a renamed sibling shim that breaks `from leanmill_X import` — fails
    # loud here. This is the parity check the suite never had: lean_env_parity covers the
    # Lean TOOLCHAIN, selfcheck imported 4 modules, the sync allowlist syncs files not
    # imports — none caught a Python-import break across the suite.
    smoke = (
        "import importlib,pathlib,warnings;warnings.filterwarnings('ignore');"
        "d=pathlib.Path(r'" + str(leanmill_dir) + "');"
        "b=[];\n"
        "import sys\n"
        "for p in sorted(d.glob('*.py')):\n"
        "  if p.stem=='__init__': continue\n"
        "  try: importlib.import_module(p.stem)\n"
        "  except Exception as e: b.append(p.stem+': '+type(e).__name__+': '+str(e)[:70])\n"
        "print('BROKEN '+str(len(b)));\n"
        "[print('  '+x) for x in b];\n"
        "sys.exit(1 if b else 0)")
    imp = subprocess.run(["python3", "-c", smoke], cwd=str(REPO), env=env2,
                         capture_output=True, text=True)
    suite_ok = imp.returncode == 0
    report["suite_imports_ok"] = suite_ok
    if not suite_ok:
        report["suite_import_error"] = (imp.stdout or imp.stderr or "")[-400:]
        log(f"[preflight] HARD ❌ leanmill suite import FAILED:\n{(imp.stdout or imp.stderr or '').strip()[-400:]}")
    else:
        log(f"[preflight] HARD ✅ leanmill suite imports (all scripts in {leanmill_dir.name}/)")

    report["hard_ok"] = (live_pair is not None) and suite_ok
    if live_pair:
        log(f"[preflight] HARD ✅ live REPL pair: {Path(live_pair[0]).name}")
    else:
        log(f"[preflight] HARD ❌ NO live REPL pair — repl_toolchain={report['repl_toolchain']!r}; "
            f"no Mathlib-built project matches it. The repl binary and project oleans are at "
            f"different Lean versions (the dead-REPL RCA). Rebuild the repl at the project's "
            f"toolchain or build a matching-toolchain Mathlib. NODE IS NOT PROOF-READY.")

    # ── SOFT 3: embedder liveness ──
    try:
        from ztare.research_director.primitive_amnesia import semantic_live
        elive, ewhy = semantic_live()
    except Exception as e:
        elive, ewhy = False, f"import/call error: {str(e)[:80]}"
    report["soft"]["embedder"] = {"live": elive, "why": ewhy}
    log(f"[preflight] SOFT embedder (amnesia semantic layer): {'LIVE' if elive else 'DEAD'} ({ewhy})")

    # ── SOFT 4: provider availability ──
    prov = {}
    # codex / claude on subscription (binary present + quick auth probe is expensive; check binary + auth file)
    prov["codex"] = bool(subprocess.run(["bash", "-lc", "command -v codex"], capture_output=True).stdout.strip()) \
        and (Path.home() / ".codex/auth.json").exists()
    prov["claude"] = bool(subprocess.run(["bash", "-lc", "command -v claude"], capture_output=True).stdout.strip()) \
        and (Path.home() / ".claude").exists()
    prov["deepseek_key"] = bool(os.environ.get("DEEPSEEK_API_KEY"))
    prov["gemini_key"] = bool(os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"))
    report["soft"]["providers"] = prov
    log(f"[preflight] SOFT providers: " + " ".join(f"{k}={'Y' if v else 'N'}" for k, v in prov.items()))

    soft_ok = elive and any(prov.values())
    if a.json:
        print(json.dumps(report))
    else:
        print(f"[preflight] => HARD {'PASS' if report['hard_ok'] else 'FAIL'} | "
              f"SOFT {'ok' if soft_ok else 'degraded (see above)'}")
    # exit: nonzero on HARD fail always; on SOFT fail unless --soft-ok
    if not report["hard_ok"]:
        sys.exit(2)
    if not soft_ok and not a.soft_ok:
        sys.exit(3)
    sys.exit(0)


if __name__ == "__main__":
    main()
