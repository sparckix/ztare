# Surgical Ansatz Candidates Worker 1

Most promising hypotheses for pre-Lean filtering:

1. `worker1_005` - defect-measure threshold-root self-tax
   - Core inequality: `int phi_root(B) dmu_def >= max(0, 1 - r^2 - 2*cross(B)*r^3) / r^4`.
   - Why it looks load-bearing: it targets the exact scalar root defect required by `QuarticSurvivalThresholdRootAmplitudeSource` while keeping the defect source separate from the Lean projection machinery.
   - Fast falsifier: look for generated Lipschitz blocks where the normalized defect measure on the predeclared root observable is zero or escaping while the required quartic allowance is positive.

2. `worker1_007` - same-observable normalized amplitude
   - Core inequality: `survivalProfit(B) <= gamma(B) * |<C_B,v_B>|^2/(||C_B||^2*||v_B||^2)`.
   - Why it looks load-bearing: it attacks the provenance gap around `QuarticSurvivalAmplitudeObservableSource`, especially the requirement that `ampSq`, survival profit, and the gain bound use the same predeclared charged observable.
   - Fast falsifier: reject if the observable has to be selected per block after payoff scoring, or if the gain bound silently uses a different observable than the declared amplitude square.

3. `worker1_009` - phase mismatch charged into quartic defect
   - Core inequality: `survivalDefect(B,r) >= 1 + c0*(theta(B) - C1*L_low(B)/(nu*N(B)^2))_+^2`.
   - Why it looks load-bearing: it links the Track B generated Lipschitz phase block to the quartic root defect without using the refuted naive `dt >= C` latency floor.
   - Fast falsifier: construct or mine a generated block where phase rotates through pressure/gauge transport with negligible `L_low/(nu*N^2)` cost and no matching defect surplus.
