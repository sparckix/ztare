#!/usr/bin/env python3
"""Run a bounded Path-C canary replay from existing Lean drivers.

Each canary takes an old before-skip driver, patches candidate proof
bodies, runs Lean once per candidate, and records exact compiler output.
This is intentionally small: one row, a few candidates, no agent calls.
"""
from __future__ import annotations

import argparse
import json
import shlex
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[3]
DEFAULT_ROW_ID = "current_scale_0080"
DEFAULT_OUT = "/tmp/rung1/path_c_canary_current_scale_0080.json"
DEFAULT_SAVE_DIR = "/tmp/rung1/path_c_canary_drivers"

CANARIES: dict[str, dict[str, Any]] = {
    "current_scale_0126": {
        "source": (
            "ztare_proofs/.tmp_gp225_v1908_parallel_replay_bundle/"
            "non_pde_source_variety_shard/81_current_scale_0126_bayesRisk_lt_top_before_skip.lean"
        ),
        "theorem": "gp225_v1795_v1800_current_scale_0126",
        "marker": (
            "lemma gp225_v1795_v1800_current_scale_0126 [Nonempty 𝓨] (P : Kernel Θ 𝓧)\n"
            "    [IsFiniteKernel P] (π : Measure Θ) [IsFiniteMeasure π] {C : ℝ≥0} (hℓC : ∀ θ y, ℓ θ y ≤ C) :\n"
            "    bayesRisk ℓ P π < ∞ := by\n"
        ),
        "candidates": [
            {
                "name": "leansearch_hinge_then_finite_bound_simp",
                "body": (
                    "  refine (bayesRisk_le_mul' P π hℓC).trans_lt ?_\n"
                    "  simp [ENNReal.mul_lt_top_iff, P.bound_lt_top]\n"
                ),
            },
            {
                "name": "leansearch_hinge_then_finite_bound_simpa",
                "body": (
                    "  refine (bayesRisk_le_mul' P π hℓC).trans_lt ?_\n"
                    "  simpa [ENNReal.mul_lt_top_iff, P.bound_lt_top]\n"
                ),
            },
            {
                "name": "apply_lt_of_le_hinge",
                "body": (
                    "  apply lt_of_le_of_lt (bayesRisk_le_mul' P π hℓC)\n"
                    "  simpa [ENNReal.mul_lt_top_iff, P.bound_lt_top]\n"
                ),
            },
            {
                "name": "wrong_source_shape_negative",
                "body": (
                    "  refine (bayesRisk_le_mul P π hℓC).trans_lt ?_\n"
                    "  simp\n"
                ),
            },
        ],
    },
    "current_scale_0080": {
        "source": (
            "ztare_proofs/.tmp_gp225_v1908_parallel_replay_bundle/"
            "non_pde_source_variety_shard/54_current_scale_0080_sum_coord_apply_eq_one_before_skip.lean"
        ),
        "theorem": "gp225_v1795_v1800_current_scale_0080",
        "marker": (
            "theorem gp225_v1795_v1800_current_scale_0080 [Fintype ι] (q : P) : "
            "∑ i, b.coord i q = 1 := by\n"
        ),
        "candidates": [
            {
                "name": "v2063_rank1_hydrated_sum_simp",
                "body": (
                    "  have hq : q ∈ affineSpan k (range b) := by\n"
                    "    rw [b.tot]\n"
                    "  classical\n"
                    "  obtain ⟨w, hw, rfl⟩ := eq_affineCombination_of_mem_affineSpan_of_fintype hq\n"
                    "  simpa [b.coord_apply_combination_of_mem] using hw\n"
                ),
            },
            {
                "name": "hq_simpa_then_sum_simp",
                "body": (
                    "  have hq : q ∈ affineSpan k (range b) := by\n"
                    "    simpa [b.tot]\n"
                    "  classical\n"
                    "  obtain ⟨w, hw, rfl⟩ := eq_affineCombination_of_mem_affineSpan_of_fintype hq\n"
                    "  simpa [b.coord_apply_combination_of_mem] using hw\n"
                ),
            },
            {
                "name": "hq_rw_trivial_then_sum_congr",
                "body": (
                    "  have hq : q ∈ affineSpan k (range b) := by\n"
                    "    rw [b.tot]\n"
                    "    trivial\n"
                    "  classical\n"
                    "  obtain ⟨w, hw, rfl⟩ := eq_affineCombination_of_mem_affineSpan_of_fintype hq\n"
                    "  trans ∑ i, w i\n"
                    "  · exact Finset.sum_congr rfl (fun i hi => b.coord_apply_combination_of_mem (Finset.mem_univ i) hw)\n"
                    "  · exact hw\n"
                ),
            },
            {
                "name": "v2063_rank1_sum_congr",
                "body": (
                    "  have hq : q ∈ affineSpan k (range b) := by\n"
                    "    rw [b.tot]\n"
                    "  classical\n"
                    "  obtain ⟨w, hw, rfl⟩ := eq_affineCombination_of_mem_affineSpan_of_fintype hq\n"
                    "  trans ∑ i, w i\n"
                    "  · exact Finset.sum_congr rfl (fun i hi => b.coord_apply_combination_of_mem (Finset.mem_univ i) hw)\n"
                    "  · exact hw\n"
                ),
            },
            {
                "name": "gold_hq_only_control",
                "body": (
                    "  have hq : q ∈ affineSpan k (range b) := by\n"
                    "    rw [b.tot]\n"
                ),
            },
        ],
    },
    "current_scale_0225": {
        "source": (
            "ztare_proofs/.tmp_gp225_v1908_parallel_replay_bundle/"
            "non_pde_source_variety_shard/21_current_scale_0225_ofScalars_smul_before_skip.lean"
        ),
        "theorem": "gp225_v1795_v1800_current_scale_0225",
        "marker": (
            "theorem gp225_v1795_v1800_current_scale_0225 (x : 𝕜) : "
            "ofScalars E (x • c) = x • ofScalars E c := by\n"
        ),
        "candidates": [
            {
                "name": "unfold_funext_simp_smul",
                "body": (
                    "  unfold ofScalars\n"
                    "  funext n\n"
                    "  simp [Pi.smul_apply, smul_smul]\n"
                ),
            },
            {
                "name": "unfold_exact_funext_smul_smul",
                "body": (
                    "  unfold ofScalars\n"
                    "  exact funext fun n => "
                    "(smul_smul x (c n) (ContinuousMultilinearMap.mkPiAlgebraFin 𝕜 n E)).symm\n"
                ),
            },
            {
                "name": "ext_simp_ofScalars_smul",
                "body": (
                    "  ext n\n"
                    "  simp [ofScalars, Pi.smul_apply, smul_smul]\n"
                ),
            },
            {
                "name": "rw_control_negative",
                "body": (
                    "  unfold ofScalars\n"
                    "  funext n\n"
                    "  rw [Pi.smul_apply, Pi.smul_apply, smul_smul]\n"
                ),
            },
        ],
    },
    "current_scale_0092": {
        "source": (
            "ztare_proofs/.tmp_gp225_v1908_parallel_replay_bundle/"
            "non_pde_source_variety_shard/49_current_scale_0092_map_ext_before_skip.lean"
        ),
        "theorem": "gp225_v1795_v1800_current_scale_0092''",
        "marker": (
            "theorem gp225_v1795_v1800_current_scale_0092'' {f g : AdicCompletion I M →ₗ[R] N}\n"
            "    (h : f.comp (AdicCompletion.mk I M) = g.comp (AdicCompletion.mk I M)) :\n"
            "    f = g := by\n"
        ),
        "candidates": [
            {
                "name": "ext_induction_linearMap_ext",
                "body": (
                    "  ext x\n"
                    "  apply induction_on I M x\n"
                    "  intro a\n"
                    "  exact LinearMap.ext_iff.mp h a\n"
                ),
            },
            {
                "name": "ext_change_comp_apply",
                "body": (
                    "  ext x\n"
                    "  apply induction_on I M x\n"
                    "  intro a\n"
                    "  change (f.comp (AdicCompletion.mk I M)) a = (g.comp (AdicCompletion.mk I M)) a\n"
                    "  rw [h]\n"
                ),
            },
            {
                "name": "ext_direct_induction_lambda",
                "body": (
                    "  ext x\n"
                    "  apply induction_on I M x\n"
                    "  exact fun a => LinearMap.ext_iff.mp h a\n"
                ),
            },
            {
                "name": "bad_exact_negative",
                "body": (
                    "  ext x\n"
                    "  exact induction_on I M x (fun a => LinearMap.ext_iff.mp h a)\n"
                ),
            },
        ],
    },
    "current_scale_0132": {
        "source": (
            "ztare_proofs/.tmp_gp225_v1908_parallel_replay_bundle/"
            "non_pde_source_variety_shard/11_current_scale_0132_radius_smul_eq_before_skip.lean"
        ),
        "theorem": "gp225_v1795_v1800_current_scale_0132",
        "marker": (
            "theorem gp225_v1795_v1800_current_scale_0132 (p : FormalMultilinearSeries 𝕜 E F)\n"
            "    {𝕜' : Type*} {c : 𝕜'} [NormedDivisionRing 𝕜'] [Module 𝕜' F] [NormSMulClass 𝕜' F]\n"
            "    [SMulCommClass 𝕜 𝕜' F] (hc : c ≠ 0) :\n"
            "    (c • p).radius = p.radius := by\n"
        ),
        "prefix_replacements": [
            {
                "reason": "repair stale copied prefix proof of radius_le_smul before testing target theorem",
                "old": (
                    "theorem radius_le_smul {p : FormalMultilinearSeries 𝕜 E F} {𝕜' : Type*} {c : 𝕜'} [NormedRing 𝕜']\n"
                    "    [Module 𝕜' F] [SMulCommClass 𝕜 𝕜' F] [IsBoundedSMul 𝕜' F] :\n"
                    "    p.radius ≤ (c • p).radius := by\n"
                    "  simp only [radius, smul_apply]\n"
                    "  refine iSup_mono fun r ↦ iSup_mono' fun C ↦ ⟨‖c‖ * C, iSup_mono' fun h ↦ ?_⟩\n"
                    "  simp only [le_refl, exists_prop, and_true]\n"
                    "  intro n\n"
                    "  grw [norm_smul_le, mul_assoc, h]\n"
                ),
                "new": (
                    "theorem radius_le_smul {p : FormalMultilinearSeries 𝕜 E F} {𝕜' : Type*} {c : 𝕜'} [NormedRing 𝕜']\n"
                    "    [Module 𝕜' F] [SMulCommClass 𝕜 𝕜' F] [IsBoundedSMul 𝕜' F] :\n"
                    "    p.radius ≤ (c • p).radius := by\n"
                    "  simp only [radius, smul_apply]\n"
                    "  refine iSup_mono fun r ↦ iSup_mono' fun C ↦ ⟨‖c‖ * C, iSup_mono' fun h ↦ ?_⟩\n"
                    "  simp only [le_refl, exists_prop, and_true]\n"
                    "  intro n\n"
                    "  calc\n"
                    "    ‖c • p n‖ * ↑r ^ n ≤ (‖c‖ * ‖p n‖) * ↑r ^ n :=\n"
                    "      mul_le_mul_of_nonneg_right (norm_smul_le c (p n)) (by positivity)\n"
                    "    _ = ‖c‖ * (‖p n‖ * ↑r ^ n) := by ring\n"
                    "    _ ≤ ‖c‖ * C := mul_le_mul_of_nonneg_left (h n) (norm_nonneg c)\n"
                ),
            },
        ],
        "candidates": [
            {
                "name": "source_shape_apply",
                "body": (
                    "  apply eq_of_le_of_ge _ radius_le_smul\n"
                    "  exact radius_le_smul.trans_eq (congr_arg _ <| inv_smul_smul₀ hc p)\n"
                ),
            },
            {
                "name": "le_antisymm_source_shape",
                "body": (
                    "  refine le_antisymm ?_ radius_le_smul\n"
                    "  exact radius_le_smul.trans_eq (congr_arg _ <| inv_smul_smul₀ hc p)\n"
                ),
            },
            {
                "name": "exact_eq_of_le_of_ge",
                "body": (
                    "  exact eq_of_le_of_ge "
                    "(radius_le_smul.trans_eq (congr_arg _ <| inv_smul_smul₀ hc p)) radius_le_smul\n"
                ),
            },
            {
                "name": "ascii_identifier_negative",
                "body": (
                    "  apply eq_of_le_of_ge _ radius_le_smul\n"
                    "  exact radius_le_smul.trans_eq (congr_arg _ <| inv_smul_smul0 hc p)\n"
                ),
            },
        ],
    },
    "current_scale_0319": {
        "source": (
            "ztare_proofs/.tmp_gp225_v1908_parallel_replay_bundle/"
            "non_pde_source_variety_shard/101_current_scale_0319_equiv_of_X_eq_of_Y_eq_before_skip.lean"
        ),
        "theorem": "gp225_v1795_v1800_current_scale_0319",
        "marker": (
            "lemma gp225_v1795_v1800_current_scale_0319 {P Q : Fin 3 → F} (hPz : P z ≠ 0) (hQz : Q z ≠ 0)\n"
            "    (hx : P x * Q z ^ 2 = Q x * P z ^ 2) (hy : P y * Q z ^ 3 = Q y * P z ^ 3) : P ≈ Q := by\n"
        ),
        "candidates": [
            {
                "name": "source_simp_only_units",
                "body": (
                    "  use Units.mk0 _ hPz / Units.mk0 _ hQz\n"
                    "  simp only [Units.smul_def, smul_fin3, Units.val_div_eq_div_val, Units.val_mk0, div_pow, mul_comm,\n"
                    "    mul_div, ← hx, ← hy, mul_div_cancel_right₀ _ <| pow_ne_zero _ hQz, mul_div_cancel_right₀ _ hQz,\n"
                    "    fin3_def]\n"
                ),
            },
            {
                "name": "source_simpa_only_units",
                "body": (
                    "  use Units.mk0 _ hPz / Units.mk0 _ hQz\n"
                    "  simpa only [Units.smul_def, smul_fin3, Units.val_div_eq_div_val, Units.val_mk0, div_pow, mul_comm,\n"
                    "    mul_div, ← hx, ← hy, mul_div_cancel_right₀ _ <| pow_ne_zero _ hQz, mul_div_cancel_right₀ _ hQz,\n"
                    "    fin3_def]\n"
                ),
            },
            {
                "name": "broad_simp_negative",
                "body": (
                    "  use Units.mk0 _ hPz / Units.mk0 _ hQz\n"
                    "  simp [Units.smul_def, smul_fin3, div_pow, hx, hy, fin3_def]\n"
                ),
            },
            {
                "name": "constructor_route_negative",
                "body": (
                    "  exact equiv_iff_eq_of_Z_eq.mp ⟨hx, hy⟩\n"
                ),
            },
        ],
    },
}


