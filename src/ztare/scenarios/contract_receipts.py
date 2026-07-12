"""Contract receipts — input-provenance ledger + the anti-cherry-pick pin (teeth via TIME, not identity).

The workbench governs its OUTPUTS meticulously (the provenance firewall). The authored INPUTS — scenario config,
charter, the declared deliverable set — were the only mutable, un-receipted state in a product whose whole thesis
is provenance. This closes that gap. At run-start, BEFORE any evidence exists, `pin_contracts` hashes the authored
contracts into an append-only receipt.

Why this has teeth where a file-vs-file "immutable charter" pin would be theater (Fable): the author can always
edit the contract, so identity-exogeneity is impossible — the author will always author it. And the charter is a
LIVING document by design (the RD loop rewrites it), so file-level immutability is architecturally impossible.
The sound substitute is exogeneity by TIME: the pin is taken before results exist, so the author cannot have
shaped the declared set in RESPONSE to an outcome that had not happened yet. "Was this deliverable pre-registered,
or added after seeing the result?" is then a COMPUTED fact off the receipt (`deliverable_provenance`), never a
self-report. Post-hoc additions stay allowed (that is legitimate work) and permanently labelled (that is the teeth).
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone


def _workspace(project: str, repo_root=None):
    if repo_root is not None:
        return repo_root / "projects" / project / "workspace"
    from ztare.common.paths import PROJECTS_DIR
    return PROJECTS_DIR / project / "workspace"


def _receipts_path(project: str, repo_root=None):
    return _workspace(project, repo_root) / "contract_receipts.jsonl"


def _sha(text: "str | None") -> "str | None":
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16] if text else None


def _charter_sha(project: str, repo_root=None) -> "str | None":
    ws = _workspace(project, repo_root)
    charter = ws.parent / "project_charter.md"
    return _sha(charter.read_text(encoding="utf-8")) if charter.is_file() else None


def pin_contracts(project: str, *, scenario: "str | None" = None, run_id=None,
                  declared: "list[str] | None" = None, repo_root=None, now: str = "") -> dict:
    """Append the run-start snapshot of the authored contracts to `workspace/contract_receipts.jsonl`. Call this
    ONCE at run-start (before evidence). `declared` defaults to the unified resolved set. Idempotent per run_id:
    a second pin for the same run_id is a no-op returning the existing record (a re-run of the same launch must
    not double-count)."""
    from ztare.scenarios.production import resolve_declared_set

    existing = pinned_receipts(project, repo_root)
    if run_id is not None:
        for rec in existing:
            if rec.get("run_id") == run_id:
                return rec
    decl = sorted(declared) if declared is not None else resolve_declared_set(project, repo_root=repo_root)
    rec = {
        "run_id": run_id,
        "ts": now or datetime.now(timezone.utc).isoformat(),
        "scenario": scenario,
        "charter_sha": _charter_sha(project, repo_root),
        "declared": decl,
        "declared_sha": _sha("\n".join(decl)),
    }
    path = _receipts_path(project, repo_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec) + "\n")
    return rec


def pinned_receipts(project: str, repo_root=None) -> "list[dict]":
    """All run-start receipts, chronological (append-only). Empty until the project's first pinned run."""
    path = _receipts_path(project, repo_root)
    if not path.is_file():
        return []
    out: "list[dict]" = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                out.append(json.loads(line))
            except Exception:  # noqa: BLE001
                pass
    return out


def deliverable_provenance(project: str, current_declared: "list[str]", repo_root=None) -> dict:
    """COMPUTED pre-registration status per currently-declared deliverable — never self-reported. A deliverable is
    `pre-registered` if it appears in some pinned run's declared set (reported with the EARLIEST run_id it was
    pinned in); otherwise `added_later` (declared after the last pin, so it could be a response to results). This
    is the ungameable surface the panel labels each deliverable with."""
    receipts = pinned_receipts(project, repo_root)
    first_run: "dict[str, object]" = {}
    for rec in receipts:  # chronological → first occurrence wins
        for name in rec.get("declared", []):
            if name not in first_run:
                first_run[name] = rec.get("run_id")
    rows: "list[dict]" = []
    for name in current_declared:
        pre = name in first_run
        rows.append({"name": name, "pre_registered": pre,
                     "first_run_id": first_run.get(name),
                     "status": "pre-registered" if pre else "added_later"})
    return {"deliverables": rows, "pinned_runs": len(receipts), "any_pinned": bool(receipts)}


