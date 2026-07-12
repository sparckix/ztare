"""Warrant recheck — the GENERAL production door that mints, holds, demotes, and expires a re-executable (W1)
warrant, by RE-RUNNING its bound check. This is what makes a scenario W1-dense WITHOUT a per-scenario script:
a scenario declares a `recheck` capability (e.g. the covenant recompute), the project binds it by name, and
`ztare scenario recheck --project X` re-executes each bound check and reconciles the project's governed overlay:

  * PASS  -> the re-executable evidence node + its SUPPORTS edge are (re)written at the earned warrant (W1/W0),
             stamped `last_checked=now`  ("earned" the first time, "held" thereafter);
  * FAIL  -> the warrant is DROPPED (a warrant you can no longer re-earn is not a warrant — the ratchet is the
             failure mode this whole feature exists to prevent);
  * EXPIRE-> a warrant whose `last_checked` is older than the `--half-life-days` horizon (and not re-earned this
             run) is dropped as stale. "Decisions age like organisms."

The DRIVER is the single writer: a capability only REPORTS pass/fail (it never writes the graph), so a warrant
is minted only by a passing check, never by fiat. All overlay writes go through the recheck-owned slice of the
governed overlay (`adapters.set_recheck_overlay_entries`), so demotion actually removes strength; wager-written
overlay entries are never touched. Deterministic given `now` (injected, not read from a clock).
"""
from __future__ import annotations

RECHECK_WARRANTS = ("W0", "W1")  # a recheck may license at most a re-executable (W1) or kernel-cert (W0) warrant


def _bindings_path(project: str, repo_root):
    from pathlib import Path
    return Path(repo_root) / "projects" / project / "workspace" / "warrant_rechecks.json"


def _state_path(project: str, repo_root):
    from pathlib import Path
    return Path(repo_root) / "projects" / project / "workspace" / "warrant_recheck_state.json"


def _receipts_path(project: str, repo_root):
    from pathlib import Path
    return Path(repo_root) / "projects" / project / "workspace" / "recheck_receipts.jsonl"


_CALIBRATION_MIN_N = 5  # below this a tier is UNCALIBRATED — never report a hold-rate off a handful of rechecks


def tier_hold_rates(project: str, repo_root) -> dict:
    """CALIBRATED confidence done honestly: the empirical HOLD-RATE per backing tier, read from the EXISTING
    recheck receipts — the only admissible calibration source today (each row is a REAL re-execution of a
    warrant: held/earned = the tier's warrant re-verified, demoted/failed = it did not; `expired` is a half-life
    event, not an outcome, so it's excluded). Small-N (W1 in practice). Per tier: {held, total, rate} if
    total ≥ _CALIBRATION_MIN_N, else {..., rate: None, uncalibrated: True}. NEVER sited at recompile (which
    recomputes HYPOTHETICAL states — logging those would fabricate outcomes, Fable); reads only the real log."""
    import json

    from ztare.scenarios.tiers import TIER_NAME

    held_by: "dict[str, int]" = {}
    total_by: "dict[str, int]" = {}
    p = _receipts_path(project, repo_root)
    if p.is_file():
        for line in p.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except Exception:  # noqa: BLE001 — a malformed line is skipped
                continue
            w, st = str(row.get("warrant") or ""), str(row.get("status") or "")
            if w not in TIER_NAME or st not in ("held", "earned", "demoted", "failed"):
                continue
            total_by[w] = total_by.get(w, 0) + 1
            if st in ("held", "earned"):
                held_by[w] = held_by.get(w, 0) + 1
    per_tier: "dict[str, dict]" = {}
    for w, total in total_by.items():
        held = held_by.get(w, 0)
        per_tier[TIER_NAME[w]] = ({"held": held, "total": total, "rate": round(held / total, 3)}
                                  if total >= _CALIBRATION_MIN_N
                                  else {"held": held, "total": total, "rate": None, "uncalibrated": True})
    return {"per_tier": per_tier, "n_total": sum(total_by.values()),
            "calibrated": any(v.get("rate") is not None for v in per_tier.values())}


def load_bindings(project: str, repo_root) -> "list[str]":
    """The recheck capability NAMES bound to a project (data, part of the seed) — a JSON list, or empty."""
    import json

    p = _bindings_path(project, repo_root)
    if not p.is_file():
        return []
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001 — a malformed bindings file binds nothing, never crashes
        return []
    return [str(n) for n in data] if isinstance(data, list) else []


