"""Live end-to-end validation of agentic_leaf.solve_leaf on a known-closable leaf (P1 d0).
Proves the PRODUCTIONIZED primitive's real dispatch+verify path (not just the mocked self-test)."""
import os, re, sys
sys.path.insert(0, "src")
from ztare.leanmill.solver.agentic_leaf import solve_leaf
from ztare.formal.lean_persistent import PersistentLean
from ztare.formal.substrate_liveness import calibrate

PROJ = "projects/atlas_lean_2026_05_29"
LAKE = os.path.expanduser("~/.elan/bin/lake")


def subcal():
    with PersistentLean(project_dir=PROJ) as pl:
        return calibrate(pl).to_dict()


def main():  # side effects in main() so the module imports cleanly (suite import-smoke)
    src = open("projects/gp_spectral_apn_seed_2026_05_28/candidates/hilbert_functions_2_sorried.lean").read()
    defs = src[:re.search(r"(?m)^\s*theorem\s+P2\b", src).start()]
    r = solve_leaf("pureOSequence GammaP1 0 = 1", defs=defs, project_dir=PROJ, repo=PROJ,
                   lake_bin=LAKE, probe_name="AgenticLeafProbe.lean", runtime="codex",
                   timeout=400, decompose=True, substrate_calibrate=subcal)
    print(f"\n[validate] closed={r.closed} inadmissible={r.inadmissible} rounds={r.rounds}")
    print(f"[validate] reason={r.reason}")
    print(f"[validate] calibration={r.calibration.get('provider',{}).get('live')},substrate_ok={'substrate' in r.calibration}")
    print("[validate] => agentic_leaf PRODUCTION PATH VERIFIED" if r.closed
          else "[validate] => not closed (check)")


if __name__ == "__main__":
    main()
