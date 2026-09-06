# CYDRA PROJECT BIBLE

## Live-Contest Development Edition

**Project:** CYDRA  
**Repository:** `Wonderadroit/cydrabug`  
**Status:** Canonical working source of truth  
**Bible version:** `2.1.0-live-contest`  
**Created:** 2026-09-04  
**Updated:** 2026-09-06

---

## 1. Mission

CYDRA is a personal, authorized bug-bounty/security research engine whose primary purpose is to understand authorized target systems deeply enough to discover real, non-obvious, reproducible vulnerabilities that can lead to valid bounty submissions.

CYDRA is **not**:

- a vulnerability dictionary;
- a checklist pretending to understand a system;
- a compliance or audit-reporting product;
- a historical-finding lookup oracle;
- an internet-exposed autonomous attack service.

Historical programs, findings, audits, and benchmarks are learning and evaluation material. They must not become the sole definition of success or a shortcut/oracle for current reasoning.

### Central optimization

`Target understanding → security invariants → evidence → competing hypotheses → high-information investigation → causal verification → verified bug → reproducible PoC → bounty-ready finding`

### Canonical reasoning chain

`System behavior → invariants → evidence → hypotheses → information-gain testing → observation → belief update → persistent system model → causal verification → finding`

---

## 2. Live-Contest Development Doctrine

CYDRA will be developed against real, currently live authorized bounty/audit programs rather than toy systems alone.

The live contest is an **integration and reality test**, not a vulnerability oracle.

The engine must behave as though it were independently performing the workflow a strong researcher would perform:

1. Find a candidate live Immunefi program/contest.
2. Acquire the complete program context.
3. Extract rules, scope, impacts, out-of-scope conditions, PoC requirements, severity, rewards, disclosure, eligibility, and known issues.
4. Follow relevant linked resources.
5. Acquire repositories, documentation, deployments, explorers, audits, known issues, and build instructions.
6. Freeze a canonical versioned `ProgramContract`.
7. Acquire source at the exact relevant revision.
8. Resolve the build system, dependencies, compiler/runtime/toolchain, and reproducibility requirements.
9. Select the strongest trustworthy program representation/variant.
10. Construct the canonical `SystemModel`.
11. Understand architecture, assets, trust boundaries, roles, state, flows, external dependencies, and invariants.
12. Generate competing security hypotheses.
13. Select observations/tests by information gain.
14. Compile, test, and execute locally within authorized authority.
15. Capture counterexamples and causal evidence.
16. Apply scope, impact, known-issue, eligibility, and reproducibility gates.
17. Emit only verified findings with reproducible PoC lineage.

No step may silently be skipped merely because a heuristic produces a plausible-looking answer.

---

## 3. Authorization and Scope Doctrine

Public availability is not testing authorization.

The following do **not**, by themselves, grant authority to test or claim a component:

- public source code;
- a public repository;
- a deployment address;
- an explorer page;
- a documentation page;
- a discovered dependency;
- an audit report;
- a historical finding.

CYDRA must distinguish:

1. **Understanding scope** — what CYDRA may need to inspect to understand the target.
2. **Testing scope** — what the current program authorizes active testing against.
3. **Claim scope** — what can legitimately appear in a bounty finding.

Out-of-scope dependencies may be acquired as contextual material when necessary to understand an in-scope system, but that does not grant active testing authority. `UNKNOWN` scope remains unresolved and must not be promoted to in-scope by inference.

---

## 4. Program Acquisition

The acquisition phase begins with discovery of a live program and ends only when the program contract has enough authoritative evidence to determine whether active testing is permitted.

CYDRA must acquire, where applicable:

- program identity;
- current status and dates;
- rules;
- in-scope assets/components;
- out-of-scope assets/components;
- impacts and severity rules;
- PoC requirements;
- rewards and eligibility;
- testing restrictions;
- disclosure requirements;
- known issues;
- source repositories;
- documentation;
- deployments and explorers;
- audit materials;
- build instructions;
- audited revision/commit;
- required prerequisites;
- relevant linked resources.

Every resource receives a provenance record containing, where available:

- canonical identity;
- authority class;
- acquisition state;
- source URL/reference;
- parent resource;
- acquisition timestamp;
- content fingerprint;
- freshness information;
- scope status;
- provenance chain.

