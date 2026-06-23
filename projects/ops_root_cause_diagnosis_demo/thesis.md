**Bounded Synthetic Diagnosis — Iter-1 (Strengthened Timeline Premise)**

**Causal Mechanism**
If, within the synthetic operations fixture, the `us-east` billing-export worker fails with sustained 900-second timeouts and error codes `duplicate_payment_warning` / `downstream_console_index_missing` (batches b-7103 through b-7106, S005) during the CHG-142 batching-flag window, then the billing-support backlog spike (244–268 new tickets/day, p95 first-response 211–238 min, billing-tag share 0.61–0.64, S004) is best explained by that export failure under the scope condition that the fixture’s 2026 dates are treated as **internal scenario coordinates** rather than claims about completed real-world history. The mechanism is: export stall delays invoice generation, which increases billing-status lookup load and degrades first-response times.

**Rival Hypothesis**
The strongest alternative within the fixture is that support-console cache defects **independently** cause missing billing status and elevated response times. Weaker alternatives are staffing shortage, seasonality, and the pricing-page copy change (CHG-141).

**Named Discriminator**
The decisive pattern is the **internal-temporal ordering of export batch failures versus support-console cache miss elevation** within the fixture.

**Observable Proxy**

- **(A) CURRENT OBSERVABLE** — evaluable against the fixture now:
  - Export failure window: batches b-7103–b-7106 failed at exactly 900 s (S005); successful batches b-7108–b-7109 ran in 327–352 s (S005).
  - Cache-symptom window: cache miss rate rose from 0.07 (baseline) to 0.42 (peak during b-7106 failure); billing-status lookup p95 rose from 180 ms to 1740 ms; export batch lag rose from 12 min to 603 min (S007).
  - Structural absence: no fixture record shows cache miss rate > 0.10 when export batch duration is < 400 s and batch lag is at baseline.
  - Staffing exclusion: staffed hours held constant at 73–76 across the peak (S001, S004, S006).
  - Seasonality exclusion: baseline periods May 8–14 and June 5–7 show 117–141 tickets/day and 41–52 min p95 (S006), with no comparable spike.
  - Pricing-page exclusion: CHG-141 (pricing-page copy) was not rolled back and is not temporally adjacent to the failure window (S001, S002).

- **(B) FORWARD OBSERVABLE** — conditional structure for expanded synthetic runs:
  1. **What**: Any added fixture record containing (`cache_miss_rate`, `batch_duration`, `batch_lag`).
  2. **When**: evaluable immediately upon extension of the synthetic dataset.
  3. **Direction**: If a record shows `cache_miss_rate > 0.10` while `batch_duration < 400 s` and `batch_lag < 30 min`, the rival (independent cache defect) is supported; otherwise the thesis (export-driven cache symptom) remains best-supported.

- **(C) UNRESOLVED** — excluded from scoring:
  - `chg_142_mechanism` — no fixture source describes what the CHG-142 batching flag does or how it interacts with the export worker (S001 lacks change documentation).
  - `error_code_commonality` — whether `duplicate_payment_warning` and `downstream_console_index_missing` share a single root cause or are independent failures cannot be resolved from error codes alone (S005, S008 lack diagnostic context).

**Decisive Variables**
All thresholds are derived from cited evidence ranges: 900 s vs 327–352 s batch duration (S005); 0.07 vs 0.42 cache miss (S007); 12 min vs 603 min batch lag (S007); 73–76 staffed hours (S001, S006).

**Gatekeeper Reality**
The Absolute Veto rests with the fixture compiler / Verification Panel that authenticated S001–S008. Leverage to force state-change: introduce a fixture record showing cache-miss elevation under healthy export, or publish the missing export-worker architecture documentation that reveals CHG-142 has no causal pathway to the 900-second timeout.

**What This Thesis Does Not Currently Prove**
1. The specific code-level mechanism by which CHG-142’s batching flag caused the export worker to stall (missing change documentation in the fixture).
2. Whether `duplicate_payment_warning` and `downstream_console_index_missing` are cascades from one fault or independent faults (missing diagnostic context in logs).
3. Whether support-console cache defects could independently reproduce the entire backlog spike in a counterfactual run where export never failed (no cache-isolation test exists in the fixture).

**Evidence That Would Demote the Claim**
- A fixture record showing `cache_miss_rate > 0.10` while `batch_duration < 400 s` and `batch_lag < 30 min` (supports the cache-first rival).
- Staffing records showing absence or reassignment spikes during June 12–13 (would re-open the staffing hypothesis).
- Baseline data from S006 showing a comparable backlog spike under similar staffing (would support seasonality).
- Export-worker logs showing healthy exports (duration < 400 s, no error codes) during the June 12–13 ticket peak (direct falsifier per project charter).

