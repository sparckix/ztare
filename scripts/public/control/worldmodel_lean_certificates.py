#!/usr/bin/env python3
"""GP-250 proof-carrying world models: Lean equivalence certificates.

For every sealed environment whose law is a seed-grammar AST, recover the
champion from a reset-witnessing log and ratify champion ≡ sealed on the
enumerated reachable probe set through leanmill's external-artifact organ
(`ztare.leanmill.audit_external`). No model tokens; spends Lean compiles.

Usage: python3 scripts/public/control/worldmodel_lean_certificates.py
"""

from __future__ import annotations

import json
import sys
from dataclasses import asdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "src"))

from ztare.substrates.arc_synthetic import ENVIRONMENTS  # noqa: E402
from ztare.worldmodel.lean_equivalence import certify_environment  # noqa: E402

OUT_DIR = REPO / "workspace" / "worldmodel_lean"


def main() -> int:
    results = []
    for env in ENVIRONMENTS:
        cert = certify_environment(env, OUT_DIR)
        if cert is None:
            print(f"  [{env.env_id}] no certificate possible (no sealed AST / ceiling)", flush=True)
            results.append({"env": env.env_id, "certified": None,
                            "detail": "no sealed AST or grammar ceiling — gate-level evidence only"})
            continue
        print(f"  [{env.env_id}] certified={cert.certified} probes={cert.probes} "
              f"{cert.detail[:80]}", flush=True)
        results.append({"env": env.env_id, **asdict(cert)})

    eligible = [r for r in results if r["certified"] is not None]
    report = {"schema": "ztare-worldmodel-lean-certificates-v1",
              "results": results,
              "ok": bool(eligible) and all(r["certified"] for r in eligible)}
    (OUT_DIR / "certificates_report.json").write_text(json.dumps(report, indent=2))
    print(json.dumps({k: report[k] for k in ("schema", "ok")}, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
