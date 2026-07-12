"""local_files — the reference EvidenceProvider. Reads a project's evidence from the repo's projects dir (or
an explicit directory path). Bounded, local, provenance-preserving — the same local-first discipline as the
rest of ZTARE; Confluence / Jira / telemetry providers plug in over the same contract."""
from __future__ import annotations

from pathlib import Path

from ztare.common.paths import PROJECTS_DIR
from ztare.scenarios.protocols import EvidenceItem
from ztare.scenarios.registry import capability

_TEXT_SUFFIXES = {".md", ".txt", ".json", ".yaml", ".yml", ".csv"}


@capability("evidence", "local_files")
class LocalFilesEvidenceProvider:
    name = "local_files"

    def _root(self, project: str) -> Path:
        # a scenario's project may be a bare name (projects/<name>/) or an explicit directory path.
        p = Path(project)
        return p if p.is_dir() else (PROJECTS_DIR / project)

    def list_evidence(self, project: str) -> "list[EvidenceItem]":
        root = self._root(project)
        if not root.is_dir():
            return []
        items: "list[EvidenceItem]" = []
        for f in sorted(root.rglob("*")):
            if f.is_file() and f.suffix.lower() in _TEXT_SUFFIXES:
                items.append(EvidenceItem(
                    ref=str(f), title=f.name, kind="document",
                    meta={"suffix": f.suffix.lower(), "bytes": f.stat().st_size},
                ))
        return items

    def fetch(self, ref: str) -> "EvidenceItem | None":
        f = Path(ref)
        if not f.is_file():
            return None
        body = ""
        if f.suffix.lower() in _TEXT_SUFFIXES:
            try:
                body = f.read_text(encoding="utf-8", errors="replace")
            except Exception:  # noqa: BLE001 — unreadable evidence still yields a ref/title, never a crash
                body = ""
        return EvidenceItem(ref=ref, title=f.name, kind="document", body=body,
                            meta={"suffix": f.suffix.lower()})