def _candidate_bodies(row_id: str) -> list[dict[str, str]]:
    return list(CANARIES[row_id]["candidates"])


def _patch_source(row_id: str, source: str, marker: str, body: str) -> str:
    if marker not in source:
        raise SystemExit("canonical theorem marker not found")
    for repl in CANARIES.get(row_id, {}).get("prefix_replacements", []):
        old = str(repl["old"])
        if old not in source:
            raise SystemExit(f"prefix replacement not found: {repl.get('reason')}")
        source = source.replace(old, str(repl["new"]), 1)
    prefix = source.split(marker, 1)[0]
    return prefix + marker + body


def _target_line(text: str, marker: str) -> int:
    # Bind inside the theorem body, not on the declaration boundary.
    # The authoritative gate maps target_line to the surrounding decl;
    # using the boundary line can select the previous declaration when
    # spans abut exactly.
    return text.split(marker, 1)[0].count("\n") + 2


def _govern_driver(text: str, row_id: str, timeout: int) -> dict[str, Any]:
    import sys
    sys.path.insert(0, str(REPO))
    sys.path.insert(0, str(REPO / "scripts/public/control"))
    import authoritative_axioms as _AX
    import coherent_rung1 as cr
    from src.ztare.formal.lean_persistent import PersistentLean

    L = PersistentLean(cr.SB)
    L.start_tactic_proof("theorem _w : True := by sorry", timeout)
    try:
        return _AX.govern(
            L,
            text,
            _target_line(text, str(CANARIES[row_id]["marker"])),
            str(CANARIES[row_id]["theorem"]),
            timeout,
            persist=True,
        )
    finally:
        L.close()