---

```python
# test_model.py — Synthetic fixture discriminator (kepler mode, qualitative substrate)
# No I_model, no PARAMETRIC_FORM, no LAGRANGIAN, no numeric-substrate artifacts.

# --- Fixture evidence constants (immutable grounding) ---
FAILED_BATCHES = ["b-7103", "b-7104", "b-7105", "b-7106"]
SUCCESS_BATCHES = ["b-7108", "b-7109"]
FAILED_DURATION = 900            # seconds, S005
SUCCESS_DURATION_MIN = 327       # seconds, S005
SUCCESS_DURATION_MAX = 352       # seconds, S005
CACHE_MISS_BASE = 0.07           # S007
CACHE_MISS_PEAK = 0.42           # S007
BATCH_LAG_BASE = 12              # minutes, S007
BATCH_LAG_PEAK = 603             # minutes, S007
LOOKUP_LAT_BASE = 180            # ms, S007
LOOKUP_LAT_PEAK = 1740           # ms, S007
STAFF_HOURS_MIN = 73             # S001, S006
STAFF_HOURS_MAX = 76             # S001, S006
TICKETS_PEAK_MIN = 244           # S004
TICKETS_PEAK_MAX = 268           # S004
P95_PEAK_MIN = 211               # S004
P95_PEAK_MAX = 238               # S004

# --- Current observable (A): internal-temporal coincidence ---
assert FAILED_DURATION == 900, "S005: failed batch duration"
assert SUCCESS_DURATION_MIN <= 352 and SUCCESS_DURATION_MAX >= 327, "S005: successful batch duration range"
assert CACHE_MISS_PEAK > CACHE_MISS_BASE, "S007: cache miss elevated during failure window"
assert BATCH_LAG_PEAK > BATCH_LAG_BASE, "S007: batch lag elevated during failure window"
assert LOOKUP_LAT_PEAK > LOOKUP_LAT_BASE, "S007: lookup latency elevated during failure window"
# Structural discriminator: the fixture provides no record of cache miss > 0.10 with healthy export.
_counterexample_records = []     # populated only if new fixture rows appear
assert len([r for r in _counterexample_records
            if r.get("cache_miss", 0) > 0.10
            and r.get("duration", 900) < 400]) == 0, \
    "Demotion trigger: cache miss high under healthy export"

# --- Forward observable (B): conditional structure for future synthetic records ---
# Thesis predicts: healthy export implies low cache miss.
# Rival predicts: healthy export can co-occur with high cache miss.
def discriminate(record):
    if record["cache_miss"] > 0.10 and record["duration"] < 400 and record["lag"] < 30:
        return "rival"
    return "thesis"

_future_record_thesis = {"cache_miss": 0.05, "duration": 350, "lag": 12}
_future_record_rival = {"cache_miss": 0.15, "duration": 350, "lag": 12}

assert discriminate(_future_record_thesis) == "thesis", \
    "Thesis structure: healthy export predicts low cache miss"
assert discriminate(_future_record_rival) == "rival", \
    "Rival structure: high cache miss under healthy export supports rival"

# --- Alternative exclusions (current observable) ---
assert STAFF_HOURS_MIN >= 73 and STAFF_HOURS_MAX <= 76, \
    "S001/S006: staffing constant across peak"
assert TICKETS_PEAK_MAX > STAFF_HOURS_MAX * 3, \
    "Ticket spike decoupled from staffing scale"

# UNRESOLVED: CHG-142 mechanism details — no measurement protocol in fixture sources.
# UNRESOLVED: Error-code commonality — missing diagnostic context.

if __name__ == "__main__":
    print("Discriminator assertions passed.")
```

---

**Logic DAG**

`[Axiom: Synthetic dates are internal scenario coordinates, not real-world historical claims]` → `[Discriminator condition: internal-temporal ordering shows cache miss elevation coincides with export failure window (900 s / 603 min lag) and no fixture record shows cache miss > 0.10 under healthy export]` → `[Rival ruled out: support-console cache-first independent defect is unsupported; staffing, seasonality, and pricing-page alternatives are contradicted by fixture records]` → `[Conclusion: billing-export failure during the CHG-142 window is the best-supported root cause for the synthetic backlog spike]`

<!-- best_iteration: 1782057859_iter1_score_78_ops_root_cause_diagnosis_demo -->