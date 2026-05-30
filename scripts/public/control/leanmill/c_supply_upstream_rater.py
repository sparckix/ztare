#!/usr/bin/env python3
"""Upstream routing rater for LeanMill C-supply spend.

This is a routing/forecast artifact, not a governance gate. It scores which
family corpora/candidate rows look worth spending static/tool/template budget on
next. Proof credit still comes only from static sweeps, canary probes, negative
controls, and governance receipts.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import time
from pathlib import Path
from typing import Any

from leanmill_paths import DATA_DIR

DEFAULT_SELECTION = f"{DATA_DIR}/c_supply_batch_c_discriminating_slice.json"
DEFAULT_DEMAND = f"{DATA_DIR}/c_supply_demand_corpus_builder.json"
DEFAULT_POPULATION_ELO = f"{DATA_DIR}/leanmill_population_elo.json"
DEFAULT_OUT = f"{DATA_DIR}/c_supply_upstream_rater.json"
DEFAULT_PACKET_OUT = f"{DATA_DIR}/c_supply_upstream_rater_packet.json"
DEFAULT_PROMPT_OUT = f"{DATA_DIR}/c_supply_upstream_rater_prompt.txt"
DEFAULT_CODEX_OUT = "/tmp/rung1/leanmill_c_supply_upstream_rater_codex.json"
VALID_MODES = {"off", "observe_only", "advisory"}


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in [here.parent, *here.parents]:
        if (parent / "src").exists() and (parent / "analytics/public/leanmill").exists():
            return parent
    return Path.cwd()


REPO = _repo_root()


def _read_json(path: str | Path) -> Any:
    p = Path(path)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(errors="ignore"))
    except json.JSONDecodeError:
        return None


def _write_json(path: str | Path, obj: Any) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n")


def _read_rows(path: str | Path, limit: int = 6) -> list[dict[str, Any]]:
    obj = _read_json(path) or {}
    rows = obj.get("rows") if isinstance(obj, dict) else []
    out: list[dict[str, Any]] = []
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        out.append({
            "row_id": row.get("row_id") or row.get("id") or row.get("target_id"),
            "goal": str(row.get("goal") or row.get("target_statement") or row.get("statement") or "")[:600],
            "source_file": row.get("source_file") or row.get("sorried_file"),
        })
        if len(out) >= max(1, int(limit)):
            break
    return out


def _population_priors(path: str | Path) -> dict[str, dict[str, Any]]:
    obj = _read_json(path) or {}
    out: dict[str, dict[str, Any]] = {}
    for row in obj.get("ratings") or []:
        if not isinstance(row, dict):
            continue
        contestant = str(row.get("contestant") or "")
        if not contestant.startswith("family:"):
            continue
        family = contestant.split(":", 1)[1]
        if family:
            out[family] = {
                "contestant": contestant,
                "rating": row.get("rating"),
                "p_ucb_priority": row.get("p_ucb_priority"),
                "games": row.get("games"),
                "wins": row.get("wins"),
                "losses": row.get("losses"),
                "ties": row.get("ties"),
            }
    return out


def _float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _deterministic_score(candidate: dict[str, Any]) -> float:
    row_count = int(candidate.get("row_count") or 0)
    prior = candidate.get("population_elo_prior") if isinstance(candidate.get("population_elo_prior"), dict) else {}
    p_ucb = _float(prior.get("p_ucb_priority"), 1000.0)
    games = _float(prior.get("games"), 0.0)
    # Conservative routing score: enough rows to amortize a static sweep, plus
    # observed family signal. Cold families keep some exploration mass.
    cold_bonus = 8.0 if games <= 0 else 0.0
    return round((10.0 * row_count) + ((p_ucb - 1000.0) / 5.0) + cold_bonus, 3)


def build_packet(args: argparse.Namespace) -> dict[str, Any]:
    demand = _read_json(args.demand_corpus) or {}
    selection = _read_json(args.selection) or {}
    priors = _population_priors(args.population_elo)
    candidates: list[dict[str, Any]] = []
    for corpus in demand.get("corpora") or []:
        if not isinstance(corpus, dict) or str(corpus.get("status") or "") != "written" or not corpus.get("path"):
            continue
        family = str(corpus.get("family") or "")
        candidate = {
            "family": family,
            "row_count": int(corpus.get("row_count") or 0),
            "corpus_path": corpus.get("path"),
            "top_rows": corpus.get("top_rows") or [],
            "sample_rows": _read_rows(str(corpus.get("path")), limit=int(args.rows_per_family_sample)),
            "population_elo_prior": priors.get(family) or {},
        }
        candidate["deterministic_routing_score"] = _deterministic_score(candidate)
        candidates.append(candidate)
    candidates.sort(key=lambda c: (-_float(c.get("deterministic_routing_score")), str(c.get("family") or "")))
    if args.max_candidates > 0:
        candidates = candidates[: int(args.max_candidates)]
    return {
        "schema": "leanmill-c-supply-upstream-routing-rater-packet-v1",
        "created_at_epoch": int(time.time()),
        "selection": args.selection,
        "demand_corpus": args.demand_corpus,
        "population_elo": args.population_elo,
        "mode": args.mode,
        "credit_boundary": "routing_forecast_only_no_proof_credit",
        "selection_status": selection.get("status"),
        "credit_ready_count": selection.get("credit_ready_count"),
        "selected_count": selection.get("selected_count"),
        "demand_summary": {
            "source_family_count": demand.get("source_family_count"),
            "scanned_new_row_count": demand.get("scanned_new_row_count"),
            "corpora_written_count": demand.get("corpora_written_count"),
            "total_rows_written": demand.get("total_rows_written"),
            "min_signature_hits": demand.get("min_signature_hits"),
        },
        "candidate_count": len(candidates),
        "candidates": candidates,
        "forecast_question": "For each candidate family corpus, estimate probability that spending static sweep/template/probe budget yields a useful governed learning-unit exit within the current controller budget.",
    }


def build_prompt(packet: dict[str, Any]) -> str:
    compact = json.dumps(packet, indent=2, sort_keys=True)[:24000]
    return (
        "You are an upstream routing forecaster for LeanMill. You do not decide proof validity. "
        "You only estimate which candidate family corpora deserve next spend.\n\n"
        "Use the deterministic evidence, family names, sample rows, row counts, and population Elo prior. "
        "Reward candidates likely to become strict static failures plus reusable Path-C template/probe value. "
        "Penalize broad lexical matches, likely static-tool positives, target-not-executable risk, and overfit-looking families.\n\n"
        "Return strict JSON only with this schema:\n"
        "{\"schema\":\"leanmill-upstream-routing-rater-output-v1\","
        "\"ratings\":[{\"family\":\"...\",\"p_useful_exit\":0.0,\"p_static_strict_fail\":0.0,"
        "\"p_template_convertible\":0.0,\"spend_rank\":1,\"rationale\":\"short\","
        "\"main_risk\":\"short\"}],\"do_not_spend\":[{\"family\":\"...\",\"reason\":\"short\"}],"
        "\"calibration_note\":\"short\"}\n\n"
        f"Packet:\n{compact}\n"
    )


def _extract_json(text: str) -> dict[str, Any]:
    stripped = text.strip()
    if stripped.startswith("{"):
        try:
            obj = json.loads(stripped)
            return obj if isinstance(obj, dict) else {}
        except json.JSONDecodeError:
            pass
    start = stripped.find("{")
    end = stripped.rfind("}")
    if start >= 0 and end > start:
        try:
            obj = json.loads(stripped[start : end + 1])
            return obj if isinstance(obj, dict) else {}
        except json.JSONDecodeError:
            return {}
    return {}


def validate_model_output(obj: dict[str, Any], candidate_families: set[str]) -> dict[str, Any]:
    errors: list[str] = []
    if obj.get("schema") != "leanmill-upstream-routing-rater-output-v1":
        errors.append("bad_schema")
    ratings = obj.get("ratings")
    if not isinstance(ratings, list):
        errors.append("ratings_not_list")
        ratings = []
    seen: set[str] = set()
    for row in ratings:
        if not isinstance(row, dict):
            errors.append("rating_not_object")
            continue
        family = str(row.get("family") or "")
        if family not in candidate_families:
            errors.append(f"unknown_family:{family}")
        if family in seen:
            errors.append(f"duplicate_family:{family}")
        seen.add(family)
        for key in ("p_useful_exit", "p_static_strict_fail", "p_template_convertible"):
            val = _float(row.get(key), -1.0)
            if val < 0.0 or val > 1.0:
                errors.append(f"{family}:{key}_out_of_range")
        if int(_float(row.get("spend_rank"), 0.0)) <= 0:
            errors.append(f"{family}:bad_spend_rank")
    return {"ok": not errors, "errors": errors, "rating_count": len(ratings)}


def _model_order(model_obj: dict[str, Any]) -> dict[str, int]:
    order: dict[str, int] = {}
    for row in model_obj.get("ratings") or []:
        if not isinstance(row, dict):
            continue
        family = str(row.get("family") or "")
        rank = int(_float(row.get("spend_rank"), 10_000.0))
        if family:
            order[family] = min(order.get(family, 10_000), rank)
    return order


def run_codex(prompt: str, args: argparse.Namespace) -> dict[str, Any]:
    out_path = Path(args.codex_out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "codex", "exec", "--skip-git-repo-check", "-C", str(REPO), "-m", args.model,
        "-c", f'model_reasoning_effort="{args.reasoning_effort}"', "-s", "read-only", "-o", str(out_path), prompt,
    ]
    start = time.time()
    proc = subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=int(args.timeout_s))
    text = out_path.read_text(errors="ignore") if out_path.exists() else ""
    obj = _extract_json(text)
    return {
        "schema": "leanmill-upstream-routing-rater-codex-call-v1",
        "model": args.model,
        "returncode": proc.returncode,
        "seconds": round(time.time() - start, 3),
        "stdout_tail": proc.stdout[-2000:],
        "stderr_tail": proc.stderr[-2000:],
        "codex_out": str(out_path),
        "raw_tail": text[-4000:],
        "parsed": obj,
    }


def build(args: argparse.Namespace) -> dict[str, Any]:
    packet = build_packet(args)
    prompt = build_prompt(packet)
    if args.packet_out:
        _write_json(args.packet_out, packet)
    if args.prompt_out:
        Path(args.prompt_out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.prompt_out).write_text(prompt + "\n")
    candidate_families = {str(c.get("family") or "") for c in packet.get("candidates") or [] if str(c.get("family") or "")}
    model_call: dict[str, Any] | None = None
    model_validation = {"ok": False, "errors": ["model_not_run"], "rating_count": 0}
    model_obj: dict[str, Any] = {}
    if args.run_model and packet.get("candidate_count"):
        model_call = run_codex(prompt, args)
        model_obj = model_call.get("parsed") if isinstance(model_call.get("parsed"), dict) else {}
        model_validation = validate_model_output(model_obj, candidate_families)
    deterministic_order = {str(c.get("family") or ""): idx + 1 for idx, c in enumerate(packet.get("candidates") or [])}
    model_order = _model_order(model_obj) if model_validation.get("ok") else {}
    combined = []
    for cand in packet.get("candidates") or []:
        family = str(cand.get("family") or "")
        combined.append({
            "family": family,
            "deterministic_rank": deterministic_order.get(family, 10_000),
            "model_rank": model_order.get(family),
            "effective_rank": model_order.get(family, deterministic_order.get(family, 10_000)) if args.mode == "advisory" and model_validation.get("ok") else deterministic_order.get(family, 10_000),
            "row_count": cand.get("row_count"),
            "deterministic_routing_score": cand.get("deterministic_routing_score"),
            "corpus_path": cand.get("corpus_path"),
        })
    combined.sort(key=lambda row: (int(row.get("effective_rank") or 10_000), int(row.get("deterministic_rank") or 10_000), str(row.get("family") or "")))
    result = {
        "schema": "leanmill-c-supply-upstream-routing-rater-v1",
        "created_at_epoch": int(time.time()),
        "mode": args.mode,
        "model": args.model,
        "run_model": bool(args.run_model),
        "packet_out": args.packet_out,
        "prompt_out": args.prompt_out,
        "candidate_count": packet.get("candidate_count"),
        "model_validation": model_validation,
        "model_call": model_call,
        "model_output": model_obj,
        "ordered_families": [row["family"] for row in combined],
        "combined_ranking": combined,
        "credit_boundary": "routing_forecast_only_no_proof_credit",
        "calibration_join_key": {
            "selection": args.selection,
            "demand_corpus": args.demand_corpus,
        },
    }
    if args.out:
        _write_json(args.out, result)
    return result


def _self_test() -> int:
    import tempfile
    with tempfile.TemporaryDirectory(prefix="leanmill_upstream_rater_") as td:
        root = Path(td)
        corpus = root / "fam.json"
        corpus.write_text(json.dumps({"rows": [{"row_id": "r1", "goal": "Alpha Beta", "source_file": "x.lean"}]}) + "\n")
        demand = root / "demand.json"
        demand.write_text(json.dumps({"corpora": [{"family": "fam", "status": "written", "row_count": 1, "path": str(corpus), "top_rows": ["r1"]}], "corpora_written_count": 1, "total_rows_written": 1}) + "\n")
        elo = root / "elo.json"
        elo.write_text(json.dumps({"ratings": [{"contestant": "family:fam", "p_ucb_priority": 1040, "rating": 1010, "games": 2}]}) + "\n")
        out = build(argparse.Namespace(selection=str(root / "missing_sel.json"), demand_corpus=str(demand), population_elo=str(elo), mode="observe_only", model="gpt-5.4-mini", run_model=False, out=None, packet_out=None, prompt_out=None, codex_out=str(root / "codex.json"), timeout_s=1, reasoning_effort="low", max_candidates=20, rows_per_family_sample=3))
        assert out["candidate_count"] == 1, out
        assert out["ordered_families"] == ["fam"], out
        good = {"schema": "leanmill-upstream-routing-rater-output-v1", "ratings": [{"family": "fam", "p_useful_exit": 0.4, "p_static_strict_fail": 0.5, "p_template_convertible": 0.3, "spend_rank": 1, "rationale": "x", "main_risk": "y"}], "do_not_spend": [], "calibration_note": "z"}
        assert validate_model_output(good, {"fam"})["ok"]
        bad = {"schema": "leanmill-upstream-routing-rater-output-v1", "ratings": [{"family": "nope", "p_useful_exit": 2, "spend_rank": 0}]}
        assert not validate_model_output(bad, {"fam"})["ok"]
    print("leanmill_c_supply_upstream_rater self-test PASS")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selection", default=DEFAULT_SELECTION)
    ap.add_argument("--demand-corpus", default=DEFAULT_DEMAND)
    ap.add_argument("--population-elo", default=DEFAULT_POPULATION_ELO)
    ap.add_argument("--mode", choices=sorted(VALID_MODES), default="observe_only")
    ap.add_argument("--model", default="gpt-5.4-mini")
    ap.add_argument("--run-model", action="store_true")
    ap.add_argument("--reasoning-effort", default="low")
    ap.add_argument("--timeout-s", type=int, default=300)
    ap.add_argument("--max-candidates", type=int, default=24)
    ap.add_argument("--rows-per-family-sample", type=int, default=4)
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--packet-out", default=DEFAULT_PACKET_OUT)
    ap.add_argument("--prompt-out", default=DEFAULT_PROMPT_OUT)
    ap.add_argument("--codex-out", default=DEFAULT_CODEX_OUT)
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return _self_test()
    if args.mode == "off":
        _write_json(args.out, {"schema": "leanmill-c-supply-upstream-routing-rater-v1", "mode": "off", "candidate_count": 0, "ordered_families": [], "credit_boundary": "routing_forecast_only_no_proof_credit"})
        return 0
    result = build(args)
    print(json.dumps({"candidate_count": result["candidate_count"], "mode": result["mode"], "model_validation": result["model_validation"], "ordered_families": result["ordered_families"][:8], "out": args.out}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
