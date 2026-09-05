# CYDRA AGENT OPERATING CONTRACT

**Repository:** `Wonderadroit/cydrabug`  
**Branch:** `live-immunefi-work`  
**Governing document:** `CYDRA_PROJECT_BIBLE.md`

## Mandatory rule

Before **any code change, repository modification, architecture recommendation, implementation recommendation, target recommendation, or research-direction recommendation**, the agent MUST read and follow `CYDRA_PROJECT_BIBLE.md`.

`CYDRA_PROJECT_BIBLE.md` is the canonical source of truth. This file is the operational enforcement layer for the agent. If this file and the Bible ever conflict, the Bible governs and this file must be updated to match it.

## Do not operate outside the Bible

The agent MUST NOT:

- introduce work that is outside CYDRA's stated mission or milestones;
- turn CYDRA into a generic reasoning engine, audit/compliance product, public service, or vulnerability-dictionary oracle;
- add architecture merely because it seems elegant without a measurable research capability;
- bypass authorization, scope, provenance, evidence, uncertainty, causal-verification, known-issue, eligibility, or reproducibility boundaries;
- treat public availability as testing authorization;
- promote `UNKNOWN` scope to in-scope by inference;
- treat probability, ranking, heuristics, or tool output as semantic verification;
- treat static-analysis alerts as vulnerabilities without the required evidence and causal chain;
- use historical findings as an oracle for blind current-target reasoning;
- silently skip a required workflow step because an answer looks plausible;
- weaken an existing trust boundary merely to make implementation easier;
- claim CI, runtime validation, source identity, build reproducibility, authorization, or vulnerability validity unless it has actually been verified.

## Required workflow before changes or recommendations

1. Read the current `CYDRA_PROJECT_BIBLE.md` from the active branch.
2. Identify the relevant mission, doctrine, milestone, boundary, invariant, and validation requirements.
3. Inspect the current implementation and repository state before proposing or changing anything.
4. Determine whether the proposed work directly advances the current milestone or repairs a boundary exposed by the live contest.
5. Preserve authority and uncertainty semantics.
6. Define the regression proof before implementing the change.
7. Make the smallest evidence-backed change that advances the research capability.
8. Update `CYDRA_PROJECT_BIBLE.md` when the change materially alters architecture, workflow, target strategy, authority/reasoning doctrine, milestones, or development doctrine.
9. Record material changes in `UPDATE_LOG.md`.
10. Verify tests/CI/runtime state before making any validation claim.

## Current strategic boundary

The Bible currently directs the first live integration through the ENS Audit Competition. The immediate boundary is:

`fresh live ENS program context → provenance-preserving ProgramContract → resource dependency graph → exact source/build identity → canonical SystemModel`

Do not jump ahead to speculative downstream features while this boundary is unresolved.

## Specialized-tool doctrine

CYDRA should orchestrate specialized security tools rather than recreate them. Where appropriate and authorized, the intended research stack may use compiler/AST evidence, Foundry, Slither, Aderyn, Echidna, Halmos, formal-verification tooling, execution traces/instrumentation, and LLM reasoning. Their outputs are evidence or investigation inputs; they do not independently establish bounty findings.

## Research success criterion

Optimize for measurable discovery capability:

`target understanding → invariants → evidence → competing hypotheses → high-information investigation → causal verification → verified bug → reproducible PoC → bounty-ready finding`

A correct investigation that finds no bug is preferable to an unsupported finding.

## Change-control rule

Any material change must be traceable to the Bible and recorded in `UPDATE_LOG.md`. If a requested action conflicts with the Bible, stop at the boundary, explain the conflict, and do not implement the conflicting action.
