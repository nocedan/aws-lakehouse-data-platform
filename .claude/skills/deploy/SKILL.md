---
name: deploy
description: "Use this skill when the user invokes /deploy, asks to \"deploy the platform\", \"walk me through deployment\", \"deploy infrastructure\", or wants step-by-step guidance to bring up the AWS lakehouse from scratch."
allowed-tools:
  - Bash
  - Read
  - AskUserQuestion
---

Deployment is automated by `scripts/deploy.py` (see
`automated-deployment-instructions.md`). Drive that CLI rather than running
the underlying commands by hand; fall back to the manual procedure in
`deployment-instructions.md` only if the CLI is unavailable or a stage needs
debugging.

## Step 0 — Python environment

Check whether the `dbt-env` (or `dbt-prod-env`, interchangeable) conda
environment exists:

```bash
conda env list
```

If it does not exist, tell the user to run:
```bash
conda create -n dbt-env python=3.11.15
```

Install dependencies and confirm the test suite passes:
```bash
conda run -n dbt-env pip install -r requirements.txt
conda run -n dbt-env pip install -r requirements-dev.txt
conda run -n dbt-env python -m pytest tests/ -v
```

All tests must pass before continuing.

## Step 1 — Preflight

```bash
conda run -n dbt-env python scripts/deploy.py check
```

This verifies terraform, docker (daemon running — required because terraform
builds the restore-Lambda image), dbt, and AWS credentials. Also confirm the
region:

```bash
aws configure get region
```

If it is not `us-west-2`, remind the user any region change must also be made
in `terraform/variables.tf` and `profiles.yml`.

## Step 2 — Infrastructure + data pipeline

```bash
conda run -n dbt-env python scripts/deploy.py all
```

This runs: terraform apply (the user will be prompted to confirm the plan) →
RDS restore via the in-VPC Lambda (no CloudShell needed) → Glue ingestion with
polling. It stops after ingestion and prints the Lake Formation checkpoint.

If the user prefers to review stages one at a time, run `infra`,
`restore-db`, and `ingest` individually.

## Step 3 — Manual Lake Formation grants

The `all` command prints the exact principals and S3 location. Use
AskUserQuestion to pause:
"Have you completed the Lake Formation grants in the Console? Reply yes to continue."
Do not proceed until the user confirms.

## Step 4 — dbt star schema

```bash
conda run -n dbt-env python scripts/deploy.py resume
```

This verifies the Lake Formation grants with a Spectrum smoke query (helpful
error + instructions if they are missing), writes `~/.dbt/profiles.yml` from
terraform outputs, runs `dbt debug`, then `dbt deps` and
`dbt run --select starschemamodel`. On success the `starschema` tables are
queryable in the Redshift Query Editor v2.
