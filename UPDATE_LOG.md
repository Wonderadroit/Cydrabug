# CYDRA UPDATE LOG

## 2026-09-05 — proot-runtime-mapping-repair

### Change
Corrected CYDRA's first supported PRoot-Distro runtime bootstrap after verification against the actual Termux/Ubuntu environment.

### Evidence
- The Termux home is bind-mounted inside Ubuntu at `/data/data/com.termux/files/home`.
- PRoot-Distro does not remap the shared Termux home to `/root`.
- The authorized ENS snapshot is therefore visible inside Ubuntu at its original absolute host-home path.
- The installed Ubuntu container is usable, but the initial container-list parser rejected its active `*` marker.

### Implementation
- `cydra/bootstrap.py` now preserves the absolute repository path for repositories under the shared home when constructing the `--shared-home` launch plan.
- The container-list parser strips PRoot-Distro's presentation-only active marker before comparing installed container names.
- `tests/test_bootstrap.py` adds regression coverage for the active marker and preserves the absolute shared-home mapping assertion.

### Safety semantics
The bootstrap layer still installs only explicitly requested CYDRA-owned base packages. It does not execute target-provided installation commands or silently install target-specific dependencies.

### Validation status
The user runtime independently verified that the ENS snapshot is visible from Ubuntu PRoot at the expected absolute mounted path and that its Git HEAD is `cda79acaad59711b943fc68207ebb3f1d0ff8596`. The corrected bootstrap code and regression test were written directly to `live-immunefi-work`; local execution of the updated tests remains to be performed in the user runtime.

### Next boundary
Run the corrected bootstrap/status and doctor paths. Then let CYDRA derive and report the ENS target environment requirements from the snapshot before any target-specific toolchain installation. Do not claim source/build verification until the required Node/pnpm environment and reproducible build receipt are established.

## 2026-09-05 — regression-boundary-repair

### Change
Repaired three regression mismatches exposed by the first full local test run after the ENS build-identity boundary.

### Repairs
- Updated the execution-observation regression to expect the stronger trusted-result mutation rejection. A trusted receipt that is modified after gateway trust is established must fail at the trust boundary before semantic observation-field validation.
- Corrected the Foundry reasoning fixture to use an evidence-backed `transition_expression` relationship, which is the current candidate-discovery input. A raw `writes` edge is not itself sufficient to manufacture an invariant candidate.
- Corrected Immunefi known-issue extraction so the parser binds the known-issue record to the acquired authoritative page that actually contains the known-issue material, preferring `resources/` when present, then `scope/`, then `information/`.

### Validation status
The first local run at the synchronized `96b9833` state reported 94 passed and 3 failed. These repairs address those three failures. The repaired branch has not yet been locally rerun, so the suite is **not claimed green** until the user runtime verifies it.

### Safety semantics
No verification boundary was weakened. Trusted-result immutability remains authoritative, candidate discovery remains conservative, and known-issue provenance now points to the actual acquired source resource instead of silently attributing evidence to the primary information page.

### Next boundary
Pull the repaired commits into the user Linux checkout, run the complete test suite, and only after a green result resume the ENS snapshot acquisition/build-identity workflow.

## 2026-09-05 — ens-build-identity-evidence

### Change
Closed the next M3 evidence sub-boundary by recording the build-relevant metadata actually observed in the public ENS contest snapshot, without claiming that a build has been executed or that the snapshot is cryptographically identical to the published audited Git object.

### Evidence
- The public contest snapshot at `cda79acaad59711b943fc68207ebb3f1d0ff8596` contains `package.json`, `pnpm-lock.yaml`, `pnpm-workspace.yaml`, and `.npmrc`.
- `package.json` declares `packageManager: pnpm@10.27.0` and the repo-wide `test:all` / scoped build and typecheck scripts.
- `pnpm-workspace.yaml` declares the workspace layout and package-resolution policy.
- `pnpm-lock.yaml` is present with lockfile version `9.0`.
- `.npmrc` declares `auto-install-peers=false` and `resolution-mode=highest`.
- Immunefi's current official resources page requires Node v22, pnpm v10, `pnpm install --frozen-lockfile`, and publishes audited revision `63772fd872af472ced58b009499355f3430c2a86`.

### Implementation
Added `cydra/ens_build_identity.py` with immutable evidence for the snapshot commit, declared origin, Node requirement, exact pnpm package-manager version, and observed blob SHAs for the build-defining root files.

Added `tests/test_ens_build_identity.py` covering preservation of the observed metadata and the fail-closed `BUILD_IDENTITY_UNRESOLVED` state.