### Authority classes

- `AUTHORITATIVE`
- `PLATFORM`
- `PROJECT`
- `AGGREGATOR`
- `CONTEXTUAL`
- `UNKNOWN`

Authority and acquisition are separate dimensions. Successfully fetching a page does not make it authoritative.

### Acquisition states

- `ACQUIRED`
- `UNRESOLVED`
- `STALE`
- `REJECTED`

A `ProgramContract` is not ready for active testing while required authoritative resources remain unresolved.

---

## 5. Resource Dependency Graph

The intake graph should preserve relationships such as:

`Program → Rules → Scope → Impacts → PoC → Repository → Documentation → Deployment → Explorer → Audit → Known Issues → Build Instructions → Audited Revision`

Relevant linked resources must be followed rather than treating the first page as the complete specification.

The graph must preserve enough provenance to answer: **why does CYDRA believe this resource matters, where did it come from, and what authority does it carry?**

---

## 6. Initial Live Target: ENS Audit Competition

The initial integration target is the **ENS Audit Competition** on Immunefi.

Snapshot taken: **2026-09-04**.

Snapshot facts:

- competition was live at snapshot time;
- listed end date: 2026-09-14;
- primary pool: $49,000;
- All Stars pool: $14,000;
- Podium pool: $7,000;
- listed vault TVL: approximately $69,995;
- listed lines of code: 137,845;
- rewards token: USDC;
- triaged by Immunefi;
- step-by-step PoC required;
- KYC required;
- vault program.

Snapshot scope included:

- Manager app Files;
- Explorer app Files;
- Workers;
- Transaction-manager;
- Smart-account.

Snapshot build/resource information:

- Node v22;
- pnpm v10;
- Docker required for E2E suites;
- setup: `pnpm install --frozen-lockfile`;
- audited revision: `63772fd872af472ced58b009499355f3430c2a86`.

Official resources:

- https://immunefi.com/audit-competition/
- https://immunefi.com/audit-competition/audit-competition-ens/information/
- https://immunefi.com/audit-competition/audit-competition-ens/scope/
- https://immunefi.com/audit-competition/audit-competition-ens/resources/

**Important:** this section is a snapshot, not permanent authority. Before active investigation, CYDRA must reacquire the live program context and compare it with the stored snapshot/fingerprint. A changed contest state, scope, rule, deadline, or revision must be treated as a context change.

---

## 7. Source and Build Identity

For source-based reasoning CYDRA must preserve:

- repository identity;
- exact revision/commit;
- relevant file manifest;
- source hashes where practical;
- build configuration;
- compiler/runtime/toolchain identity;
- dependency lock information;
- generated artifact identity;
- reproducibility evidence.

The audited revision is not interchangeable with `main`, a later commit, or an arbitrary local checkout.

### Variant selection

CYDRA should select the strongest trustworthy representation available, approximately in this order:

1. compiler/AST-backed representation;
2. build/test/execution-backed representation;
3. generated artifacts with trustworthy provenance;
4. structural source reconstruction;
5. conservative lexical/regex fallback.

Heuristic fallback may support discovery, but it must not fabricate semantic verification. In particular, a regex match must never become a claim equivalent to a compiler-backed or execution-backed fact.

---

## 7.5 Adaptive Observation and Toolchain Learning

CYDRA is **system-first, not language-first**. A target may contain one language or many languages, and the same language may be organized very differently by different developers or projects. CYDRA must not assume that a project resembles a previous target merely because it uses the same language.

### Observation capability

A compiler, parser, language server, build tool, runtime, or other language-native tool is an **observation instrument**. It is not the CYDRA reasoning engine.

CYDRA should discover and preserve, where available:

- languages and source families;
- project manifests and configuration;
- compiler/toolchain identity;
- required or observed versions;
- dependency and lock information;
- build commands and targets;
- relevant compiler/parser interfaces;
- source maps, ASTs, symbol information, and other structural representations;
- project-specific configuration required to reproduce observations.

The goal is to convert language/toolchain-specific observations into the canonical CYDRA evidence/model layer.

### Reusable observers

An observer should normally be **ecosystem/language/toolchain-oriented**, not project-oriented.

For example:

`TypeScript project A → TypeScript observer`  
`TypeScript project B → same TypeScript observer, subject to configuration/capability gaps`

