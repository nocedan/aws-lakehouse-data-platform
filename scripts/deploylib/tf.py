"""Terraform wrappers: run stages and read outputs.

All other stages discover endpoints/names via get_outputs() instead of
hardcoding them, so terraform stays the single source of truth.
"""

import json
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
TERRAFORM_DIR = REPO_ROOT / "terraform"


def _run(args: list[str]) -> None:
    subprocess.run(
        ["terraform", f"-chdir={TERRAFORM_DIR}", *args], check=True
    )


def init() -> None:
    _run(["init", "-input=false"])


def validate() -> None:
    _run(["validate"])


def apply(auto_approve: bool = False) -> None:
    args = ["apply"]
    if auto_approve:
        args.append("-auto-approve")
    _run(args)


def parse_outputs(raw_json: str) -> dict:
    """Parse `terraform output -json` into a flat {name: value} dict."""
    return {name: item["value"] for name, item in json.loads(raw_json).items()}


def get_outputs() -> dict:
    proc = subprocess.run(
        ["terraform", f"-chdir={TERRAFORM_DIR}", "output", "-json"],
        check=True,
        capture_output=True,
        text=True,
    )
    outputs = parse_outputs(proc.stdout)
    if not outputs:
        raise RuntimeError(
            "no terraform outputs found — deploy the infrastructure first"
            " (python scripts/deploy.py infra)"
        )
    return outputs