def _load_state(project: str, repo_root) -> dict:
    import json

    p = _state_path(project, repo_root)
    if not p.is_file():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8")) or {}
    except Exception:  # noqa: BLE001
        return {}


def _age_days(last: str, now: str) -> "float | None":
    """Whole days between two ISO YYYY-MM-DD dates, or None if either is unparseable (⇒ never expires on age)."""
    from datetime import date

    try:
        return (date.fromisoformat(now[:10]) - date.fromisoformat(last[:10])).days
    except Exception:  # noqa: BLE001
        return None


def recheck_project(project: str, repo_root, *, now: str = "", half_life_days: "int | None" = None,
                    capability_names: "list[str] | None" = None) -> dict:
    """Re-run every bound recheck capability and reconcile the project's recheck-owned overlay + state. Returns
    `{project, now, receipts}`. Deterministic given `now` (an ISO date string; "" ⇒ no half-life expiry)."""
    from ztare.scenarios import registry
    from ztare.scenarios.adapters import RECHECK_ID_PREFIX, set_recheck_overlay_entries

    names = list(capability_names) if capability_names is not None else load_bindings(project, repo_root)
    state = _load_state(project, repo_root)
    receipts: "list[dict]" = []
    elements: "list[dict]" = []
    edges: "list[dict]" = []

    for name in names:
        cap = registry.get("recheck", name)
        if cap is None:
            state.pop(name, None)
            receipts.append({"capability": name, "status": "missing_capability",
                             "reason": "no registered recheck capability by that name", "checked": now})
            continue
        try:
            r = cap.recheck(project) or {}
        except Exception as exc:  # noqa: BLE001 — a raising check is a FAILED check (fail-closed)
            r = {"passed": False, "detail": f"check raised {type(exc).__name__}: {exc}"}

        if not r.get("passed"):
            existed = name in state
            state.pop(name, None)
            receipts.append({"capability": name, "status": "demoted" if existed else "failed",
                             "reason": "check did not pass", "detail": str(r.get("detail", "")), "checked": now})
            continue

        warrant = str(r.get("warrant") or "W1")
        if warrant not in RECHECK_WARRANTS:
            warrant = "W1"
        tgt = r.get("target") or {}
        src = str(tgt.get("src") or f"{RECHECK_ID_PREFIX}{name}")
        if not src.startswith(RECHECK_ID_PREFIX):  # the driver OWNS the id namespace — force it, so demotion works
            src = f"{RECHECK_ID_PREFIX}{name}"
        dst = str(tgt.get("dst") or "thesis")
        kind = str(tgt.get("kind") or "SUPPORTS")
        text = str(tgt.get("text") or "")
        held = bool(state.get(name, {}).get("passed"))
        state[name] = {"last_checked": now, "warrant": warrant, "passed": True,
                       "target": {"src": src, "kind": kind, "dst": dst, "text": text},
                       "detail": str(r.get("detail", ""))}
        receipts.append({"capability": name, "status": "held" if held else "earned", "warrant": warrant,
                         "target": {"src": src, "kind": kind, "dst": dst}, "detail": str(r.get("detail", "")),
                         "checked": now})

    # Half-life: drop any recheck-owned warrant whose last_checked is older than the horizon and NOT re-earned
    # this run (re-earned entries just refreshed last_checked=now, so they cannot be stale).
    if half_life_days is not None and now:
        for name, st in list(state.items()):
            age = _age_days(str(st.get("last_checked") or ""), now)
            if age is not None and age > half_life_days:
                state.pop(name, None)
                receipts.append({"capability": name, "status": "expired",
                                 "reason": f"warrant {age}d old > {half_life_days}d half-life", "checked": now})

    # Rebuild the recheck-owned overlay from the FULL state (every currently-valid warrant), NOT just the names
    # touched this run — a scoped recheck (capability_names subset) must not silently drop a bound capability's
    # still-valid warrant (Sonnet review). `state` holds exactly the surviving warrants after pass/fail/expire.
    elements = [{"id": st["target"]["src"], "kind": "evidence", "text": st["target"].get("text", "")}
                for st in state.values() if st.get("passed") and st.get("target")]
    edges = [{"src": st["target"]["src"], "kind": st["target"].get("kind", "SUPPORTS"),
              "dst": st["target"].get("dst", "thesis"), "warrant": st.get("warrant", "W1")}
             for st in state.values() if st.get("passed") and st.get("target")]
    set_recheck_overlay_entries(project, repo_root, elements, edges)
    _save_state(project, repo_root, state)
    _append_receipts(project, repo_root, receipts)
    return {"project": project, "now": now, "receipts": receipts}


