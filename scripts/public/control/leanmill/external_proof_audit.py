"""External proof audit — batch L1+L2+L3 audit of pre-cooked Lean proofs.

Canonical name as of 2026-05-29 (previously: leanmill_lane_b_audit). Defaults
read from `operations.external_proof_audit` in the factory policy
(`leanmill_factory_policy.json`); CLI args override per-call. Uses the
canonical compile + axiom + L3 stack at `leanmill_proof_audit.py` and routes
drift / forced-sidecar cases to a pinned-toolchain sidecar Lake project
named in `operations.external_proof_audit.sidecar_lean_root`.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from argparse import Namespace
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
CONTROL = REPO / "scripts" / "public" / "control"

# Ensure imports of the canonical audit module (which itself imports v33 gates
# from the same dir) work when invoked from anywhere.
sys.path.insert(0, str(CONTROL))
sys.path.insert(0, str(REPO))

FACTORY_POLICY = REPO / "analytics/public/leanmill/dashboard_data/leanmill_factory_policy.json"


def _policy_block() -> dict:
    """Read operations.external_proof_audit from the factory policy.
    All hardcoded paths and string lists below have policy fallback only."""
    try:
        return json.loads(FACTORY_POLICY.read_text()).get(
            "operations", {}).get("external_proof_audit") or {}
    except Exception:
        return {}


def _from_policy_path(key: str, fallback_str: str) -> Path:
    val = _policy_block().get(key)
    if val is None:
        return REPO / fallback_str
    p = Path(val)
    return p if p.is_absolute() else REPO / p


CANONICAL_AUDIT = _from_policy_path(
    "canonical_audit", "scripts/public/control/leanmill/proof_audit.py")
CANDIDATES_DIR = _from_policy_path(
    "candidates_dir", "analytics/public/queries/external_proof_candidates")
LEAN_ROOT = _from_policy_path("native_lean_root", "ztare_proofs")
SIDECAR_LEAN_ROOT = _from_policy_path("sidecar_lean_root", "")
DEFAULT_OUT = _from_policy_path(
    "out_receipts", "analytics/public/queries/external_proof_audit_receipts.json")
DEFAULT_OUT_MD = _from_policy_path(
    "out_summary_md", "analytics/public/queries/external_proof_audit_summary.md")
CANDIDATE_GLOB = _policy_block().get("candidate_glob") or "*_candidate.json"
SIDECAR_DISPLAY_NAME = _policy_block().get("sidecar_display_name") or "pinned-toolchain sidecar"


# Drift signal heuristic — read from policy so a new signal phrase can be
# added without code change. Fallback baked-in for the bootstrap case.
# Only genuinely version-specific phrases belong here. `type mismatch`,
# `unsolved goals`, `tactic ... failed`, and `deprecated` are the canonical
# signatures of a REAL broken proof, not toolchain drift — including them let a
# genuine defect get re-routed to the sidecar and laundered as "drift". Removed.
_DRIFT_SIGNALS = tuple(_policy_block().get("drift_signals") or (
    "unknown constant", "unknown identifier",
    "has been renamed", "no longer exists",
))


def _looks_like_drift(receipt: dict) -> bool:
    compile_obj = receipt.get("compile") or {}
    if compile_obj.get("ok"):
        return False
    blob = (compile_obj.get("stdout_tail") or "") + "\n" + (compile_obj.get("stderr_tail") or "")
    return any(s in blob.lower() for s in _DRIFT_SIGNALS)


def audit_one(candidate_path: Path, *, timeout_s: int = 600, lean_root: Path = LEAN_ROOT) -> dict:
    import os
    cand = json.loads(candidate_path.read_text())
    target = cand["target_name"]
    artifact = REPO / cand["artifact_paths"][0]
    # Invoke the canonical pr_a1_audit script as a subprocess to its --out path;
    # cleaner than dynamic import + avoids module registration edge cases.
    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tf:
        out_path = Path(tf.name)
    cmd = [
        sys.executable,
        str(CANONICAL_AUDIT),
        "--target", str(artifact),
        "--target-name", str(target),
        "--lean-root", str(lean_root),
        "--factory-policy", str(FACTORY_POLICY),
        "--timeout-s", str(timeout_s),
        "--out", str(out_path),
    ]
    # Build env: needs lake/lean on PATH (~/.elan/bin) AND pr_a1_audit needs
    # to find leanmill_paths / v33_* (scripts/public/control) plus src.ztare
    # (REPO).
    env = os.environ.copy()
    elan_bin = str(Path.home() / ".elan/bin")
    env["PATH"] = elan_bin + os.pathsep + env.get("PATH", "")
    py_paths = [str(REPO), str(REPO / "scripts/public/control"), env.get("PYTHONPATH", "")]
    env["PYTHONPATH"] = os.pathsep.join(p for p in py_paths if p)
    try:
        p = subprocess.run(cmd, cwd=str(REPO), env=env, text=True,
                           capture_output=True, timeout=timeout_s + 60)
        receipt = json.loads(out_path.read_text()) if out_path.exists() and out_path.stat().st_size > 0 else {
            "schema": "leanmill-pr-a1-compile-l3-audit-v1",
            "target": str(artifact),
            "lean_root": str(lean_root),
            "status": "audit_invocation_failed",
            "subprocess_returncode": p.returncode,
            "stdout_tail": p.stdout[-1000:],
            "stderr_tail": p.stderr[-1000:],
        }
    finally:
        try:
            out_path.unlink()
        except Exception:
            pass
    # Augment with our candidate metadata + drift classification.
    receipt["candidate_path"] = str(candidate_path.relative_to(REPO))
    receipt["target_name_in_lean"] = target
    receipt["audited_lean_root"] = str(lean_root)
    receipt["likely_toolchain_drift"] = _looks_like_drift(receipt)
    return receipt


def main() -> int:
    # Defaults read from operations.external_proof_audit in the factory
    # policy; CLI args override per-call. Single source of truth: policy.
    try:
        policy_block = json.loads(FACTORY_POLICY.read_text()).get(
            "operations", {}).get("external_proof_audit") or {}
    except Exception:
        policy_block = {}
    def _from_policy(key, fallback):
        val = policy_block.get(key)
        if val is None:
            return fallback
        if isinstance(fallback, Path):
            v = REPO / val if not Path(val).is_absolute() else Path(val)
            return v
        return val
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--candidates-dir", type=Path,
                    default=_from_policy("candidates_dir", CANDIDATES_DIR))
    ap.add_argument("--out", type=Path,
                    default=_from_policy("out_receipts", DEFAULT_OUT))
    ap.add_argument("--out-md", type=Path,
                    default=_from_policy("out_summary_md", DEFAULT_OUT_MD))
    ap.add_argument("--timeout-s", type=int,
                    default=_from_policy("timeout_s", 1800),
                    help="Per-candidate timeout for the native audit (default 1800s = 30 min). "
                         "Mathlib-heavy proofs can require multi-minute compiles; the orphan-lake "
                         "process-group kill discipline (lean_compile_primitives) makes large budgets safe.")
    ap.add_argument("--sidecar-timeout-s", type=int,
                    default=_from_policy("sidecar_timeout_s", 3600),
                    help="Per-candidate timeout for the v4.27 sidecar audit (default 3600s = 60 min). "
                         "Sidecar compiles can require lake-package re-resolution and a colder cache than "
                         "the native toolchain, so the budget is intentionally larger than --timeout-s.")
    ap.add_argument("--force-sidecar-on-compile-failed",
                    action="store_true",
                    default=bool(_from_policy("force_sidecar_on_compile_failed", False)),
                    help="Always re-audit in the pinned-toolchain sidecar when native "
                         "compile fails, even without a drift-heuristic hit. Disambiguates "
                         "compile_failed with no recognized drift signal (real defect vs "
                         "unrecognized toolchain drift). "
                         "Default read from policy.external_proof_audit.force_sidecar_on_compile_failed.")
    args = ap.parse_args()

    cand_files = sorted(args.candidates_dir.glob(CANDIDATE_GLOB))
    if not cand_files:
        print(f"no candidates found in {args.candidates_dir} (glob={CANDIDATE_GLOB!r})", file=sys.stderr)
        return 1

    receipts = []
    sidecar_available = (
        bool(str(SIDECAR_LEAN_ROOT))
        and SIDECAR_LEAN_ROOT.exists()
        and (SIDECAR_LEAN_ROOT / "lean-toolchain").exists()
    )
    for cp in cand_files:
        print(f"[external_proof_audit] auditing {cp.name} (native toolchain)", flush=True)
        try:
            r = audit_one(cp, timeout_s=args.timeout_s, lean_root=LEAN_ROOT)
        except Exception as exc:
            r = {
                "schema": "leanmill-pr-a1-compile-l3-audit-v1",
                "candidate_path": str(cp.relative_to(REPO)),
                "status": "audit_invocation_failed",
                "error_detail": repr(exc),
            }
        print(f"   ↳ native status={r.get('status')!s:<38} drift={r.get('likely_toolchain_drift')}")

        # Sidecar branch: when the native audit fails to compile (with drift
        # signal OR with --force-sidecar-on-compile-failed), re-audit at the
        # pinned-toolchain sidecar declared in policy.sidecar_lean_root.
        # Disambiguates "drift at native toolchain" from "real defect".
        force_sidecar = bool(args.force_sidecar_on_compile_failed)
        if (
            sidecar_available
            and r.get("status") in {"compile_failed", "audit_invocation_failed"}
            and (r.get("likely_toolchain_drift") or force_sidecar)
        ):
            print(f"   → re-auditing in {SIDECAR_DISPLAY_NAME} (timeout {args.sidecar_timeout_s}s)", flush=True)
            try:
                sr = audit_one(cp, timeout_s=args.sidecar_timeout_s, lean_root=SIDECAR_LEAN_ROOT)
            except Exception as exc:
                sr = {"status": "sidecar_invocation_failed", "error_detail": repr(exc)}
            r["sidecar_audit"] = sr
            sidecar_status = sr.get("status")
            if sidecar_status in ("compile_pass_l3_advisory_pass",
                                  "compile_pass_l3_advisory_review"):
                r["combined_verdict"] = "passes_at_pinned_toolchain_only"
            elif sidecar_status == "compile_pass_l3_advisory_review_helper_blockers_only":
                # compiles at pinned toolchain BUT a confirmed L3 blocker fired
                # on a helper lemma — NOT an unqualified pass; do not launder.
                r["combined_verdict"] = "passes_at_pinned_toolchain_helper_l3_blockers"
            elif sidecar_status == "l3_confirmed_blocker_top_level":
                r["combined_verdict"] = "l3_laundering_blocker_at_pinned_toolchain"
            elif sidecar_status == "compile_failed":
                r["combined_verdict"] = "defect_confirmed_at_both_toolchains"
            else:
                r["combined_verdict"] = f"sidecar_inconclusive:{sidecar_status}"
            print(f"   ↳ sidecar status={sidecar_status!s:<38} combined={r['combined_verdict']}")
        receipts.append(r)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps({
        "schema": "leanmill-lane-b-canonical-receipts-v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "audit_module": "scripts/public/control/leanmill/proof_audit.py",
        "n": len(receipts),
        "receipts": receipts,
        "summary_by_status": {
            s: sum(1 for r in receipts if r.get("status") == s)
            for s in {r.get("status") for r in receipts}
        },
    }, indent=2))

    md_lines = [
        "# Lane B — APN Audit Receipts (canonical L1+L2+L3)",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        f"Audit module: `scripts/public/control/leanmill/proof_audit.py`",
        "",
        "| Target | Status | compile_ok | axiom_allowlist_ok | L3 status | drift |",
        "|---|---|---|---|---|---|",
    ]
    for r in receipts:
        target = (Path(r.get("target") or "")).name.replace(".lean", "")
        compile_ok = (r.get("compile") or {}).get("ok")
        ax_ok = (r.get("kernel_axiom_policy") or {}).get("allowlist_ok")
        l3 = (r.get("l3_audit") or {}).get("status")
        md_lines.append(
            f"| {target} | **{r.get('status')}** | {compile_ok} | {ax_ok} | {l3} | {r.get('likely_toolchain_drift')} |"
        )
    args.out_md.write_text("\n".join(md_lines) + "\n")
    print(f"\nwrote {args.out}")
    print(f"wrote {args.out_md}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
