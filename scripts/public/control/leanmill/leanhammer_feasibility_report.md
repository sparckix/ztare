# LeanHammer provider — feasibility report

Status: **documented stub** (not a working integration). Wired into the LeanMill
provider registry as `leanhammer` with `tested: false`. The wrapper returns a
typed `provider_unavailable` result until LeanHammer is actually installed.

- Registry entry: `scripts/public/control/leanmill/provider_registry.py` → `REGISTRY["leanhammer"]`
- Wrapper: `scripts/public/lean/providers/leanhammer.sh`
- Upstream: arXiv:2506.07477 "Premise Selection for a Lean Hammer"; code at
  `github.com/hanwenzhu/premise-selection`. Reported ~33% one-shot proof rate on
  a Mathlib eval set when premise selection feeds the hammer.

## What LeanHammer actually is

LeanHammer is **not** a single self-contained binary like a tactic. It is a
three-part Lean-native pipeline:

1. **A premise-selection model** — a trained retrieval model that, given the
   current goal, ranks Mathlib declarations likely to be useful. This is the
   arXiv:2506.07477 contribution. It runs as a client that queries a model
   (served locally or via the authors' endpoint) and returns a ranked premise
   list. Weights/model must be fetched; it is not vendored in Mathlib.
2. **A `hammer` tactic** — the Lean-side tactic that collects the selected
   premises and hands them to an automated reasoning backend.
3. **A reconstruction backend** — `lean-auto` (translation to first-order/SMT)
   plus **Duper** (a superposition prover) to actually close the goal and
   produce a kernel-checkable Lean proof term. These are themselves Lake
   dependencies with their own toolchain pins.

So "running LeanHammer on a goal" requires: the goal to elaborate inside a Lake
project that has `Hammer` (and transitively `lean-auto` + `Duper`) as
dependencies, **and** a reachable premise-selection model.

## Can this run WITHOUT a heavy install? No.

Unlike the subscription LLM providers (`claude_opus`, `codex_gpt5`) which need
only a logged-in CLI, and unlike `native_hammer` (pure Mathlib tactics, zero
extra deps), LeanHammer requires real installation work in the Lake project:

- A `require` entry in `ztare_proofs/lakefile.toml` for the Hammer package
  (which pulls `lean-auto` + `Duper`), with versions compatible with the pinned
  toolchain. **Compatibility risk:** `ztare_proofs` is pinned to
  `leanprover/lean4:v4.30.0-rc2` / Mathlib `v4.30.0-rc2` (see
  `ztare_proofs/lean-toolchain` and `lakefile.toml`). LeanHammer / lean-auto /
  Duper publish against specific Lean toolchains; getting a mutually compatible
  set against an `-rc2` Mathlib is the main unknown and may force a toolchain
  bump or a separate side Lake project.
- A `lake update` + full `lake build` (compiling Duper + lean-auto is
  non-trivial; minutes-to-tens-of-minutes the first time).
- Fetching the premise-selection model (download, and/or standing up the model
  server the client talks to).

None of that is present today: `ztare_proofs/lakefile.toml` requires only
Mathlib, there is no model fetched, and `lean-auto`/`Duper` are absent. This is
the same class of barrier as `leancopilot` (also `tested: false`, "needs install
in ztare_proofs Lake project").

**Recommendation: stub now, install later.** A faked "it works" would be
dishonest and would pollute the proof-credit ledger. The stub returns a typed
`provider_unavailable` result and the registry carries `tested: false`, so the
router records `proof_nonempty: false` and falls through to other providers.

## How the stub conforms to the existing contract

The wrapper matches the `leancopilot.sh` shape exactly:

- `arg_shape: "goal_file"` — `invoke(name, goal_file=..., timeout_s=...)` calls
  `leanhammer.sh <goal_file>`.
- On the unavailable path it writes the diagnostic to **stderr** (not stdout)
  and exits 1, so the legacy bash-wrapper path in `invoke()` populates `error`
  and leaves `proof_text` empty → `proof_nonempty: false`. (Writing to stdout
  would have made the diagnostic look like proof text, since the legacy path's
  `proof_nonempty` does not consult the return code — a pre-existing quirk
  shared by `leancopilot`/`deepseek_v2`; the stub sidesteps it rather than
  changing shared semantics.)
- A guarded **live path** (gated behind `ZTARE_LEANHAMMER_INSTALLED=1`) mirrors
  `leancopilot.sh`: `cd ztare_proofs && lake env lean <goal_file>` and scrape the
  `Try this:` / hammer suggestion from elaboration output to stdout.

Goal-file convention (matches the IDE-incumbent providers): the `.lean` file
must elaborate inside `ztare_proofs` and end the target theorem with
`:= by hammer`.

Verified stub behavior:

```
$ printf 'theorem t : True := by hammer\n' > /tmp/lh_goal.lean
$ python3 scripts/public/control/leanmill/provider_registry.py \
    invoke --provider leanhammer --goal-file /tmp/lh_goal.lean
# -> returncode 1, proof_text "", proof_nonempty false, error carries
#    the provider_unavailable diagnostic.  CLI exits 1.
```

## Exact install steps (to flip `tested` to true later)

1. **Add the dependency** to `ztare_proofs/lakefile.toml`, picking a Hammer
   release compatible with the pinned toolchain (verify against upstream's
   `lean-toolchain` before committing — expect to reconcile versions):

   ```toml
   [[require]]
   name = "Hammer"
   git = "https://github.com/JOSHCLUNE/LeanHammer"   # or hanwenzhu/premise-selection per upstream README
   rev = "<tag compatible with lean4:v4.30.0-rc2 / mathlib v4.30.0-rc2>"
   ```

   This transitively pulls `lean-auto` and `Duper`. If no release matches the
   `-rc2` toolchain, stand up a side Lake project on a toolchain LeanHammer
   supports rather than bumping the main proofs project.

2. **Resolve + build** (first build compiles Duper + lean-auto; allow time):

   ```bash
   cd ztare_proofs && lake update && lake build
   ```

3. **Fetch / serve the premise-selection model** per the upstream README
   (download the trained retriever and/or start the model server the `hammer`
   client queries). Confirm the client can reach it.

4. **Add the import** so the tactic is in scope in goal files:
   `import Hammer` (exact module name per upstream) at the top of the `.lean`
   goal file passed to the wrapper.

5. **Smoke test** a known-closable goal:

   ```bash
   ZTARE_LEANHAMMER_INSTALLED=1 \
     scripts/public/lean/providers/leanhammer.sh /path/to/goal.lean
   ```

   Expect a `Try this:` / hammer suggestion on stdout and exit 0.

6. **Flip the registry**: set `tested: True` for `leanhammer` only after the
   smoke test passes end-to-end through `provider_registry.py invoke`, and after
   a closed proof survives the same governance + matched-negative-control receipt
   every other provider's output is held to before earning proof credit.

## Caveats / honesty notes

- The ~33% figure is the upstream paper's number on their eval set; it is **not**
  a measurement on the LeanMill / NS corpus. No proof credit until governed here.
- Toolchain compatibility against `-rc2` Mathlib is the real risk and may be the
  reason a live integration slips; that is a build problem, not a wiring problem.
  The registry wiring and contract conformance are done and verified now.
- Per repo policy, provider output is never a closure on its own — it requires
  the semantic premise shelf + matched-negative-control governance receipt
  (see the `credit_boundary` field on every invoke result).
