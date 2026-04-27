# GP-126 — The Sky Survey: Point the Telescope

**Status:** OPEN — execution phase
**Opened:** 2026-04-22
**Category:** Apparatus / Engine / Discovery
**Trigger:** Panel unanimous: "Stop polishing the instrument. Point it at the sky."

## The Mandate

ZTARE is feature-complete for 1D compression. Every experiment so
far recovered KNOWN results. Zero new findings. The engine needs to
be tested on problems where the answer is UNKNOWN.

## Survey Targets (ranked by discovery potential)

### Tier 1: Millennium-Adjacent (highest impact if discovered)

1. **Stieltjes constants with a·r^k template** — recover r ≈ 1/(2π)
   from the normalized constants. If r deviates from 1/(2π), that's
   genuinely new. Substrate exists: projects/stieltjes_power_sums

2. **3-point zero correlation** — compute R₃(x,y) of Riemann zeros
   and compress. Deviation from GUE prediction = new mathematics.
   Need: compute from 2000 zeros we already have.

3. **BSD conjecture substrate** — rank of elliptic curves vs conductor.
   Data available from LMFDB. Compressible structure in rank distribution
   would be a genuine contribution.

### Tier 2: OEIS with Unknown Asymptotics (medium impact)

4. **A003418** — lcm(1..n)/e^n. Conjectured form unknown beyond
   leading term. ZTARE might find subleading corrections.

5. **A005101** — abundant number density. Growth rate debated.
   Erdős-type problem with bounties.

6. **A002182** — highly composite number growth. Connected to
   Robin's inequality. Asymptotic form has known leading term but
   unknown corrections.

7. **A000041 beyond Hardy-Ramanujan** — partition function at scales
   where the Rademacher correction becomes relevant. ZTARE already
   recovered H-R; can it find the next term?

### Tier 3: Physics/Cross-Domain (practical value)

8. **Turbulence scaling exponents** — Kolmogorov's -5/3 is the
   leading term. Intermittency corrections (She-Leveque model)
   are debated. Public data from turbulence databases.

9. **Critical exponents in 3D Ising model** — known to ~6 digits
   from conformal bootstrap. Can ZTARE recover from Monte Carlo data?

10. **Neural training dynamics** — the GP-124 Pythia experiment.
    Cancellation ratio trajectory during from-scratch training.
    Nobody has measured this.

### Tier 4: Operator Backend Targets (when ready)

11. **Berry-Keating with confining potential** — GP-125, deferred
    per panel. Backend built and tested. Activate when survey
    reveals a problem requiring eigenvalue matching.

## Protocol

For each target:
1. Acquire data (LMFDB, OEIS, public databases)
2. Set up as cold-start ZTARE substrate (GP-072 protocol)
3. Run `make discover` with 8 iterations
4. Log result: COMPRESSED (new finding) or UNDERIDENTIFIED (null)
5. If COMPRESSED: validate against literature. If novel → paper.
6. If UNDERIDENTIFIED: log as honest null. Move to next target.

## Success Metric

Hit rate = (substrates with genuinely new compression) / (total substrates)

If hit rate > 0: ZTARE is a discovery engine.
If hit rate = 0: ZTARE is a calibration/validation engine (still valuable, different product).

The number we need before justifying GP-125 or any further infrastructure.
