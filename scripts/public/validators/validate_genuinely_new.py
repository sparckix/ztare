#!/usr/bin/env python3
"""validate_genuinely_new.py — mechanized novelty-sourcing gate.

Born from the SIE false-escape bug (2026-05-16): rows were sourced as
"escape-route" because their FILE was added after the pinned tag — but
their closing identity (`integral_rpow_mul_exp_neg_mul_rpow`,
`Real.Gamma_nat_eq_factorial`) already existed in pinned v4.29.0. "File
added later" is BANNED as a novelty criterion.

A row is GENUINELY-NEW only if all hold (this gate mechanizes #1, the
one that failed, and requires explicit attestation for #2-#5):

  1. the closer lemma NAME `#check`-FAILS in the pinned env (mechanical,
     enforced here);
  2. no equivalent direct theorem found by current search (attest);
  3. proof independently compiled in the pinned env (attest);
  4. the row is NOT a wrapper around an existing hidden identity (attest);
  5. governance adjudicates the target_kind before credit (attest).

Verdicts:
  REJECT_NAME_PRESENT_IN_PINNED  -> the SIE bug; `#check` succeeded in
                                    pinned: NOT genuinely-new.
  NAME_ABSENT_NEEDS_ATTESTATION  -> #1 passes; #2-#5 must be attested
                                    before the row may be credited.
  GENUINELY_NEW                  -> #1 passes AND #2-#5 attested true.

Pinned sandbox default = the v4.29.0 carleson baseline (same env the
clean-prover experiments compile in).

PRECONDITION (2026-05-16, mechanized): the pinned env must be a
VERIFIED, materialized v4.29.0 Mathlib. `pinned_env_healthy()` runs a
positive control (`#check @Nat.add`); if it fails (incompatible-header /
missing oleans / deleted sandbox), verdict = PINNED_ENV_NOT_MATERIALIZED
and NO novelty/provenance verdict is issued. Without this, a broken pin
silently launders everything as novel (the v4.30-vs-v4.29 escape) — the
exact hole the 2026-05-16 pinned-provenance error fell through.
"""
from __future__ import annotations
import argparse, json, subprocess, sys, tempfile, os
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
SANDBOX = REPO / "analytics/public/leanmill/external_benchmarks/sandboxes/v28A_carleson_baseline/carleson"


def pinned_env_healthy(timeout: int = 180) -> tuple[bool, str]:
    """Positive control: assert the pinned sandbox is MATERIALIZED and loads.

    Without this, a broken/missing/wrong-toolchain pinned env (e.g.
    `incompatible header` when a v4.29.0 binary meets v4.30 oleans, or a
    deleted sandbox) makes `lake env lean` fail with a non-"unknown
    identifier" error, which `name_check_fails_in_pinned` would misread
    as "name absent -> GENUINELY_NEW" — laundering EVERYTHING as novel
    and silently re-opening the v4.30-vs-v4.29 escape. This is also the
    exact hole the 2026-05-16 pinned-provenance mistake fell through:
    "pinned v4.29.0" was a trusted label, never a verified fact.

    `Nat.add` exists in EVERY Mathlib since forever; if `#check @Nat.add`
    does not succeed in the sandbox, the pinned env is not real and NO
    novelty verdict may be issued.
    """
    if not SANDBOX.exists():
        return False, f"pinned sandbox missing: {SANDBOX}"
    src = "import Mathlib\n#check @Nat.add\n"
    fd, p = tempfile.mkstemp(suffix=".lean", dir=str(SANDBOX))
    try:
        os.write(fd, src.encode()); os.close(fd)
        r = subprocess.run(["lake", "env", "lean", os.path.basename(p)],
                            cwd=str(SANDBOX), capture_output=True,
                            text=True, timeout=timeout)
        out = (r.stdout or "") + (r.stderr or "")
        if "incompatible header" in out.lower():
            return False, "PINNED ENV TOOLCHAIN MISMATCH (incompatible header): " + out[-300:]
        if r.returncode != 0 or "unknown" in out.lower():
            return False, "PINNED ENV DID NOT LOAD Mathlib: " + out[-300:]
        return True, "pinned env healthy (#check @Nat.add OK)"
    except subprocess.TimeoutExpired:
        return False, "PINNED ENV HEALTH PROBE TIMEOUT (treat as not materialized)"
    finally:
        try: os.unlink(p)
        except Exception: pass