def _direct_collect_axioms_audit(text: str, row_id: str, timeout: int) -> dict[str, Any]:
    import sys
    sys.path.insert(0, str(REPO / "scripts/public/control"))
    import authoritative_axioms as _AX

    injected, audit_line = _AX._inject_axiom_audit(text, str(CANARIES[row_id]["theorem"]))
    with tempfile.TemporaryDirectory(prefix="path_c_audit_") as td:
        audit_path = Path(td) / "Audit.lean"
        audit_path.write_text(injected)
        cmd = f"cd {shlex.quote(str(REPO / 'ztare_proofs'))} && lake env lean {shlex.quote(str(audit_path))}"
        try:
            proc = subprocess.run(
                ["bash", "-lc", cmd],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=timeout,
            )
            timed_out = False
        except subprocess.TimeoutExpired as exc:
            proc = exc
            timed_out = True
        stdout = getattr(proc, "stdout", "") or ""
        stderr = getattr(proc, "stderr", "") or ""
        text_out = stdout + "\n" + stderr
        rc = None if timed_out else int(getattr(proc, "returncode", 1))
        axioms_ok = "AXIOMS [propext, Classical.choice, Quot.sound]" in text_out
        return {
            "diagnostic_only": True,
            "method": "direct_lake_collectAxioms_same_injection",
            "returncode": rc,
            "timed_out": timed_out,
            "audit_line": audit_line,
            "clean_std_axioms_only": bool(rc == 0 and axioms_ok),
            "tail": text_out[-2000:],
        }