### Safety semantics
The manifest is evidence about the declared contest snapshot and its build inputs. It does not assert successful dependency installation, a clean build, runtime compatibility, exact audited Git identity, or authorization to execute tests. `build_verified` therefore remains false until a clean, reproducible build is actually executed and its receipt is independently bound to this snapshot evidence.

### Validation status
The source files were written directly to `live-immunefi-work` as commits `6c33ccb8dc42bfc9a5914d633756c7fbe345dc2a` and `39d1c78c658b7ee70f338f083fd518d73395a82b`. GitHub Actions has not been verified for these commits, so CI is **not claimed green**.

### Next boundary
Acquire the complete snapshot into the user-controlled authorized runtime, verify the recorded file hashes against the checkout, run the official Node/pnpm setup with `pnpm install --frozen-lockfile`, capture the exact toolchain and clean-worktree identity, and establish a reproducible build receipt before projecting the source into the canonical SystemModel.

## 2026-09-05 — ens-snapshot-lineage-resolution

### Change
Closed the next M3 source-identity sub-boundary by recording the public ENS contest fork's explicit lineage declaration without falsely treating its Git object as identical to the Immunefi-published audited commit.

### Evidence
- Official Immunefi continues to publish audited revision `63772fd872af472ced58b009499355f3430c2a86` for the live ENS competition.
- Public repository `immunefi-team/audit-comp-ens` contains root/fork commit `cda79acaad59711b943fc68207ebb3f1d0ff8596` whose commit message explicitly states it is a fork of `ensdomains/apps-monorepo` at the published audited revision.
- The public fork's commit SHA is therefore a distinct Git object from the audited upstream SHA. The lineage declaration is evidence, not cryptographic equality and not build verification.
- Direct resolution of the audited SHA in the accessible public repository remains unavailable.

### Implementation
Added `cydra/ens_source_identity.py` with an immutable `ENSSourceLineage` record and explicit `DECLARED_SNAPSHOT_LINEAGE` status. The record preserves repository, audited revision, snapshot commit, declared origin, and declaration text while exposing `is_exact_git_identity == False` and `build_ready == False` for the current state.

Added regression tests proving the lineage is preserved while the audit/build gate remains closed.

### Safety semantics
A project-declared fork lineage may identify the intended source snapshot, but it does not silently promote that snapshot to exact audited Git identity or build-ready status. Active testing remains blocked until the source/build identity boundary is independently resolved.

### Validation status
The implementation and tests were written directly to `live-immunefi-work` as commits `5890d27b011db4ba3bd8edc6a9c4a71b64dddf32` and `461402d0a8196f74618ef88578d2ca5d62f81571`. GitHub Actions has not been verified for these commits, so CI is **not claimed green**.

### Next boundary
Obtain and verify the complete ENS snapshot/build at the declared lineage, including the lockfile and toolchain identity, then establish a reproducible build receipt before projecting source into the canonical SystemModel.

## 2026-09-05 — live-ens-intake-resource-graph-boundary

### Change
Continued the Bible-defined M1/M2 live-contest boundary by adding regression coverage for canonical ENS Immunefi acquisition and provenance-preserving resource dependency expansion.

### Added / verified
- Canonical Immunefi acquisition is exercised only through the ENS `information/`, `scope/`, and `resources/` pages.
- Non-Immunefi acquisition is rejected by the Immunefi adapter.
- Resource dependency expansion preserves project authority, parent-resource provenance, acquisition state, and unresolved scope rather than silently granting testing authority.
- The test uses the canonical ENS repository binding already defined by `cydra/ens_target.py` and does not promote an unresolved dependency to in-scope testing.

### Live context
The official Immunefi ENS Audit Competition page is currently live and continues to publish the audited revision `63772fd872af472ced58b009499355f3430c2a86`, Node v22, pnpm v10, and the scoped Manager app, Explorer app, Workers, transaction-manager, and smart-account areas. Current official pages remain the authority for active contest state.

### Validation status
The change was written directly to `live-immunefi-work` as commit `0a212311dc42faa1950016315d4e129ec1e2ec91`. GitHub Actions has not been verified for this commit, so CI is **not claimed green**.

### Next boundary
Acquire and verify the exact ENS repository at the published audited revision, establish reproducible build identity, and only then project the accepted source representation into the SystemModel. Do not begin active testing or downstream specialized-tool execution before the program/source authority gates are satisfied.

## 2026-09-05 — agent-operating-contract

Added `AGENTS.md` as the mandatory operational contract requiring every future CYDRA code change and recommendation to read and follow `CYDRA_PROJECT_BIBLE.md` first and prohibiting work outside the Bible's mission, boundaries, milestones, and doctrine.

Commit: `48e4c419dc0fa1f161bb742b8cb6df546237311d`.

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