def name_check_fails_in_pinned(closer_name: str, timeout: int = 180) -> tuple[bool, str]:
    """True iff `#check @<closer_name>` FAILS (unknown id) in pinned env."""
    if not SANDBOX.exists():
        return False, f"pinned sandbox missing: {SANDBOX}"
    src = f"import Mathlib\n#check @{closer_name}\n"
    fd, p = tempfile.mkstemp(suffix=".lean", dir=str(SANDBOX))
    try:
        os.write(fd, src.encode()); os.close(fd)
        r = subprocess.run(["lake", "env", "lean", os.path.basename(p)],
                            cwd=str(SANDBOX), capture_output=True,
                            text=True, timeout=timeout)
        out = (r.stdout or "") + (r.stderr or "")
        # `#check` of a present decl => rc 0 / prints the type, no error.
        # absent => "unknown identifier" / "unknown constant" error.
        absent = ("unknown identifier" in out.lower()
                  or "unknown constant" in out.lower()
                  or "unknownidentifier" in out.lower())
        present = (r.returncode == 0 and not absent)
        return (not present), out[-300:]
    except subprocess.TimeoutExpired:
        return False, "TIMEOUT (treat as inconclusive — do NOT credit novelty)"
    finally:
        try: os.unlink(p)
        except Exception: pass


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--closer-name", required=True,
                    help="the lemma that would close the row (fully qualified)")
    ap.add_argument("--no-equivalent-direct-theorem", action="store_true",
                    help="attest #2: search found no equivalent direct theorem")
    ap.add_argument("--independently-compiled-pinned", action="store_true",
                    help="attest #3: proof independently compiled in pinned env")
    ap.add_argument("--not-a-wrapper", action="store_true",
                    help="attest #4: not a wrapper around an existing hidden identity")
    ap.add_argument("--target-kind-adjudicated", action="store_true",
                    help="attest #5: governance adjudicated the target_kind")
    a = ap.parse_args()

    healthy, hnote = pinned_env_healthy()
    if not healthy:
        out = {"closer_name": a.closer_name,
               "verdict": "PINNED_ENV_NOT_MATERIALIZED",
               "name_check_fails_in_pinned": None,
               "note": ("BLOCKING: the pinned sandbox is not a verified, "
                        "materialized v4.29.0 Mathlib — NO novelty/provenance "
                        "verdict may be issued (neither credit nor reject). "
                        "Materialize the pin and re-run. " + hnote),
               "pinned_env_probe": hnote}
        print(json.dumps(out, indent=2))
        return 2

    fails, tail = name_check_fails_in_pinned(a.closer_name)
    attests = {
        "no_equivalent_direct_theorem": a.no_equivalent_direct_theorem,
        "independently_compiled_pinned": a.independently_compiled_pinned,
        "not_a_wrapper_around_hidden_identity": a.not_a_wrapper,
        "target_kind_adjudicated": a.target_kind_adjudicated,
    }
    if not fails:
        verdict = "REJECT_NAME_PRESENT_IN_PINNED"
        note = ("`#check` of the closer SUCCEEDED in pinned v4.29.0 -> the "
                "closing identity already exists. This is the SIE bug. "
                "NOT genuinely-new; do not source as escape-route.")
    elif all(attests.values()):
        verdict = "GENUINELY_NEW"
        note = "name absent in pinned AND #2-#5 attested. Creditable as escape-route."
    else:
        verdict = "NAME_ABSENT_NEEDS_ATTESTATION"
        note = ("name absent in pinned (#1 OK). Provide #2-#5 attestations "
                "before crediting; un-attested rows are not genuinely-new.")
    out = {"closer_name": a.closer_name,
           "name_check_fails_in_pinned": fails,
           "attestations": attests, "verdict": verdict, "note": note,
           "pinned_probe_tail": tail}
    print(json.dumps(out, indent=2))
    return 0 if verdict == "GENUINELY_NEW" else 1


if __name__ == "__main__":
    raise SystemExit(main())
