# AWS Data Engineering Batch Platform — Automated Deployment

This guide covers the automated deployment via `scripts/deploy.py`. Every step
of the [manual guide](deployment-instructions.md) is automated **except the
Lake Formation grants** (Step 5 there), which AWS requires to be done in the
Console. The manual guide remains the reference for doing everything by hand.

## Requirements

- AWS Account with CLI configured (`aws configure`, region `us-west-2`)
- **Docker** (daemon running — `terraform apply` builds the restore Lambda image)
- Python 3.11.15 (Miniconda), Terraform ≥ 1.4
- The conda environment with project dependencies:

```bash
conda create -n dbt-env python=3.11.15
conda activate dbt-env
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

All commands below run from the repo root inside that environment.

## TL;DR

```bash
python scripts/deploy.py all      # infra → restore RDS → Glue ingest, then stops
# ... do the manual Lake Formation grants (instructions are printed) ...
python scripts/deploy.py resume   # verify grants → configure dbt → build star schema
```

## What `all` does

1. **`check`** — preflight: terraform/docker/dbt/aws on PATH, Docker daemon
   running, AWS credentials valid.
2. **`infra`** — `terraform init / validate / apply` in `terraform/`. This now
   also builds and pushes the **restore Lambda** container image
   (`lambda/restore_db/`) to ECR and deploys it into the VPC private subnets.
   Add `--auto-approve` to skip the terraform confirmation prompt.
3. **`restore-db`** — invokes the Lambda synchronously. Because it runs inside
   the VPC, it can reach the private-subnet RDS instance: it downloads
   `dvdrental.zip` from S3, runs `pg_restore` (same flags as the manual
   CloudShell procedure, including `sslmode=verify-full`), and verifies that
   ≥ 15 tables exist in schema `public`. No CloudShell needed.
4. **`ingest`** — starts the Glue job (name read from terraform outputs) and
   polls every 30 s until `SUCCEEDED` (fails loudly on
   `FAILED/ERROR/TIMEOUT/STOPPED`).

It then **stops on purpose** and prints the Lake Formation checkpoint with the
exact principals (your IAM identity ARN and the `redshift-spectrum-role` ARN)
and the S3 location to grant. Perform those grants in the Console as described
in [deployment-instructions.md Step 5](deployment-instructions.md#step-5--configure-lake-formation-permissions).

## What `resume` does

1. **`verify-lf`** — runs `SELECT 1 FROM "awsdatacatalog"."dvdrentals"."film"
   LIMIT 1` through the **Redshift Data API** (pure HTTPS — no port-5439 or
   local-firewall issues). This exercises the actual Lake Formation grants; if
   they are missing it reprints the checkpoint instructions and exits 1.
2. **`configure-dbt`** — reads the real Redshift Serverless endpoint from
   `terraform output`, fills it into the repo `profiles.yml` template (whose
   `host` is the placeholder `REPLACED_BY_DEPLOY_CLI`), writes
   `~/.dbt/profiles.yml`, and runs `dbt debug`.
3. **dbt build** — `dbt deps` + `dbt run --select starschemamodel` in
   `dvdrentals/`, producing `dim_film`, `dim_customer`, `dim_dates`, and
   `fact_rentals` in Redshift schema `starschema`.

## Subcommand reference

Every stage is idempotent and can be run standalone:

| Command | Purpose |
|---|---|
| `python scripts/deploy.py check` | Preflight checks only |
| `python scripts/deploy.py infra [--auto-approve]` | Terraform init/validate/apply |
| `python scripts/deploy.py restore-db` | Re-run the RDS restore (safe: `--clean --if-exists`) |
| `python scripts/deploy.py ingest` | Re-run Glue ingestion and wait |
| `python scripts/deploy.py verify-lf` | Check the Lake Formation grants |
| `python scripts/deploy.py configure-dbt` | Rewrite `~/.dbt/profiles.yml` + `dbt debug` |
| `python scripts/deploy.py run-dbt` | `verify-lf`, then `dbt deps` + `dbt run` |

The CLI never hardcodes endpoints or names: every stage reads
`terraform -chdir=terraform output -json` (Lambda name, Glue job name,
Redshift workgroup/endpoint, region), so terraform stays the single source of
truth.

## Testing

```bash
conda run -n dbt-env python -m pytest tests/ -v
```

Runs without AWS credentials, Docker, or Spark: covers the ETL job config
(`tests/test_etl_job.py`) plus the CLI and Lambda handler logic
(`tests/test_deploy_cli.py` — terraform output parsing, profiles templating,
Glue polling, Lambda invoke error handling, pg_restore flags and verification).

## Troubleshooting

- **`docker daemon not running` in `check`/`infra`** — start Docker; the
  image build runs as a terraform `local-exec` provisioner during apply.
- **`restore-db` hangs ~30 s before output** — first invocation of a VPC
  Lambda has a cold start while the ENI attaches; this is normal.
- **`verify-lf` fails after you did the grants** — confirm both principals
  (your IAM user *and* `redshift-spectrum-role`) have Data Location access to
  `s3://terraform-data-lake-bucket` *and* table+column grants on database
  `dvdrentals`, then re-run.
- **`configure-dbt` / `dbt debug` fails** — make sure your IP is allowed by
  the `authorized_ips` variable in `terraform/variables.tf`; `dbt` connects
  directly to the workgroup endpoint on port 5439.
- **Changed the Lambda handler or Dockerfile?** — the image tag is a content
  hash; the next `terraform apply` rebuilds and repoints the Lambda
  automatically.
