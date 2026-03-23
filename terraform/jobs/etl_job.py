import sys
from awsglue.transforms import *
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job
from awsgluedq.transforms import EvaluateDataQuality
from awsglue import DynamicFrame

def sparkSqlQuery(glueContext, query, mapping, transformation_ctx) -> DynamicFrame:
    for alias, frame in mapping.items():
        frame.toDF().createOrReplaceTempView(alias)
    result = spark.sql(query)
    return DynamicFrame.fromDF(result, glueContext, transformation_ctx)
args = getResolvedOptions(sys.argv, ['JOB_NAME'])
sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session
job = Job(glueContext)
job.init(args['JOB_NAME'], args)

# Default ruleset used by all target nodes with data quality enabled
DEFAULT_DATA_QUALITY_RULESET = """
    Rules = [
        ColumnCount > 0
    ]
"""

# Script generated for node inventory
inventory_node1773772837637 = glueContext.create_dynamic_frame.from_options(
    connection_type = "postgresql",
    connection_options = {
        "useConnectionProperties": "true",
        "dbtable": "public.inventory",
        "connectionName": "Postgresql connection",
    },
    transformation_ctx = "inventory_node1773772837637"
)

# Script generated for node film_category
film_category_node1773773262888 = glueContext.create_dynamic_frame.from_options(
    connection_type = "postgresql",
    connection_options = {
        "useConnectionProperties": "true",
        "dbtable": "public.film_category",
        "connectionName": "Postgresql connection",
    },
    transformation_ctx = "film_category_node1773773262888"
)

# Script generated for node customer
customer_node1773772492046 = glueContext.create_dynamic_frame.from_options(
    connection_type = "postgresql",
    connection_options = {
        "useConnectionProperties": "true",
        "dbtable": "public.customer",
        "connectionName": "Postgresql connection",
    },
    transformation_ctx = "customer_node1773772492046"
)

# Script generated for node film
film_node1773773114450 = glueContext.create_dynamic_frame.from_options(
    connection_type = "postgresql",
    connection_options = {
        "useConnectionProperties": "true",
        "dbtable": "public.film",
        "connectionName": "Postgresql connection",
    },
    transformation_ctx = "film_node1773773114450"
)

# Script generated for node rental
rental_node1773755904864 = glueContext.create_dynamic_frame.from_options(
    connection_type = "postgresql",
    connection_options = {
        "useConnectionProperties": "true",
        "dbtable": "public.rental",
        "connectionName": "Postgresql connection",
    },
    transformation_ctx = "rental_node1773755904864"
)

# Script generated for node PostgreSQL
PostgreSQL_node1774012613873 = glueContext.create_dynamic_frame.from_options(
    connection_type = "postgresql",
    connection_options = {
        "useConnectionProperties": "true",
        "dbtable": "public.category",
        "connectionName": "Postgresql connection",
    },
    transformation_ctx = "PostgreSQL_node1774012613873"
)

# Script generated for node SQL Query
SqlQuery3 = '''
select * from myDataSource
'''
SQLQuery_node1773772872202 = sparkSqlQuery(glueContext, query = SqlQuery3, mapping = {"myDataSource":inventory_node1773772837637}, transformation_ctx = "SQLQuery_node1773772872202")

# Script generated for node SQL Query
SqlQuery1 = '''
select * from myDataSource
'''
SQLQuery_node1773773273826 = sparkSqlQuery(glueContext, query = SqlQuery1, mapping = {"myDataSource":film_category_node1773773262888}, transformation_ctx = "SQLQuery_node1773773273826")

# Script generated for node SQL Query
SqlQuery5 = '''
select * from myDataSource
'''
SQLQuery_node1773772557075 = sparkSqlQuery(glueContext, query = SqlQuery5, mapping = {"myDataSource":customer_node1773772492046}, transformation_ctx = "SQLQuery_node1773772557075")

# Script generated for node SQL Query
SqlQuery0 = '''
select  
    film_id,
    title,
    description,
    release_year,
    rental_duration,
    rental_rate,
    length, 
    replacement_cost,
    rating,
    last_update
from my_film
'''
SQLQuery_node1773773146792 = sparkSqlQuery(glueContext, query = SqlQuery0, mapping = {"my_film":film_node1773773114450}, transformation_ctx = "SQLQuery_node1773773146792")

# Script generated for node SQL Query
SqlQuery2 = '''
select * from myDataSource
'''
SQLQuery_node1773755909883 = sparkSqlQuery(glueContext, query = SqlQuery2, mapping = {"myDataSource":rental_node1773755904864}, transformation_ctx = "SQLQuery_node1773755909883")

# Script generated for node SQL Query
SqlQuery4 = '''
select * from myDataSource

'''
SQLQuery_node1774012619900 = sparkSqlQuery(glueContext, query = SqlQuery4, mapping = {"myDataSource":PostgreSQL_node1774012613873}, transformation_ctx = "SQLQuery_node1774012619900")

