# Project Replay Skill

## Purpose

Replay a historical software, data-science, or research workflow in its **original execution environment** whenever that environment still exists. Preserve and verify enough environment metadata to repair missing components with the smallest safe change before execution.

## Non-negotiable principles

1. Prefer the original environment over environment recreation.
2. Treat the saved environment binding as a live reference, not merely documentation.
3. Verify the current environment against its historical manifest and fingerprint before execution.
4. Repair only missing or drifted components allowed by policy.
5. Keep repairs minimal, logged, and reversible where possible.
6. Never silently replace the environment, alter CUDA/system libraries, change major dependency versions, overwrite checkpoints, or mutate source data.
7. If the original environment is unrecoverable, stop and produce a reconstruction plan instead of automatically creating a replacement unless explicitly allowed.
8. Validate outputs against historical baselines after replay.

## Required inputs

At minimum, obtain or discover:

- project root;
- original environment type and location;
- Python executable or environment prefix;
- workflow commands and working directories;
- critical data/model/cache paths;
- historical environment evidence when available;
- expected outputs or metrics.

## Execution procedure

### 1. Discover

Inspect the project and host to determine:

- Conda/venv/system Python environment;
- environment prefix and Python executable;
- project root and working directories;
- package versions;
- environment variables relevant to execution;
- CUDA/PyTorch information when available;
- critical paths and files.

Write this to `environment_binding.yaml`.

### 2. Snapshot

Capture reproducibility evidence where possible:

- `pip freeze`;
- `conda list --explicit` for Conda;
- Python version and executable;
- selected environment variables;
- CUDA, PyTorch, and GPU metadata;
- hashes for critical configuration files;
- hashes for selected critical checkpoints or artifacts.

Do not duplicate large datasets or models unless explicitly requested.

### 3. Verify

Before every replay:

- confirm the bound host/path still exists;
- confirm the Python executable exists;
- compare current package versions with the manifest;
- calculate the current fingerprint;
- classify differences as missing, modified, or unknown.

### 4. Diagnose and repair

Apply repair policy:

**Safe examples**
- create missing output/cache directory;
- restore a declared symlink;
- install a missing pure-Python package at the exact historical version;
- restore a missing declared config from a stored snapshot.

**Caution examples**
- dependency downgrade;
- replacing a package whose version drifted;
- reinstalling PyTorch;
- modifying an existing environment variable with behavioral impact.

**Dangerous examples**
- modifying drivers, CUDA, glibc, GCC, or system libraries;
- overwriting checkpoints;
- mutating raw source data;
- silently creating a replacement environment.

For caution or dangerous actions, stop and return a repair plan unless policy explicitly permits the action.

### 5. Replay

Execute workflow steps exactly as recorded:

- use the bound Python executable directly when practical;
- use the recorded working directory;
- apply recorded environment variables;
- use recorded arguments and config files;
- stop on failed steps unless the workflow explicitly allows continuation.

### 6. Validate

Compare results with historical baselines using one or more of:

- file/hash equality;
- numeric tolerance;
- statistical tolerance.

Return PASS, WARN, or FAIL for each validation.

### 7. Record

Write an execution record containing:

- environment identity;
- pre-run verification result;
- repairs attempted and their outcomes;
- commands executed;
- return codes;
- produced outputs;
- validation results;
- overall replay status.

## Fallback behavior

If the original environment is missing or irreparably damaged:

1. do not silently create a new environment;
2. use the stored manifest and snapshots to generate a reconstruction plan;
3. clearly distinguish the reconstructed environment from the historical original;
4. only build the replacement when explicitly authorized.
