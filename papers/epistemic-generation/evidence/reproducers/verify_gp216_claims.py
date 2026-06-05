#!/usr/bin/env python3
"""Verify Paper 5b headline numbers from durable GP-216/GP-218 artifacts.

This does not reproduce the original LLM enumeration or clustering passes. The
original one-off generator scripts were referenced as /tmp/gp216_*.py and are no
longer present. This script verifies that the saved artifacts bundled with the
working paper still support the headline empirical claims.
"""
from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GP216 = ROOT / "gp216_queries"
GP218 = ROOT / "gp218_external_corpus"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def approx(actual: float, expected: float, tol: float = 0.05) -> None:
    if abs(actual - expected) > tol:
        raise AssertionError(f"expected {expected}, got {actual}")


def pct_from_cross_walk(path: Path) -> float:
    data = load_json(path)
    moves = data["moves"]
    hits = sum(1 for row in moves if row.get("match_level") in {"full", "partial"})
    return 100.0 * hits / len(moves)


def main() -> int:
    results: dict[str, object] = {}

    cross = load_json(GP216 / "gp216_cross_distribution_full.json")
    summary = cross["two_direction_summary"]
    tb_gap = summary["tb_vocab_on_tb_corpus"] - summary["tb_vocab_on_ps_corpus"]
    ps_gap = summary["ps_vocab_on_ps_corpus"] - summary["ps_vocab_on_tb_corpus"]
    avg_gap = (tb_gap + ps_gap) / 2
    approx(summary["tb_vocab_on_tb_corpus"], 58.1)
    approx(summary["tb_vocab_on_ps_corpus"], 20.7)
    approx(summary["ps_vocab_on_tb_corpus"], 19.116161616161616)
    approx(summary["ps_vocab_on_ps_corpus"], 65.89646464646465)
    approx(avg_gap, 42.1, 0.1)
    results["two_cultures_2x2"] = {
        "tb_vocab_on_tb": summary["tb_vocab_on_tb_corpus"],
        "tb_vocab_on_ps": summary["tb_vocab_on_ps_corpus"],
        "ps_vocab_on_tb": summary["ps_vocab_on_tb_corpus"],
        "ps_vocab_on_ps": summary["ps_vocab_on_ps_corpus"],
        "avg_own_corpus_gap_pp": round(avg_gap, 2),
    }

    neg = load_json(GP216 / "gp216_negative_control.json")
    approx(neg["gap_pp"], 3.039044289044284)
    results["negative_control"] = {"random_split_gap_pp": neg["gap_pp"]}

    comp = load_json(GP216 / "gp216_4op_compression.json")
    approx(comp["coverage_pct"], 62.874251497005986)
    approx(comp["tb_ps_gap_pp"], 23.28)
    results["four_op_compression"] = {
        "coverage_pct": comp["coverage_pct"],
        "tb_ps_gap_pp": comp["tb_ps_gap_pp"],
    }

    eight = load_json(GP216 / "gp216_pathA_8sf_cluster.json")
    assert eight["n_moves_input"] == 1214
    assert eight["n_shared_core"] == 6
    assert eight["n_broadly"] == 8
    assert eight["n_specific"] == 4
    results["eight_subfield_v5"] = {
        "n_moves": eight["n_moves_input"],
        "n_shared_core": eight["n_shared_core"],
        "n_broadly": eight["n_broadly"],
        "n_specific": eight["n_specific"],
    }

    business = load_json(GP216 / "gp216_business_held_out_OOD.json")
    approx(business["mean_shared_plus_broadly"], 57.878787878787875)
    results["business_ood"] = {
        "mean_shared_plus_broadly_pct": business["mean_shared_plus_broadly"],
    }

    sparse = load_json(GP216 / "gp216_sparse_coverage_OOD.json")
    approx(sparse["mean_shared_plus_broadly_pct"], 75.22435897435898)
    approx(sparse["mean_shared_plus_broadly_no_ctx_pct"], 83.65384615384616)
    results["sparse_2026_ood"] = {
        "mean_shared_plus_broadly_pct": sparse["mean_shared_plus_broadly_pct"],
        "mean_shared_plus_broadly_no_ctx_pct": sparse["mean_shared_plus_broadly_no_ctx_pct"],
    }

    gp218_ids = ["2605.01279", "2605.02654", "2605.02763", "2605.02793", "2605.02879"]
    coverages = [pct_from_cross_walk(GP218 / pid / "cross_walk.json") for pid in gp218_ids]
    mean_coverage = sum(coverages) / len(coverages)
    approx(mean_coverage, 56.5, 0.1)
    adversarial_pde = pct_from_cross_walk(GP218 / "2605.02879" / "cross_walk_adversarial.json")
    approx(adversarial_pde, 12.5, 0.1)
    results["gp218_blind_validation"] = {
        "mean_tagger_a_coverage_pct": mean_coverage,
        "pde_adversarial_coverage_pct": adversarial_pde,
    }

    print(json.dumps(results, indent=2, sort_keys=True))
    print("OK: headline GP-216/GP-218 claims verified from saved artifacts")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