Likewise, when CYDRA encounters Solidity, Rust, Python, or another ecosystem, it should seek the strongest native observation path available rather than force the existing TypeScript observer onto the target.

A new project does not automatically require a new parser. A new language/toolchain may require a new observer. A project-specific gap may require an adapter extension or configuration rather than a whole new parser.

### Adaptive observer construction

When a required observer does not exist, CYDRA should be able to determine the missing observation capability and investigate how the target ecosystem can expose it.

The intended workflow is:

`Target discovery → language/toolchain detection → capability gap → toolchain investigation → observer construction/adaptation → regression validation → promotion → reusable capability`

Where an LLM or other external assistant is available, it may help interpret unfamiliar compiler APIs, documentation, configuration, errors, or implementation options. The assistant is **not** evidence, is not the security oracle, and does not have authority to promote its own interpretation.

Observer promotion requires deterministic or otherwise independently checkable validation. A generated/adapted observer must demonstrate that its observations correspond to the target's actual source/build/toolchain behavior before it becomes trusted capability.

### Uncertainty at the observation boundary

If CYDRA cannot obtain reliable compiler/toolchain observations, it must preserve that limitation explicitly:

`source discovered → observer unavailable/partial → uncertainty preserved → request better observation or choose justified fallback`

CYDRA must never convert an unavailable observation into an assumed semantic fact merely to complete the model.

### Source completeness principle

If the repository inventory contains source that belongs to an admitted source family, CYDRA must not silently omit it from compiler-backed observation because of incomplete extension/admission rules. Coverage gaps must be measurable and exposed.

The ENS source-admission experiment is a concrete example: the inventory initially contained 1,746 files while only 1,745 were supplied to the TypeScript compiler observer. Admission was expanded to JavaScript-family extensions and the measurement subsequently reached 1,746 inventoried / 1,746 supplied. This establishes the principle that source-admission completeness is an observable engineering boundary, not an assumption.

---

## 7.6 Human Review and Authorization Boundary

CYDRA is intended to minimize the amount of continuous human assistance required during an investigation while preserving explicit human authority at consequential boundaries.

The human researcher remains the **principal authority**. CYDRA should perform routine discovery, modeling, reasoning, testing preparation, validation, evidence organization, and recovery autonomously within the authority already granted to it.

Human review/authorization should be concentrated at boundaries where a human decision materially changes authority, risk, or external consequence, including where applicable:

- granting or confirming authority for active testing;
- approving actions that could materially affect external systems or assets;
- approving promotion of a newly learned observer when its consequences are not fully covered by automated validation;
- reviewing a high-impact or ambiguous interpretation;
- authorizing final bounty submission/publication;
- overriding a CYDRA uncertainty or rejected claim.

Routine mechanical work should not require the human to manually guide every parser call, compiler invocation, graph edge, hypothesis update, or test selection when those operations are already bounded by CYDRA's validated capabilities and authority model.

The desired operating pattern is:

`CYDRA discovers/reasons → assistant helps interpret when needed → CYDRA validates → CYDRA continues → human reviews/authorizes consequential boundary`

Human review is therefore a **control boundary**, not CYDRA's substitute for reasoning.

---

## 8. System Understanding

Before serious vulnerability reasoning, CYDRA should model:

- components and modules;
- functions and interfaces;
- state and state transitions;
- data flow;
- control flow;
- trust boundaries;
- privileged roles;
- attacker-controlled inputs;
- external calls and callbacks;
- token/value flows;
- oracle dependencies;
- upgrade paths;
- initialization and ownership;
- emergency controls;
- deployment boundaries;
- off-chain/on-chain boundaries;
- failure modes;
- security invariants.

The goal is not to create a visually impressive graph. The goal is to build a model that supports falsifiable security reasoning.

---

## 9. Invariant Lifecycle

Security invariants are hypotheses about what must remain true for the system's intended security properties to hold.

Lifecycle:

`candidate → evidence collection → supported / contradicted / unresolved`

Only sufficiently supported invariants may feed the verified security-hypothesis bridge.

Probability/ranking alone does not establish semantic resolution. Explicit evidentiary polarity and provenance must remain separate from confidence/probability.

---

## 10. Competing Hypotheses and Information Gain

