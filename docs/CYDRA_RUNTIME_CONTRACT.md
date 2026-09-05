# CYDRA Runtime Contract

This document describes the executable runtime boundary implemented in `cydra/runtime.py`, `cydra/target_environment.py`, and `cydra/doctor.py`.

## Base runtime

The first supported production profile is Ubuntu running under PRoot. The runtime doctor verifies Linux, Ubuntu, PRoot, Python, and Git. It does not install software and does not execute target-supplied commands.

Run:

```bash
python -m cydra.runtime
python -m cydra.doctor
```

A runtime is `READY` only when all required base capabilities are present.

## Target environment

After authorized project intake and source acquisition, CYDRA can inspect the target checkout for declared requirements from common manifests including `package.json`, package-manager declarations, Node version files, lockfiles, `foundry.toml`, and `Cargo.toml`.

Run:

```bash
python -m cydra.doctor --target /path/to/target
```

Target declarations are evidence about prerequisites, not authority. CYDRA reports missing or incompatible capabilities but does not silently install arbitrary target software.

## Boundary semantics

`CYDRA runtime READY` does not mean `target reproducible`.

`target requirements discovered` does not mean `target requirements satisfied`.

`target requirements satisfied` does not mean `source identity verified`.

`source/build verified` does not grant testing authority beyond the live ProgramContract.

The resulting chain is:

`base runtime → live program intake → target requirements → capability verification → source/build identity → SystemModel → security reasoning`

## Portability

PRoot Ubuntu is the first supported production environment because it is the current user runtime. The CYDRA reasoning model must remain independent of that substrate so native Linux, isolated VMs/containers, CI runners, and other authorized execution backends can be added later.
