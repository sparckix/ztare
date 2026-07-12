"""structured_files — a second reference EvidenceProvider (deterministic, offline). Reads a project's
`evidence/` SUBDIRECTORY (CSV rows, JSONL lines, or whole md/txt files) — a structured evidence store DISTINCT
from the flat `evidence.txt` that `local_files` + the loop already read. So a scenario declaring
`structured_files` genuinely augments the run (proving the EvidenceProvider seam end-to-end), and it's the
pattern a real connector (Jira export, telemetry CSV) follows. Bounded, local-first; deleting this file removes
it with zero kernel change (the rot test)."""
from __future__ import annotations

from pathlib import Path

from ztare.common.paths import PROJECTS_DIR
from ztare.scenarios.protocols import EvidenceItem
from ztare.scenarios.registry import capability


@capability("evidence", "structured_files")
class StructuredFilesEvidenceProvider:
    name = "structured_files"

    def _evidence_dir(self, project: str) -> Path:
        base = Path(project) if Path(project).is_dir() else (PROJECTS_DIR / project)
        return base / "evidence"

    def list_evidence(self, project: str) -> "list[EvidenceItem]":
        root = self._evidence_dir(project)
        if not root.is_dir():
            return []
        items: "list[EvidenceItem]" = []
        for f in sorted(root.rglob("*")):
            if f.is_file() and f.suffix.lower() in (".csv", ".jsonl", ".md", ".txt"):
                items.append(EvidenceItem(ref=str(f), title=f.name, kind="document",
                                          meta={"suffix": f.suffix.lower()}))
        return items

    def fetch(self, ref: str) -> "EvidenceItem | None":
        f = Path(ref)
        if not f.is_file():
            return None
        try:
            raw = f.read_text(encoding="utf-8", errors="replace")
        except Exception:  # noqa: BLE001 — unreadable evidence yields a ref/title, never a crash
            raw = ""
        body = _rows_to_text(raw, f.suffix.lower())
        return EvidenceItem(ref=ref, title=f.name, kind="document", body=body,
                            meta={"suffix": f.suffix.lower()})


def _rows_to_text(raw: str, suffix: str) -> str:
    """Flatten a structured evidence file to bounded plain text the loop can read. CSV → 'col=val; …' per row;
    JSONL → one compact object per line; md/txt → verbatim. Deterministic, no external deps."""
    if suffix == ".csv":
        import csv
        import io
        try:
            rows = list(csv.DictReader(io.StringIO(raw)))
        except Exception:  # noqa: BLE001 — a malformed CSV falls back to verbatim
            return raw
        return "\n".join("; ".join(f"{k}={v}" for k, v in r.items()) for r in rows)
    if suffix == ".jsonl":
        import json
        out: "list[str]" = []
        for line in raw.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.dumps(json.loads(line), ensure_ascii=False, separators=(",", ":")))
            except Exception:  # noqa: BLE001 — a bad line passes through verbatim
                out.append(line)
        return "\n".join(out)
    return raw


def _selftest() -> int:
    import tempfile
    from pathlib import Path as _P

    fails: "list[str]" = []

    def ok(name: str, cond: bool) -> None:
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}")
        if not cond:
            fails.append(name)

    d = _P(tempfile.mkdtemp())
    (d / "evidence").mkdir()
    (d / "evidence" / "tickets.csv").write_text("id,summary\n42,checkout latency on mobile\n", encoding="utf-8")
    (d / "evidence" / "signals.jsonl").write_text('{"metric":"p95","value":900}\n', encoding="utf-8")
    (d / "evidence.txt").write_text("this is the FLAT evidence.txt (must NOT be read by structured_files)", encoding="utf-8")

    prov = StructuredFilesEvidenceProvider()
    items = prov.list_evidence(str(d))
    ok("reads the evidence/ subdir only (2 files), NOT the flat evidence.txt",
       len(items) == 2 and all("evidence.txt" not in i.ref for i in items))
    csv_item = next(i for i in items if i.ref.endswith(".csv"))
    body = prov.fetch(csv_item.ref).body
    ok("CSV rows flatten to readable key=val text", "summary=checkout latency on mobile" in body)
    jsonl_item = next(i for i in items if i.ref.endswith(".jsonl"))
    ok("JSONL flattens to compact objects", '"metric":"p95"' in prov.fetch(jsonl_item.ref).body)
    ok("no evidence/ dir ⇒ empty (no crash)", prov.list_evidence(tempfile.mkdtemp()) == [])

    print("STRUCTURED-FILES SELFTEST", "PASSED" if not fails else f"FAILED {fails}")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(_selftest())
