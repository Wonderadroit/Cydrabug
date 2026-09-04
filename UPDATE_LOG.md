# CYDRA UPDATE LOG

## 2026-09-04 — v2.0.0-live-contest

Established the live-contest development edition of CYDRA in `Wonderadroit/cydrabug` with the ENS Audit Competition as the first live integration target.

The contest is an integration target and reality test, not a vulnerability oracle. Historical findings and benchmarks remain learning/evaluation material only.

## 2026-09-04 — core-engine-migration

### Change
Migrated the first dependency-closed implementation slice from the historical `Wonderadroit/Cydra_` engine into the canonical `Wonderadroit/cydrabug` repository.

### Added
- ProgramContract and Immunefi intake primitives.
- Passive public Immunefi acquisition boundary.
- Fail-closed scope policy.
- Repository model and passive reconnaissance.
- Compiler-AST evidence primitive.
- Canonical SystemModel and source projection boundaries.
- Repository graph records.
- Build/toolchain identity primitives.
- Core migration regression tests.

### Important qualification
This is a deliberate migration/reconciliation, not a claim that every historical CYDRA module has already been copied. `program_intake.py` and `ast_dataflow.py` currently preserve the critical contracts and safety semantics but still have historical parity work remaining.

### Live target status
Current Immunefi material still identifies ENS as live and specifies the audited revision `63772fd872af472ced58b009499355f3430c2a86`, Node v22, pnpm v10, and the five scoped application/package areas.

### Next boundary
Close the live ENS chain: current pages → fresh ProgramContract → relevant resource graph → exact repository/revision → build identity → canonical SystemModel.

### Non-negotiable
No discovered dependency, repository, explorer, documentation page, or historical known issue becomes testing authorization merely through acquisition or semantic similarity.

## 2026-09-04 — invariant-reasoning-migration

### Change
Migrated the invariant representation and conservative candidate-generation boundary into `cydrabug`.

### Added
- Explicit invariant status (`asserted`, `inferred`, `unknown`, `contradicted`).
- Evidence-bound candidate and verification records.
- Explicit verification polarity (`supports`, `contradicts`, `neutral`).
- Candidate generation from evidence-backed SystemModel relationships.
- Precondition, assertion, transition-expression, state-dependency, cross-function consistency, and transition-obligation candidates.

### Safety property
Candidate generation describes implementation relationships; it does not label them as vulnerabilities. Confidence is preserved separately and cannot resolve an invariant or verification state by itself.

### Tests
Added `tests/test_invariants.py` covering evidence requirements, confidence/state separation, explicit verification polarity, and duplicate invariant rejection.

### Validation status
The new commits were inspected through the GitHub connector. No GitHub Actions workflow run was attached to the direct commit, so CI execution is **not claimed** yet. Local/Termux test execution remains the next validation step when the repository is available to the user runtime.

## 2026-09-04 — hypothesis-planner-execution-boundary

### Change
Reconciled persistent hypothesis state with planner observations, then migrated the execution identity, investigation authorization, external gateway, and lifecycle-audit boundary into the canonical repository.

### Added
- Immutable `ExecutionRequest` with canonical payload and deterministic digest.
- Planner `Observation` execution identity/request binding and generated opaque execution IDs.
- Live `InvestigationExecutionAuthorization` with investigation identity, authority fingerprint, lease generation, and explicit scope status.
- `ExternalExecutionGateway` with request persistence, authorization checks, gateway-owned adapter capability, lifecycle enforcement, exact result binding, durable receipt requirement, replay barriers, and recovery/reconciliation primitives.
- Independent execution lifecycle validator.
- Focused execution gateway regression tests.

### Critical safety semantics
An observation remains a plan, not permission. Persisted authority is never treated as a capability. External outcomes whose identity/digest cannot be proven are recorded as `OUTCOME_UNRECORDED`, not silently treated as ordinary failures or retried. Completion requires a durable result receipt.

### Validation status
GitHub connector writes completed successfully. No GitHub Actions test workflow has been verified for these direct commits, so **CI is not claimed green**. The next validation is to run the canonical test suite in the user runtime and repair any integration mismatches before adding the next execution/recovery layer.

## 2026-09-04 — fresh-process-execution-recovery

### Change
Implemented the next execution boundary: fresh-process recovery of an already-recorded external execution without re-running the adapter.

### Added
- `cydra/execution_recovery.py` with `ExecutionRecoveryService` and immutable `RecoveredExecution`.
- Exact execution ID, request digest, adapter, lifecycle-state, and durable receipt checks before rehydration.
- Adapter rehydration through the existing `ExternalExecutionGateway`; recovery never calls the external adapter's `execute` path.
- Regression coverage for exact receipt recovery, mismatched receipt rejection, and the no-re-execution property.
- Hardened `ExternalExecutionGateway` so one external adapter instance cannot be rebound to a second gateway and thereby cross its capability boundary.

### Safety semantics
Recovery is evidence-preserving reconstruction, not a new execution. A durable receipt must bind to the exact canonical request. `OUTCOME_UNRECORDED` may be rehydrated for later reconciliation, but no recovery path is allowed to silently retry external work.

### Validation status
The new files and gateway hardening were successfully written to `Wonderadroit/cydrabug` as commits `def12212ccb64a1cee9461c00227528dd6f2cfe6`, `351e217904777b96da6b10157c7e6cd03617129b`, and `293d5b760d4632d0bd3e5b31428916ff7693297c`. No GitHub Actions test workflow has been verified for these commits, so **CI is not claimed green**.

