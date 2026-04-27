#!/usr/bin/env python3
"""GP-135 Meta-Law Hypothesis family program — substrate builder.

Scaffolds the six-substrate MLH family per the protocol in
`docs/concepts/mlh_family_protocol.md`. Five open substrates (F1..F5) for
the mutator to train its invariant hypothesis against, plus one sealed
holdout (F6). The mutator must pre-register a cross-substrate invariant
claim and a prediction for F6 BEFORE F6's evidence is revealed. Scoring
of F6 is what crosses the Newton gate (family-level generative yield),
not recovery on any individual substrate.

What this script does:

1. For each of F1..F6, call `generate_substrate` with an opaque slug
   (mlh_fN) pointing at the corresponding GT module under
   `src/ztare/substrates/mlh_fN_gt.py`. All GT modules MUST exist before
   this runs (`scripts/build_mlh_family.py` does not know the GT formula;
   only the GT module does — Division A boundary preserved).

2. Seal F6: compute evidence hash, write
   `projects/mlh_f6/sealed_holdout.json` with the hash, MOVE the raw
   evidence aside to `projects/mlh_f6/_holdout_locked/evidence.txt` so
   the apparatus does not expose it to any live mutator run. The mutator
   never receives F6 evidence in any prompt until the principal unlocks
   it post-prediction.

3. Author (but do not run) a shared MLH rubric scaffold that points all
   five open substrates at the same pre-registration fields. Each
   substrate's live rubric is a thin wrapper that sets `rubric_mode:
   newton` and injects the MLH cross-substrate prediction dimension on
   top of the common template.

4. Emit a summary manifest at `research_areas/private/mlh_family_manifest.json`
   recording slugs, GT module paths, evidence counts, and the sealed F6
   hash. This manifest IS the commitment the protocol refers to.

NOTE on the Division A/B boundary: this script intentionally does not
import any GT module or reference any specific arithmetic function. It
orchestrates the scaffold-and-seal workflow only. The substrate
generator calls each GT module directly and writes evidence under the
normal Division A path.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PROJECTS = REPO / "projects"
RUBRICS = REPO / "rubrics"
SUBSTRATES_DIR = REPO / "src" / "ztare" / "substrates"

OPEN_SLUGS = ("mlh_f1", "mlh_f2", "mlh_f3", "mlh_f4", "mlh_f5")
HOLDOUT_SLUG = "mlh_f6"
ALL_SLUGS = OPEN_SLUGS + (HOLDOUT_SLUG,)

# Shared problem brief — identical across F1..F6, so the charter does not
# leak any per-substrate information. The mutator cannot tell from the
# charter alone which of F1..F5 is which class; that must come (if at
# all) from cross-substrate comparison of the evidence, which is exactly
# the discipline the MLH protocol is trying to enforce.
SHARED_PROBLEM_BRIEF = (
    "An integer-valued function f(n) defined on positive integers. "
    "Evidence is given as raw (n, z) pairs. No domain labels. "
    "Derive the structural law."
)

SHARED_DENYLIST = [
    # Identifiers for the six OEIS targets; any of these appearing in the
    # mutator-visible artifacts is a leak.
    "A001414", "sopfr",
    "A008472",
    "A001222", "big omega", "bigomega",
    "A001221", "little omega",
    "A000005", "tau function", "d(n)", "number of divisors",
    "A000203", "sigma function", "sum of divisors",
    # Common paraphrases across the family
    "prime factorization",
    "sum of prime factors",
    "count of prime factors",
    "divisor sum",
]

# Visible range: n = 2..80 (79 points). Holdout: n = 81..120 (40 points).
# Same ranges for all six substrates so there is no per-substrate signal
# in the evidence-window boundaries.
VISIBLE_LO, VISIBLE_HI = 2, 80
HOLDOUT_LO, HOLDOUT_HI = 81, 120


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _run_generate(slug: str, gt_script: str) -> dict:
    """Call generate_substrate with --gt-script for this slug."""
    cmd = [
        sys.executable,
        "-m",
        "src.ztare.scaffold.generate_substrate",
        "--slug", slug,
        "--gt-script", gt_script,
        "--variables", "n",
        "--visible-ranges", f"n:{VISIBLE_LO}:{VISIBLE_HI}",
        "--holdout-ranges", f"n:{HOLDOUT_LO}:{HOLDOUT_HI}",
        "--problem-brief", SHARED_PROBLEM_BRIEF,
        "--denylist", ",".join(SHARED_DENYLIST),
    ]
    result = subprocess.run(
        cmd,
        cwd=str(REPO),
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"generate_substrate failed for {slug}:\n{result.stderr}", file=sys.stderr)
        raise SystemExit(result.returncode)
    return {
        "slug": slug,
        "gt_script": gt_script,
        "stdout": result.stdout.strip().splitlines()[-5:],
    }


def _seal_holdout(slug: str) -> dict:
    """Move F6's evidence aside and emit a sealed hash manifest.

    The live project directory is left with:
      - evidence.txt → 2-row placeholder pointing to `sealed_holdout.json`
      - evidence_holdout.txt → same
      - sealed_holdout.json → {hash, n_points, created_at, seal_source}

    The raw evidence is moved to `_holdout_locked/` which is git-
    tracked but never read by the apparatus. Unlocking is manual.
    """
    proj = PROJECTS / slug
    locked_dir = proj / "_holdout_locked"
    locked_dir.mkdir(exist_ok=True)

    sealed = {}
    for name in ("evidence.txt", "evidence_holdout.txt"):
        src = proj / name
        if not src.exists():
            continue
        dst = locked_dir / name
        content_hash = _sha256(src)
        n_points = sum(
            1 for line in src.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.strip().startswith("#")
        )
        shutil.copy(src, dst)
        # Replace the live file with a locked placeholder.
        placeholder = (
            f"# SEALED HOLDOUT — {name}\n"
            f"# This substrate is part of the MLH family program (GP-135).\n"
            f"# Its evidence is sealed until the mutator has committed a\n"
            f"# cross-substrate invariant prediction. Do not replace this\n"
            f"# placeholder manually; run scripts/unlock_mlh_holdout.py\n"
            f"# only after prediction is sealed.\n"
            f"# Sealed SHA-256: {content_hash}\n"
            f"# n_points: {n_points}\n"
            f"# Raw evidence location: _holdout_locked/{name}\n"
        )
        src.write_text(placeholder, encoding="utf-8")
        sealed[name] = {"sha256": content_hash, "n_points": n_points}

    seal_manifest = proj / "sealed_holdout.json"
    seal_manifest.write_text(
        json.dumps(sealed, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return sealed


def _emit_family_manifest(results: list[dict], seal: dict) -> Path:
    """Write the top-level family manifest."""
    manifest_path = REPO / "research_areas" / "private" / "mlh_family_manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest = {
        "program": "GP-135 Meta-Law Hypothesis Family",
        "open_substrates": list(OPEN_SLUGS),
        "holdout_substrate": HOLDOUT_SLUG,
        "visible_range": [VISIBLE_LO, VISIBLE_HI],
        "holdout_range": [HOLDOUT_LO, HOLDOUT_HI],
        "sealed_holdout_hash": seal,
        "generated_slugs": [r["slug"] for r in results],
        "protocol_doc": "docs/concepts/mlh_family_protocol.md",
        "seam": (
            "research_areas/private/seams/mission/"
            "GP-135_meta_law_hypothesis_family_program_seam.md"
        ),
    }
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return manifest_path


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument(
        "--skip-existing", action="store_true",
        help="Skip substrates whose project directory already exists.",
    )
    args = ap.parse_args()

    # Verify all six GT modules exist before we start — fail loudly if not.
    missing = []
    for slug in ALL_SLUGS:
        gt_path = SUBSTRATES_DIR / f"{slug}_gt.py"
        if not gt_path.exists():
            missing.append(str(gt_path))
    if missing:
        print("Missing GT modules; run Division A authoring step first:", file=sys.stderr)
        for p in missing:
            print(f"  {p}", file=sys.stderr)
        sys.exit(2)

    results = []
    for slug in ALL_SLUGS:
        proj_dir = PROJECTS / slug
        if proj_dir.exists() and args.skip_existing:
            print(f"skip: {slug} already exists")
            continue
        if proj_dir.exists():
            print(f"project {slug} already exists; pass --skip-existing or remove it first")
            sys.exit(3)
        gt_script = f"src/ztare/substrates/{slug}_gt.py"
        print(f"\n=== generating {slug} ===")
        results.append(_run_generate(slug, gt_script))

    print(f"\n=== sealing holdout {HOLDOUT_SLUG} ===")
    seal = _seal_holdout(HOLDOUT_SLUG)
    print(f"  sealed hashes: {json.dumps(seal, indent=2)}")

    manifest_path = _emit_family_manifest(results, seal)
    print(f"\n=== family manifest at {manifest_path} ===")
    print(f"\nnext: author `docs/concepts/mlh_family_protocol.md` + shared rubric; "
          f"then open `research_areas/private/seams/mission/"
          f"GP-135_meta_law_hypothesis_family_program_seam.md` "
          f"with the sealed F6 hash committed.")


if __name__ == "__main__":
    main()
