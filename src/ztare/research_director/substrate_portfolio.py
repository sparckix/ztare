"""Substrate-portfolio runner — sequential dispatch from a YAML registry.

Spec: research_areas/private/specs/active/engine/substrate_portfolio_spec.md
Seam: research_areas/private/seams/reflexive/GP-228_substrate_portfolio_v05_v3_seam.md
Parent: GP-213 (director-mechanization)

Reads the substrate portfolio registry at `org/runtime/substrate_portfolio.yaml`
and runs members SEQUENTIALLY (not parallel — sequence is consequential
for cross-substrate exclusion ledger §25 in rubric_specification.md).

Replaces a one-shot script that hardcoded the portfolio in Python. Adding
a substrate is now a YAML edit; this module always runs whatever the
registry currently lists.

Operator-confirmed only in v0 — `--unattended` requires the role's
mandate to authorize portfolio dispatch (see GP-128 agent_daemon.py).

Modes:
  list           — print the registry; do nothing
  scaffold       — for any registry member with `scaffolded: false`,
                   create a charter stub + raw/ dir; operator must
                   author rubric before that member can run
  run            — run all (or one) registry member sequentially via
                   `make loop`

CLI:
    python -m src.ztare.research_director.substrate_portfolio --list
    python -m src.ztare.research_director.substrate_portfolio --scaffold
    python -m src.ztare.research_director.substrate_portfolio --run --iters 5
    python -m src.ztare.research_director.substrate_portfolio --run --only v3 --iters 10
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
REGISTRY_PATH = REPO_ROOT / "org" / "runtime" / "substrate_portfolio.yaml"


def load_registry(path: Path = REGISTRY_PATH) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(
            f"substrate portfolio registry not found at {path} — "
            f"see substrate_portfolio_spec.md for schema"
        )
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    members = data.get("members") or []
    if not isinstance(members, list):
        raise ValueError(f"registry 'members' must be a list, got {type(members).__name__}")
    return members


def _scaffold_member(slug: str, eigenquestion: str, mechanism_family: str) -> bool:
    """Create minimal charter + raw/ dir for a registry member.

    Returns True if scaffolded fresh, False if already present.
    """
    project_dir = REPO_ROOT / "projects" / slug
    if (project_dir / "project_charter.md").exists():
        return False
    project_dir.mkdir(parents=True, exist_ok=True)
    (project_dir / "raw").mkdir(exist_ok=True)
    charter = (
        f"# Project Charter — {slug} (DRAFT, operator review required)\n\n"
        f"## Eigenquestion\n\n{eigenquestion}\n\n"
        f"## Primary mechanism family\n\nThis substrate steers toward "
        f"`{mechanism_family}` proposals; the rubric persona weights this "
        f"family higher than alternatives.\n\n"
        f"## Status\n\nSCAFFOLDED — operator must:\n"
        f"  1. Customize this charter\n"
        f"  2. Author the rubric at `rubrics/{slug}.json` (use any v0.5 sibling as template)\n"
        f"  3. Author `bash projects/{slug}/refresh_evidence.sh` (copy from a sibling)\n"
        f"  4. Run `make loop PROJECT={slug} ...`\n\n"
        f"## See also\n\n"
        f"  - `org/runtime/substrate_portfolio.yaml` — registry entry\n"
        f"  - `rubrics/ztare_on_ztare_v2_expanded_scope.json` — anti-anchoring template\n"
        f"  - `docs/concepts/rubric_specification.md` §§22-27 — discipline stack\n"
    )
    (project_dir / "project_charter.md").write_text(charter, encoding="utf-8")
    return True


def _run_member(slug: str, iters: int, mutator: str, judge: str) -> int:
    """Invoke `make loop` for one registry member. Returns subprocess returncode."""
    rubric_path = REPO_ROOT / "rubrics" / f"{slug}.json"
    if not rubric_path.exists():
        print(f"  ✗ rubric missing: {rubric_path} — operator must author before run")
        return 2
    cmd = [
        "make", "loop",
        f"PROJECT={slug}",
        f"RUBRIC={slug}",
        f"ITERS={iters}",
        f"MUTATOR_MODEL={mutator}",
        f"JUDGE_MODEL={judge}",
        "DYNAMIC=1",
        f"PYTHON={REPO_ROOT}/venv/bin/python",
    ]
    print(f"  running: {' '.join(cmd)}")
    return subprocess.run(cmd, cwd=str(REPO_ROOT), check=False).returncode


def cmd_list(_args: argparse.Namespace) -> int:
    members = load_registry()
    print(f"=== substrate portfolio registry ({REGISTRY_PATH.relative_to(REPO_ROOT)}) ===")
    for i, m in enumerate(members, 1):
        scaffold_marker = "✓" if m.get("scaffolded") else "✗ NEEDS-SCAFFOLD"
        print(f"\n  [{i}] {m['slug']}  [{scaffold_marker}]")
        print(f"      eigenquestion: {m.get('eigenquestion_summary', '(unset)')}")
        print(f"      mechanism family: {m.get('primary_mechanism_family', '(unset)')}")
        print(f"      opened: {m.get('opened_date', '?')} by {m.get('opened_by', '?')}")
    return 0


def cmd_scaffold(_args: argparse.Namespace) -> int:
    members = load_registry()
    new_count = 0
    for m in members:
        if m.get("scaffolded"):
            continue
        scaffolded = _scaffold_member(
            m["slug"],
            m.get("eigenquestion_summary", ""),
            m.get("primary_mechanism_family", ""),
        )
        if scaffolded:
            new_count += 1
            print(f"  ✓ scaffolded {m['slug']}")
    print(f"\n{new_count} new charter stub(s) created.")
    if new_count:
        print("Next: review each charter + author rubric + run `bash projects/<slug>/refresh_evidence.sh`")
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    members = load_registry()
    targets = members
    if args.only:
        targets = [m for m in members if args.only in m["slug"]]
        if not targets:
            print(f"no portfolio member matched --only={args.only}")
            return 2
    print(f"=== substrate portfolio: running {len(targets)} member(s) sequentially ===")
    results: list[tuple[str, str]] = []
    for m in targets:
        slug = m["slug"]
        print(f"\n--- {slug} ---")
        rc = _run_member(slug, args.iters, args.mutator, args.judge)
        results.append((slug, "ok" if rc == 0 else f"rc={rc}"))
    print("\n=== portfolio run summary ===")
    for slug, status in results:
        print(f"  {status:>8}  {slug}")
    return 0 if all(s == "ok" for _, s in results) else 1


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="substrate_portfolio",
        description="sequential portfolio runner reading org/runtime/substrate_portfolio.yaml",
    )
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("list", help="print the registry").set_defaults(func=cmd_list)
    sub.add_parser("scaffold", help="create charter stubs for non-scaffolded members").set_defaults(func=cmd_scaffold)

    run_p = sub.add_parser("run", help="run portfolio members sequentially via `make loop`")
    run_p.add_argument("--iters", type=int, default=5)
    run_p.add_argument("--mutator", default="gpt4.1")
    run_p.add_argument("--judge", default="gpt4.1")
    run_p.add_argument("--only", help="run only members whose slug contains this substring")
    run_p.set_defaults(func=cmd_run)

    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
