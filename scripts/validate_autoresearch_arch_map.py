#!/usr/bin/env python3
"""GP-101 executable validator — ex-ante and ex-post drift check.

Iterates a registry of (arch-map, source-file) pairs and asserts each
map's claims against its live source. Originally single-pair
(autoresearch_loop only); generalized 2026-04-25 night so Phase 4b/4c's
orchestrator/ split can register per-file arch maps without forking
this script.

Usage:
    python -m scripts.validate_autoresearch_arch_map ex-ante
    python -m scripts.validate_autoresearch_arch_map ex-post
    python -m scripts.validate_autoresearch_arch_map show   # print all claims
    python -m scripts.validate_autoresearch_arch_map ex-post --only autoresearch_loop

Exit codes:
    0 — validation passed
    1 — drift detected (see output for specifics)
    2 — validator error (map or source unreadable)

This is a first-pass validator per GP-101 Option 5. It does NOT detect
semantic drift (a region at the right line range with different behavior);
it detects structural drift (claimed region no longer exists at claimed
line range, claimed function no longer exists, claimed exit no longer
has a matching raise/break site).

Drift tolerance: ±30 lines per region, matching the map's self-stated
disclaimer that line numbers drift under routine editing.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

# Registry of (label, map_path, src_path) pairs. Adding a new arch map
# (e.g., orchestrator/telemetry_arch_map.md once Phase 4b lands) = one tuple.
# Per Linus: data drives the loop, not code.
MAP_REGISTRY: list[tuple[str, Path, Path]] = [
    (
        "autoresearch_loop",
        REPO / "docs" / "internal" / "autoresearch_loop_architectural_map.md",
        REPO / "src" / "ztare" / "validator" / "autoresearch_loop.py",
    ),
    (
        "iter_context",
        REPO / "docs" / "internal" / "orchestrator_iter_context_architectural_map.md",
        REPO / "src" / "ztare" / "orchestrator" / "iter_context.py",
    ),
    (
        "telemetry",
        REPO / "docs" / "internal" / "orchestrator_telemetry_architectural_map.md",
        REPO / "src" / "ztare" / "orchestrator" / "telemetry.py",
    ),
    (
        "state",
        REPO / "docs" / "internal" / "orchestrator_state_architectural_map.md",
        REPO / "src" / "ztare" / "orchestrator" / "state.py",
    ),
    (
        "prompt",
        REPO / "docs" / "internal" / "orchestrator_prompt_architectural_map.md",
        REPO / "src" / "ztare" / "orchestrator" / "prompt.py",
    ),
    (
        "contract_adherence",
        REPO / "docs" / "internal" / "orchestrator_contract_adherence_architectural_map.md",
        REPO / "src" / "ztare" / "orchestrator" / "contract_adherence.py",
    ),
    (
        "parallel_mutator",
        REPO / "docs" / "internal" / "orchestrator_parallel_mutator_architectural_map.md",
        REPO / "src" / "ztare" / "orchestrator" / "parallel_mutator.py",
    ),
    (
        "contract_table",
        REPO / "docs" / "internal" / "orchestrator_contract_table_architectural_map.md",
        REPO / "src" / "ztare" / "orchestrator" / "contract_table.py",
    ),
    (
        "protocols",
        REPO / "docs" / "internal" / "orchestrator_protocols_architectural_map.md",
        REPO / "src" / "ztare" / "orchestrator" / "protocols.py",
    ),
    (
        "render_evidence_template",
        REPO / "docs" / "internal" / "orchestrator_render_evidence_template_architectural_map.md",
        REPO / "src" / "ztare" / "orchestrator" / "render_evidence_template.py",
    ),
    (
        "evidence_contract",
        REPO / "docs" / "internal" / "orchestrator_evidence_contract_architectural_map.md",
        REPO / "src" / "ztare" / "orchestrator" / "evidence_contract.py",
    ),
    (
        "gate_manifest",
        REPO / "docs" / "internal" / "orchestrator_gate_manifest_architectural_map.md",
        REPO / "src" / "ztare" / "orchestrator" / "gate_manifest.py",
    ),
]

# Backwards-compat aliases (kept so any external caller that imported
# MAP_PATH / SRC_PATH does not break). Point at the first registry entry.
MAP_PATH = MAP_REGISTRY[0][1]
SRC_PATH = MAP_REGISTRY[0][2]

LINE_TOLERANCE = 30


@dataclass(frozen=True)
class RegionClaim:
    name: str
    lo: int
    hi: int
    entry: str


@dataclass(frozen=True)
class FuncClaim:
    name: str
    sig_hint: str


@dataclass(frozen=True)
class ExitClaim:
    name: str
    approx_line: int
    cause: str


def _read(path: Path) -> str:
    if not path.exists():
        print(f"ERROR: missing file: {path}", file=sys.stderr)
        sys.exit(2)
    return path.read_text(encoding="utf-8")


def parse_map_regions(map_text: str) -> list[RegionClaim]:
    """Parse lines like: `region: rubric_preflight  lines: ~2704-2760  entry: ...`"""
    out: list[RegionClaim] = []
    pat = re.compile(
        r"region:\s*(?P<name>\w+)\s+lines:\s*~?(?P<lo>\d+)[-–](?P<hi>\d+)\s+entry:\s*(?P<entry>.+?)(?:\s*$|\s+note:)",
        re.MULTILINE,
    )
    for m in pat.finditer(map_text):
        out.append(RegionClaim(
            name=m.group("name"),
            lo=int(m.group("lo")),
            hi=int(m.group("hi")),
            entry=m.group("entry").strip(),
        ))
    return out


def parse_map_functions(map_text: str) -> list[FuncClaim]:
    """Parse lines like: `func: _pop_seed_queue  sig: (...)  → None`"""
    out: list[FuncClaim] = []
    pat = re.compile(r"func:\s*(?P<name>\w+)\s+sig:\s*(?P<sig>.+)$", re.MULTILINE)
    for m in pat.finditer(map_text):
        out.append(FuncClaim(
            name=m.group("name"),
            sig_hint=m.group("sig").strip(),
        ))
    return out


def parse_map_exits(map_text: str) -> list[ExitClaim]:
    """Parse lines like: `exit: R1_exception  line: ~3178  cause: ...`"""
    out: list[ExitClaim] = []
    pat = re.compile(
        r"exit:\s*(?P<name>\w+)\s+line(?:s)?:\s*~?(?P<line>\d+)(?:[-–]\d+)?\s+cause:\s*(?P<cause>.+)$",
        re.MULTILINE,
    )
    for m in pat.finditer(map_text):
        out.append(ExitClaim(
            name=m.group("name"),
            approx_line=int(m.group("line")),
            cause=m.group("cause").strip(),
        ))
    return out


def check_region(region: RegionClaim, src: str) -> tuple[bool, str]:
    """Check that the entry hint appears near the claimed line range."""
    src_lines = src.splitlines()
    hint = region.entry.split(",")[0].strip().strip("'\"`")
    # Look for hint within claimed range ± tolerance
    search_lo = max(0, region.lo - LINE_TOLERANCE)
    search_hi = min(len(src_lines), region.hi + LINE_TOLERANCE)
    for i in range(search_lo, search_hi):
        if hint in src_lines[i]:
            if abs(i + 1 - region.lo) > LINE_TOLERANCE:
                return False, f"found at line {i+1}, claimed {region.lo}-{region.hi} (drift {abs(i+1-region.lo)} > {LINE_TOLERANCE})"
            return True, f"OK at line {i+1}"
    return False, f"entry hint {hint!r} NOT FOUND in line range {search_lo+1}-{search_hi}"


def check_function(func: FuncClaim, src: str) -> tuple[bool, str]:
    """Check that `def <name>(` appears in src."""
    pat = re.compile(rf"^\s*def\s+{re.escape(func.name)}\s*\(", re.MULTILINE)
    m = pat.search(src)
    if m:
        line_no = src[:m.start()].count("\n") + 1
        return True, f"OK at line {line_no}"
    return False, f"function def NOT FOUND"


def check_exit(exit_claim: ExitClaim, src: str) -> tuple[bool, str]:
    """Check exit site: grep for raise/break/SystemExit near claimed line, or
    for a comment mentioning this exit's name."""
    src_lines = src.splitlines()
    search_lo = max(0, exit_claim.approx_line - LINE_TOLERANCE * 2)
    search_hi = min(len(src_lines), exit_claim.approx_line + LINE_TOLERANCE * 2)
    # Exit comments like "GP-133 R4 GATE FAIL" or name matches
    name_tokens = re.split(r"[_\s]+", exit_claim.name)
    for i in range(search_lo, search_hi):
        line = src_lines[i]
        if "raise" in line or "break" in line or "SystemExit" in line:
            # Near-ish to claimed line
            if abs(i + 1 - exit_claim.approx_line) <= LINE_TOLERANCE * 2:
                return True, f"OK near line {i+1}"
    # Fallback: search for the exit name as a comment
    pat = re.compile(re.escape(exit_claim.name.replace("_", " ")), re.IGNORECASE)
    if pat.search(src):
        return True, f"exit name referenced in source (comment/string)"
    return False, f"no raise/break/SystemExit/comment found near line {exit_claim.approx_line}"


