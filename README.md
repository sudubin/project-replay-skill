# Project Replay Skill

A stateful reproducibility skill for replaying historical projects **inside their original execution environment** whenever possible.

## Core idea

This project does not default to recreating a fresh environment. Instead it:

1. locates the original environment and project directory;
2. verifies the environment fingerprint;
3. detects drift or missing components;
4. applies only policy-approved, minimal repairs in the original environment;
5. replays the recorded workflow;
6. validates outputs against historical baselines;
7. records an auditable execution and repair log.

Environment reconstruction is a last-resort fallback only when the original environment is missing or unrecoverable.

## Quick start

```bash
python -m project_replay.cli scan --project-root /path/to/project --output environment_binding.yaml
python -m project_replay.cli verify --binding environment_binding.yaml
python -m project_replay.cli replay --binding environment_binding.yaml --workflow workflow.yaml
```

## Repository layout

- `SKILL.md` – agent orchestration instructions.
- `project_replay/` – scanner, fingerprinting, repair and replay engine.
- `config/environment_binding.example.yaml` – environment binding and repair policy.
- `config/workflow.example.yaml` – deterministic workflow definition.
- `tests/` – basic validation tests.
- `snapshots/` – optional historical environment evidence.

## Safety model

Repairs are classified as:

- `safe`: may be applied automatically;
- `caution`: require explicit approval by default;
- `dangerous`: blocked by default.

The engine should never silently replace the original environment, silently upgrade major dependencies, modify CUDA/system libraries, or overwrite checkpoints.

## Reproducibility levels

Outputs may be validated at three levels:

- exact: hashes/bytes match;
- numeric: values match within a tolerance;
- statistical: model metrics remain inside an allowed band.

## Current MVP support

- Conda environments
- Python virtual environments
- system Python bindings
- package/version fingerprinting
- environment-variable capture
- minimal pip package repair
- workflow command replay
- JSON metric validation

Future extensions can add Docker/container bindings, SSH hosts, R/renv, CUDA-level repair planning, artifact provenance graphs, and automatic project distillation from historical files.
