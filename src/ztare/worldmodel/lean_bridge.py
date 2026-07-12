"""Deterministic worldmodel <-> leanmill feedback loop (GP-250).

Closes the loop the spec_lean certificate path opened: evidence -> conjectured
invariants -> a leanmill blueprint -> (campaign) -> kernel-ratified certificates
that ProvenInvariantsProvider and the reachability admissibility filter already
consume. Every edge is DETERMINISTIC — no LLM writes a conjecture or a
certificate; the leaf model only proves the `sorry` a campaign is handed.

  conjecture_invariants   evidence -> count-monotone / conserved conjectures
  blueprint_from_spec     spec_lean Theory + the first conjecture as ## Target
  write_blueprint         idempotent .md emission into <project>/workspace
  absorb_ratification     the FEEDBACK EDGE: compile-verify, then persist certs
  record_refutation       a disproved conjecture, kept out of the certs stream
"""

from __future__ import annotations

import json
import hashlib
import re
import argparse
import sys
import subprocess
import tempfile
from collections import Counter
from pathlib import Path

from ztare.worldmodel.invariant_bridge import invariant_from_theorem


def _counts(grid) -> Counter:
    c: Counter = Counter()
    for row in grid:
        c.update(row)
    return c


def _env_frames(log) -> set:
    # ponytail: env-frame detection is the gate's job; import it defensively so
    # a stripped worldmodel (or a bad log) degrades to "no frames excluded".
    try:
        from ztare.worldmodel.gates import env_frame_indices
        return env_frame_indices(log)
    except Exception:  # noqa: BLE001
        return set()


def conjecture_invariants(log, spec, roles) -> "list[dict]":
    """Deterministic count-invariant conjectures from the evidence alone.

    For every color present in the non-env transitions: emit a `non_increasing`
    conjecture if its count only ever drops (monotone with >=1 decrease), or a
    `constant` conjecture if it never moves. A color that ever refills is
    skipped. Monotone conjectures are ordered before conserved ones so the
    blueprint's ## Target is the meaningful (depleting) law, not a wall color.
    """
    rows = list(log)
    if not rows:
        return []
    env = _env_frames(log)
    colors: set = set()
    per_tr: "list[tuple[Counter, Counter]]" = []
    for i, tr in enumerate(rows):
        if i in env:
            continue
        cs, cn = _counts(tr.s), _counts(tr.s_next)
        colors |= set(cs) | set(cn)
        per_tr.append((cs, cn))
    if not per_tr:
        return []

    monotone, constant = [], []
    for c in sorted(colors):
        deltas = [cn[c] - cs[c] for cs, cn in per_tr]
        if all(d == 0 for d in deltas):
            constant.append(c)
        elif all(d <= 0 for d in deltas):
            monotone.append(c)          # non-increasing with >=1 strict drop

    out: "list[dict]" = []
    for c in monotone:
        out.append({
            "name": f"count{c}_monotone",
            "statement": (f"theorem count{c}_monotone (g : Grid) (a t : Nat) : "
                          f"countColor (specStep g a t) {c} ≤ countColor g {c} := by sorry"),
            "quantity": ["count", c], "relation": "non_increasing"})
    for c in constant:
        out.append({
            "name": f"count{c}_conserved",
            "statement": (f"theorem count{c}_conserved (g : Grid) (a t : Nat) : "
                          f"countColor (specStep g a t) {c} = countColor g {c} := by sorry"),
            "quantity": ["count", c], "relation": "constant"})
    return out


def blueprint_from_spec(spec, log, roles) -> str:
    """## Theory = spec_lean's full spec emission; ## Target = the first
    conjecture (campaign contract is one target). Remaining conjectures ride
    along as Lean comments — context for the solver, not extra targets."""
    from ztare.worldmodel.spec_lean import _PRELUDE, spec_to_lean_step

    theory = f"{_PRELUDE}\n{spec_to_lean_step(spec)}"
    conj = conjecture_invariants(log, spec, roles)
    if conj:
        target = conj[0]["statement"]
        extras = [f"-- {c['statement']}" for c in conj[1:]]
    else:
        target = "-- no deterministic invariant conjecture from the evidence"
        extras = []

    parts = ["# GP-250 worldmodel auto blueprint (deterministic conjecture)",
             "", "## Domain", "", "worldmodel-invariant",
             "", "## Theory", "", "```lean", theory, "```",
             "", "## Target", "", "```lean", target]
    if extras:
        parts += ["", "-- further conjectures (context for the solver):"] + extras
    parts += ["```", ""]
    return "\n".join(parts)


