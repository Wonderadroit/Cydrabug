# CYDRA CONTINUITY CHECKPOINT

**Purpose:** make CYDRA work resumable across chat loss, context limits, connector interruptions, or a new ChatGPT conversation.

This file is an operational checkpoint, not a replacement for `CYDRA_PROJECT_BIBLE.md`. The Bible remains the canonical source of truth. This file records the current stopping point and the exact next workflow so a fresh chat can resume without reconstructing history from memory.

## Resume protocol

At the start of every new CYDRA chat/work session:

1. Read `CYDRA_PROJECT_BIBLE.md`.
2. Read `AGENTS.md`.
3. Read this `CYDRA_CONTINUITY.md`.
4. Read the latest relevant entry in `UPDATE_LOG.md`.
5. Inspect the current branch/repository state before changing anything.
6. Treat the checkpoint below as the current work position, not as an authority claim.
7. Revalidate any runtime/CI/source/build fact before making a current validation claim.
8. Continue from `NEXT ACTION` unless the repository state or Bible requires a different boundary.

## Checkpoint format

Every material stopping point should update this file with:

- current objective;
- current boundary;
- last verified result;
- exact commit/branch when known;
- unresolved constraints;
- files/components involved;
- exact command or action to resume;
- expected result;
- what must NOT yet be claimed;
- next decision point.

Do not write speculative future results into the checkpoint.

## Current checkpoint — 2026-09-06

### Objective
Build CYDRA's reusable source-understanding boundary against the live ENS Audit Competition without turning the TypeScript adapter into a project-specific parser or a vulnerability oracle.

### Current boundary
`compiler-backed source observations → TypeChecker symbol identities → trustworthy intra-system call relationships → canonical SystemModel`

### Last verified runtime result
Before the current implementation change, the ENS source observation experiment completed successfully in the correctly configured PRoot Ubuntu environment:

- compiler_version: `6.0.3`
- inventory_files: `1746`
- supplied_source_files: `1746`
- observation_count: `62758`
- node_count: `62645`
- edge_count: `2293`
- observations: `45137 call`, `628 class`, `241 export`, `1746 file`, `1976 function`, `9018 import`, `4012 type`
- resolved_imports: `2133`
- unresolved_imports: `3086`
- resolved_exports: `160`
- unresolved_exports: `1`
- internal_relationships: `2293`

The current symbol-identity implementation has **not yet been runtime-validated against the ENS target**, so no new call-relationship coverage number is claimed.

### Meaning of the previous result
The source-admission boundary was closed for the frozen 1,746-file inventory: all 1,746 inventoried files reached the provider.

The provider was producing substantial compiler-backed structural evidence rather than the earlier zero-observation result caused by environment/inventory mistakes.

The `call` count was an observation count, not a count of verified caller/callee relationships. The current implementation now attempts to establish those identities through the TypeScript TypeChecker, but this remains to be measured.

The unresolved import/export counts are preserved uncertainty, not automatic defects.

### Current source identity constraint
ENS exact audited-source identity is still unresolved.

The competition advertises audited revision:
`63772fd872af472ced58b009499355f3430c2a86`

The acquired public contest snapshot is rooted at:
`cda79acaad59711b943fc68207ebb3f1d0ff8596`

The snapshot declares that it was forked from the audited revision, but that declaration is lineage evidence rather than cryptographic proof of identical Git identity.

Therefore the current source model remains **source reconstruction**, not an identity-verified audited-source model, until the exact Git identity is independently resolved.

### Current environment constraint
The correct target environment is PRoot Ubuntu with:

- Node `v22.23.2`
- pnpm `10.27.0`
- TypeScript compiler API `6.0.3`

`tsgo` / `@typescript/native-preview` is not being substituted for the classic compiler API because the native executable currently fails in this Android/PRoot environment with the `/.l2s/lib.d.ts` substrate error.

### Current design doctrine
CYDRA uses one language-neutral source observation contract with ecosystem/language/toolchain-specific observers.