def validate(map_text: str, src: str) -> tuple[int, int, list[str]]:
    """Return (n_passed, n_total, failure_messages)."""
    regions = parse_map_regions(map_text)
    functions = parse_map_functions(map_text)
    exits = parse_map_exits(map_text)

    failures: list[str] = []
    passed = 0
    total = 0

    for r in regions:
        total += 1
        ok, msg = check_region(r, src)
        if ok:
            passed += 1
        else:
            failures.append(f"  REGION {r.name!r}: {msg}")

    for f in functions:
        total += 1
        ok, msg = check_function(f, src)
        if ok:
            passed += 1
        else:
            failures.append(f"  FUNC {f.name!r}: {msg}")

    for e in exits:
        total += 1
        ok, msg = check_exit(e, src)
        if ok:
            passed += 1
        else:
            failures.append(f"  EXIT {e.name!r}: {msg}")

    return passed, total, failures


def _filter_registry(only: str | None) -> list[tuple[str, Path, Path]]:
    if not only:
        return MAP_REGISTRY
    keep = {s.strip() for s in only.split(",") if s.strip()}
    selected = [t for t in MAP_REGISTRY if t[0] in keep]
    if not selected:
        labels = ", ".join(t[0] for t in MAP_REGISTRY)
        print(f"ERROR: --only={only!r} matched no registered arch maps. Known: {labels}", file=sys.stderr)
        sys.exit(2)
    return selected


