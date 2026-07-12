# AxiomPack GP-251 — residual-selection smoke, attempt 2 amendment

Recorded 2026-07-10 before attempt 2 and after attempt 1 terminated without a
run artifact.

Attempt 1 used eight model calls. It rejected one zero-residual pair, found a
different presentation with one positive-residual consequence, requested the
host's presentation preview, then returned `finish` because it mistook the
preview for a frozen finalist. The host rejected that transition. A later
prompt-replay check consumed one provider ledger unit despite dispatching no
model; the immutable attempt remains failed.

Attempt 2 is allowed only to test the two apparatus repairs:

1. the prompt now states that `select_theory_presentation` is preview-only and
   only `decision=freeze` creates a finalist;
2. a pre-dispatch failure with unchanged `call_count` consumes zero provider
   budget.

All scientific inputs and caps remain those in `campaign_residual.md` and
`experiment_contract_residual.md`: same frozen context, Codex gpt-5.5 low,
20-minute wall cap, zero metered API, navigation before any boundary work.

Success requires an explicit `freeze` of a positive-residual presentation or a
host-receipted `reject_all`. Another preview→finish confusion kills this
interface version. No result from attempt 1 is converted into a finalist.
