from __future__ import annotations

import hashlib
import json
import os
import platform
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional


def run(cmd: List[str], cwd: Optional[str] = None, env: Optional[Dict[str, str]] = None) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=cwd, env=env, text=True, capture_output=True)


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_file(path: str, chunk_size: int = 1024 * 1024) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            h.update(chunk)
    return h.hexdigest()


def detect_python(project_root: str) -> Dict[str, Any]:
    candidates: List[Path] = []
    root = Path(project_root)
    for rel in [".venv/bin/python", "venv/bin/python", "env/bin/python"]:
        p = root / rel
        if p.exists():
            candidates.append(p)

    conda_prefix = os.environ.get("CONDA_PREFIX")
    if conda_prefix:
        p = Path(conda_prefix) / "bin/python"
        if p.exists():
            candidates.append(p)

    current = shutil.which("python") or shutil.which("python3")
    if current:
        candidates.append(Path(current))

    if not candidates:
        raise RuntimeError("No Python executable found")

    python_path = str(candidates[0].resolve())
    cp = run([python_path, "-c", "import sys; print(sys.version.split()[0]); print(sys.prefix)"])
    if cp.returncode != 0:
        raise RuntimeError(cp.stderr.strip())
    lines = cp.stdout.strip().splitlines()
    version = lines[0] if lines else "unknown"
    prefix = lines[1] if len(lines) > 1 else str(Path(python_path).parent.parent)

    env_type = "system"
    if "conda" in prefix.lower() or os.path.exists(os.path.join(prefix, "conda-meta")):
        env_type = "conda"
    elif os.path.exists(os.path.join(prefix, "pyvenv.cfg")):
        env_type = "venv"

    return {"type": env_type, "python": python_path, "prefix": prefix, "version": version}


def pip_freeze(python_path: str) -> str:
    cp = run([python_path, "-m", "pip", "freeze"])
    if cp.returncode != 0:
        return ""
    return "\n".join(sorted(line.strip() for line in cp.stdout.splitlines() if line.strip()))


def package_map(python_path: str) -> Dict[str, str]:
    cp = run([python_path, "-c", "import json, importlib.metadata as m; print(json.dumps({d.metadata['Name'].lower(): d.version for d in m.distributions() if d.metadata.get('Name')}))"])
    if cp.returncode != 0:
        return {}
    return json.loads(cp.stdout)


def conda_explicit(prefix: str) -> str:
    conda = shutil.which("conda")
    if not conda:
        return ""
    cp = run([conda, "list", "--explicit", "-p", prefix])
    return cp.stdout if cp.returncode == 0 else ""


def environment_fingerprint(binding: Dict[str, Any]) -> Dict[str, Any]:
    python_path = binding["python"]
    prefix = binding.get("prefix", "")
    freeze = pip_freeze(python_path)
    explicit = conda_explicit(prefix) if binding.get("type") == "conda" else ""
    return {
        "python_version": binding.get("version"),
        "python_path": python_path,
        "pip_freeze_sha256": sha256_text(freeze),
        "conda_explicit_sha256": sha256_text(explicit) if explicit else None,
        "platform": platform.platform(),
    }


def scan_environment(project_root: str) -> Dict[str, Any]:
    py = detect_python(project_root)
    packages = package_map(py["python"])
    selected_env = {k: v for k, v in os.environ.items() if k.startswith(("CUDA_", "PYTHON", "TOKENIZERS_", "OMP_", "MKL_"))}
    return {
        "environment": {
            "id": f"env://{Path(project_root).name}",
            "binding": {
                "host": "local",
                "type": py["type"],
                "prefix": py["prefix"],
                "python": py["python"],
                "project_root": str(Path(project_root).resolve()),
                "working_directory": str(Path(project_root).resolve()),
            },
            "manifest": {
                "python": py["version"],
                "packages": packages,
                "env_vars": selected_env,
            },
            "fingerprint": environment_fingerprint(py),
            "repair_policy": {
                "mode": "conservative",
                "auto_allowed": [
                    "create_missing_directory",
                    "install_missing_python_package_exact_version",
                ],
                "require_confirmation": [
                    "downgrade_python_package",
                    "replace_drifted_python_package",
                    "reinstall_torch",
                    "change_behavioral_env_var",
                ],
                "forbidden": [
                    "silently_replace_environment",
                    "silently_change_major_version",
                    "modify_cuda",
                    "modify_system_library",
                    "overwrite_checkpoint",
                    "mutate_raw_data",
                ],
            },
        }
    }


def verify_environment(cfg: Dict[str, Any]) -> Dict[str, Any]:
    e = cfg["environment"]
    b = e["binding"]
    manifest = e.get("manifest", {})
    result: Dict[str, Any] = {"binding_found": True, "issues": [], "status": "PASS"}

    if not os.path.exists(b["python"]):
        result["binding_found"] = False
        result["issues"].append({"type": "missing_python", "path": b["python"], "severity": "dangerous"})
        result["status"] = "FAIL"
        return result

    current_packages = package_map(b["python"])
    expected = {str(k).lower(): str(v) for k, v in manifest.get("packages", {}).items()}
    for name, version in expected.items():
        actual = current_packages.get(name)
        if actual is None:
            result["issues"].append({"type": "missing_package", "package": name, "expected": version, "severity": "safe"})
        elif actual != version:
            result["issues"].append({"type": "package_drift", "package": name, "expected": version, "actual": actual, "severity": "caution"})

    if result["issues"]:
        result["status"] = "WARN"
    return result


def repair_safe_issues(cfg: Dict[str, Any], verification: Dict[str, Any]) -> Dict[str, Any]:
    e = cfg["environment"]
    python_path = e["binding"]["python"]
    actions = []
    for issue in verification.get("issues", []):
        if issue.get("type") == "missing_package" and issue.get("severity") == "safe":
            pkg = issue["package"]
            ver = issue["expected"]
            cmd = [python_path, "-m", "pip", "install", f"{pkg}=={ver}"]
            cp = run(cmd)
            actions.append({
                "issue": issue,
                "command": cmd,
                "returncode": cp.returncode,
                "stdout": cp.stdout[-4000:],
                "stderr": cp.stderr[-4000:],
                "rollback": [python_path, "-m", "pip", "uninstall", "-y", pkg],
            })
    return {"actions": actions, "status": "PASS" if all(a["returncode"] == 0 for a in actions) else "FAIL"}
