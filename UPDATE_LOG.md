# CYDRA UPDATE LOG

## 2026-09-04 — v2.0.0-live-contest

### Change
Established the live-contest development edition of CYDRA in the new canonical repository `Wonderadroit/cydrabug`.

### Strategic decision
CYDRA will be built and validated against a real, currently live Immunefi contest rather than relying only on toy targets or historical examples.

### Initial target
Selected the ENS Audit Competition as the first live integration target.

### Why this target
The contest exercises a broad set of CYDRA capabilities: live program intake, scope/rules extraction, linked resources, exact source/revision handling, build/toolchain discovery, system understanding, PoC requirements, and finding eligibility.

### Non-negotiable interpretation
The live contest is an integration target and reality test, not a vulnerability oracle. Historical findings and benchmarks may inform learning/evaluation but cannot substitute for current-system evidence.

### Current next boundary
Acquire the live ENS program context and construct a provenance-preserving canonical `ProgramContract` plus relevant resource dependency graph.

### Validation
Live contest status and the initial contest/resource snapshot were checked against current Immunefi pages on 2026-09-04.

### Next update triggers
Update this log whenever there is a material:

- architectural change;
- workflow/boundary change;
- contest-context change;
- milestone completion;
- repaired security/reasoning boundary;
- doctrine or authority-semantics change.
