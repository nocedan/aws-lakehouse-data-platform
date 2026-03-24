# Aws Data Engineering Batch Platform
End to end aws ETL platform using Postgres as a data source, s3 as Data Lake Storage, Glue Jobs for ingesting data, Iceberg and Glue data catalog as lakehouse components and dbt running over Redshift to model data and serve. Terraform is used in order to build the project infrastructure in a repeatable way.

https://www.notion.so/Capstone-Project-3252a2f939f6803d93e8e229a4b8800f

## 1. Platform Architecture

The platform architecture at AWS is described in details [here](terraform/vpc_architecture.md) 

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

## Business Analytics goals

The objective is to transform the dvdrentals sample Postgres database into a star schema available in Redshift so that Analytics users can cluster users by preffered movie category and verify if there is any correlation between movie genre and delays, when rental_date + rental_duration < return_date.

The star schema is defined in four steps:

  1. Business process: rentals
  2. Grain: individual rentals (rental_id)
  3. Dimensions for these cases are: dim_film, dim_customer, dim_dates
  4. Facts: rental events and related measures

# Star Schema — dvdrentals

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

## 0. Required Software

- AWS Client and Account
- Python 3.11.15 (Miniconda with pip for requirements.txt)
- Terraform v1.14.7
- dbt Core: 1.11.7
- dbt-postgres: 1.10.0
- dbt-redshift: 1.10.1

## Building the pipeline

First login at aws

```bash
aws login
aws configure set region us-west-2
```

Terraform commands in order to build the infrastructure.

```bash
cd terraform
terraform init
terraform validate
terraform plan
terraform apply
```

# 1. PostgreSQL Sample Database

