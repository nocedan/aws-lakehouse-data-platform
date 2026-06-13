"""dbt configuration and execution.

The repo-root profiles.yml is the template: its `host` holds a placeholder
(REPLACED_BY_DEPLOY_CLI) that gets replaced with the real Redshift Serverless
endpoint from terraform outputs, and the result is written to ~/.dbt/.
"""

import subprocess
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
PROFILES_TEMPLATE = REPO_ROOT / "profiles.yml"
DBT_PROJECT_DIR = REPO_ROOT / "dvdrentals"
HOST_PLACEHOLDER = "REPLACED_BY_DEPLOY_CLI"


def render_profiles(template_text: str, redshift_host: str) -> str:
    profiles = yaml.safe_load(template_text)
    profiles["dvdrentals"]["outputs"]["dev"]["host"] = redshift_host
    return yaml.safe_dump(profiles, sort_keys=False)


def configure_profiles(
    redshift_host: str, dbt_dir: Path | None = None
) -> Path:
    target_dir = dbt_dir if dbt_dir is not None else Path.home() / ".dbt"
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / "profiles.yml"
    target.write_text(
        render_profiles(PROFILES_TEMPLATE.read_text(), redshift_host)
    )
    return target


def run_dbt(*args: str) -> None:
    subprocess.run(["dbt", *args], cwd=DBT_PROJECT_DIR, check=True)
