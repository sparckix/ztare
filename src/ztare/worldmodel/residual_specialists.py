"""Residual-class specialist driver.

Partitions the knowledge frontier into per-mechanism-family shards,
dispatches a specialist agent per shard (via agent dispatch), and records
selection receipts.  No promotion authority — selection results are written
to the receipt log only; existing dominance materialization is the sole
promoter.

CLI:
    python -m ztare.worldmodel.residual_specialists --project P [--dry-run] [--max-shards N] [--by-cells]

Callers must export:
    ZTARE_AGENT_DISPATCH=agent          (enables capability="agent" dispatch)
    ZTARE_AGENT_DISPATCH_MUTATOR=agent  (if the underlying runtime checks the mutator sub-key)

Model / effort selection is ambient:
    ZTARE_CODEX_AGENT_MODEL
    ZTARE_CODEX_AGENT_REASONING_EFFORT
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import tempfile
import textwrap
import time
from pathlib import Path
from typing import Any

from ztare.common.dispatch_model import dispatch_model
from ztare.common.width_allocator import allocate_width
from ztare.common.work_plan import partition, run
from ztare.validator.worldmodel_typed_payload import (
    parse_worldmodel_typed_payload_text,
    worldmodel_typed_payload_contract_prompt,
)
from ztare.worldmodel.batch_gate import batch_gate
from ztare.worldmodel.probe_selection import build_witness_hypergraph

# ── Specialist mode ────────────────────────────────────────────────────────
# ZTARE_SPECIALIST_MODE=workbench|sealed (default: workbench)
# workbench: stage a local preflight pack and dispatch as visible_workbench
# sealed: original one-shot sealed_completion dispatch (fallback)


def _specialist_mode() -> str:
    """Return 'workbench' or 'sealed' from env, defaulting to 'workbench'."""
    raw = os.environ.get("ZTARE_SPECIALIST_MODE", "workbench").strip().lower()
    return "sealed" if raw == "sealed" else "workbench"

# ── Receipt schema id ──────────────────────────────────────────────────────

RECEIPT_SCHEMA = "ztare.residual_specialists.v1"

# ── Frontier builder ───────────────────────────────────────────────────────


def build_frontier(project_dir: str | Path) -> dict:
    """Build the knowledge frontier from the current champion's own candidate_memory record.

    Reads champion identity from workspace/champion_materialization.jsonl (promoted_sha),
    finds the matching record in workspace/candidate_memory.json, and extracts:
      - champion_ref: sha of the champion candidate
      - survives_to_step: holdout_depth from the record (steps survived before failure)
      - first_failure: {t, action, step_index, divergent_cells} from holdout_witness
      - eliminated_families: list of eliminated_hypothesis strings from
        workspace/spec_visible_nogoods.jsonl rows with provenance.source=="investigated_science_turn"

    Returns a best-effort dict; missing fields are None / [].
    """
    project_dir = Path(project_dir)
    ws = project_dir / "workspace"

    # ── Identify champion sha from materialization log ──
    champion_sha: str | None = None
    cm_log = ws / "champion_materialization.jsonl"
    if cm_log.exists():
        rows = [
            json.loads(l)
            for l in cm_log.read_text(encoding="utf-8", errors="ignore").splitlines()
            if l.strip()
            and _safe_json(l) is not None
        ]
        for row in reversed(rows):
            psha = row.get("promoted_sha") or row.get("from_ref")
            gsha = (row.get("gate_summary_after") or {}).get("gated_sha256")
            champion_sha = psha or gsha
            if champion_sha:
                break

    # ── Find champion record in candidate_memory ──
    cm_path = ws / "candidate_memory.json"
    candidate_records: list[dict] = []
    if cm_path.exists():
        try:
            raw = json.loads(cm_path.read_text(encoding="utf-8"))
            candidate_records = raw.get("records") or [] if isinstance(raw, dict) else raw
        except Exception:  # noqa: BLE001
            pass

    champ_record: dict | None = None
    if champion_sha and candidate_records:
        short = champion_sha[:8]
        for rec in candidate_records:
            rsha = rec.get("sha") or ""
            if rsha.startswith(short) or champion_sha.startswith(rsha[:8]):
                champ_record = rec
                break
    # fallback: max holdout_depth record
    if champ_record is None and candidate_records:
        champ_record = max(candidate_records, key=lambda r: r.get("holdout_depth") or 0)

    # ── Extract first-failure witness ──
    first_failure: dict | None = None
    survives_to_step: int | None = None
    champion_ref: str | None = champion_sha

    if champ_record is not None:
        survives_to_step = champ_record.get("holdout_depth")
        ct = champ_record.get("counterexample_trace") or {}
        hw = ct.get("holdout_witness") or champ_record.get("holdout_witness") or {}
        if isinstance(hw, dict) and (hw.get("divergent_cells") or hw.get("t") is not None):
            first_failure = {
                "t": hw.get("t"),
                "action": hw.get("action"),
                "step_index": hw.get("step_index"),
                "divergent_cells": hw.get("divergent_cells") or [],
            }

    # ── Eliminated families from investigated nogoods ──
    eliminated_families: list[str] = []
    ng_path = ws / "spec_visible_nogoods.jsonl"
    if ng_path.exists():
        for line in ng_path.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except Exception:  # noqa: BLE001
                continue
            prov = row.get("provenance") or {}
            if prov.get("source") == "investigated_science_turn":
                hyp = row.get("eliminated_hypothesis") or row.get("payload", {}).get("eliminated_hypothesis")
                if hyp:
                    eliminated_families.append(hyp)

    # ── FRESH witness override: records describe a PRIOR champion's frontier
    # (round 3 provably wasted dispatches on a solved step because of this).
    # Compute the CURRENT champion's first divergence by propagated rollout;
    # prefer it whenever available.
    fresh = _fresh_frontier_witness(project_dir)
    if fresh is not None:
        first_failure = fresh
        survives_to_step = fresh.get("step_index")

    return {
        "champion_ref": champion_ref,
        "survives_to_step": survives_to_step,
        "first_failure": first_failure,
        "eliminated_families": eliminated_families,
    }


def _fresh_frontier_witness(project_dir: Path) -> dict | None:
    """Compute the CURRENT champion's first holdout divergence by propagated
    rollout. Returns {t, action, step_index, divergent_cells} or None
    (None also means: champion explains the full holdout — closure)."""
    try:
        from ztare.worldmodel.evidence_consolidation import (
            _load_carrier_from_source,
            resolve_episode_paths,
        )
        from ztare.worldmodel.episode_log import EpisodeLog
        from ztare.worldmodel.gates import as_predictor
        champ = project_dir / "test_model.py"
        hp = resolve_episode_paths(project_dir).get("holdout")
        if hp is None or not (champ.exists() and hp.exists()):
            return None
        rows = list(EpisodeLog.read_jsonl(hp))
        if not rows:
            return None
        program = _load_carrier_from_source(champ.read_text(), str(champ), project_dir)
        predict = as_predictor(program)
        state = rows[0].s
        for i, tr in enumerate(rows):
            pred = predict(state, tr.a, tr.t)
            if pred is None or pred != tr.s_next:
                cells = []
                if pred is not None:
                    for r in range(len(tr.s_next)):
                        for c in range(len(tr.s_next[0])):
                            pv = pred[r][c] if (r < len(pred) and c < len(pred[r])) else None
                            if pv != tr.s_next[r][c]:
                                cells.append({"row": r, "col": c,
                                              "predicted": pv,
                                              "actual": tr.s_next[r][c]})
                                if len(cells) >= 40:
                                    break
                        if len(cells) >= 40:
                            break
                return {"t": getattr(tr, "t", None), "action": getattr(tr, "a", None),
                        "step_index": i, "divergent_cells": cells}
            state = pred  # propagated rollout
        return None
    except Exception:  # noqa: BLE001
        return None


def _safe_json(line: str) -> dict | None:
    try:
        return json.loads(line)
    except Exception:  # noqa: BLE001
        return None


# ── Mechanism-history helpers ──────────────────────────────────────────────


def _load_mechanism_history(project_dir: Path) -> list[str]:
    """Parse MECHANISM: lines from past specialist thesis entries in residual_specialists.jsonl.

    Returns list of mechanism strings that are NOT eliminated.
    """
    rs_path = project_dir / "workspace" / "residual_specialists.jsonl"
    if not rs_path.exists():
        return []

    # Load eliminated families to filter them out
    frontier = build_frontier(project_dir)
    elim_set = set(frontier.get("eliminated_families") or [])

    mechanisms: list[str] = []
    for line in rs_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except Exception:  # noqa: BLE001
            continue
        for disp in row.get("dispatches") or []:
            thesis = disp.get("thesis") or ""
            mech = _parse_mechanism(thesis)
            if mech and mech not in elim_set and mech not in mechanisms:
                mechanisms.append(mech)
    return mechanisms


def _parse_mechanism(thesis: str) -> str | None:
    """Extract the text after 'MECHANISM:' from a thesis_markdown string."""
    if not thesis:
        return None
    m = re.search(r"MECHANISM:\s*(.+?)(?:\n|$)", thesis, re.IGNORECASE)
    if m:
        return m.group(1).strip()
    return None


_ROUTINE_CLAIM_RE = re.compile(
    r"\b(?:is|are|seems?|should be)\s+"
    r"(?:routine|clear(?:ly)?|straightforward|trivial(?:ly)?|obvious(?:ly)?|easy to see)\b",
    re.IGNORECASE,
)


def _routine_claim_lint(thesis: str) -> list[str]:
    """Observable lint (never a strike — rejection hysteresis is real): flag
    hand-waved compatibility claims ('routine', 'clearly', 'trivial', ...) so
    the receipts show them. Transplanted from the CDC prompt's audit clause:
    'claims that an unproved global compatibility statement is routine' must
    be rejected by adversarial review — here we surface them for it."""
    if not thesis:
        return []
    out = []
    for m in _ROUTINE_CLAIM_RE.finditer(thesis):
        start = max(0, m.start() - 60)
        out.append("routine_claim: ..." + thesis[start:m.end() + 20].replace("\n", " "))
        if len(out) >= 5:
            break
    return out


def _parse_discriminator(thesis: str) -> str | None:
    """Extract the text after 'DISCRIMINATOR:' from a thesis_markdown string."""
    if not thesis:
        return None
    m = re.search(r"DISCRIMINATOR:\s*(.+?)(?:\n|$)", thesis, re.IGNORECASE)
    if m:
        return m.group(1).strip()
    return None


# ── Shard construction ─────────────────────────────────────────────────────


def _load_witness_records(project_dir: Path) -> list[dict]:
    """Load near-miss / nogood records that carry holdout_witness divergent cells."""
    ws = project_dir / "workspace"
    records: list[dict] = []

    # Primary: candidate_memory.json
    cm = ws / "candidate_memory.json"
    if cm.exists():
        try:
            raw = json.loads(cm.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                records.extend(raw.get("records") or [])
            elif isinstance(raw, list):
                records.extend(raw)
        except Exception:  # noqa: BLE001
            pass

    # Fallback: spec_visible_nogoods.jsonl
    if not records:
        ng = ws / "spec_visible_nogoods.jsonl"
        if ng.exists():
            for line in ng.read_text(encoding="utf-8", errors="ignore").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    records.append(json.loads(line))
                except Exception:  # noqa: BLE001
                    pass

    # Fallback: latest gate payload files (gate_payload_*.jsonl)
    if not records:
        for gp in sorted(ws.glob("gate_payload_*.jsonl"), reverse=True)[:3]:
            for line in gp.read_text(encoding="utf-8", errors="ignore").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    records.append(json.loads(line))
                except Exception:  # noqa: BLE001
                    pass
            if records:
                break

    return records


def _extract_divergent_cells(record: dict) -> list[dict]:
    """Pull divergent_cells from a candidate_memory or gate_payload record."""
    cells: list[dict] = []
    trace = record.get("counterexample_trace") or {}
    if isinstance(trace, dict):
        hw = trace.get("holdout_witness") or {}
        if isinstance(hw, dict):
            cells.extend(hw.get("divergent_cells") or [])
    # also check top-level holdout_witness
    hw2 = record.get("holdout_witness") or {}
    if isinstance(hw2, dict):
        for cell in hw2.get("divergent_cells") or []:
            if cell not in cells:
                cells.append(cell)
    return cells


def _class_id_for_cells(cells: list[dict]) -> str:
    """Stable class id: sorted (row,col) pairs → sha8."""
    key = sorted((c.get("row"), c.get("col")) for c in cells if isinstance(c, dict))
    return hashlib.sha256(json.dumps(key, sort_keys=True).encode()).hexdigest()[:8]


def _information_yield(cells: list[dict], all_records: list[dict]) -> float:
    """Shard yield via the AGENDA one-door pricing function (partition entropy
    of match/nomatch over the witness records, identification_bits) — replaces
    a homemade -log2(p) that violated the single-pricing-door rule."""
    from ztare.common.information_yield_pricing import identification_bits

    n = len(all_records) or 1
    target_cells = {(cell.get("row"), cell.get("col")) for cell in cells}
    matching: list[dict] = []
    rest: list[dict] = []
    for record in all_records:
        record_cells = {
            (cell.get("row"), cell.get("col"))
            for cell in _extract_divergent_cells(record)
        }
        (matching if target_cells & record_cells else rest).append(record)
    partition = {k: v for k, v in (("match", matching), ("nomatch", rest)) if v}
    return identification_bits(partition, n)


def _visible_residual_records(project_dir: Path, max_rows: int = 40) -> list[dict]:
    """Mine the LIVE visible residual: rows the current champion mispredicts
    on episode_001, shaped like candidate_memory witness records so shard
    grouping is uniform. This is the fresh curriculum — evidence the champion
    cannot explain yet (backtest 2026-07-10: 173 such rows existed while the
    shard builder only read stale holdout witnesses)."""
    try:
        from ztare.worldmodel.evidence_consolidation import (
            _load_carrier_from_source,
            build_row_bitmap,
            residual_view,
        )
        from ztare.worldmodel.episode_log import EpisodeLog
        from ztare.worldmodel.gates import as_predictor
    except Exception:  # noqa: BLE001
        return []
    from ztare.worldmodel.evidence_consolidation import resolve_episode_paths
    champ = project_dir / "test_model.py"
    ep = resolve_episode_paths(project_dir)["visible"]
    if ep is None or not (champ.exists() and ep.exists()):
        return []
    try:
        bm = build_row_bitmap(champ, ep, project_dir=project_dir)
        wrong = residual_view(bm)
        if not wrong:
            return []
        rows = list(EpisodeLog.read_jsonl(ep))
        program = _load_carrier_from_source(champ.read_text(), str(champ), project_dir)
        predict = as_predictor(program)
    except Exception:  # noqa: BLE001
        return []
    records: list[dict] = []
    for i in wrong[:max_rows]:
        tr = rows[i]
        try:
            pred = predict(tr.s, tr.a, tr.t)
        except Exception:  # noqa: BLE001
            pred = None
        cells: list[dict] = []
        if pred is not None:
            h = len(tr.s_next)
            w = len(tr.s_next[0]) if h else 0
            for r in range(h):
                for c in range(w):
                    pv = pred[r][c] if (r < len(pred) and c < len(pred[r])) else None
                    if pv != tr.s_next[r][c]:
                        cells.append({"row": r, "col": c, "predicted": pv,
                                      "actual": tr.s_next[r][c]})
                        if len(cells) >= 40:
                            break
                if len(cells) >= 40:
                    break
        records.append({
            "source": "visible_residual",
            "row_index": i,
            "counterexample_trace": {"holdout_witness": {
                "t": getattr(tr, "t", None),
                "action": getattr(tr, "a", None),
                "step_index": i,
                "divergent_cells": cells,
            }},
        })
    return records


def build_shards(
    project_dir: str | Path,
    max_shards: int | None = None,
    by_cells: bool = False,
) -> list[dict]:
    """Partition into shards, one per unkilled rival mechanism family.

    Default (by_cells=False): shards = one per distinct MECHANISM: line from
    workspace/residual_specialists.jsonl history, minus eliminated families.
    Bootstrap (no history or no MECHANISM: lines) → 2 identically-briefed shards
    with distinct lane personas ('lane_a', 'lane_b') so they diversify under
    dispatch.

    Legacy path (by_cells=True or --by-cells CLI flag): original cell-class
    sharding by divergent-cell witness classes.  Each shard carries its
    witness_rows; mechanism shards also carry witness_rows from the champion's
    first-failure cells.
    """
    if max_shards is None:
        max_shards = int(os.environ.get("ZTARE_SPECIALIST_MAX_SHARDS", "4"))

    project_dir = Path(project_dir)

    if by_cells:
        return _build_cell_shards(project_dir, max_shards)

    return _build_mechanism_shards(project_dir, max_shards)


def _build_mechanism_shards(project_dir: Path, max_shards: int) -> list[dict]:
    """Mechanism-family sharding — one shard per unkilled rival family."""
    frontier = build_frontier(project_dir)
    mechanisms = _load_mechanism_history(project_dir)

    # Champion's first-failure cells as witness_rows for all mechanism shards
    ff = frontier.get("first_failure") or {}
    champ_witness_rows = []
    if ff:
        champ_witness_rows = [{
            "source": "champion_first_failure",
            "counterexample_trace": {"holdout_witness": ff},
        }]

    if not mechanisms:
        # ponytail: bootstrap — 2 shards, identical witness, distinct lane persona
        base_shard = {
            "class_id": "mech_lane_{lane}",
            "mechanism_family": None,
            "cells": ff.get("divergent_cells") or [],
            "witness_rows": champ_witness_rows,
            "yield_bits": 0.0,
            "probe_atoms": [],
            "lane": None,
        }
        shards = []
        for lane in ("lane_a", "lane_b"):
            s = dict(base_shard)
            s["class_id"] = f"mech_{lane}"
            s["lane"] = lane
            shards.append(s)
        return shards[:max_shards]

    # One shard per unkilled mechanism family
    shards = []
    for i, mech in enumerate(mechanisms[:max_shards]):
        lane = f"lane_{i}"
        cid = hashlib.sha256(mech.encode()).hexdigest()[:8]
        shards.append({
            "class_id": cid,
            "mechanism_family": mech,
            "cells": ff.get("divergent_cells") or [],
            "witness_rows": champ_witness_rows,
            "yield_bits": float(i),  # ordering preserved from history (most recent first)
            "probe_atoms": [],
            "lane": lane,
        })
    return shards[:max_shards]


def _build_cell_shards(project_dir: Path, max_shards: int) -> list[dict]:
    """Legacy cell-class sharding (--by-cells path)."""
    records = _load_witness_records(project_dir) + _visible_residual_records(project_dir)

    class_map: dict[str, dict] = {}
    for rec in records:
        cells = _extract_divergent_cells(rec)
        if not cells:
            cc = rec.get("claim_class") or rec.get("failure_family")
            if cc:
                cid = str(cc)[:8]
                if cid not in class_map:
                    class_map[cid] = {"class_id": cid, "cells": [], "witness_rows": [], "probe_atoms": [], "lane": None, "mechanism_family": None}
                class_map[cid]["witness_rows"].append(rec)
            continue
        cid = _class_id_for_cells(cells)
        if cid not in class_map:
            class_map[cid] = {"class_id": cid, "cells": cells, "witness_rows": [], "probe_atoms": [], "lane": None, "mechanism_family": None}
        class_map[cid]["witness_rows"].append(rec)

    for entry in class_map.values():
        hg = build_witness_hypergraph(entry["witness_rows"])
        atoms: set[str] = set()
        for edge in hg.values():
            atoms.update(edge)
        entry["probe_atoms"] = sorted(atoms)

    for entry in class_map.values():
        entry["yield_bits"] = _information_yield(entry["cells"], records)

    shards = sorted(class_map.values(), key=lambda s: s["yield_bits"], reverse=True)

    if not shards:
        shards = [{
            "class_id": "empty",
            "cells": [],
            "witness_rows": [],
            "yield_bits": 0.0,
            "probe_atoms": [],
            "lane": None,
            "mechanism_family": None,
        }]

    return shards[:max_shards]


# ── Pack staging (workbench mode) ─────────────────────────────────────────


def _copy_patch_base_chain(src_py: Path, project_dir: Path, pack_dir: Path, depth: int = 0) -> None:
    """Recursively copy PATCH_BASE source_ref files into the pack so batch_gate resolves them.

    Walks the chain up to 5 levels deep (avoids infinite loops on malformed chains).
    Files are copied to the same relative path under pack_dir.
    ponytail: best-effort — any error is silently swallowed; preflight still runs.
    """
    if depth > 5:
        return
    try:
        src = src_py.read_text(encoding="utf-8", errors="ignore")
        import ast as _ast
        tree = _ast.parse(src)
        for node in _ast.walk(tree):
            if (isinstance(node, _ast.Assign)
                    and any(isinstance(t, _ast.Name) and t.id == "PATCH_BASE" for t in node.targets)):
                if isinstance(node.value, _ast.Dict):
                    for k, v in zip(node.value.keys, node.value.values):
                        if (isinstance(k, _ast.Constant) and k.value == "source_ref"
                                and isinstance(v, _ast.Constant)):
                            ref = str(v.value)
                            ref_path = project_dir / ref
                            if ref_path.exists():
                                dst = pack_dir / ref
                                dst.parent.mkdir(parents=True, exist_ok=True)
                                if not dst.exists():
                                    shutil.copy2(ref_path, dst)
                                # recurse into the chain
                                _copy_patch_base_chain(ref_path, project_dir, pack_dir, depth + 1)
    except Exception:  # noqa: BLE001
        pass


def _stage_specialist_pack(
    project_dir: Path,
    briefing: str,
    class_id: str,
    survives_to_step: int | None,
) -> Path:
    """Stage a minimal preflight pack for workbench dispatch.

    Layout (mirrors how autoresearch visible_workbench receives cwd):
      <tmp_root>/projects/<project_name>/   ← pack_dir (== cwd for agent)
        BRIEFING.md                          ← specialist briefing
        PREFLIGHT.md                         ← copy-pasteable preflight one-liner
        test_model.py                        ← champion copy (patch base)
        raw/episodes/                        ← hardlinked episode files
        workspace/                           ← created for agent scratch
      <tmp_root>/rubrics/<project_name>.json ← rubric copy (satisfies resolver)

    batch_gate's rubric resolver uses project_dir.parents[1]/rubrics/<name>.json,
    so pack_dir.parents[1] == <tmp_root> must contain rubrics/.
    resolve_episode_paths falls back to raw/episodes/*.jsonl (sorted: visible=001, holdout=002).
    """
    tmp_root = Path(tempfile.gettempdir()) / "ztare_specialist_workbench"
    pack_dir = tmp_root / "projects" / project_dir.name
    if pack_dir.exists():
        shutil.rmtree(pack_dir, ignore_errors=True)
    pack_dir.mkdir(parents=True, exist_ok=True)
    (pack_dir / "workspace").mkdir(exist_ok=True)

    # BRIEFING.md
    (pack_dir / "BRIEFING.md").write_text(briefing, encoding="utf-8")

    # Champion copy (test_model.py) + resolve PATCH_BASE chain
    champ = project_dir / "test_model.py"
    if champ.exists():
        shutil.copy2(champ, pack_dir / "test_model.py")
        # If champion is a PATCH_BASE carrier, copy the source chain so preflight resolves
        _copy_patch_base_chain(champ, project_dir, pack_dir)

    # Episodes — hardlink (same device, fast) or copy as fallback
    ep_src = project_dir / "raw" / "episodes"
    ep_dst = pack_dir / "raw" / "episodes"
    ep_dst.mkdir(parents=True, exist_ok=True)
    if ep_src.is_dir():
        for ep_file in sorted(ep_src.glob("*.jsonl"))[:2]:  # visible + holdout
            dst = ep_dst / ep_file.name
            try:
                os.link(ep_file, dst)
            except OSError:
                shutil.copy2(ep_file, dst)

    # Write MANIFEST.json with explicit episode_roles so resolve_episode_paths
    # finds them without needing the rubric (belt + suspenders)
    ep_files = sorted(ep_dst.glob("*.jsonl"))
    episode_roles: dict[str, str] = {}
    if len(ep_files) >= 1:
        episode_roles["visible"] = str(ep_files[0])
    if len(ep_files) >= 2:
        episode_roles["holdout"] = str(ep_files[1])
    manifest = {"episode_roles": episode_roles}
    (pack_dir / "MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    # Rubric — copy to <tmp_root>/rubrics/<name>.json so batch_gate finds it
    rubric_dst_dir = tmp_root / "rubrics"
    rubric_dst_dir.mkdir(exist_ok=True)
    rubric_src = project_dir.parents[1] / "rubrics" / f"{project_dir.name}.json"
    rubric_dst = rubric_dst_dir / f"{project_dir.name}.json"
    if rubric_src.exists():
        shutil.copy2(rubric_src, rubric_dst)
    elif not rubric_dst.exists():
        rubric_dst.write_text("{}", encoding="utf-8")

    # Abs paths for PREFLIGHT.md
    # parents[3] = repo root (residual_specialists.py is at src/ztare/worldmodel/residual_specialists.py)
    repo_root = Path(__file__).resolve().parents[3]
    src_dir = repo_root / "src"
    # find venv python: VIRTUAL_ENV > repo/venv > sys.executable
    venv_python = Path(os.environ.get("VIRTUAL_ENV", str(repo_root / "venv"))) / "bin" / "python"
    if not venv_python.exists():
        import sys as _sys
        venv_python = Path(_sys.executable)

    survives_str = str(survives_to_step) if survives_to_step is not None else "(unknown)"
    preflight_cmd = (
        f"PYTHONPATH={src_dir} {venv_python} -m ztare.worldmodel.batch_gate "
        f"--project {pack_dir} "
        f"--candidates <your_candidate_file.py>"
    )
    preflight_md = textwrap.dedent(f"""\
        # Preflight Instructions

        You have a local workbench. Before submitting, test your candidate:

        ```
        {preflight_cmd}
        ```

        Iterate until your candidate is visible-perfect AND holdout_depth exceeds {survives_str}.
        Then output the final JSON payload as your last message.

        A submission that has not been preflight-tested wastes the turn.
        """)
    (pack_dir / "PREFLIGHT.md").write_text(preflight_md, encoding="utf-8")

    return pack_dir


# ── Briefing construction ──────────────────────────────────────────────────


def _champion_sha(project_dir: Path) -> str | None:
    """Return the full 64-hex sha256 of the briefing-known champion file.

    Tries in order:
    1. The from_ref file named in champion_materialization.jsonl (the exact file
       the briefing cited as PATCH_BASE), so the worker can expand a truncated
       sha that matches that file.
    2. test_model.py (current champion, may differ if a second promotion happened
       between briefing and normalization).
    """
    ws = project_dir / "workspace"
    cm_log = ws / "champion_materialization.jsonl"
    if cm_log.exists():
        rows = []
        for line in cm_log.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except Exception:  # noqa: BLE001
                pass
        for row in reversed(rows):
            ref = row.get("from_ref")
            if ref:
                ref_path = project_dir / ref if not Path(ref).is_absolute() else Path(ref)
                if ref_path.exists():
                    return hashlib.sha256(ref_path.read_bytes()).hexdigest()
                break  # found most recent row but file missing; fall through
    tm = project_dir / "test_model.py"
    if tm.exists():
        return hashlib.sha256(tm.read_bytes()).hexdigest()
    return None


def _patch_base_ref_and_sha(project_dir: Path) -> tuple[str | None, str | None]:
    """Return (source_ref, full_sha256) from champion_materialization or test_model.py fallback."""
    ws = project_dir / "workspace"
    cm_log = ws / "champion_materialization.jsonl"
    full_sha = _champion_sha(project_dir)  # always compute from live test_model.py

    if cm_log.exists():
        rows = []
        for line in cm_log.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except Exception:  # noqa: BLE001
                pass
        for row in reversed(rows):
            ref = row.get("from_ref")
            if ref:
                # Use live sha (full 64-hex); fall back to log sha if we have no live file
                sha = full_sha or row.get("promoted_sha") or row.get("sha")
                return ref, sha

    tm = project_dir / "test_model.py"
    if tm.exists():
        return f"{project_dir.name}/test_model.py", full_sha

    return None, None


def _patch_base_directive(project_dir: Path) -> str:
    """Build the PATCH_BASE block from champion_materialization.jsonl or test_model.py.

    Bug-3(a): sha rendered on its own line with a verbatim-copy instruction so
    leaves don't silently truncate it.
    """
    ref, sha = _patch_base_ref_and_sha(project_dir)
    if ref and sha:
        return (
            f"PATCH_BASE: {ref}\n"
            f"sha256 (copy verbatim, all 64 hex): {sha}\n"
            "Preserve behavior for all visible + holdout cells not in this shard.\n"
            "Modify ONLY where this shard's witnesses diverge.\n"
            "Regressions on other cells are auto-rejected."
        )

    return (
        "PATCH_BASE: (champion not located — check workspace/champion_materialization.jsonl)\n"
        "Preserve all existing behavior; modify only shard witnesses."
    )


_HEX64_RE = re.compile(r'[0-9a-fA-F]{12,63}')  # prefix candidates


def _normalize_patch_base_sha(code: str, champion_sha: str, notes: list[str]) -> str:
    """Bug-3(b): if code contains a PATCH_BASE dict whose sha256 is a prefix
    (>=12 chars) of champion_sha, replace it with the full 64-hex digest.

    Only replaces when the truncated value is unambiguously a prefix of the
    known champion sha (safe: the gate still verifies the full sha).
    """
    # Match: "sha256": "HEXSTRING" inside a PATCH_BASE dict
    pat = re.compile(r'(PATCH_BASE\s*=\s*\{[^\}]*"sha256"\s*:\s*")([0-9a-fA-F]{12,63})(")')
    def _expand(m: re.Match) -> str:
        prefix = m.group(2)
        if champion_sha.startswith(prefix) and len(prefix) < 64:
            notes.append(f"patch_base_sha_expanded: {prefix!r} → {champion_sha!r}")
            return m.group(1) + champion_sha + m.group(3)
        return m.group(0)
    return pat.sub(_expand, code)


def _format_witness_table(shard: dict, max_rows: int = 20) -> str:
    """Format witness table — always from champion's first-failure cells."""
    rows = shard.get("witness_rows") or []
    lines = ["t\taction\tstep\tcell\tpredicted->actual"]
    for rec in rows[:max_rows]:
        trace = rec.get("counterexample_trace") or {}
        hw = trace.get("holdout_witness") or rec.get("holdout_witness") or {}
        t = hw.get("t", trace.get("t", rec.get("t", "?")))
        action = hw.get("action", trace.get("action", rec.get("action", "?")))
        step = hw.get("step_index", "?")
        cell_strs = [
            f"({c.get('row')},{c.get('col')}) {c.get('predicted','?')}->{c.get('actual', c.get('observed','?'))}"
            for c in _extract_divergent_cells(rec)
        ]
        lines.append(f"{t}\t{action}\t{step}\t{'; '.join(cell_strs) or '?'}")
    if len(rows) > max_rows:
        lines.append(f"... ({len(rows) - max_rows} more rows)")
    return "\n".join(lines)


def specialist_briefing(shard: dict, project_dir: str | Path, *, mode: str | None = None) -> str:
    """Build a ~4-6k specialist briefing string.

    Sections (Christensen reframe): FRONTIER, ELIMINATED FAMILIES, THE JOB,
    PATCH_BASE, witness table (champion's first-failure cells), ground truth,
    champion source, INVESTIGATED option, contract prompt.

    mode: 'workbench' (default) or 'sealed' — controls whether the workbench
    paragraph is injected into THE JOB section.
    """
    if mode is None:
        mode = _specialist_mode()
    project_dir = Path(project_dir)
    patch_base = _patch_base_directive(project_dir)

    champion_src = ""
    champ_path = project_dir / "test_model.py"
    if champ_path.exists():
        champion_src = champ_path.read_text(encoding="utf-8", errors="ignore")
        if len(champion_src) > 12_000:
            champion_src = champion_src[:12_000] + "\n# ... (truncated; full source at PATCH_BASE ref)"

    dyn = None
    try:
        rb = Path("rubrics") / f"{project_dir.name}.json"
        if rb.exists():
            dyn = json.loads(rb.read_text()).get("dynamics_assumption")
    except Exception:  # noqa: BLE001
        dyn = None
    contract_prompt = worldmodel_typed_payload_contract_prompt(dyn)
    witness_table = _format_witness_table(shard)

    # ── FRONTIER section ──
    frontier = build_frontier(project_dir)
    champ_ref = frontier.get("champion_ref") or "(unknown)"
    survives = frontier.get("survives_to_step")
    survives_str = str(survives) if survives is not None else "(unknown)"
    ff = frontier.get("first_failure") or {}
    if ff:
        ff_str = (
            f"t={ff.get('t')}  action={ff.get('action')}  step_index={ff.get('step_index')}\n"
            f"  divergent_cells: " + "; ".join(
                f"({c.get('row')},{c.get('col')}) predicted={c.get('predicted','?')} actual={c.get('actual','?')}"
                for c in (ff.get("divergent_cells") or [])[:10]
            )
        )
    else:
        ff_str = "(no first-failure witness in candidate_memory)"
    elim = frontier.get("eliminated_families") or []
    elim_str = "\n".join(f"  - {h}" for h in elim) if elim else "  (none recorded yet)"

    # Mechanism family for this shard (if from history)
    mech_family = shard.get("mechanism_family")
    lane = shard.get("lane")
    if mech_family:
        lane_persona = f"Your lane: {lane}  Mechanism family under investigation: {mech_family}"
    elif lane:
        lane_persona = (
            f"Your lane: {lane}  "
            "Bootstrap run — no prior MECHANISM: lines. Propose a distinct causal mechanism "
            "from the evidence; do NOT anchor on prior candidates."
        )
    else:
        lane_persona = "(single-lane run)"

    # ── Ground truth (DISCOVERY consumable) ──
    ground_truth = ""
    from ztare.worldmodel.evidence_consolidation import resolve_episode_paths
    ep2 = resolve_episode_paths(project_dir)["holdout"]
    if ep2 is not None and ep2.exists():
        try:
            from ztare.worldmodel.episode_log import EpisodeLog
            rows2 = list(EpisodeLog.read_jsonl(ep2))
            if rows2:
                tr = rows2[0]
                delta = []
                for r in range(len(tr.s_next)):
                    for c in range(len(tr.s_next[0])):
                        if tr.s[r][c] != tr.s_next[r][c]:
                            delta.append(f"({r},{c}) {tr.s[r][c]}->{tr.s_next[r][c]}")
                            if len(delta) >= 80:
                                break
                    if len(delta) >= 80:
                        break
                ground_truth = (
                    "\n## First-Divergence Ground Truth (DISCOVERY consumable)\n"
                    f"holdout row 0: t={getattr(tr, 't', '?')} action={getattr(tr, 'a', '?')} — "
                    f"COMPLETE cell delta s->s_next ({len(delta)} changed cells):\n"
                    + "; ".join(delta)
                    + "\n\n(Also computable via contrast_worldmodel_episodes affordance.)"
                )
        except Exception:  # noqa: BLE001
            ground_truth = ""

    probe_atoms = shard.get("probe_atoms") or []
    class_id = shard.get("class_id", "?")
    yield_bits = shard.get("yield_bits", 0.0)
    n_witnesses = len(shard.get("witness_rows") or [])

    # Shard-relevant nogood clauses
    nogood_excerpt = ""
    ws = project_dir / "workspace"
    ng = ws / "spec_visible_nogoods.jsonl"
    if ng.exists():
        probe_set = set(probe_atoms)
        relevant = []
        for line in ng.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = line.strip()
            if not line:
                continue
            if any(atom in line for atom in probe_set) or not probe_set:
                relevant.append(line)
            if len(relevant) >= 5:
                break
        if relevant:
            nogood_excerpt = "\n## Shard-Relevant Nogood Clauses (up to 5)\n" + "\n".join(relevant)
        else:
            nogood_excerpt = "\n## Shard-Relevant Nogood Clauses\n(none found for this shard)"

    # ponytail: workbench paragraph injected only when mode=workbench
    if mode == "workbench":
        workbench_job_paragraph = textwrap.dedent("""\

            ## Workbench
            You have a preflight workbench: read PREFLIGHT.md for the exact command.
            Test your candidate with the preflight command BEFORE submitting.
            Question: does your candidate pass visible-perfect AND holdout_depth > {survives_str}?
            Budget: iterate freely in the workbench until you have a green run.
            Payoff: an untested submission wastes the turn; a preflight-confirmed submission
            is worth a full science credit.
            """).format(survives_str=survives_str)
    else:
        workbench_job_paragraph = ""

    briefing = textwrap.dedent(f"""\
        # Residual Specialist Briefing — class_id={class_id}

        ## FRONTIER
        Champion: {champ_ref}
        Survives to step: {survives_str}
        First failure (receipts-derived witness — lawful):
          {ff_str}

        ## ELIMINATED FAMILIES (do not re-propose these)
        {elim_str}

        ## THE JOB
        {lane_persona}

        State the causal mechanism your candidate embodies under 'MECHANISM:' in thesis_markdown.
        Name the discriminating observable that would kill it under 'DISCRIMINATOR:' in thesis_markdown.
        If instead you can ELIMINATE a family from the evidence, emit the INVESTIGATED control
        receipt — a credited elimination is an equal win.

        Identify your mechanism family by the mathematical idea it uses, not its wording:
        two mechanisms are the SAME family if they predict the same transitions, however
        differently phrased. Do not present a rephrasing of an eliminated family as new.
        Claims that an unproved compatibility statement is "routine", "clear", or
        "straightforward" will not survive audit — support each load-bearing compatibility
        claim with a concrete witness (a transition, a construction, a computation) or
        mark it explicitly as an open assumption of your mechanism.

        Example thesis_markdown fragment:
          MECHANISM: <one-sentence causal claim>
          DISCRIMINATOR: <observable that falsifies it>
        {workbench_job_paragraph}

        ## PATCH_BASE Directive
        {patch_base}

        ## Witness Table (champion first-failure cells: t, action, step, cell, predicted→actual)
        {witness_table}
        {nogood_excerpt}
        {ground_truth}

        ## PATCH_BASE Source (the champion you are patching)
        ```python
        {champion_src}
        ```

        ## DISCOVERY EVIDENCE AUTHORITY (read carefully — this changes what you may use)
        This dispatch runs under run_role=DISCOVERY. Per the CEGIS membrane
        (arc_agi_3_system.md: "Discovery may stage holdout-like slices as
        consumable counterexamples; evaluation keeps them sealed"), the holdout
        episode staged in this pack (raw/episodes, second episode) is LAWFUL
        counterexample evidence for law inference. You MAY condition your
        mechanism on its transitions. You may NOT claim clean transfer from it:
        any transfer claim will be evaluated on a FRESH sealed slice you have
        never seen. A law that merely memorizes those rows will die there —
        prefer the general mechanism that EXPLAINS them.

        ## INVESTIGATED Option
        If you conclude a hypothesis family is ELIMINATED by these witnesses,
        leave test_model_py empty and emit a control receipt:
        {{"type": "INVESTIGATED", "payload": {{"eliminated_hypothesis": "...",
        "witness": {{"t": ..., "a": ..., "cell": ..., "observed": ...,
        "predicted": ...}}, "evidence_refs": ["..."]}}}} in control_receipts.
        An honest credited elimination is a valid science turn.

        ## Output Contract
        {contract_prompt}
    """)
    return briefing


# ── Worker ─────────────────────────────────────────────────────────────────


def _specialist_worker(item: dict) -> dict:
    """Work-plan worker: dispatch one shard, parse response, return result dict."""
    shard = item["shard"]
    briefing = item["briefing"]
    project_dir = Path(item["project_dir"])
    class_id = shard.get("class_id", "?")
    mode = _specialist_mode()

    result: dict = {
        "class_id": class_id,
        "shard": {k: v for k, v in shard.items() if k != "witness_rows"},
        "dispatch_ok": False,
        "investigated": False,
        "control_only": False,
        "parse_error": None,
        "candidate_path": None,
        "gate_result": None,
        "mdl": None,
        "mechanism": None,
        "discriminator": None,
        "timestamp": time.time(),
        "mode": mode,
    }

    if mode == "workbench":
        # Stage a preflight pack so the agent can test locally before submitting.
        frontier = build_frontier(project_dir)
        survives = frontier.get("survives_to_step")
        pack_dir = _stage_specialist_pack(project_dir, briefing, class_id, survives)
        dispatch_result = dispatch_model(
            briefing,
            capability="agent",
            agent_id=f"residual_specialist_{class_id}",
            timeout_seconds=600,
            agent_execution_mode="visible_workbench",
            repo=str(pack_dir),
        )
    else:
        # Sealed fallback (original behavior)
        pack_dir = None
        dispatch_result = dispatch_model(
            briefing,
            capability="agent",
            agent_id=f"residual_specialist_{class_id}",
            timeout_seconds=600,
            agent_execution_mode="sealed_completion",
            repo=str(project_dir.parent if (project_dir.parent / ".git").exists() else project_dir),
        )
    result["dispatch_ok"] = dispatch_result.returncode == 0
    result["dispatch_returncode"] = dispatch_result.returncode

    # Best-effort: count preflight receipts from workbench (workbench_receipts in dispatch log)
    # ponytail: _visible_workbench_receipt_count is internal to dispatch_model; best-effort -1 if unknown
    preflight_receipts: int = -1
    if mode == "workbench" and pack_dir is not None:
        receipts_dir = pack_dir / "workspace" / "visible_cli_receipts"
        try:
            preflight_receipts = sum(1 for p in receipts_dir.glob("*.json") if p.is_file())
        except OSError:
            preflight_receipts = -1
    result["preflight_receipts"] = preflight_receipts

    text = dispatch_result.text or ""
    if not text.strip():
        result["control_only"] = True
        result["parse_error"] = "empty dispatch response"
        return result

    try:
        payload = parse_worldmodel_typed_payload_text(text)
    except ValueError as exc:
        result["parse_error"] = str(exc)
        result["control_only"] = True
        return result

    thesis = payload.get("thesis_markdown", "")
    result["thesis"] = thesis
    result["mechanism"] = _parse_mechanism(thesis)
    result["discriminator"] = _parse_discriminator(thesis)
    lints = _routine_claim_lint(thesis)
    if lints:
        result["lints"] = lints

    code = (payload.get("test_model_py") or "").strip()
    if code == "INVESTIGATED":
        result["investigated"] = True
        return result

    if not code:
        result["control_only"] = True
        return result

    # Bug-3(b): if PATCH_BASE dict has a truncated sha256 (>=12 hex prefix of
    # the known champion sha), expand it to the full 64-hex before writing.
    dispatch_receipt_notes: list[str] = []
    champion_sha = _champion_sha(project_dir)
    if champion_sha:
        code = _normalize_patch_base_sha(code, champion_sha, dispatch_receipt_notes)

    # Write candidate file
    ws = project_dir / "workspace" / "submissions"
    ws.mkdir(parents=True, exist_ok=True)
    n = len(list(ws.glob(f"specialist_{class_id}_*.py")))
    candidate_path = ws / f"specialist_{class_id}_{n}.py"
    candidate_path.write_text(code, encoding="utf-8")
    # Bug-1: store resolved absolute path so gate_by_path lookup succeeds
    result["candidate_path"] = str(candidate_path.resolve())
    result["control_receipts"] = payload.get("control_receipts") or {}
    if dispatch_receipt_notes:
        result["dispatch_receipt_notes"] = dispatch_receipt_notes

    return result


# ── Selection helpers ──────────────────────────────────────────────────────


def _mdl(candidate_path: str) -> int:
    """MDL tie-breaker: grid_dsl_size if >=0 else normalized source length."""
    # ponytail: grid_dsl_size from gate result preferred; fallback = source len
    src = Path(candidate_path).read_text(encoding="utf-8")
    # strip comments + blank lines for a cheap normalized size
    lines = [l for l in src.splitlines() if l.strip() and not l.strip().startswith("#")]
    return len("\n".join(lines))


def _gate_candidates(project_dir: Path, candidate_paths: list[str]) -> list[dict]:
    """Run batch_gate on all candidates; returns gate rows list parallel to candidate_paths."""
    if not candidate_paths:
        return []
    results = batch_gate(str(project_dir), candidate_paths, episodes=("visible", "holdout"))
    return results


def _partition_too_fine(shard_patches: list[dict]) -> bool:
    """Detect shared t-condition keys or similar guard tokens across shard patches.

    Heuristic: if >=2 patches contain the same literal `if t ==` guard value,
    a single unified mechanism is likely better than separate specialists.
    """
    t_guards: list[set[str]] = []
    for sp in shard_patches:
        path = sp.get("candidate_path")
        if not path or not Path(path).exists():
            continue
        src = Path(path).read_text(encoding="utf-8")
        guards = set(re.findall(r"if\s+t\s*==\s*(\d+)", src))
        if guards:
            t_guards.append(guards)

    if len(t_guards) < 2:
        return False

    # shared guard: intersection of any two patches
    for i in range(len(t_guards)):
        for j in range(i + 1, len(t_guards)):
            if t_guards[i] & t_guards[j]:
                return True
    return False


def _append_refuted_mechanism(project_dir: Path, mechanism: str, gate_receipt: dict) -> None:
    """Append a candidate (NOT credited) refuted-mechanism bookkeeping row to nogoods.

    This is bookkeeping only — INVESTIGATED credit stays leaf-authored.
    The row is marked provenance.source="gate_refuted_candidate" to distinguish
    it from investigated_science_turn rows.
    """
    ws = project_dir / "workspace"
    ws.mkdir(parents=True, exist_ok=True)
    ng_path = ws / "spec_visible_nogoods.jsonl"
    row = {
        "schema": "spec_visible_nogood_v1",
        "ts": time.strftime("%Y%m%dT%H%M%S"),
        "eliminated_hypothesis": mechanism,
        "refuted_by_gate": {
            "visible_exact": gate_receipt.get("visible_exact"),
            "holdout_depth": gate_receipt.get("holdout_depth"),
            "load_error": gate_receipt.get("load_error"),
        },
        "provenance": {
            "source": "gate_refuted_candidate",
            "note": "bookkeeping only — not INVESTIGATED-credited; leaf must emit control receipt for credit",
        },
    }
    with ng_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row) + "\n")


def _append_form_error_receipt(project_dir: Path, shard_result: dict, gate_receipt: dict) -> None:
    """Append a form-error receipt row to spec_visible_nogoods.jsonl.

    Bug-2: load/parse failures are form errors, NOT mechanism refutations.
    These rows have kind='form_error' and provenance.source='form_error'
    so build_frontier ignores them (it only reads 'investigated_science_turn').
    """
    ws = project_dir / "workspace"
    ws.mkdir(parents=True, exist_ok=True)
    ng_path = ws / "spec_visible_nogoods.jsonl"
    row = {
        "schema": "spec_visible_nogood_v1",
        "kind": "form_error",
        "ts": time.strftime("%Y%m%dT%H%M%S"),
        "class_id": shard_result.get("class_id"),
        "candidate_path": shard_result.get("candidate_path"),
        "detail": gate_receipt.get("load_error"),
        "provenance": {
            "source": "form_error",
            "note": "load/parse failure — not a mechanism refutation; gate never ran",
        },
    }
    with ng_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row) + "\n")


def _unification_briefing(shard_results: list[dict], project_dir: Path) -> str:
    """Build a unification briefing from all shards' theses and patches."""
    patch_base = _patch_base_directive(project_dir)
    contract_prompt = worldmodel_typed_payload_contract_prompt(None)
    summaries = []
    for sr in shard_results:
        cid = sr.get("class_id", "?")
        thesis = sr.get("thesis", "(no thesis)")
        summaries.append(f"### Shard {cid}\n{thesis}\n")
    body = "\n".join(summaries)
    return textwrap.dedent(f"""\
        # Unification Specialist Briefing

        ## PATCH_BASE Directive
        {patch_base}

        ## Objective
        Propose a SINGLE mechanism that explains and fixes ALL of the following
        residual classes.  The unified patch must not regress any non-shard cells.
        It wins only if it subsumes >=2 shard patches at lower MDL.

        ## Per-Shard Theses
        Group these theses by the mathematical idea each uses, not by wording —
        two theses phrased differently that predict the same transitions are ONE
        family, and a unification that merely renames one of them is not a
        unification.
        {body}

        ## DISCOVERY EVIDENCE AUTHORITY (read carefully — this changes what you may use)
        This dispatch runs under run_role=DISCOVERY. Per the CEGIS membrane
        (arc_agi_3_system.md: "Discovery may stage holdout-like slices as
        consumable counterexamples; evaluation keeps them sealed"), the holdout
        episode staged in this pack (raw/episodes, second episode) is LAWFUL
        counterexample evidence for law inference. You MAY condition your
        mechanism on its transitions. You may NOT claim clean transfer from it:
        any transfer claim will be evaluated on a FRESH sealed slice you have
        never seen. A law that merely memorizes those rows will die there —
        prefer the general mechanism that EXPLAINS them.

        ## INVESTIGATED Option
        If no single mechanism explains all classes, leave test_model_py empty
        and emit an INVESTIGATED control receipt naming the eliminated
        unification hypothesis with its witnesses.

        ## Output Contract
        {contract_prompt}
    """)


# ── Main entry point ───────────────────────────────────────────────────────


def run_specialists(
    project_dir: str | Path,
    *,
    dry_run: bool = False,
    by_cells: bool = False,
) -> dict:
    """Partition + dispatch + select + record.

    Returns the full receipt dict (also written to workspace/residual_specialists.jsonl).
    """
    project_dir = Path(project_dir)
    ws = project_dir / "workspace"
    ws.mkdir(parents=True, exist_ok=True)
    receipts_path = ws / "work_plan_attestations.jsonl"

    # ponytail: env ZTARE_SPECIALIST_MAX_SHARDS wins; if unset, compute from receipts
    if os.environ.get("ZTARE_SPECIALIST_MAX_SHARDS") is None:
        alloc = allocate_width(project_dir)
        _max_shards = alloc["shards"]
        import logging as _logging
        _logging.getLogger(__name__).info(
            "width_allocator: %s", alloc["rationale"]
        )
    else:
        _max_shards = None  # build_shards reads the env var itself

    shards = build_shards(project_dir, max_shards=_max_shards, by_cells=by_cells)
    mode = _specialist_mode()
    briefings = {s["class_id"]: specialist_briefing(s, project_dir, mode=mode) for s in shards}

    if dry_run:
        return {
            "dry_run": True,
            "shards": [
                {
                    "class_id": s["class_id"],
                    "yield_bits": s["yield_bits"],
                    "n_witnesses": len(s.get("witness_rows") or []),
                    "briefing_preview": briefings[s["class_id"]][:200],
                    "mechanism_family": s.get("mechanism_family"),
                    "lane": s.get("lane"),
                }
                for s in shards
            ],
            "briefings": briefings,
        }

    items = [
        {"shard": s, "briefing": briefings[s["class_id"]], "project_dir": str(project_dir)}
        for s in shards
    ]

    plan = partition(items, _specialist_worker, merge={"kind": "collect"})
    shard_results: list[dict] = run(plan, receipts_path=str(receipts_path))

    # Gate all produced candidates
    candidate_paths = [r["candidate_path"] for r in shard_results if r.get("candidate_path")]
    gate_rows = _gate_candidates(project_dir, candidate_paths) if candidate_paths else []
    # batch_gate keys result rows by "candidate" (maiden-run bug: joined on
    # a nonexistent "candidate_path" key → every gate_result was None)
    gate_by_path = {str(r.get("candidate", "")): r for r in gate_rows}

    # Bug-2: champion baseline, cached once per run (for genuine refutation check)
    champion_baseline: dict | None = None
    champ_path = project_dir / "test_model.py"
    if champ_path.exists() and candidate_paths:
        try:
            champ_gate_rows = _gate_candidates(project_dir, [str(champ_path.resolve())])
            champion_baseline = champ_gate_rows[0] if champ_gate_rows else None
        except Exception:  # noqa: BLE001
            champion_baseline = None

    # Attach gate results + MDL; categorize errors correctly
    for sr in shard_results:
        cp = sr.get("candidate_path")
        if cp:
            gr = gate_by_path.get(cp)
            sr["gate_result"] = gr
            if gr and not gr.get("load_error"):
                dsl = gr.get("grid_dsl_size", -1)
                sr["mdl"] = dsl if (isinstance(dsl, int) and dsl >= 0) else _mdl(cp)
                # Bug-2: genuine mechanism refutation only when candidate loads
                # AND performs no better than champion baseline
                mech = sr.get("mechanism")
                if mech and champion_baseline and not champion_baseline.get("load_error"):
                    cand_depth = gr.get("holdout_depth", -1)
                    champ_depth = champion_baseline.get("holdout_depth", -1)
                    cand_exact = gr.get("visible_exact", -1)
                    champ_exact = champion_baseline.get("visible_exact", -1)
                    is_worse = (cand_depth < champ_depth) or (cand_depth == champ_depth and cand_exact <= champ_exact)
                    if is_worse:
                        _append_refuted_mechanism(project_dir, mech, gr)
            else:
                sr["mdl"] = None
                # Bug-2: load_error → form_error receipt only; NEVER mechanism refutation
                if gr and gr.get("load_error"):
                    _append_form_error_receipt(project_dir, sr, gr)

    # Partition-too-fine detection
    ptf = _partition_too_fine(shard_results)

    # Selection: best non-regressor per shard (no promotion)
    selection: list[dict] = []
    for sr in shard_results:
        entry: dict = {
            "class_id": sr["class_id"],
            "selected": False,
            "reason": "",
            "mechanism": sr.get("mechanism"),
            "discriminator": sr.get("discriminator"),
        }
        if sr.get("investigated"):
            entry["reason"] = "INVESTIGATED"
        elif sr.get("control_only"):
            entry["reason"] = f"control_only: {sr.get('parse_error') or 'no patch produced'}"
        elif sr.get("candidate_path") and sr.get("gate_result"):
            gr = sr["gate_result"]
            if gr.get("load_error"):
                # Bug-2: form error in receipt, not a mechanism refutation
                entry["kind"] = "form_error"
                entry["reason"] = f"gate load error: {gr['load_error']}"
                entry["detail"] = gr["load_error"]
            else:
                entry["selected"] = True
                entry["candidate_path"] = sr["candidate_path"]
                entry["mdl"] = sr.get("mdl")
                entry["gate_summary"] = {
                    "visible_exact": gr.get("visible_exact"),
                    "visible_total": gr.get("visible_total"),
                    "holdout_depth": gr.get("holdout_depth"),
                }
                entry["reason"] = "gated"
        else:
            entry["reason"] = "no candidate produced"
        selection.append(entry)

    # Unification lane (if not partition_too_fine and >=2 patches)
    unification_result: dict = {"attempted": False}
    productive = [sr for sr in shard_results if sr.get("candidate_path")]
    if not ptf and len(productive) >= 2:
        unification_result["attempted"] = True
        uni_briefing = _unification_briefing(shard_results, project_dir)
        try:
            uni_dispatch = dispatch_model(
                uni_briefing,
                capability="agent",
                agent_id="residual_specialist_unifier",
                timeout_seconds=600,
                agent_execution_mode="sealed_completion",
                repo=str(project_dir),
            )
            uni_text = uni_dispatch.text or ""
            if uni_text.strip():
                uni_payload = parse_worldmodel_typed_payload_text(uni_text)
                uni_code = (uni_payload.get("test_model_py") or "").strip()
                if uni_code and uni_code != "INVESTIGATED":
                    sub_dir = ws / "submissions"
                    sub_dir.mkdir(parents=True, exist_ok=True)
                    uni_path = sub_dir / "specialist_unification_0.py"
                    uni_path.write_text(uni_code, encoding="utf-8")
                    uni_gate = _gate_candidates(project_dir, [str(uni_path)])
                    uni_gr = uni_gate[0] if uni_gate else {}
                    uni_mdl = _mdl(str(uni_path))
                    if uni_gr.get("grid_dsl_size", -1) >= 0:
                        uni_mdl = uni_gr["grid_dsl_size"]

                    shard_mdls = [sr.get("mdl") for sr in productive if sr.get("mdl") is not None]
                    avg_shard_mdl = sum(shard_mdls) / len(shard_mdls) if shard_mdls else None
                    subsumes = len(productive) >= 2
                    wins = (
                        not uni_gr.get("load_error")
                        and subsumes
                        and (avg_shard_mdl is None or uni_mdl < avg_shard_mdl)
                    )
                    unification_result.update({
                        "candidate_path": str(uni_path),
                        "mdl": uni_mdl,
                        "gate_result": uni_gr,
                        "wins": wins,
                        "outcome": "wins" if wins else "subsumed_but_higher_mdl",
                    })
                elif uni_code == "INVESTIGATED":
                    unification_result["outcome"] = "INVESTIGATED"
                else:
                    unification_result["outcome"] = "empty_response"
            else:
                unification_result["outcome"] = "empty_dispatch"
        except Exception as exc:  # noqa: BLE001
            unification_result["outcome"] = f"error: {exc}"

    # Build and write receipt
    receipt: dict = {
        "_schema": RECEIPT_SCHEMA,
        "timestamp": time.time(),
        "project": str(project_dir),
        "sharding_mode": "by_cells" if by_cells else "by_mechanism",
        "shards": [
            {
                "class_id": s["class_id"],
                "yield_bits": s["yield_bits"],
                "n_witnesses": len(s.get("witness_rows") or []),
                "probe_atoms": s.get("probe_atoms") or [],
                "mechanism_family": s.get("mechanism_family"),
                "lane": s.get("lane"),
            }
            for s in shards
        ],
        "dispatches": [
            {
                "class_id": sr["class_id"],
                "dispatch_ok": sr.get("dispatch_ok"),
                "dispatch_returncode": sr.get("dispatch_returncode"),
                "investigated": sr.get("investigated"),
                "control_only": sr.get("control_only"),
                "parse_error": sr.get("parse_error"),
                "candidate_path": sr.get("candidate_path"),
                "mdl": sr.get("mdl"),
                "mechanism": sr.get("mechanism"),
                "discriminator": sr.get("discriminator"),
                "mode": sr.get("mode", "sealed"),
                "preflight_receipts": sr.get("preflight_receipts", -1),
            }
            for sr in shard_results
        ],
        "gate_results": {
            sr["class_id"]: sr.get("gate_result")
            for sr in shard_results
            if sr.get("gate_result") is not None
        },
        "partition_too_fine": ptf,
        "unification_attempted": unification_result.get("attempted", False),
        "unification": unification_result,
        "selection": selection,
        "composition_deferred": ptf,
        "composition_deferred_reason": "partition_too_fine: unification required first" if ptf else None,
    }

    receipt_path = ws / "residual_specialists.jsonl"
    with receipt_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(receipt, default=str) + "\n")

    return receipt


# ── CLI ────────────────────────────────────────────────────────────────────


def _cli() -> None:
    p = argparse.ArgumentParser(description="Residual specialist driver")
    p.add_argument("--project", required=True, help="Path to project dir (e.g. projects/arc3_ls20_gov)")
    p.add_argument("--dry-run", action="store_true", help="Build shards + briefings, no dispatch")
    p.add_argument("--max-shards", type=int, default=None, help="Override ZTARE_SPECIALIST_MAX_SHARDS")
    p.add_argument("--by-cells", action="store_true", help="Legacy: shard by divergent-cell class instead of mechanism family")
    args = p.parse_args()

    project_dir = Path(args.project)
    if not project_dir.exists():
        # Try relative to repo root
        repo_root = Path(__file__).parents[4]
        alt = repo_root / args.project
        if alt.exists():
            project_dir = alt

    if args.max_shards is not None:
        os.environ["ZTARE_SPECIALIST_MAX_SHARDS"] = str(args.max_shards)

    result = run_specialists(project_dir, dry_run=args.dry_run, by_cells=args.by_cells)

    if args.dry_run:
        print(f"=== DRY RUN — {len(result['shards'])} shards ===")
        for s in result["shards"]:
            print(f"  class_id={s['class_id']}  yield_bits={s['yield_bits']:.3f}  witnesses={s['n_witnesses']}  lane={s.get('lane')}  mech={s.get('mechanism_family')}")
        for cid, briefing in result["briefings"].items():
            lines = briefing.splitlines()
            print(f"\n--- briefing class_id={cid} (first 40 lines) ---")
            for line in lines[:40]:
                print(line)
    else:
        print(f"=== residual_specialists done — {len(result['selection'])} shards ===")
        for sel in result["selection"]:
            flag = "SELECTED" if sel.get("selected") else "skip"
            print(f"  {flag}  class_id={sel['class_id']}  reason={sel['reason']}  mech={sel.get('mechanism')}")
        print(f"  partition_too_fine={result['partition_too_fine']}")
        print(f"  unification_attempted={result['unification_attempted']}")
        print(f"  sharding_mode={result['sharding_mode']}")


if __name__ == "__main__":
    _cli()
