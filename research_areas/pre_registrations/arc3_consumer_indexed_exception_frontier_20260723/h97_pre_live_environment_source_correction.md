# H97 pre-live environment-source correction

Date: 2026-08-04

Applies to:
`H-GPSA-CAUSAL-RESPONSE-DERIVATIVE-20260803-97`

Frozen experiment:
`8f9ae209831786c58ec83cea87e54a33caba821d0f0096d56cee7ba43210a4a6`

## Evidence state before this correction

The only live invocation received `credit_balance_exhausted` before the
Responses API created a model response. It produced no controller proposal,
eligible parent, branch revision, environment observation, or ARC action.
The H97 success criterion remains unobserved.

An injected-client settlement test then exposed that `_restore_prefix`
constructed the SDK's default `Arcade()` object. Default `NORMAL` mode
contacts the ARC service for an anonymous key and game discovery even when
gameplay subsequently uses the local engine. That concealed service bootstrap
inside each matched-arm restoration and prevented a network-independent
settlement test.

## Correction

Bind every H97 arm to the H96 environment identity already present in the
repository cache:

- game version: `ls20-9607627b`;
- environment code SHA-256:
  `298c810da2850d557c95d92a2cbd846df29a45d7134e20888617bedf5dafcd92`;
- metadata SHA-256:
  `2b93037f5584cdfa6c67418e2cce888f739ec9ea17f9efced45f2b4fedc8e175`;
- SDK operation mode: `OFFLINE`;
- seed: `0`.

The runner must fail closed if the cached files, their hashes, the H96 game
version, or the SDK operation mode drift. It may construct a fresh local game
instance for each arm only through this source. Tests may inject a
deterministic adapter factory, and the resulting settlement must identify that
source as test-owned rather than external evidence.

Before this correction, a direct offline replay of the seven frozen actions
`[2, 2, 2, 0, 0, 0, 1]` reproduced the registered endpoint exactly:
expected and observed observation SHA-256 were both
`82e380095fe14a67f08a83d0fe7440877b83537d8ef72b6e58704c4d206175cf`.

This correction makes the environment owner explicit. It does not change the
response derivative, intervention bytes, exact-parent fork, pair order,
primitive-action budget, outcome metric, success threshold, or claim
boundary.
