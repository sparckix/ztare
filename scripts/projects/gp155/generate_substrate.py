"""GP-155 substrate generator (run ONCE; OUT OF runtime PROJECT_DIR).

This script holds the ground-truth law for gp155 synthetic substrate.
It is intentionally located OUTSIDE projects/gp155_*/ so the mutator
cannot read it via runner_allowed_imports=["features"] or via
open("features.py").read() at runtime.

Re-run only when the substrate needs regenerating with a different seed
or row count. Output: projects/gp155_synthetic_dense_d_N_substrate/features.py
plus evidence_holdout.txt.
"""
import math, random

NOISE_SIGMA = 0.02
SMOOTHNESS = 0.5
SEED = 1729
D_VISIBLE = [2,3,4,5,6,7,8,10,12,14,16]
D_FARTHER = [18,20]
LOG10_N = [3,4,5,6,7,8,9,10]

def _sigmoid(x):
    if x>50: return 1.0
    if x<-50: return 0.0
    return 1.0/(1.0+math.exp(-x))

def alpha_truth(d, log10_N):
    """Ground-truth law: regime crossover between α=2/d (Sharma
    resolution-limited) and α=1 (Bahri variance-limited) via
    sigmoid blend at log10(N_crit(d)) = 0.5*d + 3, smoothness 0.5.
    """
    aR = 2.0 / d
    aV = 1.0
    blend = _sigmoid((0.5*d + 3.0 - log10_N) / SMOOTHNESS)
    return aV + (aR - aV) * blend

if __name__ == "__main__":
    print("Run-once generator. See module docstring.")