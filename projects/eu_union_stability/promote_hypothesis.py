#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import re
import shutil
import symtable
from datetime import datetime, timezone
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parent
HYPOTHESES_DIR = PROJECT_DIR / "hypotheses"
WORKSPACE_DIR = PROJECT_DIR / "workspace"
ACTIVE_BUNDLE_PATH = PROJECT_DIR / ".active_bundle.json"
DEFAULT_WARN_THRESHOLD = 0.30

STATUS_FILES = (
    "latest_information_yield.json",
    "underidentification_verdict.json",
    "latest_candidate_selection.json",
    "latest_mutation_declaration.json",
    "latest_mutation_validation.json",
)


def _copy(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _files_match(path_a: Path, path_b: Path) -> bool:
    return path_a.exists() and path_b.exists() and _read_text(path_a) == _read_text(path_b)


def _bundle_matches_root(bundle_dir: Path) -> bool:
    root_thesis = PROJECT_DIR / "thesis.md"
    bundle_thesis = bundle_dir / "thesis.md"
    if not _files_match(root_thesis, bundle_thesis):
        return False

    root_test_model = PROJECT_DIR / "test_model.py"
    bundle_test_model = bundle_dir / "test_model.py"
    if root_test_model.exists() != bundle_test_model.exists():
        return False
    if root_test_model.exists() and not _files_match(root_test_model, bundle_test_model):
        return False
    return True


def _infer_active_bundle_name() -> str | None:
    matches: list[str] = []
    for bundle_dir in sorted(HYPOTHESES_DIR.iterdir()):
        if not bundle_dir.is_dir():
            continue
        try:
            if _bundle_matches_root(bundle_dir):
                matches.append(bundle_dir.name)
        except OSError:
            continue
    if len(matches) == 1:
        return matches[0]
    return None


def _load_active_bundle_name() -> tuple[str | None, str]:
    if ACTIVE_BUNDLE_PATH.exists():
        try:
            payload = json.loads(_read_text(ACTIVE_BUNDLE_PATH))
        except json.JSONDecodeError as exc:
            raise SystemExit(f"Invalid active bundle state file: {ACTIVE_BUNDLE_PATH} ({exc})")
        name = payload.get("name")
        if not isinstance(name, str) or not name:
            raise SystemExit(f"Invalid active bundle state payload: {ACTIVE_BUNDLE_PATH}")
        return name, "state"

    inferred = _infer_active_bundle_name()
    if inferred:
        return inferred, "inferred"
    return None, "none"


def _write_active_bundle_name(name: str) -> None:
    payload = {
        "name": name,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    ACTIVE_BUNDLE_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _snapshot_root_to_bundle(bundle_name: str) -> list[str]:
    bundle_dir = HYPOTHESES_DIR / bundle_name
    if not bundle_dir.is_dir():
        return [f"skipped snapshot: missing bundle directory {bundle_dir}"]

    actions: list[str] = []
    root_thesis = PROJECT_DIR / "thesis.md"
    if root_thesis.exists():
        _copy(root_thesis, bundle_dir / "thesis.md")
        actions.append("saved thesis.md")

    root_test_model = PROJECT_DIR / "test_model.py"
    bundle_test_model = bundle_dir / "test_model.py"
    if root_test_model.exists():
        _copy(root_test_model, bundle_test_model)
        actions.append("saved test_model.py")
    elif bundle_test_model.exists():
        bundle_test_model.unlink()
        actions.append("removed stale bundle test_model.py")
    else:
        actions.append("root had no test_model.py")

    return actions


def _collect_name_targets(target: ast.AST) -> set[str]:
    names: set[str] = set()
    if isinstance(target, ast.Name):
        names.add(target.id)
    elif isinstance(target, (ast.Tuple, ast.List)):
        for elt in target.elts:
            names.update(_collect_name_targets(elt))
    return names


def _extract_unresolved_tokens(source: str) -> set[str]:
    tokens: set[str] = set()
    stopwords = {"a", "an", "and", "as", "for", "of", "or", "the", "to", "vs", "whether"}
    for line in source.splitlines():
        if "UNRESOLVED:" not in line:
            continue
        _, _, tail = line.partition("UNRESOLVED:")
        candidate = tail.lstrip(" :#")
        candidate = re.split(r"[—.-]", candidate, maxsplit=1)[0]
        words = [
            word
            for word in re.findall(r"[A-Za-z]+", candidate.lower())
            if word not in stopwords
        ]
        if words:
            tokens.add(f"unresolved:{'_'.join(words[:3])}")
    return tokens


def extract_proxy_set(test_model_path: Path) -> set[str]:
    source = test_model_path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(test_model_path))
    table = symtable.symtable(source, str(test_model_path), "exec")

    module_level_names: set[str] = set()
    test_nodes: list[ast.FunctionDef | ast.AsyncFunctionDef] = []

    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            module_level_names.add(node.name)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith(
                "test_"
            ):
                test_nodes.append(node)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                module_level_names.update(_collect_name_targets(target))
        elif isinstance(node, ast.AnnAssign):
            module_level_names.update(_collect_name_targets(node.target))

    function_tables = {
        (child.get_name(), child.get_lineno()): child
        for child in table.get_children()
        if child.get_type() == "function"
    }

    proxies: set[str] = set()
    for node in test_nodes:
        proxies.add(f"test:{node.name}")
        fn_table = function_tables.get((node.name, node.lineno))
        if fn_table is None:
            continue
        for symbol in fn_table.get_symbols():
            if not symbol.is_referenced() or not symbol.is_global():
                continue
            name = symbol.get_name()
            if name in module_level_names and not name.startswith("__"):
                proxies.add(f"proxy:{name}")

    proxies.update(_extract_unresolved_tokens(source))
    return proxies


def jaccard_distance(set_a: set[str], set_b: set[str]) -> float:
    union = set_a | set_b
    if not union:
        return 0.0
    return 1.0 - (len(set_a & set_b) / len(union))


def _emit_diversity_report(bundle_dir: Path, warn_threshold: float) -> None:
    test_model_src = bundle_dir / "test_model.py"
    if not test_model_src.exists():
        print("- no diversity report: bundle has no test_model.py yet")
        return

    try:
        candidate_set = extract_proxy_set(test_model_src)
    except SyntaxError as exc:
        print(f"- no diversity report: could not parse bundle test_model.py ({exc})")
        return

    comparisons: list[tuple[float, str, int, int, list[str]]] = []
    for other in sorted(HYPOTHESES_DIR.iterdir()):
        if other == bundle_dir or not other.is_dir():
            continue
        other_test_model = other / "test_model.py"
        if not other_test_model.exists():
            continue
        try:
            other_set = extract_proxy_set(other_test_model)
        except SyntaxError:
            continue
        overlap = sorted(candidate_set & other_set)
        comparisons.append(
            (
                jaccard_distance(candidate_set, other_set),
                other.name,
                len(other_set),
                len(overlap),
                overlap[:5],
            )
        )

    print(f"- proxy signature size: {len(candidate_set)}")
    if not comparisons:
        print("- no diversity report: no other hypothesis bundles with test_model.py")
        return

    print("- operational neighborhood (Jaccard distance on proxy signatures):")
    for distance, name, other_size, overlap_count, overlap_preview in sorted(comparisons):
        label = "WARNING" if distance < warn_threshold else "ok"
        overlap_text = ", ".join(overlap_preview) if overlap_preview else "none"
        print(
            f"  [{label}] {name}: distance={distance:.2f}, "
            f"overlap={overlap_count}, other_size={other_size}, sample={overlap_text}"
        )


def _archive_status_files() -> list[str]:
    archived: list[str] = []
    archive_dir = WORKSPACE_DIR / "promotion_archive"
    archive_dir.mkdir(parents=True, exist_ok=True)
    for name in STATUS_FILES:
        target = WORKSPACE_DIR / name
        if not target.exists():
            continue
        archived_target = archive_dir / name
        if archived_target.exists():
            archived_target.unlink()
        shutil.move(str(target), str(archived_target))
        archived.append(name)
    return archived


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Promote a hypothesis bundle into the active project root."
    )
    parser.add_argument("name", help="Hypothesis bundle directory name under hypotheses/")
    parser.add_argument(
        "--clear-status",
        action="store_true",
        help="Archive stale workspace status files for operator clarity.",
    )
    parser.add_argument(
        "--warn-threshold",
        type=float,
        default=DEFAULT_WARN_THRESHOLD,
        help=(
            "Warning threshold for Jaccard distance between proxy signatures. "
            "Lower distance means operationally closer bundles."
        ),
    )
    parser.add_argument(
        "--no-snapshot",
        action="store_true",
        help="Skip auto-saving the currently active branch back into its bundle before switching.",
    )
    parser.add_argument(
        "--assume-current",
        help=(
            "Treat the current project root as belonging to this bundle for this promotion. "
            "Useful on first use when no .active_bundle.json exists and inference cannot identify "
            "the active branch."
        ),
    )
    args = parser.parse_args()

    bundle_dir = HYPOTHESES_DIR / args.name
    thesis_src = bundle_dir / "thesis.md"
    test_model_src = bundle_dir / "test_model.py"

    if not bundle_dir.is_dir():
        raise SystemExit(f"Missing hypothesis bundle: {bundle_dir}")
    if not thesis_src.exists():
        raise SystemExit(f"Bundle is missing thesis.md: {thesis_src}")

    active_bundle_name, active_bundle_source = _load_active_bundle_name()
    if args.assume_current:
        assumed_bundle = HYPOTHESES_DIR / args.assume_current
        if not assumed_bundle.is_dir():
            raise SystemExit(f"Missing assumed current bundle: {assumed_bundle}")
        active_bundle_name = args.assume_current
        active_bundle_source = "assumed"
    snapshot_actions: list[str] = []
    if not args.no_snapshot and active_bundle_name:
        snapshot_actions = _snapshot_root_to_bundle(active_bundle_name)

    _copy(thesis_src, PROJECT_DIR / "thesis.md")

    active_test_model = PROJECT_DIR / "test_model.py"
    if test_model_src.exists():
        _copy(test_model_src, active_test_model)
        test_model_action = f"copied {test_model_src.name}"
    else:
        if active_test_model.exists():
            active_test_model.unlink()
            test_model_action = "deleted stale project-root test_model.py"
        else:
            test_model_action = "no test_model.py present; runner will fail closed"

    archived: list[str] = []
    if args.clear_status:
        archived = _archive_status_files()

    _write_active_bundle_name(args.name)

    print(f"Promoted hypothesis bundle: {args.name}")
    if active_bundle_name:
        print(f"- previous active bundle: {active_bundle_name} ({active_bundle_source})")
    else:
        print("- previous active bundle: none")
        print("- WARNING: no active bundle state or exact bundle match found; current root was not snapshotted")
    if args.no_snapshot:
        print("- auto-snapshot: skipped by --no-snapshot")
    elif snapshot_actions:
        print(f"- auto-snapshot: {', '.join(snapshot_actions)}")
    else:
        print("- auto-snapshot: nothing to save")
    print(f"- thesis.md <- {thesis_src}")
    print(f"- test_model.py: {test_model_action}")
    print(f"- active bundle state <- {ACTIVE_BUNDLE_PATH.name}")
    _emit_diversity_report(bundle_dir, args.warn_threshold)
    if args.clear_status:
        if archived:
            print(f"- archived workspace status files: {', '.join(archived)}")
        else:
            print("- no workspace status files needed archiving")
    print("")
    print("Next step:")
    print(
        "python -m src.ztare.validator.autoresearch_loop "
        "--project eu_union_stability "
        "--rubric eu_union_integration "
        "--iters 3 "
        "--mutator_model claude "
        "--judge_model claude "
        "--deterministic_score_gates"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