### Remaining integration boundary
The canonical repository still lacks the historical `ReasoningOrchestrator` and its complete evidence-ingestion dependencies. The next implementation step is therefore to reconcile a minimal canonical reasoning/evidence boundary around the recovered receipt, rather than importing the historical orchestrator wholesale.

## 2026-09-04 — receipt-evidence-hypothesis-replay-hardening

### Change
Closed the next reasoning integrity boundary between exact external receipts, semantic observation verification, and persistent hypothesis belief updates.

### Added / hardened
- `ExecutionEvidence` requires exact execution ID, canonical request digest, adapter identity, and independently recomputed receipt fingerprint.
- Receipt evidence enters the semantic layer with neutral polarity by default; receipt outcome names do not themselves imply support or contradiction.
- `ObservationVerificationBinding` requires an explicit outcome-to-role mapping for the exact two competing hypotheses.
- Non-neutral receipt evidence is rejected at the semantic boundary, preventing callers from smuggling conclusions through the receipt layer.
- Canonical invariant→hypothesis bridging now constructs the reconciled persistent/planner `Hypothesis` model rather than the obsolete planner-era constructor.
- `Hypothesis` now records consumed evidence IDs and rejects duplicate evidence within an update or evidence already applied to that hypothesis.
- Regression tests cover symmetric priors, canonical hypothesis identity, explicit semantic mapping, unknown outcomes, observation identity, and evidence replay.

### Safety semantics
Authenticity of an execution receipt proves what execution record was returned; it does not prove what that outcome means. Semantic polarity remains an explicit verification contract. Evidence consumption is also monotonic and replay-resistant, preventing the same observation receipt from silently increasing or decreasing belief multiple times.

### Validation status
GitHub Actions run `33898238966` on the preceding recovery branch completed successfully with 45 tests passing. The historical branch adds further changes after that run; its own CI result remains pending and is not claimed green yet.

## 2026-09-04 — blind-historical-evaluation-boundary

### Change
Started the isolated historical Immunefi evaluation using the completed Arbitration contest as a blind benchmark.

### Pinned target
- Repository: `immunefi-team/vaults`
- Revision: `49c1de26cda19c9e8a4aa311ba3b0dc864f34a25`
- Blind inputs: `README.md`, `foundry.toml`, `src/`

### Added
- `cydra/historical_evaluation.py` phase gate preventing oracle reveal before CYDRA output freeze.
- `cydra/historical_workspace.py` fail-closed allowlist materialization and deterministic input fingerprinting.
- `docs/HISTORICAL_IMMUNEFI_EVALUATION.md` defining the blind experiment and evaluation metrics.
- Compiler-AST-backed `cydra/solidity_model.py` projection for contract/function/state declarations and explicit state read/write/transition relationships.
- Regression tests for the Solidity projection and historical evaluation boundary.

### Safety semantics
Historical findings, reports, leaderboards, write-ups, and remediation knowledge remain outside the blind reasoning input. The Solidity adapter produces compiler-linked implementation evidence only; it does not create findings or security claims.

### Current status
The blind workspace and model boundary are implemented. The next step is to run the pinned target through Foundry build/AST production and feed the resulting evidence into invariant and hypothesis generation. Historical oracle material remains sealed until the complete CYDRA candidate output is frozen.

## 2026-09-04 — protocol-specific-build-identity-hardening

### Change
Hardened the build/toolchain boundary so compiler identity is treated as target-specific evidence rather than a generic local assumption.

### Added / changed
- Foundry detection now preserves an explicitly declared `solc_version`/`solc` value from `foundry.toml` when present.
- An unspecified compiler version remains `None` with explicit `compiler-unspecified` provenance instead of being guessed from the local environment.
- Build profiles preserve lock/config files as part of configuration identity.
- Successful Foundry builds now discover generated artifact files and parse available `build-info` compiler metadata, including `solcVersion` and `solcLongVersion`.
- Dependency-lock fingerprints are recorded separately from the general configuration fingerprint.
- Node and Foundry toolchain identity remain protocol/repository-specific; CYDRA does not assume Foundry for every target.
- Added regression tests for declared compiler versions, unknown compiler versions, configuration/lock fingerprints, and unavailable build tools.

### Safety semantics
A successful local command is not sufficient to establish compiler-backed semantic authority. The compiler/toolchain version, configuration, dependency state, exact revision, and generated artifacts must be bound to the target before those artifacts are treated as authoritative reasoning evidence. Missing compiler identity remains explicit uncertainty.

### Next boundary
Use the exact pinned Arbitration revision and its declared Foundry configuration to produce the compiler-backed build receipt and AST, then connect that evidence to conservative invariant candidate generation. Historical findings remain sealed until CYDRA's candidate and PoC output is frozen.

## 2026-09-04 — blind-evaluation-state-hardening

### Change
Hardened the historical benchmark state boundary before beginning the actual blind run.

### Fixed
- Historical evaluation phase transitions now use an explicit ordered lifecycle rather than lexicographic enum-string comparison.
- Transitions must advance exactly one phase at a time, preventing accidental jumps over required blind/freeze stages.
- Regression coverage now verifies that the oracle remains sealed through verification/freeze and that backward or multi-phase jumps are rejected.

### Safety semantics
The benchmark cannot legally reach `ORACLE_REVEALED` except immediately after `FROZEN`, and cannot reach `COMPARED` except immediately after oracle reveal. This keeps historical knowledge outside CYDRA reasoning until the candidate output is frozen.

### Validation status
Changes were written to `historical-immunefi-evaluation`; CI for the new commits has not yet been verified and is not claimed green.
