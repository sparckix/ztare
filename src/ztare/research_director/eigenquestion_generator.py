"""Frontier-eigenquestion generator — LLM-drafted advisory eigenquestion.

Spec: maintainer-only eigenquestion generator spec
Seam: maintainer-only substrate portfolio seam
Parent: GP-213 (director-mechanization)

Replaces a fixed substrate eigenquestion with a per-run LLM-generated
one tailored to (a) the most recent mining outputs and (b) the
substrate's prior-run history of explored primitive classes. Designed
to break the family-attractor failure mode that v2's fixed eigenquestion
exhibits (5 runs → 1 primitive family because the eigenquestion always
points the mutator at one framing).

Output is ADVISORY — never auto-modifies the charter. Operator review
gates promotion (`projects/<slug>/proposed_eigenquestion_<ts>.md` is the
output; `project_charter.md` Eigenquestion section is the target).

Pure-Python apparatus + 1 LLM call via `LLMRuntime`. Cost ~$0.005-0.01
per invocation depending on selected model.

CLI:
    python -m src.ztare.research_director.eigenquestion_generator \\
        --project ztare_on_ztare_v2_expanded_scope
    python -m src.ztare.research_director.eigenquestion_generator \\
        --project <slug> --model claude-sonnet-4-6
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]


def _load_jsonl(p: Path) -> list[dict[str, Any]]:
    if not p.exists():
        return []
    out: list[dict[str, Any]] = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except Exception:  # noqa: BLE001
            continue
    return out


def _first_relevant_lines(path: Path, *, max_lines: int = 8, max_chars: int = 900) -> str:
    """Return compact evidence-bearing lines from a project artifact."""
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return ""

    picked: list[str] = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if (
            stripped.startswith("#")
            or stripped.startswith("Status")
            or stripped.startswith("Verdict")
            or stripped.startswith("Decision")
            or stripped.startswith("Current")
            or stripped.startswith("Next")
            or stripped.startswith(">")
            or stripped.startswith("- ")
        ):
            picked.append(stripped)
        if len(picked) >= max_lines:
            break

    if not picked:
        picked = [line.strip() for line in lines if line.strip()][:max_lines]
    text = " / ".join(picked)
    return text[:max_chars]


def _summarize_file_set(paths: list[Path], *, base: Path, limit: int = 24) -> str:
    rows: list[str] = []
    for path in paths[:limit]:
        rel = path.relative_to(base)
        suffix = ""
        if path.suffix.lower() == ".md":
            excerpt = _first_relevant_lines(path)
            if excerpt:
                suffix = f" — {excerpt}"
        rows.append(f"  - {rel} ({path.stat().st_size // 1024}KB){suffix}")
    return "\n".join(rows) if rows else "  - (none)"


def _summarize_available_evidence(project_dir: Path) -> str:
    """Summarize evidence where real substrates keep it, not only raw/ snapshots."""
    parts: list[str] = []

    top_level = [
        p for p in [project_dir / "thesis.md", project_dir / "memory.md", project_dir / "current_iteration.md"]
        if p.exists()
    ]
    if top_level:
        parts.append("TOP-LEVEL PROJECT STATE:\n" + _summarize_file_set(top_level, base=project_dir))

    raw_dir = project_dir / "raw"
    raw_files = []
    if raw_dir.exists():
        raw_files = sorted(raw_dir.glob("*.json")) + sorted(raw_dir.glob("*.md"))
    parts.append("RAW SNAPSHOTS:\n" + _summarize_file_set(raw_files, base=project_dir, limit=16))

    workspace_dir = project_dir / "workspace"
    workspace_files: list[Path] = []
    if workspace_dir.exists():
        md_files = sorted(workspace_dir.glob("*.md"), key=lambda p: (p.stat().st_mtime, p.name), reverse=True)
        json_files = sorted(workspace_dir.glob("*.json"), key=lambda p: (p.stat().st_mtime, p.name), reverse=True)
        csv_files = sorted(workspace_dir.glob("*.csv"), key=lambda p: (p.stat().st_mtime, p.name), reverse=True)
        workspace_files = md_files[:18] + json_files[:4] + csv_files[:4]
    parts.append("WORKSPACE EVIDENCE ARTIFACTS:\n" + _summarize_file_set(workspace_files, base=project_dir, limit=26))

    return "\n\n".join(parts)


def _summarize_explored_classes(explored: list[dict[str, Any]]) -> str:
    """Summarize explored primitive classes for the mutator-prompt context.

    GP-233 / §14 (negative-evidence backpressure, ideas_felices.md): rows
    whose ``outcome`` field starts with ``FALSIFIED_`` are split into a
    separate "DO NOT PROPOSE NEAR-NEIGHBORS" block, with their evidence
    path quoted. This converts the previously-decorative ``outcome``
    field into consequential prompt context. The mutator may still
    propose in the falsified neighborhood, but must do so by *explicitly
    citing divergence* from the named verification finding.
    """
    if not explored:
        return "(no primitive classes explored yet — first run, full ceiling)"

    # Roll up per-class summaries, carrying the worst-known outcome and
    # any evidence_path so the prompt can quote it.
    by_class: dict[str, dict[str, Any]] = {}
    for e in explored:
        cls = str(e.get("class_name") or "unknown")
        info = by_class.setdefault(cls, {
            "count": 0,
            "best_score": 0,
            "first_seen_run": e.get("run_id"),
            "outcome": "",
            "evidence_path": "",
        })
        info["count"] += 1
        s = e.get("score") or 0
        if s > info["best_score"]:
            info["best_score"] = s
        # Last-seen outcome / evidence_path wins (rows are append-only;
        # the latest tells us the current status of the premise).
        if e.get("outcome"):
            info["outcome"] = str(e["outcome"])
        if e.get("evidence_path"):
            info["evidence_path"] = str(e["evidence_path"])

    explored_lines: list[str] = []
    falsified_lines: list[str] = []
    for cls, info in sorted(by_class.items(), key=lambda kv: -kv[1]["best_score"]):
        outcome = info["outcome"]
        base = (
            f"  - {cls!r}: proposed {info['count']}× across runs "
            f"(best score {info['best_score']}, first seen run {info['first_seen_run']})"
        )
        if outcome.upper().startswith("FALSIFIED"):
            evidence = info["evidence_path"] or "(no evidence_path; treat as soft signal)"
            falsified_lines.append(
                f"{base}\n      outcome: {outcome}\n      evidence: {evidence}"
            )
        else:
            if outcome:
                base += f" [outcome: {outcome}]"
            explored_lines.append(base)

    parts: list[str] = []
    if explored_lines:
        parts.append("EXPLORED CLASSES (history; rank by best score):\n" + "\n".join(explored_lines))
    if falsified_lines:
        parts.append(
            "FALSIFIED PREMISES — DO NOT PROPOSE NEAR-NEIGHBORS UNLESS EXPLICITLY CITING DIVERGENCE:\n"
            + "\n".join(falsified_lines)
        )
    return "\n\n".join(parts) if parts else "(no explored classes after filtering)"


def validate_explored_classes(explored: list[dict[str, Any]]) -> list[str]:
    """GP-233 / §14 caveat: any row whose ``outcome`` declares a
    falsification must carry an ``evidence_path`` pointing at an existing
    file on disk. Insincere or evidence-less falsifications would feed
    garbage into the FALSIFIED block above. Returns a list of validation
    errors (empty list = valid)."""
    errors: list[str] = []
    for i, e in enumerate(explored):
        outcome = str(e.get("outcome") or "")
        if not outcome.upper().startswith("FALSIFIED"):
            continue
        ev = e.get("evidence_path")
        if not ev:
            errors.append(
                f"row {i} ({e.get('class_name', '?')}): outcome={outcome!r} "
                "but no evidence_path field"
            )
            continue
        ev_abs = REPO_ROOT / ev if not Path(ev).is_absolute() else Path(ev)
        if not ev_abs.exists():
            errors.append(
                f"row {i} ({e.get('class_name', '?')}): outcome={outcome!r} "
                f"but evidence_path {ev!r} does not exist on disk"
            )
    return errors


def _extract_current_eigenquestion(charter_path: Path) -> str:
    if not charter_path.exists():
        return "(no charter)"
    text = charter_path.read_text(encoding="utf-8")
    m = re.search(
        r"^##\s*Eigenquestion\s*\n+(.*?)(?:\n##\s|\n---|\Z)",
        text, re.DOTALL | re.MULTILINE,
    )
    return m.group(1).strip() if m else "(charter exists but Eigenquestion section not found)"


def _build_prompt(slug: str, current_eq: str, evidence_summary: str, explored_summary: str) -> str:
    return f"""You are generating a fresh EIGENQUESTION for a research-apparatus
