# AWS Lakehouse Data Platform

Just built an end-to-end AWS batch data platform covering the full data engineering lifecycle (ingestion → storage → transformation → serving). Inspired by @Joe Reis's [Data Engineering Specialization](https://www.deeplearning.ai/courses/data-engineering/) capstone project.

→ GitHub: https://github.com/nocedan/aws-etl-platform

**What's the real accomplishment:** This project can serve as a foundation for a Lakehouse where Data Scientists, Data Engineers, and Business Analysts can build data products.

**The business case example:** A star schema model derived from the dvdrentals sample [database](https://neon.com/postgresql/postgresql-getting-started/postgresql-sample-database), ready to be queried and help investigating whether rental delays are correlated with a customer's preferred category.

**The stack:**
- PostgreSQL as source → AWS Glue (Spark) for ingestion → S3 Data Lake (Iceberg) → Redshift Serverless for serving.
- dbt for data modeling and transform raw data into useful information following software development best practices.
- Terraform infrastructure as code for repeatable, version-controlled infrastructure.
- Iceberg + Glue Data Catalog + Lake Formation as the lakehouse layer.

**Why Redshift over Athena?** Redshift is better suited for heavier, concurrent analytical workloads at the serving layer.

**One painful learning:** Lake Formation permission management at table and column level still has Terraform quirks.

**Coming next:**
→ Apache Airflow for orchestration
→ Streaming layer (Kinesis or Kafka)

# 0. Deployment instructions

See instructions [here](deployment-instructions.md).

# 1. Platform Architecture

```
Internet / Local PC
        │
        ▼
┌──────────────────────────────────────────────────────────┐
│  VPC 172.31.0.0/16                                        │
│                                                           │
│  ┌─────────────── Public Subnets ───────────────────┐  │
│  │                                                     │  │
│  │   NAT Gateway ◄──── (outbound from private subnets) │  │
│  │                                                     │  │
│  │   Redshift Serverless (external IAM access)         │  │
│  │                                                     │  │
│  └──────────────────────┬──────────────────────────────┘  │
│                         │ IGW                             │
│  ┌─────────────── Private Subnets ───────────────────┐  │
│  │                                                     │  │
│  │   AWS Glue ETL Jobs ──────────────────────────┐    │  │
│  │                                               │    │  │
│  │   RDS Postgres (source)                       │    │  │
│  │                                               ▼    │  │
│  └───────────────────────────────────────────────┼────┘  │
│                                                   │       │
│                              S3 Gateway Endpoint  │       │
└───────────────────────────────────────────────────┼───────┘
                                                    │
                                                    ▼
                                              S3 — Data Lake
                                              (Iceberg Tables)
```

---

# 2. Example Business Analytics Goals

The objective is to transform the dvdrentals sample Postgres database into a star schema available in Redshift so that Analytics users can cluster users by preferred movie category and verify if there is any correlation between movie genre and delays, when rental_date + rental_duration < return_date.

The star schema is defined in four steps:

1. Business process: rentals
2. Grain: individual rentals (rental_id)
3. Dimensions for these cases are: dim_film, dim_customer, dim_dates
4. Facts: rental events and related measures

# 3. Star Schema

## Source tables

The tables used from the **dvdrentals** database are:

- `inventory`
- `film_category`
- `customer`
- `film`
- `rental`
- `category`

---

## Dimensions and Fact

From these tables, the following dimensions will be produced:

- `dim_film`
- `dim_customer`
- `dim_dates`

and the fact table `fact_rentals`.

---

## dim_film

| Column | Type / Role |
|---|---|
| `film_key` | PK (surrogate key) |
| `film_id` | NK (natural key) |
| `title` | |
| `description` | |
| `release_year` | |
| `rental_duration` | allowed rental days |
| `rental_rate` | |
| `length` | |
| `replacement_cost` | |
| `rating` | |
| `last_update` | |
| `category_id` | FK → `category` |
| `film_category_last_update` | |

---

## dim_customer

| Column | Type / Role |
|---|---|
| `customer_key` | PK (surrogate key) |
| `customer_id` | NK (natural key) |
| `store_id` | |
| `first_name` | |
| `last_name` | |
| `email` | |
| `address_id` | |
| `activebool` | |
| `create_date` | |
| `last_update` | |
| `active` | |

---

## dim_dates

| Column | Type / Role |
|---|---|
| `date_key` | PK (surrogate key) |
| `full_date` | full date |
| `day_of_week` | |
| `day_of_month` | |
| `month` | |
| `quarter` | |
| `year` | |
| `is_weekend` | |

> **Note:** `rental_date` and `return_date` are attributes of `fact_rentals` that reference `dim_dates` via FK — not columns of the dimension itself.

---

## fact_rentals

| Column | Type / Role |
|---|---|
| `rental_key` | PK (surrogate key) |
| `rental_id` | NK (natural key) |
| `customer_key` | FK → `dim_customer` |
| `film_key` | FK → `dim_film` |
| `rental_date_key` | FK → `dim_dates` |
| `return_date_key` | FK → `dim_dates` |

### Measures

| Column | Description |
|---|---|
| `rental_duration_expected` | expected rental duration (days), from `film.rental_duration` |
| `rental_duration_actual` | actual rental duration (days), calculated as `return_date − rental_date` |
| `delay_days` | delay in days (`rental_duration_actual − rental_duration_expected`); 0 if negative |
| `is_delayed` | boolean — `true` if `delay_days > 0` |