# Script generated for node Amazon S3
EvaluateDataQuality().process_rows(frame=SQLQuery_node1773772872202, ruleset=DEFAULT_DATA_QUALITY_RULESET, publishing_options={"dataQualityEvaluationContext": "EvaluateDataQuality_node1773758884683", "enableDataQualityResultsPublishing": True}, additional_options={"dataQualityResultsPublishing.strategy": "BEST_EFFORT", "observations.scope": "ALL"})
additional_options = {}
tables_collection = spark.catalog.listTables("dvdrentals")
table_names_in_db = [table.name for table in tables_collection]
table_exists = "inventory" in table_names_in_db
if table_exists:
    AmazonS3_node1773772888286_df = SQLQuery_node1773772872202.toDF()
    AmazonS3_node1773772888286_df        .writeTo("glue_catalog.dvdrentals.inventory") \
        .tableProperty("format-version", "2") \
        .tableProperty("location", "s3://terraform-data-lake-bucket/landing-layer/dvdrentals/inventory") \
        .tableProperty("write.parquet.compression-codec", "snappy") \
        .options(**additional_options) \
.append()
else:
    AmazonS3_node1773772888286_df = SQLQuery_node1773772872202.toDF()
    AmazonS3_node1773772888286_df        .writeTo("glue_catalog.dvdrentals.inventory") \
        .tableProperty("format-version", "2") \
        .tableProperty("location", "s3://terraform-data-lake-bucket/landing-layer/dvdrentals/inventory") \
        .tableProperty("write.parquet.compression-codec", "snappy") \
        .options(**additional_options) \
.create()

# Script generated for node Amazon S3
EvaluateDataQuality().process_rows(frame=SQLQuery_node1773773273826, ruleset=DEFAULT_DATA_QUALITY_RULESET, publishing_options={"dataQualityEvaluationContext": "EvaluateDataQuality_node1773758884683", "enableDataQualityResultsPublishing": True}, additional_options={"dataQualityResultsPublishing.strategy": "BEST_EFFORT", "observations.scope": "ALL"})
additional_options = {}
tables_collection = spark.catalog.listTables("dvdrentals")
table_names_in_db = [table.name for table in tables_collection]
table_exists = "film_category" in table_names_in_db
if table_exists:
    AmazonS3_node1773773278770_df = SQLQuery_node1773773273826.toDF()
    AmazonS3_node1773773278770_df        .writeTo("glue_catalog.dvdrentals.film_category") \
        .tableProperty("format-version", "2") \
        .tableProperty("location", "s3://terraform-data-lake-bucket/landing-layer/dvdrentals/film_category") \
        .tableProperty("write.parquet.compression-codec", "snappy") \
        .options(**additional_options) \
.append()
else:
    AmazonS3_node1773773278770_df = SQLQuery_node1773773273826.toDF()
    AmazonS3_node1773773278770_df        .writeTo("glue_catalog.dvdrentals.film_category") \
        .tableProperty("format-version", "2") \
        .tableProperty("location", "s3://terraform-data-lake-bucket/landing-layer/dvdrentals/film_category") \
        .tableProperty("write.parquet.compression-codec", "snappy") \
        .options(**additional_options) \
.create()

# Script generated for node Amazon S3
EvaluateDataQuality().process_rows(frame=SQLQuery_node1773772557075, ruleset=DEFAULT_DATA_QUALITY_RULESET, publishing_options={"dataQualityEvaluationContext": "EvaluateDataQuality_node1773758884683", "enableDataQualityResultsPublishing": True}, additional_options={"dataQualityResultsPublishing.strategy": "BEST_EFFORT", "observations.scope": "ALL"})
additional_options = {}
tables_collection = spark.catalog.listTables("dvdrentals")
table_names_in_db = [table.name for table in tables_collection]
table_exists = "customer" in table_names_in_db
if table_exists:
    AmazonS3_node1773772679208_df = SQLQuery_node1773772557075.toDF()
    AmazonS3_node1773772679208_df        .writeTo("glue_catalog.dvdrentals.customer") \
        .tableProperty("format-version", "2") \
        .tableProperty("location", "s3://terraform-data-lake-bucket/landing-layer/dvdrentals/customer") \
        .tableProperty("write.parquet.compression-codec", "gzip") \
        .options(**additional_options) \
.append()
else:
    AmazonS3_node1773772679208_df = SQLQuery_node1773772557075.toDF()
    AmazonS3_node1773772679208_df        .writeTo("glue_catalog.dvdrentals.customer") \
        .tableProperty("format-version", "2") \
        .tableProperty("location", "s3://terraform-data-lake-bucket/landing-layer/dvdrentals/customer") \
        .tableProperty("write.parquet.compression-codec", "gzip") \
        .options(**additional_options) \
