#!/usr/bin/env python3
"""bundle_verify.py — the reusable Path-A verifier (productizes the
disposable per-corpus /tmp/run_*.py scripts that were themselves the
rewrite anti-pattern).

Substrate/version-parameterized: pass ANY canonical pinned sandbox
(`--sandbox`) so NS or any substrate runs against its OWN Mathlib
version (the meta-solver contract: version is a per-substrate sandbox
parameter, never a global constant).

Inputs:
  --corpus  corpus.json : {"rows":[{"id","statement"}...]}  (for exact? goals)
  --proofs  proofs.json : {"proofs":{id:full_theorem_src},"gaps":[id...]}
  --sandbox PATH        : a registered canonical pinned Mathlib sandbox
Emits the standard result line per row (the format
gp233_adversary_yield_decomp consumes):
  <id>: compile=COMPILE_OK|FAIL|PINNED_ENV_BROKEN|PROVER_GAP | exact?=...

Hard precondition: pinned_env_healthy(sandbox) (positive control, the
v4.30/v4.29-escape guard). If the sandbox is not a materialized loading
Mathlib, NO verdict is emitted (PINNED_ENV_NOT_MATERIALIZED).
Separation: proofs are compiled VERBATIM (one mechanical `∑ in`→`∑ ∈`
notation port only); never hand-edited here.
"""
from __future__ import annotations
import argparse, json, os, re, subprocess, tempfile, sys, importlib.util
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]


