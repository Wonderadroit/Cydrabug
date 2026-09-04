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
