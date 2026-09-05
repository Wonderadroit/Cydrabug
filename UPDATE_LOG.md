# CYDRA UPDATE LOG

## 2026-09-05 — typescript-source-provider

### Change
Connected the language-neutral source observation boundary to a real TypeScript compiler-backed provider for the ENS live-contest exercise.

### Boundary
`TypeScript compiler API → SourceObservation → canonical SystemModel`

### Implementation
- Added `cydra/typescript_observer.cjs` as a small compiler-API observer using the target project's installed `typescript` package.
- Updated `cydra/typescript_provider.py` to pass acquired source text to the observer, normalize compiler observations, preserve source SHA-256 provenance, preserve scope state, and record compiler version/tool identity.
- The provider fails closed when the TypeScript compiler capability is unavailable or the observer returns malformed output.
- Added regression tests for compiler strength, tool/version metadata, source provenance, scope preservation, and unavailable-compiler behavior.

### Safety semantics
The adapter emits structural facts only. It does not infer authorization, vulnerabilities, security properties, or scope from names or lexical patterns. Missing compiler capability is an explicit provider failure rather than a downgrade to an untrusted semantic claim.

### Live-contest exercise
ENS TypeScript/TSX source is the first non-Python implementation exercising the same normalized observation contract. This validates the thesis that CYDRA needs one source-understanding interface, not one universal parser.

### Validation status
GitHub-side regression tests are committed. The provider still requires execution in the user's PRoot target environment with the acquired ENS dependency tree before any runtime capability claim is made. ENS exact audited-source identity remains unresolved; this change does not authorize active vulnerability investigation.

## 2026-09-05 — language-neutral-source-observation-boundary

### Change
Introduced the first explicit language-neutral source-ingestion contract for M4 system reconstruction.

### Boundary
`language/tool-specific provider → SourceObservation → canonical SystemModel`

### Implementation
- Added `cydra/source_provider.py` with `SourceProvider`, normalized `SourceObservationKind`, `ObservationStrength`, and provenance-bearing `SourceObservation`.
- The contract supports compiler-backed, specialized-tool, structural, lexical, and unresolved observation strength without equating any of them with a security conclusion.
- Added regression tests proving provider identity, tool metadata, scope state, provenance, and language-neutral observation kinds survive normalization.

### Safety semantics
The provider contract does not grant authorization, promote scope, or establish vulnerabilities. Observation strength remains explicit so a lexical or structural observation cannot silently become a compiler-backed semantic fact.

### Live-contest exercise
ENS is the first real integration target. Its TypeScript source will later exercise a TypeScript-native provider through this same contract, while existing Python and Solidity-specific ingestion paths remain adapters rather than being replaced by a universal parser.

### Validation status
The contract tests are committed; local full-suite execution in the user's PRoot runtime is the next validation step. ENS source/build identity remains unresolved, so this change does not authorize active vulnerability investigation.

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