def _load_pinned_env_healthy():
    """Reuse validate_genuinely_new.pinned_env_healthy (single source for
    the positive-control guard) — parameterized by sandbox path."""
    p = REPO / "scripts/public/validators/validate_genuinely_new.py"
    spec = importlib.util.spec_from_file_location("vgn", p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _run(sandbox: Path, src: str, timeout: int) -> tuple[int, str]:
    src = src.replace(" in Finset", " ∈ Finset")  # notation port (syntax only)
    fd, p = tempfile.mkstemp(suffix=".lean", dir=str(sandbox))
    try:
        os.write(fd, ("import Mathlib\n" + src + "\n").encode()); os.close(fd)
        r = subprocess.run(["lake", "env", "lean", os.path.basename(p)],
                            cwd=str(sandbox), capture_output=True,
                            text=True, timeout=timeout)
        return r.returncode, (r.stdout or "") + (r.stderr or "")
    except subprocess.TimeoutExpired:
        return 124, "TIMEOUT"
    finally:
        try: os.unlink(p)
        except Exception: pass


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", required=True)
    ap.add_argument("--proofs", required=True)
    ap.add_argument("--sandbox", required=True,
                    help="canonical pinned Mathlib sandbox (substrate/version param)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--timeout", type=int, default=320)
    a = ap.parse_args()

    sandbox = Path(a.sandbox).expanduser().resolve()
    # HARD precondition: pinned env materialized (reused single-source guard).
    vgn = _load_pinned_env_healthy()
    vgn.SANDBOX = sandbox  # parameterize the guard to THIS substrate's env
    healthy, hnote = vgn.pinned_env_healthy()
    if not healthy:
        print(json.dumps({"verdict": "PINNED_ENV_NOT_MATERIALIZED",
                          "sandbox": str(sandbox), "note": hnote}, indent=2))
        return 2

    corpus = {r["id"]: r for r in json.load(open(a.corpus))["rows"]}
    pj = json.load(open(a.proofs))
    proofs = pj.get("proofs", {})
    gaps = set(pj.get("gaps", []))
    ids = [r["id"] for r in json.load(open(a.corpus))["rows"]]

    out = Path(a.out); out.write_text("")
    for rid in ids:
        if rid in gaps:
            line = f"{rid}: compile=PROVER_GAP | exact?=n/a (honest prover refusal)"
        elif rid not in proofs:
            line = f"{rid}: compile=PROVER_GAP | exact?=n/a (no proof submitted)"
        else:
            rc, o = _run(sandbox, proofs[rid], a.timeout)
            low = o.lower()
            comp = ("PINNED_ENV_BROKEN" if "incompatible header" in low
                    else "COMPILE_OK" if (rc == 0 and "error" not in low
                                          and "sorry" not in low) else "FAIL")
            ex = "n/a"
            if comp == "COMPILE_OK":
                stmt = corpus[rid]["statement"].split(":=")[0].rstrip()
                erc, eo = _run(sandbox, stmt + " := by exact?", a.timeout)
                elo = eo.lower()
                # Adjudication MUST be conservative: a row is only eligible to
                # be counted genuine when exact? RAN TO COMPLETION and
                # explicitly reported it could not single-lemma-close. A
                # deterministic `whnf` heartbeat timeout / wall timeout /
                # any unrecognized output is INCONCLUSIVE and must never be
                # laundered as "could not close" (false-genuine). Surfaced
                # by independent Meta-Darwin on the Tier-2 closure-route
                # (T2P_93: 4M-hb deterministic whnf timeout was being read
                # as a genuine closure).
                _is_timeout = (erc == 124 or "timeout" in elo
                               or "heartbeat" in elo
                               or "(deterministic) timeout" in elo
                               or "maximum recursion depth" in elo)
                if "try this" in elo:
                    ex = "Try this:"
                elif _is_timeout:
                    ex = "EXACT_TIMEOUT (adjudication inconclusive — NOT genuine)"
                elif "could not close" in elo:
                    ex = "`exact?` could not close"
                else:
                    ex = "EXACT_INCONCLUSIVE (unrecognized exact? output — NOT genuine)"
            ax = "n/a"
            if comp == "COMPILE_OK":
                # AUTHORITATIVE 0-false-ratify guard (operator-approved
                # 2026-05-16; supersedes the regex CE organ as the source
                # of truth, which is demoted to advisory pre-filter). The
                # Lean kernel tracks EVERY axiom/sorry a proof term
                # depends on, so this is idiom-INDEPENDENT and complete
                # by construction: any smuggle (sorry/admit/stop/declared
                # axiom/native-trust), through ANY surface syntax — incl.
                # idioms no adversary enumerated — surfaces here. Only
                # Mathlib's three foundational axioms are trusted; ANY
                # other dependency ⇒ the proof relies on something
                # unproven ⇒ NOT a genuine closure. Conservative:
                # UNVERIFIED (could not confirm) is also NOT genuine.
                _STD = {"propext", "Classical.choice", "Quot.sound"}
                # rr (adversary-found, fixed 2026-05-16): a clean decoy
                # `theorem` first + an axiom-backed real claim second made
                # first-`theorem`-match report the DECOY's clean axioms ⇒
                # false ratification. Must (1) strip comments BEFORE name
                # extraction, (2) collect EVERY declared name (theorem
                # AND lemma), (3) `#print axioms` ALL of them in one
                # compile and UNION their dependencies — a clean sibling
                # can never whitelist a dirty one. Also fixes the
                # `lemma`-keyword honest-proof yield-loss.
                _nocom = re.sub(r"/-.*?-/", " ", proofs[rid], flags=re.S)
                _nocom = re.sub(r"--[^\n]*", " ", _nocom)
                _names = re.findall(
                    r"\b(?:theorem|lemma)\s+([A-Za-z_][\w'.]*)", _nocom)
                if not _names:
                    ax = ("AXIOMS_UNVERIFIED (no theorem/lemma name to "
                          "target — NOT genuine)")
                else:
                    _prints = "\n".join(f"#print axioms {n}"
                                        for n in dict.fromkeys(_names))
                    _arc, _ao = _run(sandbox,
                                     proofs[rid] + "\n" + _prints + "\n",
                                     a.timeout)
                    _aol = _ao.lower()
                    _deps: set[str] = set()
                    for _mm in re.finditer(
                            r"depends on axioms:\s*\[([^\]]*)\]", _ao, re.S):
                        _deps |= {x.strip() for x in
                                  re.split(r"[,\s]+", _mm.group(1))
                                  if x.strip()}
                    _bad = sorted(_deps - _STD)
                    _unknown = ("unknown constant" in _aol
                                or "unknown identifier" in _aol)
                    if "incompatible header" in _aol:
                        ax = "AXIOMS_UNVERIFIED (pinned env broken — NOT genuine)"
                    elif _bad:
                        ax = ("AXIOMS_SMUGGLED:" + ",".join(_bad)
                              + " (kernel dependency, any declared name — "
                              "NOT genuine)")
                    elif "sorryax" in _aol or "'sorry'" in _aol:
                        ax = "AXIOMS_SMUGGLED:sorryAx (kernel — NOT genuine)"
                    elif _unknown:
                        ax = ("AXIOMS_UNVERIFIED (a declared name did not "
                              "resolve — NOT genuine)")
                    elif _deps or ("no axioms" in _aol
                                   or "does not depend on any axiom" in _aol):
                        ax = "AXIOMS_CLEAN"
                    else:
                        ax = ("AXIOMS_UNVERIFIED (no #print axioms result "
                              "— NOT genuine)")
            line = f"{rid}: compile={comp} | exact?={ex} | axioms={ax}"
        with out.open("a") as f:
            f.write(line + "\n")
        print(line, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
