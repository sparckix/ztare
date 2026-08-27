# H97 pre-live amendment: exact Codex app-server subscription fork

Date: 2026-08-07

Status: pre-registered before app-server fork conformance testing or ARC contact;
controller-identity correction added after conformance and before H97 app-server
preflight or ARC contact

## Trigger

Three unchanged H97 live attempts reached the OpenAI Responses API and
returned `credit_balance_exhausted` before model response, controller proposal,
eligible parent, environment contact, or ARC action. Their evidence effect is
`none`. Repeating the same request cannot distinguish the H97 mechanism until
the project credit balance changes.

The installed Codex app-server exposes an official headless subscription
protocol with `thread/start`, `turn/start`, and `thread/fork`. A fork may be
bound to a completed `lastTurnId`; it copies stored history through that turn,
creates a distinct thread identity, and returns `forkedFromId`. This supplies
the experimental identity H97 needs: two continuations of one exact blind
parent without serial branch contamination.

## Controller-identity correction before live integration

Stage T established the fork protocol, but it also made one category boundary
inspectable: a Codex app-server thread is not the same controller object as a
stored Responses API continuation. The app-server contributes a distinct
stored-thread envelope and transports tool-result semantics through typed user
input plus a constrained JSON assistant message. Calling that difference
"transport only" would cross controller authority even when model, reasoning
effort, task state, experimental revisions, and external environment are held
fixed.

Therefore the three Responses-API attempts retain their original
`persistent_responses_reasoner` controller and experiment identity. The
subscription probe MUST compile a new manifest under
`persistent_codex_app_server_reasoner`, with a new controller hash, target
scope, live derivative, intervention revisions, and experiment hash. No
parent attempt, response id, branch, controller instance, or outcome from the
Responses lineage may enter the app-server lineage.

The following transport envelope is frozen before app-server H97 preflight:

- Responses input text becomes app-server `text`; Responses input images
  become app-server `image` inputs with the identical data URL;
- a Responses `function_call_output` becomes a canonical JSON protocol-event
  text envelope, because the app-server branch emitted no callable tool item;
- the `commit_arc_plan` parameter schema becomes the app-server turn's exact
  `outputSchema`; the returned assistant JSON is lowered to the same
  `ResponsesToolDecision` compatibility receipt used by the downstream H97
  proposal compiler;
- app-server thread id, turn id, exact fork receipt, prompt-envelope hash,
  assistant-output hash, and per-turn token use are recorded in addition to
  that compatibility receipt;
- every resumed rollout continues the recorded branch thread rather than
  assigning a turn id to a newly started thread.

This correction changes controller identity and apparatus identity. It does
not change the scientific contrast or allow cross-lineage pooling. It was
written before compiling the subscription manifest and before any app-server
ARC controller or environment contact.

## Frozen scientific contract

Within the newly compiled app-server controller lineage, this amendment does
not change:

- the H95 source response family or H97 causal derivative;
- task, context, choice set, action vocabulary, prefix, or proposal basin;
- model `gpt-5.6-sol`, reasoning effort `xhigh`, or structured output schema;
- the requirement that one blind parent proposal be completed before either
  causal or placebo revision is supplied;
- the causal and placebo revision bytes or their alternating order;
- admission timing, environment-action accounting, pair count, first stage,
  task/composite outcome rules, child-promotion rule, or kill conditions.

The Responses API fields `previous_response_id`, `store=true`, and
`reasoning.context=all_turns` are replaced by their Codex subscription
equivalent: one persisted parent thread followed by two
`thread/fork(lastTurnId=parent_turn_id)` operations. Both branches must inherit
the same stored history through the exact completed parent turn.

## Tool and environment seal

The app-server thread is started with:

- `model=gpt-5.6-sol` and no provider fallback;
- `sandbox=read-only`, `approvalPolicy=never`;
- `environments=[]` and `dynamicTools=[]`;
- structured JSON output schema on every controller turn;
- no web search, shell, MCP, or environment tool required by the controller;
- raw JSON-RPC request, response, notification, stderr, prompt, and parsed
  controller output persisted incrementally.

ARC environment contact remains owned by the existing H97 harness after a
controller action has passed the same eligibility and proposal checks.

## Stage T: transport conformance discriminator

Before ARC contact:

1. start one sealed Sol/xhigh thread;
2. complete one parent turn and record its exact thread id, turn id, prompt
   hash, assistant item, and output hash;
3. fork twice through that exact `lastTurnId`;
4. require distinct branch thread ids, identical `forkedFromId`, identical
   inherited turn prefix, and the same parent output hash;
5. run different opaque branch prompts and verify neither branch contains the
   sibling branch's prompt, turn id, or output;
6. require both branches to report the requested model/effort and complete
   without tools or filesystem/environment contact.

## Stage-T success criterion

Every identity and isolation check passes from persisted protocol receipts;
both branch outputs satisfy the frozen schema; the raw transcript is
resumable; tool count and environment-contact count are zero. Only then may
the H97 harness use this transport.

## Stage-T kill conditions

Kill the transport if the protocol cannot bind the fork to the completed
parent turn; if either branch has the parent rather than a distinct thread
identity; if `forkedFromId` differs; if inherited histories differ; if one
branch sees sibling-only input/output; if a developer-instruction override is
needed on the first forked turn; if the effective model or reasoning effort
drifts; if tools run; or if the transcript cannot be persisted per message.

## H97 live interpretation

A transport pass is apparatus evidence only. The H97 live result still
requires two matched causal/placebo pairs and external settlement under the
original scientific success criterion, evaluated wholly inside the new
controller lineage. Subscription transport does not itself support a response
child, compounding, ARC improvement, or capability takeoff.

## Source boundary

Protocol reference: OpenAI Codex app-server `thread/fork` documentation and
the installed generated JSON schema. The current Codex version is recorded by
the conformance receipt. A later protocol/version change requires a new
transport identity and conformance run.
