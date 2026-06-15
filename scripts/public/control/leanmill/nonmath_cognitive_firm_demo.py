#!/usr/bin/env python3
"""Non-math governance wedge, END-TO-END across repos: LeanMill firewall → signed payload → cognitive-firm.

The differentiator the prover race structurally cannot reproduce: a NON-MATH compliance rule (Basel CET1
capital adequacy) is checked by LeanMill's kernel/SMT faithfulness firewall, the verdict is emitted as a
SIGNED `formal-verification-provider/v1` payload, and cognitive-firm's governance kernel INGESTS it over a
verified Ed25519 signature — no import coupling, payload-only boundary. Two arms, the anti-laundering contrast:

  • FAITHFUL rule (CET1 ≥ 450bp), with the laundered (≥449) twin as the matched control → `verified`
  • LAUNDERED rule (≥449) presented AS the claim → the firewall FAILS it → `invalid`

Both are signed by LeanMill and re-verified by cognitive-firm's installed trust policy. `invalid` makes a
cognitive-firm governed-run bundle FAIL; `verified` (with the required faithfulness + checker refs) passes.

HERMETIC selftest: a stub battery (faithful passes, laundered fails) keeps it Lean-free + deterministic while
exercising the REAL signing + the REAL cognitive-firm CLI. `--real` swaps in LeanMill's Lean firewall battery.

  python scripts/public/control/leanmill/nonmath_cognitive_firm_demo.py [--selftest] [--real] [--cf-root DIR]
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
DEFAULT_CF_ROOT = REPO.parent / "cognitive-firm"   # the sibling repo (the verification CONSUMER)

# The Basel CET1 ≥ 450bp policy: the laundered twin shifts the threshold to 449 (admits a 4.49% bank).
_RULE_NL = "Basel CET1 capital adequacy: approve iff CET1 ratio >= 450 bp"
_FAITHFUL_SRC = "def rule (c : Int) : Bool := decide (c >= 450)"
_LAUNDERED_SRC = "def rule (c : Int) : Bool := decide (c >= 449)"
_CASES = [("(450)", True), ("(449)", False)]   # the SMT-boundary edge: 449 must be DENIED


def _stub_battery(src, pred, cases):
    """Deterministic stand-in for the Lean kernel battery: the launder (threshold 449) FAILS the boundary
    case; the faithful rule passes. Lean-free so the cross-repo signing + ingest is what gets exercised."""
    return False if "449" in src else True


def produce_payloads(*, battery_fn, private_pem: str) -> "dict[str, dict]":
    """Run the LeanMill certify firewall for both arms and return {arm: signed_payload}."""
    from ztare.leanmill.formal_verification_provider import certify_demo_to_payload
    faithful = certify_demo_to_payload(
        rule_nl=_RULE_NL, faithful_src=_FAITHFUL_SRC, laundered_src=_LAUNDERED_SRC,
        predicate="rule", cases=_CASES, subject_ref="basel://rule/cet1",
        claim_ref="basel://claim/faithful", battery_fn=battery_fn,
        private_key_pem=private_pem, run_id="basel_faithful")
    laundered = certify_demo_to_payload(   # the launder claimed as faithful → firewall fails it → invalid
        rule_nl=_RULE_NL, faithful_src=_LAUNDERED_SRC,
        predicate="rule", cases=_CASES, subject_ref="basel://rule/cet1",
        claim_ref="basel://claim/laundered", battery_fn=battery_fn,
        private_key_pem=private_pem, run_id="basel_laundered")
    return {"faithful": faithful, "laundered": laundered}


def _cf_cli(cf_root: Path, org: Path, args: "list[str]") -> "subprocess.CompletedProcess":
    """Invoke cognitive-firm's formal-verification CLI as a SUBPROCESS (payload-only boundary — leanmill
    never imports cognitive_firm). `PYTHONPATH=<cf>/src` so the module resolves from the sibling repo."""
    env = {**os.environ, "PYTHONPATH": str(cf_root / "src")}
    return subprocess.run(
        [sys.executable, "-m", "cognitive_firm.orchestration.formal_verification", *args],
        cwd=str(cf_root), env=env, capture_output=True, text=True, timeout=120)


def run_demo(cf_root: Path, *, battery_fn) -> dict:
    """Full round-trip: keygen → sign both arms → install the leanmill key into a temp cognitive-firm org →
    ingest both → return the per-arm verdict + signature-verified flag as cognitive-firm RECORDED them."""
    from ztare.leanmill.formal_verification_provider import generate_keypair
    priv, pub = generate_keypair()
    payloads = produce_payloads(battery_fn=battery_fn, private_pem=priv)
    out: dict = {"leanmill": {a: p["verdict"] for a, p in payloads.items()}, "cognitive_firm": {}}
    with tempfile.TemporaryDirectory(prefix="nonmath_cf_") as _td:
        td = Path(_td)
        org = td / "org"
        org.mkdir(parents=True, exist_ok=True)
        (td / "leanmill.pub").write_text(pub, encoding="utf-8")
        trust = _cf_cli(cf_root, org, ["trust-provider", "--provider", "leanmill",
                                       "--public-key-file", str(td / "leanmill.pub"),
                                       "--authority-root", str(org)])
        out["trust_provider_ok"] = (trust.returncode == 0)
        for arm, payload in payloads.items():
            pf = td / f"{arm}.json"
            pf.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            res = _cf_cli(cf_root, org, ["create-from-provider-payload", "--payload-json", str(pf),
                                         "--authority-root", str(org)])
            verdict = sig_ver = None
            try:
                d = json.loads(res.stdout)
                fv = d.get("formal_verification", d)
                verdict = fv.get("verdict")
                sig_ver = (fv.get("metadata") or {}).get("provider_payload_signature_verified")
            except (ValueError, AttributeError):
                pass
            out["cognitive_firm"][arm] = {"verdict": verdict, "signature_verified": sig_ver,
                                          "ingested": res.returncode == 0}
    return out


def render(out: dict) -> str:
    lines = ["# Non-math governance wedge — LeanMill firewall → cognitive-firm (end-to-end)", ""]
    lines.append(f"trust-provider installed: {out.get('trust_provider_ok')}")
    lines.append(f"{'arm':<11} {'leanmill verdict':<18} {'cognitive-firm verdict':<24} {'sig-verified':<12} ingested")
    for arm in ("faithful", "laundered"):
        lm = out["leanmill"].get(arm)
        cf = out["cognitive_firm"].get(arm, {})
        lines.append(f"{arm:<11} {str(lm):<18} {str(cf.get('verdict')):<24} "
                     f"{str(cf.get('signature_verified')):<12} {cf.get('ingested')}")
    lines.append("\nEXPECTED: faithful → verified (bundle passes); laundered → invalid (bundle FAILS); "
                 "both signature-verified. The launder is caught by the LeanMill kernel AND rejected by "
                 "cognitive-firm's governed bundle, over a cryptographically verified cross-repo boundary.")
    return "\n".join(lines)


def _contract_ok(out: dict) -> bool:
    cf = out.get("cognitive_firm", {})
    return bool(
        out.get("trust_provider_ok")
        and out["leanmill"].get("faithful") == "verified" and out["leanmill"].get("laundered") == "invalid"
        and cf.get("faithful", {}).get("verdict") == "verified"
        and cf.get("laundered", {}).get("verdict") == "invalid"
        and cf.get("faithful", {}).get("signature_verified") is True
        and cf.get("laundered", {}).get("signature_verified") is True
    )


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true", help="hermetic stub battery + real signing + real CF CLI")
    ap.add_argument("--real", action="store_true", help="use the real LeanMill Lean firewall battery (slow)")
    ap.add_argument("--cf-root", default=str(DEFAULT_CF_ROOT), help="path to the cognitive-firm repo")
    a = ap.parse_args(argv)
    cf_root = Path(a.cf_root)
    if not (cf_root / "src" / "cognitive_firm").exists():
        print(f"[skip] cognitive-firm not found at {cf_root} — the verification CONSUMER is required for this demo.")
        return 0
    if a.real:
        from ztare.leanmill.solver.autoformalize import default_instance_battery
        lean_root = str(REPO / "ztare_proofs")
        battery_fn = lambda src, pred, cs: default_instance_battery(src, pred, cs, sandbox=lean_root)  # noqa: E731
    else:
        battery_fn = _stub_battery
    out = run_demo(cf_root, battery_fn=battery_fn)
    print(render(out))
    ok = _contract_ok(out)
    print("\nCONTRACT:", "PASS — non-math wedge verified end-to-end across repos" if ok else f"FAIL: {out}")
    return 0 if ok else 1


def _selftest() -> int:
    if not (DEFAULT_CF_ROOT / "src" / "cognitive_firm").exists():
        print("  [SKIP] cognitive-firm sibling repo not present — cross-repo demo needs the consumer")
        print("SELFTEST SKIPPED")
        return 0
    rc = main(["--cf-root", str(DEFAULT_CF_ROOT)])
    print("SELFTEST", "PASSED" if rc == 0 else "FAILED")
    return rc


if __name__ == "__main__":
    if "--selftest" in (sys.argv[1:] or []):
        sys.exit(_selftest())
    sys.exit(main())