def cmd_show(only: str | None) -> int:
    for label, map_path, _src_path in _filter_registry(only):
        if not map_path.exists():
            print(f"\n[{label}] MISSING: {map_path}")
            continue
        map_text = _read(map_path)
        regions = parse_map_regions(map_text)
        functions = parse_map_functions(map_text)
        exits = parse_map_exits(map_text)
        print(f"\n=== {label} ===")
        print(f"Regions: {len(regions)}")
        for r in regions:
            print(f"  • {r.name}  {r.lo}-{r.hi}  entry={r.entry[:60]!r}")
        print(f"Functions: {len(functions)}")
        for f in functions:
            print(f"  • {f.name}  sig={f.sig_hint[:60]!r}")
        print(f"Exits: {len(exits)}")
        for e in exits:
            print(f"  • {e.name}  line~{e.approx_line}  cause={e.cause[:60]!r}")
    return 0


def _run_mode(mode: str, only: str | None) -> int:
    """Run ex-ante or ex-post over the (filtered) registry."""
    is_ante = mode == "ex-ante"
    banner = (
        "GP-101 arch-map ex-ante validation (read before editing)"
        if is_ante
        else "GP-101 arch-map ex-post validation (run after editing)"
    )
    print(banner)

    selected = _filter_registry(only)
    overall_failed = False
    grand_passed = 0
    grand_total = 0

    for label, map_path, src_path in selected:
        print(f"\n--- {label} ---")
        map_text = _read(map_path)
        src = _read(src_path)
        passed, total, failures = validate(map_text, src)
        grand_passed += passed
        grand_total += total
        print(f"{passed}/{total} claims verified for {label}.")
        if failures:
            overall_failed = True
            print("Drift detected:")
            for f in failures:
                print(f)

    print(f"\n=== Total: {grand_passed}/{grand_total} claims verified across {len(selected)} arch map(s). ===")
    if overall_failed:
        if is_ante:
            print("Ex-ante is advisory: you may proceed, but maps are known-stale on the listed claims.")
            print("If your edit touches a drifted area, update the relevant map as part of the edit.")
        else:
            print("Drift detected AFTER edit. For each drifted map, either:")
            print("  (a) Update the arch map to reflect current state, OR")
            print("  (b) Revert the edit if it inadvertently broke a claim you did not intend to change.")
        return 1
    print("No drift. Proceed." if is_ante else "No drift. Edit is consistent with the map(s).")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "mode",
        choices=["ex-ante", "ex-post", "show"],
        help="ex-ante: read before editing. ex-post: verify after editing. show: dump all claims.",
    )
    parser.add_argument(
        "--only",
        default=None,
        help=(
            "Comma-separated arch-map labels to validate (e.g. 'autoresearch_loop'). "
            "Default: all registered maps."
        ),
    )
    args = parser.parse_args(argv)

    if args.mode == "show":
        return cmd_show(args.only)
    if args.mode in {"ex-ante", "ex-post"}:
        return _run_mode(args.mode, args.only)
    return 2


if __name__ == "__main__":
    sys.exit(main())