def run_canary(row_id: str, source_path: Path, out: Path, timeout: int = 90,
               save_dir: Path | None = None, govern_winners: bool = False) -> dict[str, Any]:
    if row_id not in CANARIES:
        raise SystemExit(f"unsupported row_id: {row_id}")
    source = source_path.read_text(errors="ignore")
    marker = str(CANARIES[row_id]["marker"])
    rows: list[dict[str, Any]] = []
    out.parent.mkdir(parents=True, exist_ok=True)
    if save_dir:
        save_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="path_c_canary_") as td:
        tmp_root = Path(td)
        for cand in _candidate_bodies(row_id):
            lean_path = tmp_root / f"{cand['name']}.lean"
            patched = _patch_source(row_id, source, marker, cand["body"])
            lean_path.write_text(patched)
            saved_path = None
            if save_dir:
                saved_path = save_dir / f"{row_id}_{cand['name']}.lean"
                saved_path.write_text(patched)
            cmd = f"cd {shlex.quote(str(REPO / 'ztare_proofs'))} && lake env lean {shlex.quote(str(lean_path))}"
            start = time.time()
            try:
                proc = subprocess.run(
                    ["bash", "-lc", cmd],
                    text=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=timeout,
                )
                timed_out = False
            except subprocess.TimeoutExpired as exc:
                proc = exc
                timed_out = True
            stdout = getattr(proc, "stdout", "") or ""
            stderr = getattr(proc, "stderr", "") or ""
            rc = None if timed_out else int(getattr(proc, "returncode", 1))
            row = {
                "candidate": cand["name"],
                "driver_path": str(saved_path) if saved_path else None,
                "returncode": rc,
                "timed_out": timed_out,
                "seconds": round(time.time() - start, 3),
                "closed": rc == 0 and not timed_out,
                "stdout_tail": stdout[-4000:],
                "stderr_tail": stderr[-4000:],
            }
            if govern_winners and row["closed"]:
                row["governance"] = _govern_driver(patched, row_id, timeout=max(timeout, 160))
                row["direct_collect_axioms_audit"] = _direct_collect_axioms_audit(
                    patched, row_id, timeout=max(timeout, 160)
                )
            rows.append(row)
    payload = {
        "schema": "path-c-canary-replay-v1",
        "row_id": row_id,
        "source_path": str(source_path),
        "timeout": timeout,
        "rows": rows,
        "closed_candidates": [r["candidate"] for r in rows if r["closed"]],
        "n_closed": sum(1 for r in rows if r["closed"]),
    }
    out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return payload