It does **not** use one universal parser.

The TypeScript observer remains reusable across TypeScript/JavaScript projects and uses target-native compiler/configuration semantics. Other languages should receive their own strongest native/specialized observation path when needed.

### Current semantic relationship rule
Function and method observations may carry TypeScript compiler symbol identities. Call observations may carry compiler-resolved caller/callee identities.

A `calls` relationship is created only when:

1. the TypeChecker supplies caller and callee symbol identities;
2. both identities map to supplied function observations;
3. the relationship records the originating call observation as evidence;
4. the relationship basis is explicitly identified as TypeChecker symbol identity.

External, dynamic, ambiguous, or otherwise unresolved calls remain observations with explicit relationship-status attributes. Expression text is never semantic proof.

### Current canonical-model rule
The canonical model does not have generic `call`, `export`, or `type` node kinds.

Those facts are preserved as canonical `observation` nodes with `source_observation_kind` rather than being silently dropped or promoted into unsupported semantic relationships.

Compiler-established `calls` relationships connect canonical function observations through the existing source-relationship projection; they do not turn call observations themselves into a generic semantic node kind.

### Files/components involved
- `cydra/typescript_observer.cjs`
- `cydra/typescript_provider.py`
- `cydra/source_provider.py`
- `cydra/source_ingestion.py`
- `cydra/system_model.py`
- `cydra/ens_source_experiment.py`
- `tests/test_typescript_provider.py`

### Current implementation state
The TypeScript observer now constructs a compiler `Program` over the supplied source set and uses the target compiler's `TypeChecker` for symbol identity. The provider performs a second-pass identity join before projecting relationships.

This implementation is committed on `live-immunefi-work` together with the regression definitions and experiment metrics. The full test suite and ENS runtime experiment have not yet been rerun after the implementation change.

### NEXT ACTION
Run the focused TypeScript provider tests first.

If they pass, rerun the ENS source experiment in the correctly configured PRoot Ubuntu target environment:

```bash
cd /workspace/cydrabug
python -m cydra.ens_source_experiment /workspace/target .cydra/ens-source-files-target.txt
```

Compare the resulting:

- `call_observations`
- `internally_resolved_call_observations`
- `internal_call_relationships`
- `internal_relationships`
- `edge_count`

against the previous baseline of 45,137 call observations and 2,293 internal relationships.

Then inspect representative resolved relationships and any compiler-resolution failures before deciding whether further semantic enrichment is justified.

### Expected result
A useful result is not necessarily high coverage. The required property is correctness:

- direct compiler-resolved internal calls produce explicit caller→callee relationships;
- external calls do not become internal relationships;
- dynamic/ambiguous/unresolved calls remain observations;
- relationship provenance identifies the call observation and TypeChecker basis;
- baseline source-admission metrics remain comparable.

### MUST NOT CLAIM YET
- exact ENS audited-source identity is verified;
- the 62,758 observations are a complete semantic model;
- all 45,137 calls have known callees;
- any particular new call-relationship coverage percentage is verified;
- unresolved imports/calls are vulnerabilities;
- the ENS target is ready for active vulnerability testing;
- any security finding exists;
- any compiler observation establishes authorization or bounty eligibility;
- the new symbol-identity implementation is runtime-validated until the focused tests and ENS experiment pass.

## Live-contest safety boundary

The ENS contest remains the live integration exercise. Public source availability and the acquired contest fork do not by themselves establish active-testing authorization. Before active vulnerability investigation, CYDRA must reacquire and validate the current live program context and preserve the distinction between understanding scope, testing scope, and claim scope.

## Checkpoint maintenance rule

Update this file whenever a material change creates a new stopping point. The update should be made in the same development change as the relevant implementation/update-log change whenever practical. Keep the checkpoint concise enough for a fresh chat to read quickly, but precise enough to reproduce the stopping point without relying on conversation memory.
