# aws-etl-platform
End to end aws etl platform using Postgres, s3, Glue, Airflow, Iceberg, Redshift and dbt

https://www.notion.so/Capstone-Project-3252a2f939f6803d93e8e229a4b8800f

The objective of the initial demo is to transform the dvdrentals original Postgres database into a star schema available in Redshift so that Analytics users can cluster users by preffered movie category and verify if there is any correlation between movie genre and delays (when rental_date + rental_duration < return_date).

The star schema is defined by:

Business process: rentals
Grain: individual rentals (rental_id)
Dimensions for these cases are: dim_film, dim_customer, dim_dates
Facts:

fact_rentals
-----------
rental_id (PK)
customer_id (FK)
film_id (FK)
rental_date_id (FK)
return_date_id (FK)

-- measures
rental_duration_expected
rental_duration_actual
delay_days
is_delayed

Therefore, the original tables needed to be extracted in order to implement this star schema are:
dim_film: inventory, film, film_category.
dim_customer: customer.
fact_rentals: rental

## 0. Install requirements

- AWS Client

## 1. Postgres sample database

Here follows the steps necessary to load the dvdrentals(https://neon.com/postgresql/postgresql-getting-started/load-postgresql-sample-database) sample database:

host: postgres-sample-database.crwu02mq48w6.us-east-2.rds.amazonaws.com
port: 5432
dbname: postgres-sample-database
user: postgres
password: system-hero

Connect to the RDS database and create a new dvdrental database which will recieve the load

```bash
psql --host=postgres-sample-database.crwu02mq48w6.us-east-2.rds.amazonaws.com --port=5432 --username=postgres --password --dbname=postgres-sample-database
```

```sql
SELECT schema_name
FROM information_schema.schemata;

CREATE DATABASE dvdrental;

SELECT datname FROM pg_database;
```

Load the database dvdrental.zip in a s3 bucket:

bucket-name: dvd-rentals-database

Crie um Endpoint do tipo Gateway para o s3 e associe à tabela de rotas das subnets utilizadas pelo cloudshell.
Novamente, no Cloudshell.

bash ```
aws s3 cp s3://dvd-rentals-database/dvdrental.zip .

pg_restore \
  -d "host=postgres-sample-database.crwu02mq48w6.us-east-2.rds.amazonaws.com \
  port=5432 \
  user=postgres \
  dbname=dvdrental \
  sslmode=verify-full \
  sslrootcert=/certs/global-bundle.pem" \
  dvdrental.tar
```

Verifique que os dados foram carregados:

bash```
\c dvdrental # a database criada no restore
\dt
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