# CYDRA UPDATE LOG

## 2026-09-06 — source-observation-canonical-projection

### Change
Hardened the normalized source-observation to canonical SystemModel boundary for source facts that do not yet have a dedicated canonical node kind.

### Boundary
`SourceObservation → canonical SystemModel`

### Why
The live ENS experiment reached compiler-backed observations but exposed a schema mismatch: the TypeScript provider emits `call` and `export` facts, while the canonical model deliberately has no generic `call` or `export` node kinds. Dropping those facts would lose evidence; inventing semantic relationships would overstate compiler evidence because the current observer does not yet establish the identities needed for those relationships.

### Implementation
- Canonical projection maps `call`, `export`, and `type` source facts to `observation` nodes while preserving `source_observation_kind`.
- Existing canonical kinds such as files, modules, functions, classes, imports, entry points, state variables, authorization, data flow, and trust boundaries retain their explicit canonical representation.
- Unknown future source kinds fail closed rather than being silently coerced.
- Regression coverage proves that noncanonical source facts are preserved without inventing semantic edges.

### Safety semantics
A source fact is not promoted into a stronger semantic relationship merely to satisfy the canonical schema. In particular, a compiler-observed call expression remains an observation until a provider establishes the relevant caller/callee identities and an explicit relationship.

### Live-contest exercise
This boundary is exercised by the ENS TypeScript reconstruction over the frozen 1,746-file inventory.

### Validation status
The canonical projection repair and regression test are committed on `live-immunefi-work`. The full ENS runtime experiment must be rerun before claiming observation, relationship, or model coverage. ENS exact audited-source identity remains unresolved; this remains source reconstruction work only.

## 2026-09-06 — typescript-workspace-resolution