def _self_test() -> None:
    marker = str(CANARIES["current_scale_0080"]["marker"])
    sample = "prefix\n" + marker + "  skip\n"
    patched = _patch_source("current_scale_0080", sample, marker, "  trivial\n")
    assert "prefix" in patched
    assert "trivial" in patched
    assert "skip" not in patched
    assert len(_candidate_bodies("current_scale_0080")) >= 2
    assert len(_candidate_bodies("current_scale_0126")) >= 2
    assert len(_candidate_bodies("current_scale_0225")) >= 2
    assert len(_candidate_bodies("current_scale_0092")) >= 2
    assert len(_candidate_bodies("current_scale_0132")) >= 2
    assert len(_candidate_bodies("current_scale_0319")) >= 2
    print("path_c_canary_replay self-test PASS")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--row-id", choices=sorted(CANARIES), default=DEFAULT_ROW_ID)
    ap.add_argument("--source")
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--timeout", type=int, default=90)
    ap.add_argument("--save-dir", default=DEFAULT_SAVE_DIR)
    ap.add_argument("--govern-winners", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        _self_test()
        return
    row_id = args.row_id
    source = args.source or str(CANARIES[row_id]["source"])
    out = args.out
    if args.out == DEFAULT_OUT and row_id != DEFAULT_ROW_ID:
        out = f"/tmp/rung1/path_c_canary_{row_id}.json"
    payload = run_canary(row_id, REPO / source, Path(out), args.timeout,
                         Path(args.save_dir) if args.save_dir else None,
                         args.govern_winners)
    print(json.dumps({
        "out": out,
        "row_id": payload["row_id"],
        "n_closed": payload["n_closed"],
        "closed_candidates": payload["closed_candidates"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
