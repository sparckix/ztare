#!/usr/bin/env python3
"""Validate that `papers/` contains only public paper-surface artifacts.

Regular paper directories are intentionally small public mirrors: manuscript
Markdown/TeX/BibTeX/PDF files at the top level, optional `evidence/`, and
optional `figures/`. Build logs, LaTeX intermediates, editor metadata, and
working/submission directories belong in the root-level ignored workspace that
mirrors the paper name, not under `papers/`.
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path


REPO = Path(__file__).resolve().parents[3]
PAPERS = REPO / "papers"

ROOT_ALLOWED_FILES = {"README.md"}
PUBLIC_COLLECTION_DIRS = {"case_studies"}

MANUSCRIPT_EXTS = {".md", ".tex", ".bib", ".pdf"}
COLLECTION_EXTS = {".md", ".py", ".json", ".pdf"}
EVIDENCE_EXTS = {
    ".bib",
    ".csv",
    ".ipynb",
    ".json",
    ".jsonl",
    ".lean",
    ".jpeg",
    ".jpg",
    ".md",
    ".pdf",
    ".png",
    ".py",
    ".svg",
    ".tex",
    ".tsv",
    ".txt",
    ".webp",
}
FIGURE_EXTS = {".jpeg", ".jpg", ".pdf", ".png", ".svg", ".tex", ".webp"}

ALLOWED_PAPER_SUBDIRS = {"evidence", "figures"}
DISALLOWED_NAMES = {".DS_Store", "Thumbs.db"}
DISALLOWED_DIR_NAMES = {
    ".ipynb_checkpoints",
    ".pytest_cache",
    "__pycache__",
    "build",
    "preview",
    "source",
    "SUBMISSION",
    "tmp",
    "working",
}
LATEX_BUILD_SUFFIXES = {
    ".aux",
    ".bbl",
    ".blg",
    ".fdb_latexmk",
    ".fls",
    ".lof",
    ".log",
    ".lot",
    ".out",
    ".synctex.gz",
    ".toc",
}


@dataclass(frozen=True)
class Finding:
    path: str
    reason: str


def rel(path: Path) -> str:
    return str(path.relative_to(REPO))


def has_suffix(path: Path, suffixes: set[str]) -> bool:
    name = path.name
    return any(name.endswith(suffix) for suffix in suffixes)


def classify_file(path: Path) -> str | None:
    """Return an error reason for a file, or None if allowed."""
    if path.name in DISALLOWED_NAMES:
        return "editor/system metadata is not allowed in papers/"
    if has_suffix(path, LATEX_BUILD_SUFFIXES):
        return "LaTeX build artifact belongs in a gitignored working directory"

    parts = path.relative_to(PAPERS).parts
    if len(parts) == 1:
        if path.name not in ROOT_ALLOWED_FILES:
            return "only README.md is allowed directly under papers/"
        return None

    top = parts[0]
    if top in PUBLIC_COLLECTION_DIRS:
        if path.suffix not in COLLECTION_EXTS:
            return f"unsupported file extension in public collection {top}/"
        return None

    if len(parts) == 2:
        if path.suffix not in MANUSCRIPT_EXTS:
            return "paper root files must be .md, .tex, .bib, or .pdf"
        return None

    subdir = parts[1]
    if subdir == "evidence":
        if path.suffix not in EVIDENCE_EXTS:
            return "unsupported evidence artifact extension"
        return None
    if subdir == "figures":
        if path.suffix not in FIGURE_EXTS:
            return "unsupported figure artifact extension"
        return None

    return "paper subdirectories must be evidence/ or figures/"


def validate(root: Path) -> list[Finding]:
    findings: list[Finding] = []
    if not root.exists():
        return [Finding(rel(root), "papers/ directory is missing")]

    for path in sorted(root.rglob("*")):
        if path.is_dir():
            if path.name in DISALLOWED_DIR_NAMES:
                findings.append(Finding(rel(path), "working/build/submission directories are not allowed under papers/"))
                continue
            parts = path.relative_to(root).parts
            if len(parts) >= 2 and parts[0] not in PUBLIC_COLLECTION_DIRS:
                subdir = parts[1]
                if subdir not in ALLOWED_PAPER_SUBDIRS:
                    findings.append(Finding(rel(path), "paper subdirectories must be evidence/ or figures/"))
            continue

        reason = classify_file(path)
        if reason:
            findings.append(Finding(rel(path), reason))

    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="emit JSON instead of human-readable text")
    args = parser.parse_args()

    findings = validate(PAPERS)
    payload = {
        "schema": "papers-public-tree-validation-v1",
        "papers_root": rel(PAPERS),
        "status": "pass" if not findings else "fail",
        "findings": [finding.__dict__ for finding in findings],
    }

    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    elif findings:
        print("papers/ public-tree validation failed:")
        for finding in findings:
            print(f"- {finding.path}: {finding.reason}")
    else:
        print("papers/ public-tree validation passed")

    return 0 if not findings else 1


if __name__ == "__main__":
    sys.exit(main())
