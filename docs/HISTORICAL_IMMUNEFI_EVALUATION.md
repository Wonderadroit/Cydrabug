# Historical Immunefi Evaluation

## Purpose

This branch is a blind evaluation of CYDRA against a completed Immunefi competition. It measures whether CYDRA can independently derive security findings from the target system rather than reproducing historical reports.

## Selected contest

**Immunefi Arbitration Audit Competition**

- Contest: Immunefi Arbitration
- Period: 12 March 2024 – 2 April 2024
- Reward pool: $30,000
- Historical target repository: `immunefi-team/vaults`
- Planned pinned revision: `49c1de26cda19c9e8a4aa311ba3b0dc864f34a25`

The official Immunefi page identifies this as a finished audit competition and states that duplicates and private known issues were eligible for rewards in this particular contest. citeturn0search1

## Blindness rules

During the CYDRA run, the engine must not receive:

- historical bug reports;
- historical findings lists;
- leaderboard data;
- public write-ups describing the winning vulnerabilities;
- post-contest remediation commits when they reveal the defect;
- any generated oracle mapping target code to historical findings.

The historical reports are evaluation material only and are revealed after CYDRA's candidate-finding output is frozen.

## Input boundary

The initial blind workspace should contain only the pinned target source and the contest information that a researcher could legitimately use before submitting a report:

1. exact repository and revision;
2. contest scope;
3. contest rules and prohibited activities;
4. build/toolchain instructions;
5. source code and compiler/build artifacts obtainable from that revision.

## Evaluation phases

### Phase A — Intake

Construct the canonical `ProgramContract`, resource graph, exact repository binding, revision identity, and build identity.

### Phase B — System understanding

Construct the SystemModel from source/build evidence. Preserve provenance and distinguish observed relationships from inferred relationships.

### Phase C — Reasoning

Generate security invariants and competing hypotheses. No historical finding IDs or descriptions may enter the model.

### Phase D — Investigation

Select observations by expected information gain. Execute only observations permitted by the contest rules and the CYDRA authorization boundary.

### Phase E — Verification

A candidate finding is not counted merely because a suspicious pattern exists. CYDRA must establish a causal chain sufficient to explain the security consequence and produce reproducible evidence.

### Phase F — Freeze

Persist and cryptographically identify CYDRA's complete candidate output before historical reports are revealed.

### Phase G — Oracle reveal

Only after the freeze, import historical reports as a separate evaluation dataset. They must never alter the blind run's beliefs or candidate generation.

### Phase H — Comparison

Compare candidates using:

- exact finding overlap;
- root-cause overlap;
- affected asset overlap;
- impact/severity overlap;
- evidence/PoC quality;
- false positives;
- missed historical findings;
- findings correctly rejected because they were out of scope or otherwise ineligible.

## Important contest context

Immunefi's historical page says proof of concept was required for all severities and prohibited mainnet/public-testnet testing, directing testing to local forks. citeturn0search1

That means a historical reproduction must respect the same safety boundary: source analysis can be performed passively, while any executable validation must remain in an authorized local environment and must not attack deployed assets.

## Success criterion

The experiment succeeds only if CYDRA can produce at least one independently verified, historically valid security finding without receiving the historical answer during reasoning.

A missed finding is useful data. A false positive is also useful data. Neither is hidden.

The primary metric is therefore **validated independent rediscovery**, not the number of suspicious candidates produced.
