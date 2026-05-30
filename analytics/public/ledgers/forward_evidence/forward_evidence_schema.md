# Forward-Evidence Ledger Schema (`forward_evidence_ledger.jsonl`)

**v35 (2026-05-15).** Forward-only, append-only JSON Lines. One research-move
per line. This ledger exists to stop the failure that killed the GP-225
solver line: **mixing proof closure / consequence exposure / gap isolation /
killed claims into one mushy "success" vocabulary.** Every row MUST declare
a strict `target_kind` and carry independent ratification, exactly like the
catch ledger's SOX §1220 discipline.

**Forward-only invariant:** do NOT backfill historical rows. Backfilling
pre-v35 work would re-introduce the mushy vocabulary and is the precise
laundering this ledger prevents. The ledger starts with the v34 governance
audit as its first honest (pending-ratification) row and accrues only
*forward* moves from 2026-05-15 on.

## Fields (all required)

| Field | Type | Notes |
|---|---|---|
| `row_id` | string | `FE-YYYY-MM-DD-NN` |
| `claim` | string | One sentence. The specific thing asserted. |
| `target_kind` | string | **Strict enum** — see below. The anti-mush field. |
| `source_artifact` | string | Repo-relative path the move operated on (must exist on disk). |
| `attempt_trace` | string | Repo-relative path to the trace/run/diff (must exist) or `"none"` if pure analysis. |
| `result` | string | **Strict enum**: `achieved` / `not_achieved` / `partial` / `inconclusive`. |
| `evidence_pointer` | string | Repo-relative path to the artifact proving `result` (must exist). |
| `anti_pattern_audit` | string | Which anti-pattern(s) were checked + outcome, or `clean`. Must name AP ids if any fired. |
| `author_agent` | string | Stable agent id or `human:operator`. |
| `ratifier_identity` | string | An independent ratifier distinct from `author_agent` (see "Independent ratification without an external human" below). `pending` only with `status: pending_ratification`. |
| `status` | string | **Strict enum**: `pending_ratification` / `ratified` / `retired`. |
| `created_at` | string | ISO 8601. |
| `ratification_evidence` | object | Required when `status: ratified`. `{mode, providers[], steelman_first, n_independent, operator_inversion, scope}`. |

### Independent ratification without an external human (2026-05-16)

No external human ratifier is available (operator has no such connections).
Independence is therefore satisfied by the mechanism ANTI-PATTERN-014's gate
already specifies — **steelman-first + (≥2 independent adversaries OR operator
inversion-reflex)** — with these guards so it is genuine independence, not
self-review:

- **`mode: xpanel`** — a cross-provider panel (reuse `closure_claim_discipline_linter_tier3.py` `PROVIDERS`). Every provider in `providers[]` MUST differ from the provider/model of `author_agent` (distinct weights = genuine independence, no shared context).
- **`steelman_first: true`** — the panel argues the strongest case FOR the claim before adversarial review (RC-B guard: attack-only single adversary is a noisy diagnostic, not a ratifier).
- **`n_independent >= 2`** providers, OR **`operator_inversion: true`** (the operator's inversion-reflex — the human check that needs no external connection; it is what caught the pessimism and the parser bug this thread).
- **`scope`** (RC-A guard): `xpanel` ratifies **artifact discipline + reproducibility ONLY** — encoding is clean, evidence replays, target_kind is honest, no anti-pattern fired. It does **not** certify mathematical IDEA validity. For a `proof_closure` whose truth depends on deep mathematics, `scope` must be `discipline_and_reproducibility` and the row additionally requires `operator_inversion: true`; absent that it stays `pending_ratification` for the idea even if discipline-ratified. Never let an `xpanel` verdict be read as idea-truth (that is ANTI-PATTERN-014 verdict_scope_conflation).

`ratifier_identity` for this mode = `xpanel:<provider-a>+<provider-b>[+operator_inversion]`.
The independence rule (`author_agent != ratifier_identity`) still holds by
construction. This is weaker than a domain-expert human for idea-truth and
the `scope` field states exactly that — honest, not laundered.

### `target_kind` strict enum (the load-bearing discipline)

- `proof_closure` — a goal/obligation is *fully discharged* (Lean-checked or textbook-cited end to end). The ONLY kind that may claim "closed".
- `consequence_exposure` — a consequence of an assumption was made explicit. **Not** proof progress.
- `gap_isolation` — a missing analytic atom was named/localized. **Not** closure.
- `falsifier` — a bad bridge/route was killed with a counterexample or failed-search trace.
- `route_reduction` — a target was reduced to a smaller/known subgoal. **Not** closure of the original.
- `apparatus_audit` — a governance/reliability finding about the apparatus itself (e.g. v34).

Conflating these is the documented cause of the GP-225 mushy-success
collapse. A `consequence_exposure` / `gap_isolation` / `route_reduction`
row claiming `result: achieved` is **not** a closure and must never be
counted as one. Only `target_kind: proof_closure` + `result: achieved` +
`status: ratified` (independent ratifier) is a real closure.

## Validator

`scripts/public/validators/validate_forward_evidence.py` — exit 1 on any
violation. Enforces enums, independence (`author_agent != ratifier_identity`),
path existence, and the `pending` ↔ `pending_ratification` coupling.
Mirrors `validate_catch_ledger.py`.
