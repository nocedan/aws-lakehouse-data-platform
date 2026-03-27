# AWS Data Engineering Batch Platform

Just built an end-to-end AWS batch data platform covering the full data engineering lifecycle (ingestion → storage → transformation → serving). Inspired by @Joe Reis's [Data Engineering Specialization](https://www.deeplearning.ai/courses/data-engineering/) capstone project.

→ GitHub: https://github.com/nocedan/aws-etl-platform

**What's the real accomplishment:** This project can serve as a foundation for a Lakehouse where Data Scientists, Data Engineers, and Business Analysts can build data products.

**The business goal example:** A star schema model derived from the dvdrentals sample database (dim_film, dim_customer, dim_dates, fact_rentals), ready to be queried and investigate whether rental delays are correlated with a customer's preferred category.

**The stack:**
- PostgreSQL as source → AWS Glue (Spark/Iceberg) for ingestion → S3 Data Lake → Redshift Serverless for serving
- dbt for star schema modeling
- Terraform for repeatable, version-controlled infrastructure
- Iceberg + Glue Data Catalog + Lake Formation as the lakehouse layer
- [Network Architecture](#1-network-architecture)

**Why Redshift over Athena?** More complex to implement here, but better suited for heavier, concurrent analytical workloads at the serving layer.

**One learning:** Lake Formation permission management at the column level still has Terraform quirks — something I'm actively working through.

**Coming next:**
→ Apache Airflow for orchestration
→ Streaming layer (Kinesis or Kafka)

# 0. Deployment instructions

  See instructions [here](deployment-instructions.md).

# 1. Network Architecture

```
Internet / PC Local
        │
        ▼
┌──────────────────────────────────────────────────────────┐
│  VPC 172.31.0.0/16                                        │
│                                                           │
│  ┌─────────────── Subnets Públicas ───────────────────┐  │
│  │                                                     │  │
│  │   NAT Gateway ◄──── (saída das subnets privadas)   │  │
│  │                                                     │  │
│  │   Redshift Serverless (acesso IAM externo)          │  │
│  │                                                     │  │
│  └──────────────────────┬──────────────────────────────┘  │
│                         │ IGW                             │
│  ┌─────────────── Subnets Privadas ───────────────────┐  │
│  │                                                     │  │
│  │   AWS Glue ETL Jobs ──────────────────────────┐    │  │
│  │                                               │    │  │
│  │   RDS Postgres (fonte)                        │    │  │
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

# 2. Business Analytics Goals

The objective is to transform the dvdrentals sample Postgres database into a star schema available in Redshift so that Analytics users can cluster users by preffered movie category and verify if there is any correlation between movie genre and delays, when rental_date + rental_duration < return_date.

The star schema is defined in four steps:

  1. Business process: rentals
  2. Grain: individual rentals (rental_id)
  3. Dimensions for these cases are: dim_film, dim_customer, dim_dates
  4. Facts: rental events and related measures

# 3. Star Schema

## Tabelas de origem

As tabelas utilizadas do database **dvdrentals** são:

- `inventory`
- `film_category`
- `customer`
- `film`
- `rental`
- `category`

---

## Dimensões e Fato

A partir dessas tabelas serão produzidas as dimensões:

- `dim_film`
- `dim_customer`
- `dim_dates`

e a tabela fato `fact_rentals`.

---

## dim_film

| Coluna | Tipo / Papel |
|---|---|
| `film_key` | PK (surrogate key) |
| `film_id` | NK (natural key) |
| `title` | |
| `description` | |
| `release_year` | |
| `rental_duration` | dias permitidos de locação |
| `rental_rate` | |
| `length` | |
| `replacement_cost` | |
| `rating` | |
| `last_update` | |
| `category_id` | FK → `category` |
| `film_category_last_update` | |

---

## dim_customer

| Coluna | Tipo / Papel |
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

| Coluna | Tipo / Papel |
|---|---|
| `date_key` | PK (surrogate key) |
| `full_date` | data completa |
| `day_of_week` | |
| `day_of_month` | |
| `month` | |
| `quarter` | |
| `year` | |
| `is_weekend` | |

> **Nota:** `rental_date` e `return_date` são atributos de `fact_rentals` que referenciam `dim_dates` via FK — não colunas da própria dimensão.

---

## fact_rentals

| Coluna | Tipo / Papel |
|---|---|
| `rental_key` | PK (surrogate key) |
| `rental_id` | NK (natural key) |
| `customer_key` | FK → `dim_customer` |
| `film_key` | FK → `dim_film` |
| `rental_date_key` | FK → `dim_dates` |
| `return_date_key` | FK → `dim_dates` |

### Medidas

| Coluna | Descrição |
|---|---|
| `rental_duration_expected` | duração prevista da locação (dias), vinda de `film.rental_duration` |
| `rental_duration_actual` | duração real da locação (dias), calculada como `return_date − rental_date` |
| `delay_days` | dias de atraso (`rental_duration_actual − rental_duration_expected`); 0 se negativo |
| `is_delayed` | booleano — `true` se `delay_days > 0` |