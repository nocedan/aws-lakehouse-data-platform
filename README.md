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