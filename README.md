# CYDRA

CYDRA is a personal authorized bug-bounty/security research engine focused on understanding real target systems and producing evidence-backed, reproducible findings.

## Current development mode

CYDRA is being developed against a live Immunefi contest. The first target is the **ENS Audit Competition**.

The live target is used to expose real engineering and reasoning boundaries. It is not a vulnerability oracle.

## Canonical documents

- [`CYDRA_PROJECT_BIBLE.md`](./CYDRA_PROJECT_BIBLE.md) — canonical living project doctrine and architecture source of truth.
- [`LIVE_TARGET_ENS.md`](./LIVE_TARGET_ENS.md) — dated snapshot of the initial live contest.
- [`UPDATE_LOG.md`](./UPDATE_LOG.md) — material change history.

## Core doctrine

`System behavior → invariants → evidence → competing hypotheses → information-gain testing → observation → belief update → persistent system model → causal verification → finding`

## Immediate next step

Acquire the current ENS Immunefi program context, preserve provenance and authority, and construct the canonical `ProgramContract` and resource dependency graph before moving downstream into source/build analysis.

See the Project Bible for the full development doctrine, milestones, authorization boundaries, evidence rules, and definition of done.