substrate that has been running for several iterations and is showing
diminishing diversity in its primitive proposals (mutator anchors on
the same family of refinements across runs).

The substrate's job is to ingest the apparatus's mining outputs and
propose typed refinements. Your job is to generate ONE NEW eigenquestion
the substrate's mutator should consider for its next run, structurally
ORTHOGONAL to what has been explored, but still anchored to the
apparatus's evidence.

---

PROJECT: {slug}

CURRENT EIGENQUESTION (used for prior runs):
{current_eq[:1500]}

PRIMITIVE CLASSES ALREADY EXPLORED ACROSS PRIOR RUNS:
{explored_summary}

(If a FALSIFIED PREMISES block appears above, those premises were
empirically tested and refuted. A new eigenquestion may still touch
that neighborhood, but only by EXPLICITLY citing the named evidence
path and stating how its candidate mechanism diverges from the refuted
premise. Re-proposing a refuted premise without divergence-citation is
a hard violation of the anti-rehash discipline.)

AVAILABLE PROJECT EVIDENCE:
{evidence_summary}

---

GENERATE A FRESH EIGENQUESTION that:

  1. Is STRUCTURALLY ORTHOGONAL to the explored primitive classes —
     don't just rephrase a question that would land in the same family.
     If the explored classes are about "trust/redundancy/attestation",
     the new eigenquestion should NOT pull the mutator into that family.

  2. Is ANCHORED to specific project evidence sources — name 1-2 of the
     files above whose evidence is decisive for this eigenquestion.
     Do not invent files, schemas, or JSONPaths that are not listed.

  3. Has a CLEAR CANDIDATE FORM — what kind of refinement would answer
     this eigenquestion (retire / wire-loop / promote-primitive /
     new-substrate / propose-new-primitive-class / etc.)

  4. Is FALSIFIABLE — the next run's mining outputs should produce
     evidence that would either confirm or refute proposals made
     under this eigenquestion.

  5. Is NEWTON-mode — names a SECONDARY OBSERVABLE that follows from
     the candidate's mechanism (not just the primary apparatus-output
     metric).