The following steps describe how to load the [dvdrentals sample database](https://neon.com/postgresql/postgresql-getting-started/load-postgresql-sample-database) into your RDS instance.

---

### Step 1 — Retrieve Database Connection Details

Run the following command to get the database outputs from Terraform:

```bash
terraform output
```

Expected output:

```
db_endpoint = "dvdrentals-database.cbia4semc2rv.us-west-2.rds.amazonaws.com:5432"
db_hostname = "dvdrentals"
db_password = <sensitive>
db_port     = 5432
db_username = "postgres_master_user"
```

> **Note:** The password is marked as sensitive. Retrieve it from AWS Secrets Manager — see Step 2.

---

### Step 2 — Retrieve the Database Password

Fetch the password from AWS Secrets Manager:

```bash
aws secretsmanager get-secret-value \
  --secret-id <secret-arn> \
  --region us-west-2 \
  --query SecretString \
  --output text
```

Example password: `NevhwOZ03W:A*rQfWLPy?ll9SMt!`

---

### Step 3 — Connect to the Database

Since the RDS instance is on a **private subnet**, direct access from your machine is not possible. Connect through **AWS CloudShell** in the console.

```bash
psql \
  --host=dvdrentals-database.cbia4semc2rv.us-west-2.rds.amazonaws.com \
  --port=5432 \
  --username=postgres_master_user \
  --password \
  --dbname=dvdrentals
```

---

### Step 4 — Create the Target Database

Once connected, create the `dvdrentals` database that will receive the restored data:

```sql
-- List existing schemas (optional, for reference)
SELECT schema_name FROM information_schema.schemata;

-- Create the target database
CREATE DATABASE dvdrentals;

-- Confirm it was created
SELECT datname FROM pg_database;
```

---

### Step 5 — Upload the Backup File to S3

Upload the `dvdrental.zip` file to the S3 bucket:

```
bucket-name: dvd-rentals-database
```

> **Note:** Verify that the **S3 Gateway Endpoint** is associated with the route table of the private subnets used by CloudShell. Without this, CloudShell will not be able to reach the S3 bucket.

---

### Step 6 — Download and Extract the Backup in CloudShell

If you are currently connected to the database, exit first:

```bash
exit
```

Then download and extract the backup:

```bash
aws s3 cp s3://dvd-rentals-database/dvdrental.zip .

unzip dvdrental.zip
```

---

### Step 7 — Restore the Database

Run `pg_restore` to load the data into the `dvdrentals` database:

```bash
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

---

### Step 8 — Verify the Restore

Reconnect to the database using the connection command from Step 3, then confirm the tables were loaded:

```sql
\c dvdrentals   -- switch to the restored database
\dt             -- list tables
```

Expected output:

```
                   List of relations
 Schema |     Name      | Type  |        Owner
--------+---------------+-------+----------------------
 public | actor         | table | postgres_master_user
 public | address       | table | postgres_master_user
 public | category      | table | postgres_master_user
 public | city          | table | postgres_master_user
 public | country       | table | postgres_master_user
 public | customer      | table | postgres_master_user
 public | film          | table | postgres_master_user
 public | film_actor    | table | postgres_master_user
 public | film_category | table | postgres_master_user
```

## 2. Glue job to ingest data into the Landing Zone

First, we create a bucket called dvdrentals-datalake, with three buckets landing-layer, transformation-layer, serving-layer.

```bash
aws s3api create-bucket \
  --bucket dvdrentals-datalake \
  --region us-east-2 \
  --create-bucket-configuration LocationConstraint=us-east-2

aws s3api put-object --bucket dvdrentals-datalake --key landing-layer/
aws s3api put-object --bucket dvdrentals-datalake --key transformation-layer/
aws s3api put-object --bucket dvdrentals-datalake --key serving-layer/
```

Then, we create a Glue Job for extracting the database tables into the landing-layer.
Is necessary to create a role for this job with permission to read from RDS and write at dvdrentals-datalake.
Is also necessary to create the job within the same VPC and garantee connectivity.

Find, the VPC, subnet and security group before creating the Glue Connection:

```bash
database identifier: postgres-sample-database
security group: sg-06490937e96b1ed81
VPC: vpc-061faf1ae5ffd07b3
Detalhes do grupo de sub-redes (default-vpc-061faf1ae5ffd07b3):
    subnet-07a282d1f8cbfd440
    subnet-085468e52285240bb --> us-east-2c
    subnet-03f92c672f0727bea
```

Sem o NAT, precisamos criar Endpoints para o S3, sts,  secretsmanager e Glue nesta VPC (estou usando a Default).
Crie o Gateway Endpoint para o S3 e associe à tabela de rotas referente as subnets acima.

Create an IAM role (named glue-dvdrentals-role) for Glue and attatch policies:

Attach policies:

✅ AWSGlueServiceRole (mandatory baseline)
✅ AmazonS3FullAccess (or scoped to your bucket)
✅ SecretsManagerReadWrite (or read-only if already created secret)
✅ AmazonRDSFullAccess


Glue job requirements:

Create a connection (use postgres database: dvdrental) and a Glue >> Database (dvdrentals) before hand.

## 3. Data Modelling

Given that the original tables are already extracted into dvdrentals-datalake/landing-layer, it is time to apply a transformation job that creates the star schema 

## Questões

Tamanho do database:

\c dvdrental 
SELECT pg_size_pretty(pg_database_size(current_database()));


Now install dbt VsCode extension and then dbt core with pip

https://docs.getdbt.com/docs/local/install-dbt?version=1.12

https://docs.getdbt.com/guides/manual-install?step=3

https://docs.getdbt.com/docs/local/install-dbt?version=1.12

https://docs.getdbt.com/guides/manual-install?step=3&version=2.0




conda create -n dbt-env python=3.10 -y
conda activate dbt-env
pip install "dbt-core~=1.7.0" "dbt-postgres~=1.7.0" "dbt-redshift~=1.7.0"
dbt --version
pip freeze > requirements.txt

Instalar o client do aws para conectar com o Redshift via credenciais.

msiexec.exe /i https://awscli.amazonaws.com/AWSCLIV2.msi
aws --version
aws login

aws redshift-serverless get-credentials --workgroup-name myworkgroup --db-name dev --region us-east-2 --profile default

aws sts get-caller-identity --profile default

Configure o Cluster do Redshift (Workspace neste caso) para ser publicamente acessível.


Após descobrir o grupo de segurança 
aws redshift-serverless get-workgroup --workgroup-name myworkgroup --region us-east-2 --profile default  | jq '.workgroup.securityGroupIds'

"sg-06490937e96b1ed81"


Libere o acesso:

meu ip
(Invoke-WebRequest -Uri "https://checkip.amazonaws.com").Content.Trim()

aws ec2 authorize-security-group-ingress --group-id sg-06490937e96b1ed81 --protocol tcp --port 5439 --cidr 179.135.238.237/32 --region us-east-2 --profile default

A porta está acessível: 
Test-NetConnection -ComputerName myworkgroup.396768596145.us-east-2.redshift-serverless.amazonaws.com -Port 5439



aws redshift-serverless get-workgroup --workgroup-name myworkgroup --region us-east-2 --profile default


vpc-061faf1ae5ffd07b3


us-east-2a 172.31.0.0/20
us-east-2c 172.31.32.0/20
us-east-2b 172.31.16.0/20

Criando subnets públicas

aws ec2 create-subnet --vpc-id vpc-061faf1ae5ffd07b3 --cidr-block 172.31.48.0/24 --availability-zone us-east-2a --region us-east-2 --profile default

aws ec2 create-subnet --vpc-id vpc-061faf1ae5ffd07b3 --cidr-block 172.31.49.0/24 --availability-zone us-east-2b --region us-east-2 --profile default

aws ec2 create-subnet --vpc-id vpc-061faf1ae5ffd07b3 --cidr-block 172.31.50.0/24 --availability-zone us-east-2c --region us-east-2 --profile default


# 1. Verifique se as subnets foram criadas
aws ec2 describe-subnets --filters "Name=vpc-id,Values=vpc-061faf1ae5ffd07b3" --region us-east-2 --profile default

2. Habilitar IP público nas novas subnets
aws ec2 modify-subnet-attribute --subnet-id subnet-07a282d1f8cbfd440 --map-public-ip-on-launch --region us-east-2 --profile default
aws ec2 modify-subnet-attribute --subnet-id subnet-085468e52285240bb --map-public-ip-on-launch --region us-east-2 --profile default
aws ec2 modify-subnet-attribute --subnet-id subnet-03f92c672f0727bea --map-public-ip-on-launch --region us-east-2 --profile default

Sub-rede
subnet-07a282d1f8cbfd440,
subnet-085468e52285240bb,
subnet-03f92c672f0727bea,

3. Verificar Internet Gateway
aws ec2 describe-internet-gateways --filters "Name=attachment.vpc-id,Values=vpc-061faf1ae5ffd07b3" --region us-east-2 --profile default

4. Criar Route Table
aws ec2 create-route-table --vpc-id vpc-061faf1ae5ffd07b3 --region us-east-2 --profile default | jq '.RouteTable.RouteTableId'



6. Associar subnets à Route Table
5. Adicionar rota para internet
aws ec2 create-route --route-table-id rtb-05f4254242443


Credenciais do redshift:

namespace: dvdrentalsnamespace
banco de dados: dev
user: admin
password: YZDYhdmxm669.-

# Como testar a conexão do Redshift Serverless da máquina local

Assim valido:
  - que tenho acesso
  - que a VPC, security group, subnets e route table estão configuradas de forma adequada.

aws redshift-data execute-statement --workgroup-name dvdrentalsworkgroup --database dev --sql "select awsdatacatalog.dvdrentals.film limit 1;"
aws redshift-data get-statement-result --id 181fdacf-a518-429d-a3b5-66b2468a363b

aws redshift-data execute-statement --workgroup-name myworkgroup --database dev --sql "select 3.14;"
aws redshift-data get-statement-result --id c9f32308-8dd8-4745-bd17-072adadefda2

aws redshift-data execute-statement --workgroup-name dvdrentalsworkgroup --database dev --sql "SELECT * FROM awsdatacatalog.dvdrentals.film limit 1;"

aws redshift-data get-statement-result --id 5a29d86d-468d-492a-b00c-87af88f2201c


conda create -n dbt-env python=3.11 -y
conda activate dbt-env
pip install "dbt-core~=1.8.9" "dbt-redshift~=1.8.0"
dbt --version

pip install "botocore[crt]"

## Criar um Cluster Redshift para conseguir completar

https://docs.getdbt.com/guides/redshift?step=1

# Construir um Star Schema no dbt para disponibilizar as views

No Redshift é necessário criar um schema

create schema if not exists starschema;

Useful guide to dbt:

https://docs.getdbt.com/guides/redshift?step=10