"""Reader-only LeanMill proof-job briefing.

Proof work is intentionally async: worldmodel play should emit proof tasks and
continue, while later cycles consume job receipts and kernel-ratified invariant
certificates. This provider keeps the async job state visible without polling a
process or running proof code during prompt assembly.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from ztare.orchestrator.mutator_briefing import BriefingContext, BriefingProvider


class LeanMillProofJobsProvider(BriefingProvider):
    name = "leanmill_proof_jobs"
    priority = 33
    max_fragment_chars = 900

    _DECL_RE = re.compile(r"^(?:private\s+)?(?:theorem|lemma)\s+([A-Za-z0-9_'.]+)\b")

    def _repo_root(self, project: Path) -> Path:
        return project.parent.parent

    def _job_rows(self, project: Path) -> list[dict]:
        root = project / "leanmill" / "jobs"
        if not root.exists():
            return []
        rows: list[dict] = []
        for path in sorted(root.glob("lm_*.json"), reverse=True):
            if path.name.endswith("_result.json"):
                continue
            try:
                job = json.loads(path.read_text(encoding="utf-8"))
            except SystemExit:
                raise
            except Exception as exc:  # noqa: BLE001
                # Corrupt job file: surface it (do not silently drop) so the
                # section renders a marker instead of vanishing.
                rows.append({
                    "job": {}, "result": {}, "result_unreadable": "",
                    "job_unreadable": f"{path.name}: {type(exc).__name__}: {exc}",
                })
                if len(rows) >= 5:
                    break
                continue
            if not isinstance(job, dict):
                continue
            result = {}
            result_unreadable = ""
            result_ref = (job.get("paths") or {}).get("result") or job.get("result_path")
            if result_ref:
                rpath = project.parent.parent / result_ref
                if not rpath.exists():
                    rpath = project / result_ref
                if rpath.exists():
                    # An UNREADABLE result must NOT masquerade as a live
                    # "pending" — that fabricates job status. Flag it.
                    try:
                        result = json.loads(rpath.read_text(encoding="utf-8"))
                    except SystemExit:
                        raise
                    except Exception as exc:  # noqa: BLE001
                        result_unreadable = f"{type(exc).__name__}: {exc}"
            rows.append({"job": job, "result": result, "result_unreadable": result_unreadable})
            if len(rows) >= 5:
                break
        return rows

    def _feedback_receipt(self, project: Path) -> dict:
        path = project / "workspace" / "worldmodel_lean_feedback_receipt.json"
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
        except Exception:  # noqa: BLE001
            return {}

    def _wip_surfaces(self, project: Path) -> list[dict]:
        root = self._repo_root(project) / "ztare_proofs" / ".solver_scratch"
        if not root.exists():
            return []
        surfaces: list[dict] = []
        # `RobustProbe_<target>_<provider>_<attempt>.lean` is deterministic
        # via ztare.leanmill.solver.agentic_leaf.robust_probe_name. Read every
        # canonical probe surface; do not assume a specific provider or attempt.
        for path in sorted(root.glob("RobustProbe_*.lean"),
                           key=lambda p: p.stat().st_mtime, reverse=True)[:8]:
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except Exception:  # noqa: BLE001
                continue
            names: list[str] = []
            receipts: list[str] = []
            for line in text.splitlines():
                stripped = line.strip()
                m = self._DECL_RE.match(stripped)
                if m:
                    names.append(m.group(1))
                if stripped.startswith("-- RECEIPT:"):
                    receipts.append(stripped[3:].strip())
            interesting = [
                n for n in names
                if not n.startswith(("growOnce", "componentsOf", "componentGo"))
            ]
            if not interesting and not receipts:
                continue
            surfaces.append({
                "path": path.relative_to(self._repo_root(project)).as_posix(),
                "decls": interesting[-8:],
                "receipts": receipts[-3:],
                "status": "wip_hypothesis_only",
            })
        return surfaces[:3]

    def applies(self, ctx: BriefingContext) -> bool:
        project = Path(ctx.project_dir)
        return bool(
            self._job_rows(project)
            or self._feedback_receipt(project)
            or self._wip_surfaces(project)
        )

    def fragment(self, ctx: BriefingContext) -> str:
        project = Path(ctx.project_dir)
        jobs = self._job_rows(project)
        receipt = self._feedback_receipt(project)
        surfaces = self._wip_surfaces(project)
        lines = [
            "## LeanMill Proof Jobs",
            "- Proof work is async. Do not block the play loop waiting on a proof; consume only persisted job receipts and `workspace/invariant_certificates.jsonl`.",
            "- Abstraction boundary: read grid/color proof names as finite-support predicate-measure witnesses; do not promote substrate vocabulary into a kernel concept without a ratified operator certificate.",
        ]
        if receipt.get("async_command"):
            lines.append(f"- launch_async={receipt['async_command']}")
        if receipt.get("absorb_command_template"):
            lines.append(f"- absorb_on_close={receipt['absorb_command_template']}")
        for row in jobs:
            if row.get("job_unreadable"):
                lines.append(
                    f"- ⚠️  UNREADABLE job file: {row['job_unreadable']}; "
                    f"status UNKNOWN; prior guidance still in force"
                )
                continue
            job, result = row["job"], row["result"]
            paths = job.get("paths") or {}
            result_status = (
                f"UNREADABLE ({row['result_unreadable']})"
                if row.get("result_unreadable")
                else result.get("status", "pending")
            )
            lines.append(
                f"- job={paths.get('job', '?')}; action={job.get('action', '?')}; "
                f"target={job.get('target_name') or job.get('notes_path') or '?'}; "
                f"status={job.get('status', '?')}; result={result_status}; "
                f"artifact={result.get('artifact_path') or job.get('expected_artifact') or '?'}"
            )
        for surf in surfaces:
            lines.append(
                f"- wip_surface={surf['path']}; status={surf['status']}; "
                f"decls={', '.join(surf['decls'][:6]) or '?'}"
            )
            for note in surf["receipts"]:
                lines.append(f"  - {note}")
        return "\n".join(lines) + "\n"

    def structured_records(self, ctx: BriefingContext) -> list[dict]:
        records = []
        project = Path(ctx.project_dir)
        receipt = self._feedback_receipt(project)
        if receipt:
            records.append({
                "provider": self.name,
                "source_type": "leanmill_feedback_receipt",
                "summary": "worldmodel proof-work handoff is available",
                "action": receipt.get("async_command") or receipt.get("next_command") or "",
                "source_ref": "workspace/worldmodel_lean_feedback_receipt.json",
                "authority": "proof work only until invariant certificates are written",
            })
        for row in self._job_rows(project):
            if row.get("job_unreadable"):
                records.append({
                    "provider": self.name,
                    "source_type": "leanmill_proof_job_unreadable",
                    "summary": f"UNREADABLE job file: {row['job_unreadable']}",
                })
                continue
            job, result = row["job"], row["result"]
            result_status = (
                f"UNREADABLE ({row['result_unreadable']})"
                if row.get("result_unreadable")
                else result.get("status", "pending")
            )
            records.append({
                "provider": self.name,
                "source_type": "leanmill_proof_job",
                "summary": f"{job.get('action', '?')} {job.get('status', '?')} / {result_status}",
                "action": result.get("artifact_path") or job.get("expected_artifact") or "",
                "source_ref": (job.get("paths") or {}).get("job", ""),
                "target_name": job.get("target_name", ""),
            })
        for surf in self._wip_surfaces(project):
            records.append({
                "provider": self.name,
                "source_type": "leanmill_wip_proof_surface",
                "summary": ", ".join(surf["decls"][:6]),
                "source_ref": surf["path"],
                "authority": "hypothesis only until absorbed as an invariant certificate",
                "receipts": surf["receipts"],
                "status": surf["status"],
            })
        return records
