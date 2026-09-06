# CYDRA UPDATE LOG

## 2026-09-06 — resumable-continuity-checkpoint

### Change
Added a durable CYDRA handoff/checkpoint workflow so work can resume from the exact stopping point after chat loss, context limits, connector interruptions, or a new ChatGPT conversation.

### Boundary
`repository truth → continuity checkpoint → reproducible resume → current validation → next decision boundary`

### Why
Conversation memory must not be a required part of CYDRA's development state. The repository must contain enough current workflow state for a fresh agent session to determine what was completed, what remains unresolved, what must not yet be claimed, and exactly how to continue.

### Implementation
- Added `CYDRA_CONTINUITY.md` as the operational handoff/checkpoint.
- Updated `AGENTS.md` so every new CYDRA work session reads the Bible, agent contract, continuity checkpoint, and latest relevant update-log entry before making changes or recommendations.
- The checkpoint records the completed ENS source-observation baseline: 1,746 inventoried / 1,746 supplied files, TypeScript 6.0.3, 62,758 observations, 62,645 nodes, 2,293 edges, 2,133 resolved imports, 3,086 unresolved imports, 160 resolved exports, and 1 unresolved export.
- The checkpoint explicitly preserves the unresolved ENS audited-source identity constraint and distinguishes compiler observations from semantic/security conclusions.
- The checkpoint defines the next investigation boundary as compiler-backed symbol identity and trustworthy intra-system relationships, with call relationships as the first candidate because 45,137 call observations currently exist without equivalent resolved caller/callee coverage.

### Safety semantics
The checkpoint is operational state, not evidence authority. Reproduction instructions do not establish authorization, source identity, vulnerability validity, or independent variant validation. Fresh sessions must revalidate current runtime/CI/source/build facts before making current claims.

### Live-contest exercise
The checkpoint is anchored to the live ENS Audit Competition reconstruction experiment and its current PRoot Ubuntu environment.

### Validation status
The continuity file and agent contract are committed on `live-immunefi-work`. The Bible already identifies interrupted-work recovery as a research-critical boundary; this change operationalizes that existing doctrine rather than replacing the Bible.

## 2026-09-06 — adaptive-observation-and-human-authorization-doctrine

### Change
Added the CYDRA doctrine for adaptive observation capability, reusable language/toolchain observers, assistant-assisted interpretation, and concentrated human review/authorization.

### Boundary
`target ecosystem → toolchain discovery → observation capability gap → observer construction/adaptation → independent validation → reusable observer → CYDRA reasoning`

### Why
CYDRA must be system-first rather than language-first. A target may use Rust, Solidity, TypeScript/JavaScript, Python, or multiple ecosystems, and different developers may structure the same language very differently. CYDRA therefore needs reusable language/toolchain observers that translate native compiler/toolchain observations into the common evidence and SystemModel layers. The reasoning engine must not be rebuilt for each language or project.

### Architecture doctrine
- Compilers, parsers, language servers, build tools, and runtimes are observation instruments; they are not the CYDRA reasoning engine.
- Existing observers should be reusable across projects in the same ecosystem, subject to configuration and capability gaps.
- A new language/toolchain may require a new observer; a project-specific difference should normally require configuration or an adapter extension rather than a project-specific parser.
- When an observer is missing, CYDRA should identify the observation capability it needs, investigate the target ecosystem/toolchain, construct or adapt the observer, validate it, and promote it only when the observations are independently checkable.
- If an LLM or other assistant is available, it may help interpret unfamiliar compiler APIs, documentation, configuration, errors, or implementation options. Assistant output is guidance, not evidence or a security conclusion.
- CYDRA remains responsible for validation, evidence semantics, uncertainty, reasoning, hypothesis selection, testing, and causal verification.

### Human-assistance doctrine
CYDRA is intended to minimize continuous human assistance. The human researcher remains the principal authority, while CYDRA performs routine bounded discovery, modeling, reasoning, validation, and recovery. Human attention should be concentrated at consequential boundaries such as active-testing authorization, materially risky external actions, ambiguous/high-impact interpretation, exceptional observer promotion, and final bounty submission/publication.

### Safety semantics
No compiler/toolchain observation may silently become a security claim. An unavailable or partially validated observer must preserve uncertainty. Human authorization cannot be inferred from public availability or assistant output.

### Resulting capability
This establishes the intended path toward CYDRA autonomously adapting its observation layer while keeping the core reasoning engine language-agnostic and keeping consequential authority with the human researcher.

## 2026-09-06 — typescript-javascript-source-coverage

### Change
Closed the TypeScript source adapter's JavaScript-family coverage gap exposed by the completed ENS reconstruction experiment.