.create()

# Script generated for node Amazon S3
EvaluateDataQuality().process_rows(frame=SQLQuery_node1773773146792, ruleset=DEFAULT_DATA_QUALITY_RULESET, publishing_options={"dataQualityEvaluationContext": "EvaluateDataQuality_node1773758884683", "enableDataQualityResultsPublishing": True}, additional_options={"dataQualityResultsPublishing.strategy": "BEST_EFFORT", "observations.scope": "ALL"})
additional_options = {}
tables_collection = spark.catalog.listTables("dvdrentals")
table_names_in_db = [table.name for table in tables_collection]
table_exists = "film" in table_names_in_db
if table_exists:
    AmazonS3_node1773773161170_df = SQLQuery_node1773773146792.toDF()
    AmazonS3_node1773773161170_df        .writeTo("glue_catalog.dvdrentals.film") \
        .tableProperty("format-version", "2") \
        .tableProperty("location", "s3://terraform-data-lake-bucket/landing-layer/dvdrentals/film") \
        .tableProperty("write.parquet.compression-codec", "snappy") \
        .options(**additional_options) \
.append()
else:
    AmazonS3_node1773773161170_df = SQLQuery_node1773773146792.toDF()
    AmazonS3_node1773773161170_df        .writeTo("glue_catalog.dvdrentals.film") \
        .tableProperty("format-version", "2") \
        .tableProperty("location", "s3://terraform-data-lake-bucket/landing-layer/dvdrentals/film") \
        .tableProperty("write.parquet.compression-codec", "snappy") \
        .options(**additional_options) \
.create()

# Script generated for node Amazon S3
EvaluateDataQuality().process_rows(frame=SQLQuery_node1773755909883, ruleset=DEFAULT_DATA_QUALITY_RULESET, publishing_options={"dataQualityEvaluationContext": "EvaluateDataQuality_node1773755892412", "enableDataQualityResultsPublishing": True}, additional_options={"dataQualityResultsPublishing.strategy": "BEST_EFFORT", "observations.scope": "ALL"})
additional_options = {}
tables_collection = spark.catalog.listTables("dvdrentals")
table_names_in_db = [table.name for table in tables_collection]
table_exists = "rental" in table_names_in_db
if table_exists:
    AmazonS3_node1773755915810_df = SQLQuery_node1773755909883.toDF()
    AmazonS3_node1773755915810_df        .writeTo("glue_catalog.dvdrentals.rental") \
        .tableProperty("format-version", "2") \
        .tableProperty("location", "s3://terraform-data-lake-bucket/landing-layer/dvdrentals/rental") \
        .tableProperty("write.parquet.compression-codec", "gzip") \
        .options(**additional_options) \
.append()
else:
    AmazonS3_node1773755915810_df = SQLQuery_node1773755909883.toDF()
    AmazonS3_node1773755915810_df        .writeTo("glue_catalog.dvdrentals.rental") \
        .tableProperty("format-version", "2") \
        .tableProperty("location", "s3://terraform-data-lake-bucket/landing-layer/dvdrentals/rental") \
        .tableProperty("write.parquet.compression-codec", "gzip") \
        .options(**additional_options) \
.create()

# Script generated for node Amazon S3
EvaluateDataQuality().process_rows(frame=SQLQuery_node1774012619900, ruleset=DEFAULT_DATA_QUALITY_RULESET, publishing_options={"dataQualityEvaluationContext": "EvaluateDataQuality_node1774012593625", "enableDataQualityResultsPublishing": True}, additional_options={"dataQualityResultsPublishing.strategy": "BEST_EFFORT", "observations.scope": "ALL"})
additional_options = {}
tables_collection = spark.catalog.listTables("dvdrentals")
table_names_in_db = [table.name for table in tables_collection]
table_exists = "category" in table_names_in_db
if table_exists:
    AmazonS3_node1774012625276_df = SQLQuery_node1774012619900.toDF()
    AmazonS3_node1774012625276_df        .writeTo("glue_catalog.dvdrentals.category") \
        .tableProperty("format-version", "2") \
        .tableProperty("location", "s3://terraform-data-lake-bucket/landing-layer/dvdrentals/category") \
        .tableProperty("write.parquet.compression-codec", "gzip") \
        .options(**additional_options) \
.append()
else:
    AmazonS3_node1774012625276_df = SQLQuery_node1774012619900.toDF()
    AmazonS3_node1774012625276_df        .writeTo("glue_catalog.dvdrentals.category") \
        .tableProperty("format-version", "2") \
        .tableProperty("location", "s3://terraform-data-lake-bucket/landing-layer/dvdrentals/category") \
        .tableProperty("write.parquet.compression-codec", "gzip") \
        .options(**additional_options) \
.create()

job.commit()