def write_blueprint(project, spec, log, roles) -> Path:
    """Write <project>/workspace/worldmodel_auto_blueprint.md; idempotent
    (content-equal == sha-equal, so re-emit is a no-op)."""
    out = Path(project) / "workspace" / "worldmodel_auto_blueprint.md"
    content = blueprint_from_spec(spec, log, roles)
    if out.exists() and out.read_text() == content:
        return out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(content)
    return out


def _proofs_dir() -> Path:
    return Path(__file__).resolve().parents[3] / "ztare_proofs"


def _run_proof_audit(lean_file_path: Path, theorem_name: str) -> dict:
    """Run the canonical L1/L2/L3 audit and return its content-bound receipt."""

    proofs = _proofs_dir()
    if not proofs.exists():
        return {}
    repo = Path(__file__).resolve().parents[3]
    with tempfile.TemporaryDirectory(prefix="worldmodel_lean_audit_") as td:
        receipt_path = Path(td) / "proof_audit.json"
        markdown_path = Path(td) / "proof_audit.md"
        proc = subprocess.run(
            [
                sys.executable,
                "-m",
                "src.ztare.cli",
                "leanmill",
                "proof-audit",
                "--target",
                str(lean_file_path.resolve()),
                "--target-name",
                theorem_name,
                "--lean-root",
                str(proofs.resolve()),
                "--out",
                str(receipt_path),
                "--md",
                str(markdown_path),
            ],
            cwd=str(repo),
            capture_output=True,
            text=True,
            timeout=600,
        )
        if proc.returncode != 0 or not receipt_path.exists():
            return {}
        try:
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        return receipt if isinstance(receipt, dict) else {}


def _proof_audit_passes(receipt: dict, lean_file_path: Path, theorem_name: str) -> bool:
    """Accept only a byte-matched, clean canonical audit for this declaration."""

    try:
        source = lean_file_path.read_text(encoding="utf-8")
        artifact_sha256 = hashlib.sha256(source.encode("utf-8")).hexdigest()
        target_matches = Path(str(receipt.get("target") or "")).resolve() == lean_file_path.resolve()
    except OSError:
        return False
    compile_receipt = receipt.get("compile") if isinstance(receipt.get("compile"), dict) else {}
    axiom_policy = (
        receipt.get("kernel_axiom_policy")
        if isinstance(receipt.get("kernel_axiom_policy"), dict)
        else {}
    )
    l3 = receipt.get("l3_audit") if isinstance(receipt.get("l3_audit"), dict) else {}
    static = receipt.get("static") if isinstance(receipt.get("static"), dict) else {}
    audited_names = {
        str(row.get("name") or "")
        for row in l3.get("rows") or []
        if isinstance(row, dict)
    }
    clean_source = re.sub(r"/-[\s\S]*?-/|--[^\n]*", "", source)
    local_static_clean = not re.search(r"\b(sorry|admit)\b|^\s*axiom\s+", clean_source, re.MULTILINE)
    return bool(
        receipt.get("schema") == "leanmill-pr-a1-compile-l3-audit-v1"
        and receipt.get("status") == "compile_pass_l3_advisory_pass"
        and target_matches
        and receipt.get("target_sha256") == artifact_sha256
        and receipt.get("top_level_target_resolved") == theorem_name
        and theorem_name in audited_names
        and receipt.get("static_clean") is True
        and all(int(static.get(key) or 0) == 0 for key in ("sorry_count", "admit_count", "axiom_decl_count"))
        and local_static_clean
        and compile_receipt.get("ok") is True
        and axiom_policy.get("allowlist_ok") is True
        and not axiom_policy.get("disallowed_axioms")
        and l3.get("status") == "pass"
        and not l3.get("confirmed_blockers")
        and not l3.get("review_flags")
    )


