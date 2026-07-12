"""Loop consumption of a scenario's declared `evidence_sources` — the seam that makes an EvidenceProvider
plugin actually FEED a run (previously resolved-but-unused). `scenario_supplementary_evidence` gathers evidence
from a scenario's providers BEYOND the default `local_files` (which already reads the project's `evidence.txt`
off disk), so declaring a Jira / CSV / telemetry / structured provider genuinely augments what the loop sees.
Guarded: any failure returns '' so the run's disk-evidence path is never broken."""
from __future__ import annotations


def scenario_supplementary_evidence(scenario_name: str, project: str) -> str:
    """Concatenated evidence-item bodies from a scenario's NON-default EvidenceProviders (each stamped with its
    provenance header). '' when there's no scenario, no such provider, or anything goes wrong — the caller keeps
    its disk evidence. `local_files` is excluded here because the loop already reads the flat `evidence.txt`;
    supplementary providers are the point (a structured `evidence/` dir, a connector)."""
    if not scenario_name:
        return ""
    try:
        from ztare.scenarios.loader import load_scenario
        from ztare.scenarios.resolver import resolve_capabilities

        providers = [p for p in resolve_capabilities(load_scenario(scenario_name)).get("evidence", [])
                     if getattr(p, "name", "") != "local_files"]
        chunks: "list[str]" = []
        for provider in providers:
            for item in (provider.list_evidence(project) or []):
                fetched = provider.fetch(item.ref)
                body = (getattr(fetched, "body", "") or "").strip() if fetched else ""
                if body:
                    chunks.append(f"[{getattr(provider, 'name', '?')}:{item.title}]\n{body}")
        return ("\n\n".join(chunks) + "\n") if chunks else ""
    except Exception:  # noqa: BLE001 — evidence augmentation is best-effort; never break the run's disk path
        return ""


def _selftest() -> int:
    fails: "list[str]" = []

    def ok(name: str, cond: bool) -> None:
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}")
        if not cond:
            fails.append(name)

    # A fake non-default provider + a REAL temp scenario file exercise the whole function end-to-end (proving
    # loop consumption WITHOUT the 9k-line loop). local_files is declared too — it must be SKIPPED (disk path).
    from ztare.common.paths import SCENARIOS_DIR
    from ztare.scenarios import registry
    from ztare.scenarios.protocols import EvidenceItem

    class _FakeProvider:
        name = "fake_evidence"

        def list_evidence(self, project):
            return [EvidenceItem(ref=f"{project}/x", title="ticket-42", kind="document")]

        def fetch(self, ref):
            return EvidenceItem(ref=ref, title="ticket-42", kind="document",
                                body="Customers report checkout latency spikes on mobile.")

    registry.register("evidence", "fake_evidence", _FakeProvider())
    tmp = SCENARIOS_DIR / "__evidence_intake_selftest.yaml"
    try:
        SCENARIOS_DIR.mkdir(parents=True, exist_ok=True)
        tmp.write_text("name: __evidence_intake_selftest\nrubric: product_manager\n"
                       "evidence_sources:\n  - local_files\n  - fake_evidence\n", encoding="utf-8")
        got = scenario_supplementary_evidence("__evidence_intake_selftest", "proj")
        ok("a non-default provider is consumed end-to-end (local_files skipped, no dup of evidence.txt)",
           "latency spikes" in got and "ticket-42" in got)
    finally:
        tmp.unlink(missing_ok=True)
    ok("no-scenario ⇒ empty (guarded, never breaks the disk path)",
       scenario_supplementary_evidence("", "proj") == "")
    ok("unknown scenario ⇒ empty, no crash", scenario_supplementary_evidence("__nope__", "proj") == "")

    print("EVIDENCE-INTAKE SELFTEST", "PASSED" if not fails else f"FAILED {fails}")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(_selftest())
