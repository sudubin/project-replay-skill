from __future__ import annotations

import argparse
import json

import yaml

from .core import repair_safe_issues, scan_environment, verify_environment
from .replay import execute_workflow


def load_yaml(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def dump_yaml(obj, path: str):
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(obj, f, sort_keys=False, allow_unicode=True)


def main():
    parser = argparse.ArgumentParser(prog="project-replay")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("scan")
    p.add_argument("--project-root", required=True)
    p.add_argument("--output", default="environment_binding.yaml")

    p = sub.add_parser("verify")
    p.add_argument("--binding", required=True)

    p = sub.add_parser("repair")
    p.add_argument("--binding", required=True)

    p = sub.add_parser("replay")
    p.add_argument("--binding", required=True)
    p.add_argument("--workflow", required=True)

    args = parser.parse_args()

    if args.cmd == "scan":
        cfg = scan_environment(args.project_root)
        dump_yaml(cfg, args.output)
        print(args.output)
    elif args.cmd == "verify":
        print(json.dumps(verify_environment(load_yaml(args.binding)), indent=2, ensure_ascii=False))
    elif args.cmd == "repair":
        cfg = load_yaml(args.binding)
        v = verify_environment(cfg)
        print(json.dumps(repair_safe_issues(cfg, v), indent=2, ensure_ascii=False))
    elif args.cmd == "replay":
        print(json.dumps(execute_workflow(load_yaml(args.binding), load_yaml(args.workflow)), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
