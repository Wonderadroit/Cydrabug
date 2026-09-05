# CYDRA UPDATE LOG

## 2026-09-05 — ens-source-observation-experiment

### Change
Added a narrow ENS experiment harness that measures compiler-backed TypeScript source reconstruction over the frozen source inventory.

### Boundary
`ENS source inventory + acquired source text → TypeScript compiler observations → explicit module relationships → canonical SystemModel`

### Why
The next research-critical question is empirical: whether the TypeScript provider can turn the 1,746-file ENS inventory into a useful, provenance-preserving model. More architecture work without this measurement would not establish research capability.

### Implementation
- Added `cydra/ens_source_experiment.py`.
- Reads the existing `.cydra/ens-source-files.txt` inventory and acquired source files.
- Runs the existing compiler-backed TypeScript provider once and projects that exact observation set into the canonical SystemModel.
- Reports deterministic measurement categories: supplied files, observations by kind, resolved/unresolved imports and exports, internal relationships, external resolutions, node/edge counts, and compiler version.
- Added a regression test using a mocked provider so metric semantics can be checked without requiring the ENS dependency tree in CI.

### Safety semantics
This harness performs source reconstruction measurement only. It does not establish exact audited-source identity, grant testing authority, or perform active vulnerability testing.

### Live-contest exercise
The experiment is designed specifically for the ENS Audit Competition source inventory and its current TypeScript reconstruction boundary.

### Validation status
Implementation and regression test are committed on `live-immunefi-work`. Actual ENS runtime measurement must be performed in the user's correctly configured PRoot target environment before claiming observation or relationship coverage.

## 2026-09-05 — typescript-module-resolution

### Change
Extended the TypeScript compiler-backed source observer with compiler-driven import/export resolution.

### Boundary
`TypeScript AST + project compiler options → resolved module observations → SourceObservation → canonical SystemModel`

### Why
Flat declarations are insufficient for system reconstruction. CYDRA needs trustworthy relationships between source files/modules before reasoning about data flow, trust boundaries, or security hypotheses.

### Implementation
- The observer discovers the target project's `tsconfig.json` when available and uses its compiler options.
- Import/export module specifiers are resolved through TypeScript's module resolver rather than lexical path guessing.
- Each import/export observation records `RESOLVED` or `UNRESOLVED` plus the resolved file path when available.
- The observer keeps supplied acquired source text authoritative for files being analyzed; target filesystem reads are limited to dependency/config resolution required by the compiler.

### Safety semantics
An unresolved module is preserved as unresolved. CYDRA does not infer a relationship from a matching filename or import string when the compiler cannot resolve it.

### Live-contest exercise
ENS is the first real TypeScript system-model exercise. This boundary will expose whether the 1,746-file source inventory can become a useful dependency graph using the project's own compiler semantics.

### Validation status
Code is committed on `live-immunefi-work`. Runtime execution against the ENS snapshot is still required before claiming resolution coverage or graph completeness. ENS exact audited-source identity remains unresolved, so this remains reconstruction work only.

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