CYDRA should avoid immediately committing to the first plausible vulnerability explanation.

For a security question, maintain competing hypotheses where appropriate and choose observations/tests that most efficiently distinguish them.

The preferred investigation loop is:

`Question → competing hypotheses → candidate observations → information gain → authorized test → observation → evidence → belief update`

The best next action is the one that most reduces uncertainty while remaining authorized, reproducible, and proportionate.

---

## 10.5 Variant-Based Real-World Validation

A security observation is not a vulnerability merely because static reasoning identifies suspicious behavior. CYDRA validates important security hypotheses through independently meaningful variants of the relevant system state and execution conditions.

Principle: **Do not trust one experiment. Vary the conditions that the SystemModel and hypothesis identify as causally relevant, then determine whether the predicted security behavior survives those variants.**

A variant is a deliberate change to a relevant state, input, ordering, boundary condition, dependency, or execution condition. Variants must be justified by evidence-backed SystemModel relationships rather than generated as an arbitrary vulnerability checklist. Repeating identical conditions is useful for reproducibility, but is not independent variant validation.

Supporting variants increase confidence in a causal explanation. Contradictory variants are valuable evidence: they must reduce or qualify confidence rather than be ignored.

A security claim must distinguish: observation; hypothesis; invariant; variant prediction; observed variant behavior; causal explanation; reproduced invariant violation; and final claim. Variant results must retain provenance and remain attributable to the hypothesis and execution that produced them.

Historical benchmarks may later evaluate whether frozen CYDRA reasoning survives comparison with known ground truth. Historical findings must not become an oracle during blind reasoning.

---

## 11. External Execution and Durable Evidence

Execution must have a strict lifecycle:

`Plan → persist request → obtain authority → execute through gateway → persist durable receipt → recover/rehydrate if necessary → ingest exact receipt-bound evidence`

Planning is not execution.

A missing execution receipt is not success.

Silent retries must not create ambiguous evidence lineage.

Execution results must preserve exact inputs, environment, command/test identity, outcome, and receipt/provenance sufficient for later causal analysis.

---

## 12. Evidence and Causality

CYDRA must preserve:

- evidence provenance;
- observation identity;
- evidentiary polarity;
- correlation versus causation;
- source/build identity;
- test authority;
- reproducibility.

A candidate finding should be causally traceable as:

`attacker-controlled condition → security-relevant boundary → violated invariant → observable consequence → eligible impact`

A suspicious pattern is not a verified vulnerability.

A simulated economic result is not, by itself, execution evidence.

---

## 13. Finding Eligibility Gate

A finding may be emitted only after checking, as applicable:

- authorization;
- in-scope status;
- eligible impact;
- known-issue status;
- causal validity;
- evidence sufficiency;
- PoC sufficiency;
- reproducibility.

The engine should prefer **no finding** over an unsupported finding.

Known issues must have explicit statuses rather than an undifferentiated historical list.

---

## 14. Finding and PoC Lineage

The durable lineage should be:

`ProgramContract → SystemModel → Invariant → Hypothesis → Observation → Evidence → CausalTrace → Impact → Finding → PoC`

A PoC is a causal demonstration, not a decorative attachment.

A bounty-ready PoC should preserve:

- prerequisites;
- setup;
- exact steps;
- expected behavior;
- actual behavior;
- evidence;
- causal explanation;
- impact;
- reproducibility information.

Publication is another trust boundary. CYDRA should not confuse an internally verified result with a successfully submitted or accepted bounty report.

---

## 15. Learning Doctrine

Learning from historical findings, audits, benchmarks, and prior programs is allowed and encouraged for improving reasoning.

Learning must not:

- silently expand testing authority;
- convert a historical pattern into a current vulnerability claim;
- replace current evidence;
- become a shortcut that bypasses current-system understanding.

Historical material should improve hypothesis generation, prioritization, and evaluation—not provide an oracle for the current target.

---

## 16. Development Doctrine

Every implementation change must identify:

1. the real system boundary being implemented or repaired;
2. the invariant or contract it must preserve;
3. how the live contest exercises that boundary;
4. the regression proof required;
5. any change to authority or uncertainty semantics;
6. the discovery/reasoning capability gained.

Avoid architecture work that cannot be connected to a measurable research capability.