def absorb_ratification(project, lean_file_path, statements) -> list:
    """Persist only invariants that pass the canonical content-bound proof audit."""
    lean_file_path = Path(lean_file_path)
    try:
        audited_source = lean_file_path.read_text(encoding="utf-8")
    except OSError:
        return []
    requested_names: list[str] = []
    for stmt in statements:
        match = re.search(r"\btheorem\s+([A-Za-z0-9_'.]+)", str(stmt))
        if match:
            requested_names.append(match.group(1))
    theorem_statements: list[tuple[str, str]] = []
    for theorem_name in dict.fromkeys(requested_names):
        extracted = extract_theorem_statements(audited_source, [theorem_name])
        if extracted:
            theorem_statements.append((theorem_name, extracted[0]))
    if not theorem_statements:
        return []

    audit_by_theorem: dict[str, dict] = {}
    for theorem_name, _stmt in theorem_statements:
        receipt = _run_proof_audit(lean_file_path, theorem_name)
        if not _proof_audit_passes(receipt, lean_file_path, theorem_name):
            continue
        audit_by_theorem[theorem_name] = receipt
    if not audit_by_theorem:
        return []

    out_path = Path(project) / "workspace" / "invariant_certificates.jsonl"
    seen: set = set()
    if out_path.exists():
        for line in out_path.read_text().splitlines():
            try:
                d = json.loads(line)
                seen.add((tuple(d["quantity"]), d["relation"], d.get("theorem", "")))
            except Exception:  # noqa: BLE001
                continue

    written, lines = [], []
    artifact_sha256 = hashlib.sha256(lean_file_path.read_bytes()).hexdigest()
    for theorem_name, stmt in theorem_statements:
        receipt = audit_by_theorem.get(theorem_name)
        if receipt is None:
            continue
        m = re.search(r"theorem\s+([A-Za-z0-9_'.]+)", stmt)
        cert = invariant_from_theorem(stmt, status="kernel_ratified",
                                      theorem=m.group(1) if m else "")
        if cert is None:
            continue
        key = (tuple(cert.quantity), cert.relation, cert.theorem)
        if key in seen:
            continue
        seen.add(key)
        written.append(cert)
        receipt_sha256 = hashlib.sha256(
            json.dumps(receipt, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        lines.append(json.dumps({
            "quantity": list(cert.quantity),
            "relation": cert.relation,
            "status": cert.status,
            "theorem": cert.theorem,
            "artifact_sha256": artifact_sha256,
            "proof_audit_sha256": receipt_sha256,
        }))
    if lines:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with out_path.open("a") as f:
            f.write("\n".join(lines) + "\n")
    return written


def extract_theorem_statements(source: str, theorem_names: "list[str]") -> "list[str]":
    """Extract theorem headers for the deterministic proof->cert bridge.

    The certificate parser needs the theorem statement, not the proof body.
    We therefore stop at the first top-level-looking `:=` after the named
    theorem and append a dummy `by sorry` body for the downstream regex. The
    Lean file itself is still compiled by `absorb_ratification`; this helper
    only identifies which proven declarations should become certificates.
    """
    out: "list[str]" = []
    for name in theorem_names:
        pat = re.compile(rf"(?ms)\btheorem\s+{re.escape(name)}\b.*?(?=:=)")
        m = pat.search(source)
        if m:
            out.append(m.group(0).strip() + " := by sorry")
    return out


def main(argv: "list[str] | None" = None) -> int:
    ap = argparse.ArgumentParser(description="Worldmodel LeanMill feedback edge.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    pa = sub.add_parser("absorb", help="compile a Lean proof artifact and persist invariant certificates")
    pa.add_argument("--project", required=True, help="project root containing workspace/")
    pa.add_argument("--lean-file", required=True, help="Lean file to compile")
    pa.add_argument("--theorem", action="append", default=[],
                    help="theorem name to extract from --lean-file; repeatable")
    pa.add_argument("--statement", action="append", default=[],
                    help="raw theorem statement to certify after compile; repeatable")
    args = ap.parse_args(argv)

    if args.cmd == "absorb":
        lean_path = Path(args.lean_file).resolve()
        statements = list(args.statement)
        if args.theorem:
            statements.extend(extract_theorem_statements(
                lean_path.read_text(encoding="utf-8"), args.theorem))
        certs = absorb_ratification(Path(args.project), lean_path, statements)
        print(json.dumps({
            "schema": "ztare-worldmodel-invariant-absorb-v1",
            "status": "absorbed" if certs else "no_certificates_written",
            "certificates": [
                {"quantity": list(c.quantity), "relation": c.relation,
                 "status": c.status, "theorem": c.theorem}
                for c in certs
            ],
        }, sort_keys=True))
        return 0
    return 2


def record_refutation(project, theorem_name, note) -> Path:
    """A disproved conjecture. Kept in a SEPARATE invariant_dispositions.jsonl,
    never the certs stream: the only current file consumer (ProvenInvariants)
    tolerates non-cert lines via a broad except, but the task-named
    arc3_play_loop._invariants consumer does not exist yet to verify, so the
    certs file stays pure-certificate by construction."""
    path = Path(project) / "workspace" / "invariant_dispositions.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as f:
        f.write(json.dumps({"disposition": "refuted", "theorem": theorem_name,
                            "note": note}) + "\n")
    return path


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
