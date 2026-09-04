# CYDRA Live ENS Integration Status

**Snapshot:** 2026-09-04  
**Canonical target:** ENS Audit Competition on Immunefi

## Migration result

The canonical `Wonderadroit/cydrabug` repository now contains the first dependency-closed implementation slice from the historical CYDRA engine.

Migrated/reconciled boundaries:

- `cydra/program_intake.py` — ProgramContract, provenance, scope/resource semantics, known-issue context, bounded discovery, Immunefi adapter.
- `cydra/immunefi_live.py` — passive public Immunefi HTTP acquisition.
- `cydra/project_build.py` — build/toolchain profile and exact revision identity primitives.
- `cydra/scope.py` — fail-closed scope policy.
- `cydra/repository_model.py` — deterministic source inventory/model.
- `cydra/recon.py` — passive structural reconnaissance.
- `cydra/ast_dataflow.py` — compiler-AST evidence primitive.
- `cydra/system_model.py` — canonical graph model.
- `cydra/system_model_ingestion.py` and `cydra/repository_graph.py` — canonical projection boundaries.

## Migration qualification

Some modules are exact historical implementations where the source was transferred byte-for-byte. Other modules are reconciled compatibility implementations created from the historical contracts while the remaining dependency-closed source is migrated.

In particular, `program_intake.py` and `ast_dataflow.py` are not yet full byte-for-byte historical parity. Their current contracts preserve the critical fail-closed semantics, but the remaining historical parser/extractor surface is still a migration boundary.

Therefore CYDRA must not claim full historical parity yet.

## Current live ENS facts

Immunefi currently lists the ENS Audit Competition as live. The current resources page specifies Node v22, pnpm v10, `pnpm install --frozen-lockfile`, and audited revision `63772fd872af472ced58b009499355f3430c2a86`. The current scope lists Manager app Files, Explorer app Files, Workers, Transaction-manager, and Smart-account.

## Current executable boundary

`Immunefi public pages → AcquiredResource → ProgramContract → resource graph → exact revision/build identity → passive repository model → canonical SystemModel`

Active testing remains downstream and requires explicit authoritative scope/authority evidence.

## Next boundary

1. Acquire current ENS pages.
2. Persist the fresh ProgramContract fingerprint and page provenance.
3. Discover and classify authoritative project repository/resource references.
4. Bind the exact audited revision.
5. Verify Node/pnpm/build identity against the checkout.
6. Project only passive material into the canonical SystemModel.
7. Migrate/activate the next historical reasoning boundary.

## Safety/eligibility

ENS known issues remain context, not a generic vulnerability blacklist. Known defects and same-root-cause duplicates are ineligible, while genuinely new consequences and uncovered areas can remain eligible. CYDRA must preserve this distinction and require evidence-backed identity before excluding a candidate.

## Milestone state

**M0:** complete.  
**M1:** core live-intake primitives migrated/reconciled.  
**M2:** resource graph primitives migrated; live ENS acquisition remains to be exercised.  
**M3:** build identity primitives migrated; exact repository/revision binding remains.  
**M4:** canonical SystemModel primitives migrated; live ENS projection is next.

No vulnerability claim is made by this document.