def _save_state(project: str, repo_root, state: dict) -> None:
    import json

    p = _state_path(project, repo_root)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(state, indent=2), encoding="utf-8")


def _append_receipts(project: str, repo_root, receipts: "list[dict]") -> None:
    import json

    if not receipts:
        return
    p = _receipts_path(project, repo_root)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as fh:
        for r in receipts:
            fh.write(json.dumps(r) + "\n")


def _selftest() -> int:
    """A hermetic end-to-end: a stub recheck capability, an in-place temp project, PASS→earn, FAIL→demote,
    stale→expire — all through the real overlay + strength path. No filesystem fixtures beyond a temp dir."""
    import tempfile
    from pathlib import Path

    from ztare.scenarios import registry
    from ztare.scenarios.adapters import governed_state_from_research_map
    from ztare.scenarios.strength import strength_profile

    # a togglable stub capability registered directly (bypasses the providers package)
    class _Stub:
        name = "selftest_recompute"
        passes = True

        def recheck(self, project):
            return {"passed": self.passes, "warrant": "W1",
                    "target": {"src": "ev.recheck.selftest_recompute", "kind": "SUPPORTS", "dst": "thesis",
                               "text": "recomputed: holds"}, "detail": "stub"}

    stub = _Stub()
    registry.register("recheck", stub.name, stub)

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        proj = "t"
        pdir = root / "projects" / proj
        (pdir / "workspace").mkdir(parents=True)
        # a minimal carrier: a thesis grounded by one W2 evidence + one challenge → CONTESTED at W2
        (pdir / "latest_probability_dag.json").write_text('{"outcome":{"label":"T thesis","probability":0.5},"nodes":[]}')
        (pdir / "compiled_evidence_packet.json").write_text(
            '{"immutable_ground_truth":[{"statement":"a filed figure supports T","strength":"strong"}],'
            '"identified_contradictions":[{"topic":"x","claim_a":"a","claim_b":"b","why_it_matters":"c"}]}')

        before = strength_profile(governed_state_from_research_map(proj, root))
        assert before["status"] == "CONTESTED" and before["profile"][1] <= 1e-6, before

        # PASS → earn W1 → re-executable stratum lights
        r1 = recheck_project(proj, root, now="2026-07-10", half_life_days=30, capability_names=[stub.name])
        assert r1["receipts"][0]["status"] == "earned", r1
        after = strength_profile(governed_state_from_research_map(proj, root))
        assert after["profile"][1] > before["profile"][1], (before["profile"], after["profile"])

        # re-run PASS → held (idempotent, no duplicate edge)
        r2 = recheck_project(proj, root, now="2026-07-11", half_life_days=30, capability_names=[stub.name])
        assert r2["receipts"][0]["status"] == "held", r2
        held = strength_profile(governed_state_from_research_map(proj, root))
        assert held["profile"] == after["profile"], (after["profile"], held["profile"])

        # FAIL → demote → the re-executable stratum goes dark again
        stub.passes = False
        r3 = recheck_project(proj, root, now="2026-07-12", half_life_days=30, capability_names=[stub.name])
        assert r3["receipts"][0]["status"] == "demoted", r3
        demoted = strength_profile(governed_state_from_research_map(proj, root))
        assert demoted["profile"][1] <= 1e-6, demoted

        # re-earn, then EXPIRE via half-life (now is far past last_checked, and we run with NO bound caps so it
        # cannot be re-earned this pass)
        stub.passes = True
        recheck_project(proj, root, now="2026-07-12", half_life_days=30, capability_names=[stub.name])
        rexp = recheck_project(proj, root, now="2026-09-30", half_life_days=30, capability_names=[])
        assert any(x["status"] == "expired" for x in rexp["receipts"]), rexp
        expired = strength_profile(governed_state_from_research_map(proj, root))
        assert expired["profile"][1] <= 1e-6, expired

    print("WARRANT-RECHECK SELFTEST PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(_selftest())