### Boundary
`frozen source inventory → language-family admission → compiler ScriptKind → normalized SourceObservation`

### Why
The ENS inventory includes JavaScript-family files alongside TypeScript/TSX files, but the provider previously admitted only `.ts`, `.tsx`, `.mts`, and `.cts`. That meant inventory coverage could silently exceed provider coverage. The adapter must either observe an inventory file or make the unsupported language boundary explicit; it must not silently drop source files.

### Implementation
- The TypeScript provider now admits `.js`, `.jsx`, `.mjs`, and `.cjs` in addition to TypeScript-family extensions.
- The compiler observer selects the corresponding TypeScript `ScriptKind` instead of parsing every supplied file as TSX.
- The ENS experiment admits the same JavaScript-family extensions when loading acquired source text.
- Added regression coverage proving a JavaScript source file reaches the compiler observer and produces normalized observations.
- Restored the full historical `UPDATE_LOG.md` content that was accidentally truncated by the previous projection-boundary commit, preserving the earlier development record.

### Safety semantics
JavaScript-family files use the same compiler-backed observation strength and provenance model. This change expands source understanding only; it does not infer security meaning, scope, authorization, or vulnerability claims.

### Live-contest exercise
This directly repairs the coverage boundary exposed by the ENS 1,746-file source inventory experiment.

### Validation status
Regression coverage is committed. The ENS runtime experiment must be rerun to measure the resulting source coverage and identify any remaining unsupported inventory files. Exact ENS audited-source identity remains unresolved; this remains source reconstruction work only.

## 2026-09-06 — source-observation-canonical-projection

### Change
Hardened the normalized source-observation to canonical SystemModel boundary for source facts that do not yet have a dedicated canonical node kind.

### Boundary
`SourceObservation → canonical SystemModel`

### Why
The live ENS experiment reached compiler-backed observations but exposed a mismatch: the TypeScript provider emits `call` facts, while the canonical model deliberately has no generic `call` node kind. Dropping those facts would lose evidence; inventing caller/callee edges would overstate compiler evidence because the current observer does not yet establish both identities.

### Implementation
- Canonical projection now maps `call` source observations to `observation` nodes while preserving `source_observation_kind=call`.
- Type observations and other explicit source kinds are mapped only where the canonical model already has a semantically compatible representation.
- Unknown future source kinds fail closed rather than being silently coerced.
- Added regression coverage proving a compiler-backed call fact is preserved without inventing a call edge.

### Safety semantics
A source fact is not promoted into a stronger semantic relationship merely to satisfy the canonical schema. Call observations remain compiler-backed observations until a provider establishes the relevant caller/callee identities and an explicit relationship.

### Live-contest exercise
This boundary is exercised by the ENS TypeScript reconstruction over the frozen 1,746-file inventory.

### Validation status
The canonical projection repair and regression test are committed on `live-immunefi-work`. The full ENS runtime experiment must be rerun before claiming observation, relationship, or model coverage. ENS exact audited-source identity remains unresolved; this remains source reconstruction work only.

## 2026-09-06 — typescript-workspace-resolution

### Change
Corrected TypeScript compiler resolution for the ENS monorepo experiment so the observer resolves the compiler from the workspace package owning the supplied source file rather than assuming the repository root exposes `typescript`.

### Boundary
`acquired source file → owning workspace package → declared compiler capability → compiler observations → normalized SystemModel`

### Why
The live ENS experiment proved that `typescript@6.0.3` is installed and usable through the `manager` and `portal` workspace contexts, while root-level `require("typescript")` fails. CYDRA must follow the target's actual workspace dependency semantics instead of altering the target or substituting an unrelated compiler path.

### Implementation
- Updated `cydra/typescript_observer.cjs` to locate the nearest owning `package.json` from each supplied source path.
- Resolves `typescript` through `Module.createRequire()` anchored to that workspace package.
- Keeps the compiler-backed observation contract unchanged.
- Retains the existing fail-closed behavior when the owning workspace cannot provide the required compiler API.
- Does not install or modify target dependencies.

### Safety semantics
The resolver follows declared target workspace dependencies; it does not infer compiler availability from pnpm's internal store layout. `@typescript/native-preview`/`tsgo` remains a separate capability and is not substituted for the classic TypeScript Compiler API.

### Live-contest exercise
ENS manager and portal both resolve `tsc` 6.0.3 through their workspace contexts. The next runtime measurement must verify that the compiler observer now produces observations across the frozen 1,746-file inventory.

### Validation status
The target-environment diagnostic established the workspace resolution fact. The workspace-aware observer change is committed on `live-immunefi-work`. Full 1,746-file runtime measurement is still required before claiming coverage. ENS exact audited-source identity remains unresolved, so this remains source reconstruction work only.

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
