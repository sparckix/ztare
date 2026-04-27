---
id: GP-157
status: active
summary: GP-101 self-model for src/ztare/orchestrator/contract_table.py + protocols.py + render_evidence_template.py (Layer 1 typed-contract foundation)
---

# orchestrator/contract_table.py — architectural map

GP-157 v5.0 Layer 1 self-model. Per Task #67 panel synthesis: typed
ABI registry that becomes the single source of truth for substrate
contracts, replacing the 5-source-contradiction failure mode shipped
under prompt.py / contract_adherence.py / mutation_suite_guard.py.

## Region map

region: substrate_abi_enum  lines: 35-65  entry: class SubstrateABI(Enum)
region: contract_spec  lines: 68-110  entry: @dataclass(frozen=True)
region: scalar_skeleton  lines: 130-155  entry: _SCALAR_1D_SKELETON
region: feature_skeleton  lines: 157-180  entry: _FEATURE_DICT_SKELETON
region: contract_registry  lines: 185-240  entry: CONTRACT_REGISTRY
region: public_api  lines: 245-265  entry: def get_spec

## Function/method index

func: get_spec  sig: (abi: SubstrateABI) -> ContractSpec
func: get_spec_by_class  sig: (cage_meta_class: str) -> Optional[ContractSpec]
func: list_substrate_classes  sig: () -> tuple[str, ...]

## Companion arch maps

- `orchestrator_protocols_architectural_map.md` — runtime-checkable Protocols + adapt().
- `orchestrator_render_evidence_template_architectural_map.md` — evidence.txt §D rendering.

## Drift policy

Three files registered together as label `contract_table`. Edit any of
them → run `make arch-validate`. Adding a new SubstrateABI member is the
common case; that's an append at the enum + the table + the test
parameterization, no other files touched (until L70 wires the dispatch).

## Migration plan

L1 (this commit): additive primitives. No existing code paths replaced.
L2 (deferred per panel): canonicalizing AST normalizer.
L3 (deferred per telemetry): structured-output FIT_DECLARATION generalization.

After L70 (Phase 2 wire-in) lands, the legacy `enable_fit_primitive_*`
rubric-flag dispatch in autoresearch_loop dies — replaced by
`select_adapter(substrate).fit(declaration, evidence)`.
