# LIVE TARGET — ENS AUDIT COMPETITION

**Snapshot date:** 2026-09-04  
**Platform:** Immunefi  
**Status at snapshot:** Live  
**Target:** ENS Audit Competition

## Contest snapshot

- Listed end date: 2026-09-14
- Primary pool: $49,000
- All Stars pool: $14,000
- Podium pool: $7,000
- Listed vault TVL: approximately $69,995
- Listed lines of code: 137,845
- Rewards token: USDC
- Triaged by Immunefi
- Step-by-step PoC required
- KYC required
- Vault program

## Scope snapshot

The snapshot listed:

- Manager app Files
- Explorer app Files
- Workers
- Transaction-manager
- Smart-account

## Build/resource snapshot

- Node v22
- pnpm v10
- Docker required for E2E suites
- Setup: `pnpm install --frozen-lockfile`
- Audited revision: `63772fd872af472ced58b009499355f3430c2a86`

## Official resources

- https://immunefi.com/audit-competition/
- https://immunefi.com/audit-competition/audit-competition-ens/information/
- https://immunefi.com/audit-competition/audit-competition-ens/scope/
- https://immunefi.com/audit-competition/audit-competition-ens/resources/

## Authority warning

This file is a **snapshot**, not permanent authority.

Before active investigation CYDRA must reacquire the current Immunefi program context and compare it with this snapshot. Changes to contest state, dates, rules, scope, impacts, requirements, or audited revision must be treated as context changes and incorporated through the canonical `ProgramContract`.

Public source, repositories, deployments, explorers, documentation, or dependencies do not independently grant testing authorization.

## Next action

Build a fresh provenance-preserving ENS `ProgramContract` and resource dependency graph from the live program before moving to source/build acquisition or vulnerability reasoning.