The first live contest is the integration environment. The code should evolve where reality exposes a missing boundary, not where speculative abstraction seems attractive.

---

## 17. Milestones

### M0 — Bible + Live Target
Establish the canonical doctrine and select a live contest.

### M1 — Live Program Acquisition
Acquire and fingerprint the current program context.

### M2 — Resource Graph
Follow relevant references and build the provenance-preserving dependency graph.

### M3 — Exact Source/Build
Resolve repository identity, audited revision, build system, dependencies, compiler/runtime/toolchain, and reproducibility.

### M4 — System Reconstruction
Construct the canonical system model and architecture relationships.

### M5 — Security Reasoning
Generate supported invariants and competing security hypotheses.

### M6 — High-Information Investigation
Plan and perform authorized observations/tests selected for information gain.

### M7 — Causal Verification
Bind observations to violated invariants and observable security consequences.

### M8 — Finding Eligibility
Apply authorization, scope, impact, known-issue, evidence, and reproducibility gates.

### M9 — Reproducible Finding
Produce a bounty-ready finding and step-by-step PoC when a real bug is verified.

### M10 — Live-Contest Evaluation
Evaluate CYDRA's complete chain against the live contest without using historical findings as a shortcut/oracle.

### M11 — Adaptive Observation Capability
Demonstrate that CYDRA can detect an observation-capability gap, determine the target ecosystem/toolchain requirements, use assistant support when helpful, construct or adapt an observer, validate it against independently checkable observations, and preserve uncertainty when validation is insufficient.

---

## 18. Definition of Done for the First Live Contest

The first live-contest implementation is complete when CYDRA can demonstrate a connected, provenance-preserving chain from:

`live Immunefi program → authoritative program contract → exact source/build → system model → supported invariants → competing hypotheses → high-information observation → causal verification → eligibility gate → reproducible PoC → bounty-ready finding`

Finding no bug is not a failure if the investigation was correct and evidence-backed.

Claiming an unsupported bug is a failure.

---

## 19. Boundaries to Actively Stress-Test

The first live integration should deliberately exercise:

- live program intake;
- linked-reference following;
- source/build identity;
- audited-revision binding;
- variant selection;
- heuristic fallback safety;
- exact call/write evidence;
- overloaded-function handling;
- system model → invariants;
- invariants → hypotheses;
- hypotheses → observations;
- execution receipt → evidence ingestion;
- causal verification → finding eligibility;
- live scope/impact/known-issue checks;
- PoC generation;
- recovery after interrupted work;
- language/toolchain detection;
- source-admission completeness;
- observer capability gaps;
- observer validation and promotion;
- assistant-derived implementation guidance versus independently validated evidence;
- human authorization at consequential boundaries.

These are research-critical boundaries, not merely engineering details.

---

## 20. Immediate Next Boundary

**Next implementation boundary:** take the live ENS Immunefi contest and produce a fresh, provenance-preserving canonical `ProgramContract` plus its relevant resource graph without inventing authority.

If this boundary works, proceed to exact source/build acquisition.

If it fails, repair the boundary before adding downstream reasoning features.

---

## 21. Change Control

This Bible is a living document and the canonical working source of truth for CYDRA.

Every material change to:

- architecture;
- workflow;
- target strategy;
- authority semantics;
- reasoning doctrine;
- milestone definition;
- evidence semantics;
- development doctrine

must update this Bible and `UPDATE_LOG.md`.

Each update should record:

- version;
- date;
- reason;
- affected boundary/modules;
- tests/validation;
- resulting capability;
- unresolved risks where relevant.

Important historical snapshots must remain recoverable. Do not silently rewrite history.

A ZIP export is a snapshot only; the extracted repository Bible is the current working truth.

---

## 22. Success Criterion

CYDRA succeeds by becoming measurably better at:

- understanding real systems;
- constructing defensible security invariants;
- generating useful competing hypotheses;
- choosing high-information observations;
- preserving uncertainty and provenance;
- proving causality;
- avoiding unsupported claims;
- producing reproducible evidence;
- finding real bounty-eligible vulnerabilities.

The ultimate test is not how much code CYDRA contains.

It is whether CYDRA can understand a real authorized target well enough to discover and prove something that was not obvious before the investigation began.