OUTPUT FORMAT (markdown, ≤600 words):

## Proposed Eigenquestion (orthogonal to explored)

**Eigenquestion:** [one paragraph, the question itself]

**Why this is orthogonal:** [name the explored families and explain
how this question pulls the mutator into a structurally different
basin]

**Anchored evidence:** [1-2 named files above + exact section names or
JSONPath fragments only when those paths are known from the listed evidence]

**Expected candidate form:** [which mechanism types are admissible,
which are forbidden]

**Newton-mode secondary observable:** [what NEW measurable thing a
candidate's mechanism would predict beyond the primary effect]

**Falsifier:** [what next-run project evidence would refute candidates
made under this eigenquestion]

Output ONLY the markdown. No preamble, no explanation outside the format.
"""


def generate_eigenquestion(project_slug: str, model_id: str | None = None,
                           out_path: Path | None = None) -> Path:
    """Programmatic API. Returns path to written advisory file.

    Raises FileNotFoundError if project dir missing, RuntimeError on LLM failure.
    """
    project_dir = REPO_ROOT / "projects" / project_slug
    if not project_dir.exists():
        raise FileNotFoundError(f"project dir not found at {project_dir}")

    evidence_summary = _summarize_available_evidence(project_dir)
    explored = _load_jsonl(project_dir / "workspace" / "explored_primitive_classes.jsonl")
    explored_summary = _summarize_explored_classes(explored)
    current_eq = _extract_current_eigenquestion(project_dir / "project_charter.md")
    prompt = _build_prompt(project_slug, current_eq, evidence_summary, explored_summary)

    from ztare.common.llm_runtime import LLMRuntime, pick_default_model_id_for_scripts
    chosen_model = model_id or pick_default_model_id_for_scripts()
    if chosen_model is None:
        raise RuntimeError(
            "no LLM provider — set ANTHROPIC_API_KEY / OPENAI_API_KEY / GEMINI_API_KEY"
    )
    runtime = LLMRuntime()
    from ztare.common.dispatch_model import dispatch_call_text

    resp = dispatch_call_text(
        "eigenquestion_generator",
        prompt,
        llm_response_call=lambda p: runtime.call_text(
            p, model_id=chosen_model, max_tokens=2000,
            request_label="frontier_eigenquestion_generator",
        ),
        repo=project_dir,
        timeout_seconds=300,
    )
    text = (resp.text or "").strip()
    if not text:
        raise RuntimeError("empty response from LLM")

    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    target = out_path or (project_dir / f"proposed_eigenquestion_{ts}.md")
    header = (
        f"# Proposed Eigenquestion — {project_slug}\n\n"
        f"_Generated {datetime.now(timezone.utc).isoformat()}_  \n"
        f"_Model:_ `{chosen_model}`  \n"
        f"_Method:_ `src.ztare.research_director.eigenquestion_generator`\n\n"
        f"This is an ADVISORY proposal. Operator must review + manually merge\n"
        f"into `project_charter.md` (Eigenquestion section) before the next\n"
        f"substrate run.\n\n"
        f"---\n\n"
    )
    target.write_text(header + text + "\n", encoding="utf-8")
    return target


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="eigenquestion_generator",
        description="frontier-eigenquestion generator (advisory, operator-confirmed)",
    )
    ap.add_argument("--project", required=True)
    ap.add_argument("--model", default=None,
                    help="Model id; default uses pick_default_model_id_for_scripts()")
    ap.add_argument("--out", type=Path, default=None,
                    help="Output path; default proposed_eigenquestion_<ts>.md in project dir")
    ap.add_argument("--validate-explored", action="store_true",
                    help="GP-233/§14: lint workspace/explored_primitive_classes.jsonl "
                         "for falsified rows missing evidence_path or pointing at "
                         "nonexistent files. Exits non-zero on any violation; does "
                         "not call the LLM.")
    args = ap.parse_args(argv)

    if args.validate_explored:
        project_dir = REPO_ROOT / "projects" / args.project
        if not project_dir.exists():
            print(f"  ERROR: project dir not found at {project_dir}")
            return 2
        explored = _load_jsonl(project_dir / "workspace" / "explored_primitive_classes.jsonl")
        errors = validate_explored_classes(explored)
        if errors:
            print(f"=== {args.project}: explored_primitive_classes.jsonl validation FAILED ===")
            for err in errors:
                print(f"  - {err}")
            return 1
        n_falsified = sum(
            1 for e in explored if str(e.get("outcome") or "").upper().startswith("FALSIFIED")
        )
        print(
            f"=== {args.project}: explored_primitive_classes.jsonl OK "
            f"({len(explored)} rows, {n_falsified} falsified, all with valid evidence) ==="
        )
        return 0

    print(f"=== frontier-eigenquestion generator: {args.project} ===")
    try:
        out_path = generate_eigenquestion(args.project, model_id=args.model, out_path=args.out)
    except (FileNotFoundError, RuntimeError) as exc:
        print(f"  ERROR: {exc}")
        return 2
    print(f"  wrote {out_path}")
    print(f"\n  next: review the proposal, manually update projects/{args.project}/project_charter.md::Eigenquestion if accepted")
    return 0


if __name__ == "__main__":
    sys.exit(main())
