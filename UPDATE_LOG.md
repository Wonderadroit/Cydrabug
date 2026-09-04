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
