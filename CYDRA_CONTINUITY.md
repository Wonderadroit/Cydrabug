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
`frozen ENS source inventory → language/toolchain admission → compiler-backed observations → normalized SourceObservation → canonical SystemModel`

### Last verified runtime result
The ENS source observation experiment completed successfully in the correctly configured PRoot Ubuntu environment:

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
- external_resolutions: `3805`

### Meaning of the result
The source-admission boundary is now closed for the frozen 1,746-file inventory: all 1,746 inventoried files reached the provider.

The provider is producing substantial compiler-backed structural evidence rather than the earlier zero-observation result caused by environment/inventory mistakes.

The `call` count is an observation count, not a count of verified caller/callee relationships. Do not infer security semantics from the count.

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

The TypeScript observer should remain reusable across TypeScript/JavaScript projects and should use target-native compiler/configuration semantics. Other languages should receive their own strongest native/specialized observation path when needed.

### Current canonical-model rule
The canonical model does not have generic `call`, `export`, or `type` node kinds.

Those facts are preserved as canonical `observation` nodes with `source_observation_kind` rather than being silently dropped or promoted into unsupported semantic relationships.

In particular, compiler-observed calls must not become `calls` edges unless the observer establishes the relevant caller/callee identities.

### NEXT ACTION
Do not immediately build another parser or start vulnerability hunting.

First inspect the completed 62,758-observation model and determine whether the next useful capability is **semantic relationship enrichment from compiler-backed symbol identity**.

The highest-value next boundary is likely:

`compiler-backed source observations → resolved symbol identities → trustworthy intra-system relationships → security-reasoning-ready SystemModel`

The first candidate is call relationships, because the experiment currently has `45,137` call observations but only `2,293` explicit internal relationships. However, this must be investigated rather than assumed: use TypeScript's `TypeChecker`/symbol APIs to establish caller/callee identity where the compiler can do so, preserve unresolved calls as observations, and measure the resulting relationship coverage.

### Resume command
From the correctly configured PRoot Ubuntu guest:

```bash
cd /workspace/cydrabug
python -m cydra.ens_source_experiment /workspace/target .cydra/ens-source-files-target.txt
```

Use this only to reproduce/compare the baseline. Do not treat identical reruns as independent variant validation.

### Before implementing call-identity enrichment
Inspect:

- `cydra/typescript_observer.cjs`
- `cydra/typescript_provider.py`
- `cydra/source_provider.py`
- `cydra/source_ingestion.py`
- `cydra/system_model.py`
- `tests/test_typescript_provider.py`
- `tests/test_source_ingestion.py`
- `cydra/ens_source_experiment.py`

Define the regression proof first:

1. a compiler-backed call observation remains present;
2. resolved caller/callee symbols become explicit relationships only when TypeChecker establishes them;
3. unresolved/dynamic/ambiguous calls remain observations;
4. relationship provenance points to the compiler observation and source revision;
5. no security conclusion is emitted merely because a call relationship exists;
6. baseline metrics remain reproducible and comparable.

### MUST NOT CLAIM YET
- exact ENS audited-source identity is verified;
- the 62,758 observations are a complete semantic model;
- all 45,137 calls have known callees;
- unresolved imports are vulnerabilities;
- the ENS target is ready for active vulnerability testing;
- any security finding exists;
- any compiler observation establishes authorization or bounty eligibility.

## Live-contest safety boundary

The ENS contest remains the live integration exercise. Public source availability and the acquired contest fork do not by themselves establish active-testing authorization. Before active vulnerability investigation, CYDRA must reacquire and validate the current live program context and preserve the distinction between understanding scope, testing scope, and claim scope.

## Checkpoint maintenance rule

Update this file whenever a material change creates a new stopping point. The update should be made in the same development change as the relevant implementation/update-log change whenever practical. Keep the checkpoint concise enough for a fresh chat to read quickly, but precise enough to reproduce the stopping point without relying on conversation memory.
