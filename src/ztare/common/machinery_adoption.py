"""Adoption leg for machinery-patch proposals — BUILD 3.

``adopt_machinery_patch`` is the only public surface: backup/apply/test/restore,
with a Rule-6 attestation written on pass and byte-exact restore on fail.

Safety gates (before any file is touched):
  Rule 3  — certifier_touched cards refused outright.
  Rule 3/4 — any patch path on the certifier denylist refused outright.

Denylist (cognitive-firm/draft.md §3, Rules 3/4):
  src/ztare/worldmodel/gates.py, tests/, gate_harness, MACHINERY_RULES.md
"""
from __future__ import annotations

import subprocess
from pathlib import Path

from ztare.common.operator_proposal_contract import attest, record_disposition

# ponytail: substring denylist — simple, correct for the four known certifier paths.
_DENYLIST = (
    "src/ztare/worldmodel/gates.py",
    "tests/",
    "gate_harness",
    "MACHINERY_RULES.md",
)


def _is_denied(path_str: str) -> bool:
    p = path_str.replace("\\", "/")
    return any(frag in p for frag in _DENYLIST)


def adopt_machinery_patch(
    card: dict,
    patch: "dict[str, str]",   # path string -> new file content
    run_tests_cmd: list,
    principal: str,
    *,
    ledger: "Path | str | None" = None,
    ts: str = "",
    rules_path: "Path | str | None" = None,
) -> dict:
    """Run the adoption leg for one machinery-patch card.

    (a) Refuse outright if ``card.get("certifier_touched")`` (Rule 3) or any
        patch path matches the certifier denylist (Rules 3/4).
    (b) Back up target files in memory, write the patch.
    (c) Run ``run_tests_cmd`` (subprocess, captured).
        Pass → keep changes; return accepted dict + persist attestation via the
        contract (Rule 6, I3).
        Fail → restore backups byte-exact; return rejected with the test tail.

    ``ts`` and ``suite`` are caller-supplied per the I3 attestation contract.
    ``rules_path`` overrides the default MACHINERY_RULES.md location for tests.
    """
    # (a) — Rule 3: certifier gate
    if card.get("certifier_touched"):
        return {
            "status": "refused",
            "reason": "certifier_touched — conductor disposition required (Rule 3)",
        }

    # (a) — Rules 3/4: denylist
    for path_str in patch:
        if _is_denied(str(path_str)):
            return {
                "status": "refused",
                "reason": f"denylist path: {path_str} (Rules 3/4)",
            }

    # (b) — backup
    backups: dict[str, bytes | None] = {}
    for path_str in patch:
        fp = Path(path_str)
        backups[path_str] = fp.read_bytes() if fp.exists() else None

    # write patch
    for path_str, content in patch.items():
        fp = Path(path_str)
        fp.parent.mkdir(parents=True, exist_ok=True)
        fp.write_text(content, encoding="utf-8")

    # (c) — run tests
    result = subprocess.run(run_tests_cmd, capture_output=True, text=True)

    if result.returncode == 0:
        suite_str = (result.stdout.strip() or result.stderr.strip() or "passed")
        receipt = attest(card, "accepted", principal, ts=ts, suite=suite_str,
                         rules_path=rules_path)
        out = dict(card)
        out["disposition"] = "accepted"
        out["attestation"] = receipt["attestation"]
        if ledger is not None:
            record_disposition(ledger, out, attestation=receipt["attestation"])
        return {"status": "accepted", **receipt}

    # fail — restore byte-exact
    for path_str, orig in backups.items():
        fp = Path(path_str)
        if orig is None:
            if fp.exists():
                fp.unlink()
        else:
            fp.write_bytes(orig)
    tail = (result.stdout + result.stderr)[-500:]
    return {"status": "rejected", "reason": "test suite failed", "test_tail": tail}