def contract_drift(project: str, repo_root=None) -> dict:
    """The input-provenance diff: the authored contracts at the LATEST pin vs NOW (charter changed? deliverables
    added/removed since?). Answers "what did this project's contract say when it last ran, vs what it says now?"
    Empty (`pinned: False`) until the first pinned run."""
    from ztare.scenarios.production import resolve_declared_set

    receipts = pinned_receipts(project, repo_root)
    if not receipts:
        return {"pinned": False}
    latest = receipts[-1]
    now_declared = set(resolve_declared_set(project, repo_root=repo_root))
    pinned_declared = set(latest.get("declared", []))
    return {
        "pinned": True,
        "latest_run_id": latest.get("run_id"),
        "charter_changed": _charter_sha(project, repo_root) != latest.get("charter_sha"),
        "declared_added": sorted(now_declared - pinned_declared),
        "declared_removed": sorted(pinned_declared - now_declared),
    }


def _selftest() -> int:
    import tempfile
    from pathlib import Path

    fails: "list[str]" = []

    def ok(name: str, cond: bool) -> None:
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}")
        if not cond:
            fails.append(name)

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        proj = "_selftest_contracts"
        ws = root / "projects" / proj / "workspace"
        ws.mkdir(parents=True, exist_ok=True)
        (root / "projects" / proj / "project_charter.md").write_text("# Charter\nCore Question: does X hold?\n",
                                                                     encoding="utf-8")

        ok("no receipts before any pin → empty provenance", deliverable_provenance(proj, ["decision_memo"], root)
           == {"deliverables": [{"name": "decision_memo", "pre_registered": False, "first_run_id": None,
                                 "status": "added_later"}], "pinned_runs": 0, "any_pinned": False})
        ok("no drift before any pin", contract_drift(proj, root) == {"pinned": False})

        # run 1 pins {decision_memo, risk_register}
        r1 = pin_contracts(proj, scenario="product-manager", run_id=1,
                           declared=["risk_register", "decision_memo"], repo_root=root, now="2026-07-10T00:00:00Z")
        ok("pin sorts the declared set", r1["declared"] == ["decision_memo", "risk_register"])
        ok("pin records the scenario + a charter sha", r1["scenario"] == "product-manager" and r1["charter_sha"])

        # idempotent per run_id
        again = pin_contracts(proj, run_id=1, declared=["something_else"], repo_root=root)
        ok("re-pinning the same run_id is a no-op", again["declared"] == ["decision_memo", "risk_register"])
        ok("only one receipt on disk after the idempotent re-pin", len(pinned_receipts(proj, root)) == 1)

        # both are pre-registered at run 1
        prov = deliverable_provenance(proj, ["decision_memo", "risk_register"], root)
        ok("both declared deliverables read pre-registered (run 1)",
           all(d["pre_registered"] and d["first_run_id"] == 1 for d in prov["deliverables"]))

        # run 2 (later) drops risk_register and adds an appendix — the cherry-pick shape
        pin_contracts(proj, run_id=2, declared=["decision_memo", "appendix"], repo_root=root,
                      now="2026-07-10T01:00:00Z")
        prov2 = deliverable_provenance(proj, ["decision_memo", "risk_register", "appendix"], root)
        by = {d["name"]: d for d in prov2["deliverables"]}
        ok("decision_memo keeps its EARLIEST pin (run 1)", by["decision_memo"]["first_run_id"] == 1)
        ok("risk_register stays pre-registered (it was pinned at run 1, even though run 2 dropped it)",
           by["risk_register"]["pre_registered"] and by["risk_register"]["first_run_id"] == 1)
        ok("appendix reads added_later (first pinned at run 2 — could be a response to results)",
           by["appendix"]["first_run_id"] == 2 and by["appendix"]["pre_registered"])

        # drift: current set vs the latest pin (run 2)
        (ws / "required_deliverables.json").write_text(json.dumps(["decision_memo", "appendix", "late_addition"]),
                                                       encoding="utf-8")
        drift = contract_drift(proj, root)
        ok("drift flags a deliverable added since the latest pin", drift["declared_added"] == ["late_addition"])
        ok("drift flags nothing spuriously removed", drift["declared_removed"] == [])

    print("CONTRACT-RECEIPTS SELFTEST PASSED" if not fails else f"FAILED: {fails}")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(_selftest())
