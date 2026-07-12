"""Tests for the ARC↔LeanMill feedback return edge (GP-250 checkpoint hook).

Three contracts:
  1. COMPLETED proof_audit job → absorb_ratification called → invariant_certificates.jsonl written.
  2. No completed job → no-op, no crash, nothing written.
  3. Campaign kick is idempotent: same blueprint sha → single Popen call.

Wire-through:
  4. A certificate in invariant_certificates.jsonl is returned by _invariants() and ProvenInvariantsProvider.
  5. absorb_ratification round-trip: job receipt → jsonl → _invariants reads it.

All tests are unit/integration only — no live play-loop run.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_project(tmp_path: Path) -> Path:
    """Minimal project directory layout."""
    p = tmp_path / "projects" / "test_proj"
    (p / "workspace").mkdir(parents=True)
    (p / "leanmill" / "jobs").mkdir(parents=True)
    return p


def _write_cert_direct(project: Path, theorem: str = "myInvariant") -> None:
    """Write a well-formed certificate line directly (bypasses proof audit)."""
    line = json.dumps({
        "quantity": ["count", 3],
        "relation": "non_increasing",
        "status": "kernel_ratified",
        "theorem": theorem,
        "artifact_sha256": "abc",
        "proof_audit_sha256": "def",
    })
    out = project / "workspace" / "invariant_certificates.jsonl"
    out.write_text(line + "\n", encoding="utf-8")


def _make_lean_file(tmp_path: Path, theorem_name: str = "myInvariant") -> Path:
    """Minimal .lean file with a theorem matching invariant_from_theorem's regex.

    Must not contain 'sorry' or 'admit' — _proof_audit_passes checks local_static_clean.
    The proof body is a placeholder native tactic that won't be executed in tests.
    """
    lean = tmp_path / f"{theorem_name}.lean"
    lean.write_text(
        f"theorem {theorem_name} (g : Grid) :\n"
        "  countColor (specStep g) 3 ≤ countColor g 3 := by\n"
        "  exact Nat.le_refl _\n",
        encoding="utf-8",
    )
    return lean


def _make_proof_audit_receipt(lean_file: Path, theorem_name: str) -> dict:
    """A receipt that passes _proof_audit_passes (schema + sha-matched to the lean file).

    _proof_audit_passes computes sha256 over source.encode('utf-8') (text), so match that.
    """
    import hashlib
    source = lean_file.read_text(encoding="utf-8")
    sha = hashlib.sha256(source.encode("utf-8")).hexdigest()
    return {
        "schema": "leanmill-pr-a1-compile-l3-audit-v1",
        "status": "compile_pass_l3_advisory_pass",
        "target": str(lean_file),
        "target_sha256": sha,
        "top_level_target_resolved": theorem_name,
        "static_clean": True,
        "static": {"sorry_count": 0, "admit_count": 0, "axiom_decl_count": 0},
        "compile": {"ok": True},
        "kernel_axiom_policy": {"allowlist_ok": True, "disallowed_axioms": []},
        "l3_audit": {
            "status": "pass",
            "rows": [{"name": theorem_name}],
            "confirmed_blockers": [],
            "review_flags": [],
        },
    }


def _write_job_file(project: Path, lean_file: Path, theorem_name: str,
                    result_status: str = "completed", ok: bool = True) -> Path:
    """Write a lm_*.json job + result file for a proof_audit action."""
    jobs_dir = project / "leanmill" / "jobs"
    job_id = "lm_20260709_test0001"
    job_path = jobs_dir / f"{job_id}.json"
    result_path = jobs_dir / f"{job_id}_result.json"
    # paths stored relative to REPO root
    try:
        src_rel = lean_file.relative_to(REPO)
    except ValueError:
        src_rel = lean_file  # absolute fallback
    try:
        res_rel = result_path.relative_to(REPO)
    except ValueError:
        res_rel = result_path
    job = {
        "schema": "ztare-leanmill-workbench-job-v1",
        "action": "proof_audit",
        "status": result_status,
        # ponytail: store absolute path so the checkpoint can find the file regardless of REPO
        "source_file": str(lean_file.resolve()),
        "target_name": theorem_name,
        "paths": {
            "job": str(job_path.resolve()),
            "result": str(result_path.resolve()),
        },
    }
    result = {
        "schema": "ztare-leanmill-workbench-action-v1",
        "ok": ok,
        "status": result_status,
        "action": "proof_audit",
        "artifact_path": str(lean_file),
    }
    job_path.write_text(json.dumps(job, indent=2) + "\n", encoding="utf-8")
    result_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return job_path


# ---------------------------------------------------------------------------
# 1. Completed job → absorb_ratification → certificate written
# ---------------------------------------------------------------------------

def test_checkpoint_absorbs_completed_job(tmp_path):
    """A COMPLETED proof_audit job causes absorb_ratification to write invariant_certificates.jsonl."""
    project = _make_project(tmp_path)
    lean_file = _make_lean_file(tmp_path, "myInvariant")
    _write_job_file(project, lean_file, "myInvariant", result_status="completed", ok=True)

    receipt = _make_proof_audit_receipt(lean_file, "myInvariant")

    sys.path.insert(0, str(REPO / "scripts" / "public" / "control"))
    import importlib
    import arc3_play_loop as pl
    importlib.reload(pl)  # ensure fresh module with our edits

    with patch("ztare.worldmodel.lean_bridge._run_proof_audit", return_value=receipt), \
         patch("subprocess.Popen") as mock_popen:
        mock_popen.return_value = MagicMock(pid=99999)
        pl._lean_feedback_checkpoint(project, None, None)

    cert_path = project / "workspace" / "invariant_certificates.jsonl"
    assert cert_path.exists(), "invariant_certificates.jsonl was not written"
    lines = [l for l in cert_path.read_text().splitlines() if l.strip()]
    assert len(lines) == 1
    cert = json.loads(lines[0])
    assert cert["theorem"] == "myInvariant"
    assert cert["status"] == "kernel_ratified"
    assert cert["relation"] == "non_increasing"


# ---------------------------------------------------------------------------
# 2. No completed job → no-op, no crash
# ---------------------------------------------------------------------------

def test_checkpoint_noop_when_no_completed_job(tmp_path):
    """When no completed proof_audit job exists, the checkpoint is a silent no-op."""
    project = _make_project(tmp_path)
    # write a running (not completed) job
    lean_file = _make_lean_file(tmp_path, "pendingInvariant")
    _write_job_file(project, lean_file, "pendingInvariant", result_status="running", ok=False)

    sys.path.insert(0, str(REPO / "scripts" / "public" / "control"))
    import importlib
    import arc3_play_loop as pl
    importlib.reload(pl)

    pl._lean_feedback_checkpoint(project, None, None)  # must not raise

    cert_path = project / "workspace" / "invariant_certificates.jsonl"
    assert not cert_path.exists(), "should not have written certs for a running job"


# ---------------------------------------------------------------------------
# 3. Campaign kick is idempotent
# ---------------------------------------------------------------------------

def test_campaign_kick_idempotent(tmp_path):
    """Same blueprint sha → Popen called only once across two checkpoint calls."""
    project = _make_project(tmp_path)
    bp = tmp_path / "worldmodel_auto_blueprint.md"
    bp.write_text("# Blueprint\n", encoding="utf-8")
    sha = "deadbeef" * 8  # 64-char hex

    sys.path.insert(0, str(REPO / "scripts" / "public" / "control"))
    import importlib
    import arc3_play_loop as pl
    importlib.reload(pl)

    with patch("subprocess.Popen") as mock_popen:
        mock_popen.return_value = MagicMock(pid=12345)
        pl._lean_feedback_checkpoint(project, bp, sha)
        pl._lean_feedback_checkpoint(project, bp, sha)  # same sha → idempotent

    assert mock_popen.call_count == 1, (
        f"Popen called {mock_popen.call_count} times for the same blueprint sha "
        "(expected 1 — idempotency violated)"
    )


# ---------------------------------------------------------------------------
# 4. Wire-through: certificate reaches _invariants() and ProvenInvariantsProvider
# ---------------------------------------------------------------------------

def test_invariants_reads_certificate(tmp_path):
    """_invariants() returns the certificate once invariant_certificates.jsonl exists."""
    project = _make_project(tmp_path)
    _write_cert_direct(project, "myInvariant")

    sys.path.insert(0, str(REPO / "scripts" / "public" / "control"))
    import importlib
    import arc3_play_loop as pl
    importlib.reload(pl)

    certs = pl._invariants(project)
    assert len(certs) == 1
    c = certs[0]
    assert c.relation == "non_increasing"
    assert c.theorem == "myInvariant"
    assert c.status == "kernel_ratified"


def test_proven_invariants_provider_returns_certificate(tmp_path):
    """ProvenInvariantsProvider.applies() is True and fragment() mentions the theorem."""
    project = _make_project(tmp_path)
    _write_cert_direct(project, "capstoneInvariant")

    from ztare.orchestrator.briefing_providers.proven_invariants import ProvenInvariantsProvider
    from ztare.orchestrator.mutator_briefing import BriefingContext

    ctx = BriefingContext(project_dir=project, iter_index=0, rubric={})
    provider = ProvenInvariantsProvider()
    assert provider.applies(ctx), "provider should apply when certs exist"
    fragment = provider.fragment(ctx)
    assert "capstoneInvariant" in fragment or "non_increasing" in fragment


def test_reachability_reads_certificate(tmp_path):
    """reachability.py uses invariant_certificates.jsonl path (smoke check the import)."""
    from ztare.worldmodel import reachability
    # The module references "invariant_certificates.jsonl" in its docstring/code
    src = Path(reachability.__file__).read_text(encoding="utf-8")
    assert "invariant_certificates.jsonl" in src, (
        "reachability.py no longer references invariant_certificates.jsonl — check the wire"
    )


# ---------------------------------------------------------------------------
# 5. absorb_ratification round-trip (the severed wire, end-to-end)
# ---------------------------------------------------------------------------

def test_absorb_ratification_roundtrip(tmp_path):
    """absorb_ratification → invariant_certificates.jsonl → _invariants reads it."""
    project = _make_project(tmp_path)
    lean_file = _make_lean_file(tmp_path, "roundtripInvariant")
    receipt = _make_proof_audit_receipt(lean_file, "roundtripInvariant")

    from ztare.worldmodel.lean_bridge import absorb_ratification, extract_theorem_statements
    from ztare.worldmodel.invariant_bridge import InvariantCertificate

    stmts = extract_theorem_statements(
        lean_file.read_text(encoding="utf-8"), ["roundtripInvariant"]
    )
    assert stmts, "extract_theorem_statements returned nothing"

    with patch("ztare.worldmodel.lean_bridge._run_proof_audit", return_value=receipt):
        certs = absorb_ratification(project, lean_file, stmts)

    assert len(certs) == 1
    assert isinstance(certs[0], InvariantCertificate)
    assert certs[0].theorem == "roundtripInvariant"

    # Now read back via _invariants
    sys.path.insert(0, str(REPO / "scripts" / "public" / "control"))
    import importlib
    import arc3_play_loop as pl
    importlib.reload(pl)

    read_back = pl._invariants(project)
    assert len(read_back) == 1
    assert read_back[0].theorem == "roundtripInvariant"
    assert read_back[0].status == "kernel_ratified"


# ---------------------------------------------------------------------------
# 6. ZTARE_ARC_LEAN_FEEDBACK=0 disables the hook
# ---------------------------------------------------------------------------

def test_env_flag_disables_hook(tmp_path, monkeypatch):
    """ZTARE_ARC_LEAN_FEEDBACK=0 makes _lean_feedback_checkpoint a no-op."""
    monkeypatch.setenv("ZTARE_ARC_LEAN_FEEDBACK", "0")
    project = _make_project(tmp_path)
    lean_file = _make_lean_file(tmp_path, "disabledInvariant")
    _write_job_file(project, lean_file, "disabledInvariant", result_status="completed", ok=True)

    sys.path.insert(0, str(REPO / "scripts" / "public" / "control"))
    import importlib
    import arc3_play_loop as pl
    importlib.reload(pl)

    with patch("subprocess.Popen") as mock_popen, \
         patch("ztare.worldmodel.lean_bridge._run_proof_audit") as mock_audit:
        pl._lean_feedback_checkpoint(project, None, None)
        assert mock_popen.call_count == 0
        assert mock_audit.call_count == 0

    assert not (project / "workspace" / "invariant_certificates.jsonl").exists()
