from __future__ import annotations

import json
import os
import subprocess
from typing import Any, Dict


def execute_workflow(binding_cfg: Dict[str, Any], workflow_cfg: Dict[str, Any]) -> Dict[str, Any]:
    env_cfg = binding_cfg["environment"]
    python_path = env_cfg["binding"]["python"]
    runtime_env = dict(os.environ)
    runtime_env.update({str(k): str(v) for k, v in env_cfg.get("manifest", {}).get("env_vars", {}).items()})

    results = []
    workflow = workflow_cfg["workflow"]
    for step in workflow.get("steps", []):
        cmd = [str(x).replace("{python}", python_path) for x in step["command"]]
        cp = subprocess.run(cmd, cwd=step.get("cwd") or env_cfg["binding"].get("working_directory"), env=runtime_env, text=True, capture_output=True)
        results.append({"name": step["name"], "command": cmd, "cwd": step.get("cwd"), "returncode": cp.returncode, "stdout": cp.stdout[-8000:], "stderr": cp.stderr[-8000:]})
        if cp.returncode != 0 and workflow.get("stop_on_error", True):
            break

    validations = []
    for rule in workflow.get("validations", []):
        if rule["type"] == "json_numeric":
            with open(rule["file"], "r", encoding="utf-8") as f:
                obj = json.load(f)
            actual = obj[rule["key"]]
            delta = abs(float(actual) - float(rule["expected"]))
            passed = delta <= float(rule["tolerance"])
            validations.append({**rule, "actual": actual, "delta": delta, "status": "PASS" if passed else "FAIL"})

    ok_steps = all(x["returncode"] == 0 for x in results)
    ok_validations = all(x["status"] == "PASS" for x in validations)
    return {"steps": results, "validations": validations, "status": "PASS" if ok_steps and ok_validations else "FAIL"}
