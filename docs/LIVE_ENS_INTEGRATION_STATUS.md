# CYDRA Live ENS Integration Status

**Snapshot:** 2026-09-04  
**Canonical target:** ENS Audit Competition on Immunefi  
**Purpose:** record the first implementation-boundary inspection before migrating/reusing the existing CYDRA engine.

## 1. Inspection result

The previous CYDRA implementation is not a conceptual prototype that needs to be rebuilt. The old `Wonderadroit/Cydra_` repository at commit `c0896818781afb226934b8f0356060ee5ae319d6` already contains the major canonical boundaries required by the live-contest doctrine.

The new `Wonderadroit/cydrabug` repository should therefore be treated as the canonical continuation of the existing engine, with deliberate migration/reconciliation rather than a rewrite.

## 2. Existing implementation boundaries confirmed

### Program intake

`Cydra_/cydra/program_intake.py` already contains:

- `AcquisitionState`;
- `AuthorityClass`;
- `ScopeStatus`;
- `ResourceKind`;
- `KnownIssueStatus`;
- provenance-bound `ProgramResource`;
- `ProgramAssertion`;
- `ProgramContract`;
- content fingerprints;
- canonical resource identities;
- bounded reference discovery;
- resource dependency expansion;
- Immunefi acquisition adapter;
- structured program parsing;
- conversion of the program contract into the canonical system model.

The implementation explicitly keeps acquisition separate from authority and does not treat discovered references as testing authorization.

### Repository and AST reconstruction

`Cydra_/cydra/audit_session.py` already provides an atomic passive repository audit boundary. It validates persisted scan provenance, source manifests, Solidity AST manifests, scope decisions, and the passive nature of the session before committing the projection.

`Cydra_/cydra/solidity_recon.py` consumes compiler-produced Solidity JSON ASTs without invoking a compiler or inventing semantic relationships. Declaration IDs are preserved as identity anchors.

### Build/toolchain

`Cydra_/cydra/project_build.py` already detects project ecosystems and records build profiles, toolchain declarations, observed tool versions, configuration fingerprints, build results, dependency metadata where supported, reproducibility state, and compiler-produced Solidity artifacts.

The build layer deliberately does not silently install or substitute toolchains.

### Canonical composition

`Cydra_/cydra/canonical_pipeline.py` already composes passive repository intake with the reasoning orchestrator without creating a second reasoning engine. It stops at planning and does not execute observations itself.

### System model and reasoning

The existing repository contains the canonical `SystemModel`, repository graph ingestion, invariant generation/verification, competing hypotheses, information-gain planning, reasoning orchestration, and the invariant-to-security-hypothesis bridge.

### Execution and evidence

The existing reasoning orchestrator contains persisted execution-request identity, explicit observation binding, gateway execution, durable result receipts, receipt validation, recovery/reconciliation paths, and evidence ingestion. This preserves the distinction between planning, authorization, execution, receipt, and evidence.

### Causal verification and finding boundary

The existing repository also contains causal verification, finding eligibility/persistence, PoC lineage, reproducibility, and publication-boundary logic. These remain downstream of the live intake/build/modeling work and should not be duplicated in the new repository.

## 3. Existing live-program test precedent

The old repository already contains a real captured Immunefi integration test at:

`Cydra_/tests/test_live_immunefi_0x_intake.py`

It exercises the actual `ImmunefiAcquisitionAdapter`, canonical program acquisition, structured assertions, bounded linked-resource expansion, and the rule that repository/documentation children remain `UNKNOWN` scope until explicitly classified.

This is valuable precedent, but it is a historical evaluation fixture. It must not be treated as current ENS authority or as a vulnerability oracle.

## 4. Current ENS reality check

The ENS Audit Competition remains listed as **Live** on Immunefi on 2026-09-04. Current Immunefi pages report:

- end date: 14 September 2026;
- primary pool: $49,000;
- All Stars pool: $14,000;
- Podium pool: $7,000;
- listed LoC: 137,845;
- Node v22;
- pnpm v10;
- Docker for E2E suites;
- setup: `pnpm install --frozen-lockfile`;
- audited revision: `63772fd872af472ced58b009499355f3430c2a86`.

Current scope lists Manager app Files, Explorer app Files, Workers, Transaction-manager, and Smart-account.

The current known-issues material explicitly marks previously known defects as ineligible while allowing genuinely new consequences or areas not covered by those audits to remain eligible under the competition rules. CYDRA therefore needs exact current known-issue ingestion rather than a generic historical blacklist.

## 5. Actual missing boundary

The main missing capability is **not** another reasoning abstraction.

The missing live integration is:

`current Immunefi ENS pages → fresh ProgramContract → complete relevant resource graph → exact repository/revision binding → build identity → canonical SystemModel`

The old engine has the individual primitives, but the new canonical repository does not yet contain the executable implementation that connects them to the current ENS target.

## 6. Migration rule

Do not copy the entire old repository blindly.

First migrate the minimum dependency-closed slice required for:

1. live Immunefi acquisition;
2. provenance/resource graph;
3. source/revision identity;
4. build/toolchain detection;
5. passive repository/AST reconstruction;
6. canonical SystemModel projection.

Then run the existing tests that cover those boundaries and add an ENS-specific live snapshot/integration test only from freshly acquired current program material.

Downstream reasoning/execution/finding modules should be migrated only when the live ENS pipeline reaches their boundary.

## 7. Current decision

**M0:** complete.  
**M1:** implementation exists historically; live ENS wiring is the active boundary.  
**M2:** resource graph primitives exist; ENS-specific live acquisition must be exercised.  
**M3:** build primitives exist; exact ENS repository identity must be bound before execution.  
**M4:** canonical modeling primitives exist; they become the next boundary after M1–M3 are connected.

No vulnerability claim is made by this document.
