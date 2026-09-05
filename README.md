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

## Runtime and target environment

CYDRA has an executable environment boundary rather than relying on documentation alone.

The first supported mobile production profile is **Ubuntu under PRoot**. The Termux host is not itself the CYDRA production runtime; CYDRA must run inside the Ubuntu userspace.

### Bootstrap into the supported Ubuntu runtime

From the CYDRA checkout in Termux:

```bash
python -m cydra.bootstrap --status
python -m cydra.bootstrap --doctor
python -m cydra.bootstrap --shell
```

The bootstrap uses PRoot-Distro's shared-home or explicit bind mechanism to make the CYDRA checkout available inside Ubuntu. It does not install arbitrary target software.

To explicitly install CYDRA-owned base prerequisites in the Ubuntu container:

```bash
python -m cydra.bootstrap --install-base
```

This is an operator-approved bootstrap action. It installs only CYDRA's declared base packages (`python3`, `python3-venv`, `git`, and `ca-certificates`). Target-specific dependencies remain a later, separately verified requirement step.

### Runtime checks

Inside the supported Ubuntu runtime:

```bash
python3 -m cydra.runtime
python3 -m cydra.doctor
```

After a target checkout has been acquired through the authorized intake flow:

```bash
python3 -m cydra.doctor --target /path/to/target
```

The target environment detector reads repository declarations such as `package.json`, lockfiles, `.nvmrc`, `foundry.toml`, and `Cargo.toml`, then reports missing or incompatible capabilities. It does **not** automatically install arbitrary target-supplied software or treat a declaration as testing authority.

Native Linux and other isolated execution backends can be added without changing CYDRA's reasoning model.

## Immediate next step

Validate the PRoot Ubuntu bootstrap and runtime boundary, then continue ENS source/build verification. A target is not considered reproducible merely because its declared dependencies can be installed.

See the Project Bible for the full development doctrine, milestones, authorization boundaries, evidence rules, and definition of done.
