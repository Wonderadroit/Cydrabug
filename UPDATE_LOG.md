# CYDRA UPDATE LOG

## 2026-09-05 — ens-target-correction-and-intake-hardening

### Change
Corrected the experiment identity boundary to use the canonical ENS live-contest repository and audited revision from `cydra/ens_target.py` instead of the stale Vaults target.

### Hardened
- `cydra/experiment.py` now imports `DEFAULT_REPOSITORY` and `AUDITED_REVISION` from the canonical ENS target binding, preventing target drift between planning and the live contest.
- `cydra/program_intake.py` now binds the program-published known-issues record to the acquired authoritative program resource rather than constructing an unacquired resource identity.
- Added regression coverage for the corrected experiment target and known-issue provenance.

### Live status
The current official Immunefi listing identifies the ENS Audit Competition as live with a $70,000 total reward pool and an end date of 14 September 2026. The official resources page specifies audited revision `63772fd872af472ced58b009499355f3430c2a86`, Node v22, pnpm v10, and `pnpm install --frozen-lockfile`.

### Validation status
The changes were written directly to `live-immunefi-work`. GitHub Actions execution has not been verified for this commit, so CI is **not claimed green**.

### Next boundary
Acquire/verify the exact ENS repository at the published audited revision, establish reproducible build identity, then feed the accepted source representation into the existing SystemModel/evidence pipeline. Do not begin active testing until the live program contract and source identity are both resolved.

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
GitHub connector writes completed successfully on branch `recovery-receipt-evidence` in commits `71e07da7989797e3f64ed777c4aae87bdd394976`, `64ae67049b95d1086ad0c6bc0939c003badae8b0`, and the accompanying update-log commit. No GitHub Actions test workflow has been verified, so **CI is not claimed green**. The branch remains pending runtime test execution and review before merge.
