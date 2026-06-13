# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

End-to-end AWS batch data platform: **PostgreSQL (RDS) → AWS Glue (Spark/Iceberg) → S3 Data Lake → Redshift Serverless**, with dbt transforming raw data into a star schema. Terraform manages all infrastructure.

## Key Commands

### Miniconda environment

```bash
# If non existing
conda create -n dbt-env python=3.11.15

# To activate this project's environment use
conda activate dbt-env

#If not installed
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### Infrastructure
```bash
cd terraform
terraform init
terraform validate
terraform plan
terraform apply
```

### Glue ETL Job
```bash
# Trigger ingestion from RDS → S3 landing layer
aws glue start-job-run --job-name dvdrentals-extraction-tf

# Check job status
aws glue get-job-run --job-name dvdrentals-extraction-tf --run-id <run-id>
```

### dbt (run from repo root or dvdrentals/)
```bash
# Setup conda environment once
conda create -n dbt-prod-env python=3.11.15
conda activate dbt-prod-env
pip install -r requirements.txt

# Copy profiles config to dbt home
cp profiles.yml ~/.dbt/

cd dvdrentals
dbt debug                                    # validate connection to Redshift
dbt run --select starschemamodel             # build all star schema tables
dbt run --select starschemamodel.dim_film    # run a single model
dbt run --debug --select starschemamodel     # verbose output
```

## Architecture

### Data Flow
```
RDS PostgreSQL (private subnet)
    → AWS Glue job (dvdrentals-extraction-tf)  [terraform/jobs/etl_job.py]
    → S3 landing-layer (Iceberg tables, Glue Data Catalog: dvdrentals DB)
    → dbt on Redshift Serverless (reads via Redshift Spectrum + Lake Formation)
    → Redshift schema: starschema
```

### S3 Bucket Layout (`terraform-data-lake-bucket`)
- `/landing-layer/dvdrentals/<table>/` — raw Iceberg tables written by Glue
- `/transformation-layer/` — reserved for future use
- `/serving-layer/` — reserved for future use

### Terraform Modules (`terraform/`)
Each `.tf` file manages one resource type: `rds.tf`, `glue.tf`, `s3.tf`, `redshift.tf`, `vpc.tf`, `security_group.tf`. Region and bucket names are variables in `variables.tf` — changing the region requires updating `variables.tf` and `profiles.yml`.

### Glue ETL (`terraform/jobs/etl_job.py`)
Extracts 6 tables from RDS via a named Glue connection (`postgres_connection`) and writes them as Iceberg v2 Parquet tables to S3. Table metadata (name, compression, extraction SQL — `DEFAULT_QUERY` or a custom query with an `{alias}` placeholder) is declared in the `TABLES` list using the `TableConfig` dataclass. The `run_extraction()` function loops over that list, appending to each Iceberg table if it already exists in the catalog and creating it otherwise. All Glue runtime imports are deferred inside functions or the `__main__` guard so the module can be imported locally without the Glue runtime.

### dbt Project (`dvdrentals/`)
- **Sources**: reads from `awsdatacatalog.dvdrentals.*` (the Glue Data Catalog landing-layer tables) via Redshift Spectrum
- **Models** (`models/starschemamodel/`): all materialized as tables in Redshift schema `starschema`
  - `dim_film`, `dim_customer`, `dim_dates` — dimension tables
  - `fact_rentals` — central fact table; surrogate keys via `dbt_utils.generate_surrogate_key`
- **Macro** (`macros/cents_to_dollars.sql`): adapter-dispatched macro for currency conversion; not yet used in models
- **Profile** (`profiles.yml` → `~/.dbt/profiles.yml`): IAM auth to Redshift Serverless; update `host` before running

### Permissions — Lake Formation (manual step)
Lake Formation table/column permissions cannot be fully managed via Terraform (known quirk). After `terraform apply`, manually grant the following principals access to all tables and columns in the `dvdrentals` catalog database:
- Your IAM user
- `redshift-spectrum-role`

Also verify both principals appear under **Data Locations** for `s3://terraform-data-lake-bucket`.

### Local testing (Glue ETL)
```bash
pip install -r requirements-dev.txt
pytest tests/ -v
```
No AWS credentials or Spark runtime required — tests cover config integrity.

## Important Notes

- **RDS is in a private subnet** — restore the dvdrental DB via AWS CloudShell from the RDS console page, not from your local machine.
- **Region**: defaults to `us-west-2`. Any change must be applied in both `terraform/variables.tf` and `profiles.yml`.
- **Postgres password** is set in `terraform/variables.tf` (`default = "password"`) — override via `-var` or `terraform.tfvars` before applying to production.
- The `authorized_ips` variable in `variables.tf` controls which IPs can reach Redshift — update it to your current public IP before `terraform apply`.
