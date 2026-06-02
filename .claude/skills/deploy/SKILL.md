---
name: deploy
description: "Use this skill when the user invokes /deploy, asks to \"deploy the platform\", \"walk me through deployment\", \"deploy infrastructure\", or wants step-by-step guidance to bring up the AWS lakehouse from scratch."
allowed-tools:
  - Bash
  - Read
  - AskUserQuestion
---

## Step 0 — Python environment

Check whether the `dbt-prod-env` or `dbt-env` (use interchangeably) conda environment exists:

```bash
conda env list
```

If it does not exist, tell the user to run:
```bash
conda create -n dbt-prod-env python=3.11.15
```

Install dependencies inside the environment:
```bash
conda run -n dbt-prod-env pip install -r requirements.txt
conda run -n dbt-prod-env pip install -r requirements-dev.txt
```

Confirm pytest works by running:
```bash
conda run -n dbt-prod-env pytest tests/ -v
```

All 9 tests must pass before continuing.

---

## Step 1 — Configure AWS CLI

Check current AWS identity and region:

```bash
aws sts get-caller-identity
aws configure get region
```

If the region is not `us-west-2`, tell the user to run:
```bash
aws configure set region us-west-2
```

Remind the user that any region change must also be updated in `terraform/variables.tf`.

---

## Step 2 — Deploy infrastructure with Terraform

```bash
cd terraform
terraform init
terraform validate
terraform plan
```

Show the user the plan output and ask them to confirm before applying.
Once confirmed:

```bash
terraform apply
```

Wait for apply to complete. Check for errors. Remind the user that after apply,
Lake Formation permissions must be granted manually (but that step is out of scope here).

---

## Step 3 — Load the PostgreSQL sample database

### 3.1 Verify the backup is in S3

```bash
aws s3 ls s3://terraform-data-lake-bucket/rds-database-backups/dvdrental.zip
```

If the file is not present, tell the user to upload `dvdrental.zip` to that S3 path before continuing.

### 3.2 Restore the database via CloudShell

The RDS instance is on a private subnet — it cannot be reached from a local machine.
Tell the user to:

1. Open the AWS Console and navigate to **Aurora and RDS > Databases > dvdrentals-database**
2. Open **CloudShell** from that page
3. Run the following commands in CloudShell:

```bash
aws s3 cp s3://terraform-data-lake-bucket/rds-database-backups/dvdrental.zip .
unzip dvdrental.zip

pg_restore \
  --no-owner \
  --no-privileges \
  --clean \
  --if-exists \
  -d "host=dvdrentals-database.cbia4semc2rv.us-west-2.rds.amazonaws.com \
  port=5432 \
  user=postgres_master_user \
  dbname=dvdrentals \
  sslmode=verify-full \
  sslrootcert=/certs/global-bundle.pem" \
  dvdrental.tar
```

After giving the user the CloudShell commands above, use AskUserQuestion to pause and ask:
"Have you completed the pg_restore in CloudShell? Reply yes to continue to the verification step."
Do not proceed to Step 3.3 until the user confirms.

### 3.3 Verify the restore

Still in CloudShell, connect to the DB and confirm the tables exist:

```bash
psql \
  --host=dvdrentals-database.cbia4semc2rv.us-west-2.rds.amazonaws.com \
  --port=5432 \
  --username=postgres_master_user \
  --password \
  --dbname=dvdrentals
```

```sql
\c dvdrentals
\dt
```

Expected output includes at minimum: `category`, `customer`, `film`, `film_category`, `inventory`, `rental`.

Ask the user to confirm the tables are present before continuing.

---

## Step 4 — Run the Glue ingestion job

Trigger the job:

```bash
aws glue start-job-run --job-name dvdrentals-extraction-tf
```

Capture the `JobRunId` from the response and poll for completion:

```bash
aws glue get-job-run --job-name dvdrentals-extraction-tf --run-id <JobRunId>
```

Look for `"JobRunState": "RUNNING"` transitioning to `"JobRunState": "SUCCEEDED"`.
Poll every 30–60 seconds until the job finishes. If the state is `"FAILED"` or `"ERROR"`,
show the user the `ErrorMessage` field from the response.

Once the job reaches `SUCCEEDED`, confirm to the user that the landing layer is populated
and that they are ready to proceed with Lake Formation permissions and dbt (out of scope for this command).
