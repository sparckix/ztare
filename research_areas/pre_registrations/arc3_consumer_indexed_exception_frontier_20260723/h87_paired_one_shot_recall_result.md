# H87 paired one-shot recall result

H87 supports the narrow claim that the evidence-derived H86 memory bundle can
improve a fresh Sol controller's decisions on the same game. It does not yet
support cross-game transfer, individual-memory credit, or calibrated
per-context value prediction.

## Result

All six GPT-5.6 Sol `xhigh` arms:

- restored settled initial observation
  `e55a1c1775c34a88319adea39042846b6100c4c674bbfc809b9711334430e778`;
- used a fresh resumed runtime session;
- spent exactly 20 charged actions;
- retained distinct harness-controller, runtime-session, and trajectory
  identities within every pair.

The three inject arms received the H86 three-memory bundle on decision zero
only. The direct authorization was burned before inference and no later prompt
contained another injection. Controls received none.

| Pair | Order | Inject Level 1 | Control Level 1 | Task delta | Composite delta |
|---|---|---:|---:|---:|---:|
| 1 | inject, control | action 13 | action 20 | 0 | +0.07 |
| 2 | control, inject | action 15 | miss | +1 | +0.86 |
| 3 | inject, control | action 15 | action 15 | 0 | 0.00 |

The frozen criterion passed: inject had greater total task score (`3` versus
`2`) and won the composite decision score in two of three pairs. Mean observed
composite lift was `+0.31`, compared with the preregistered prediction `+0.20`.
The squared error of those two means was `0.0121`.

That aggregate hides large stratum variance. The three observed deltas were
`0.07, 0.86, 0.00`, giving per-pair prediction MSE `0.1642`. The circuit has a
positive same-game value signal; it does not yet predict which restored
controller context will benefit.

Mean unique-settled-observation yield delta was exactly `0.00`. Recall improved
task-directed use of a fixed amount of contact rather than increasing the
number of distinct visible outcomes. This separates task allocation from the
current observation-novelty proxy for information yield.

## Architectural settlement

H86's memory bridge was invalid because one scope represented acquisition and
consumption, then the digest persisted after the observation changed. H87
uses three objects:

1. immutable acquisition provenance: source episode, boundary observation,
   source controller instance, and supporting transition hashes;
2. a one-shot consumption decision: current observation, controller instance,
   sparse recall receipt, and compatibility-transport claim;
3. an experimental stratum: restored prefix and observation, controller
   class, choice set, action vocabulary, action budget, primitive cost, and
   sealed randomization identity.

Distinct stochastic controllers inhabit inject and control arms. The stratum,
not a shared controller instance, owns the comparison.

The intervention remains a bundle. Assigning the observed effect to any of its
three memories would be unsupported. The next discriminator should factor the
bundle—mechanic memory versus control-map memory, with a prompt-length-matched
placebo—and learn a state-triggered retrieval rule across new episodes before
testing another game.

## Evidence

- machine result: `h87_paired_one_shot_recall/result.json`
  (`ebbc2209ce1b684e804d7751236d7c1a236c4309362ce906580b14bd3f12228a`)
- frozen manifest: `h87_paired_one_shot_recall/manifest.json`
- arm receipts: `h87_paired_one_shot_recall/arms/`
- incremental turn checkpoints: `h87_paired_one_shot_recall/turns/`
- matched settlements: `h87_paired_one_shot_recall/settlements/`
