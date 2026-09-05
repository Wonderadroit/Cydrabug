# CYDRA Runtime Contract

This document describes the executable runtime boundary implemented in `cydra/runtime.py`, `cydra/target_environment.py`, `cydra/doctor.py`, and `cydra/bootstrap.py`.

## Base runtime

The first supported production profile is Ubuntu running under PRoot. The Termux/Android host is the bootstrap substrate, not the CYDRA production userspace.

The runtime doctor verifies Linux userspace, Ubuntu, PRoot, Python, and Git. It does not install software and does not execute target-supplied commands.

Run from the CYDRA checkout:

```bash
python -m cydra.bootstrap --status
python -m cydra.bootstrap --doctor
python -m cydra.bootstrap --shell
```

The bootstrap uses PRoot-Distro's shared-home mechanism when the checkout is under the host home directory and an explicit bind when it is elsewhere. This makes the exact CYDRA checkout available inside the Ubuntu userspace without copying or silently changing its contents.

CYDRA-owned base prerequisites may be installed only through the explicit operator action:

```bash
python -m cydra.bootstrap --install-base
```

That action is limited to CYDRA's declared base packages. It must never be reused as an arbitrary target dependency installer.

Inside Ubuntu, the runtime doctor is invoked with `python3` because Ubuntu does not guarantee a `python` alias:

```bash
python3 -m cydra.runtime
python3 -m cydra.doctor
```

A runtime is `READY` only when all required base capabilities are present.

## Target environment

After authorized project intake and source acquisition, CYDRA can inspect the target checkout for declared requirements from common manifests including `package.json`, package-manager declarations, Node version files, lockfiles, `foundry.toml`, and `Cargo.toml`.

Run inside the verified CYDRA runtime:

```bash
python3 -m cydra.doctor --target /path/to/target
```

Target declarations are evidence about prerequisites, not authority. CYDRA reports missing or incompatible capabilities but does not silently install arbitrary target software.

## Boundary semantics

`CYDRA runtime READY` does not mean `target reproducible`.

`target requirements discovered` does not mean `target requirements satisfied`.

`target requirements satisfied` does not mean `source identity verified`.

`source/build verified` does not grant testing authority beyond the live ProgramContract.

The resulting chain is:

`host bootstrap → PRoot Ubuntu runtime → live program intake → target requirements → capability verification → source/build identity → SystemModel → security reasoning`

## Portability

PRoot Ubuntu is the first supported production environment because it is the current user runtime. The CYDRA reasoning model must remain independent of that substrate so native Linux, isolated VMs/containers, CI runners, and other authorized execution backends can be added later.
