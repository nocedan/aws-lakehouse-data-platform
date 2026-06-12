import sys
from dataclasses import dataclass
from typing import Optional


# ── Config ────────────────────────────────────────────────────────────────────

@dataclass
class TableConfig:
    name: str
    compression: str          # "snappy" | "gzip"
    sql: Optional[str] = None  # None → SELECT *; use {alias} placeholder
    source_schema: str = "public"


TABLES: list[TableConfig] = [
    TableConfig("inventory",     compression="snappy"),
    TableConfig("film_category", compression="snappy"),
    TableConfig("customer",      compression="gzip"),
    TableConfig("film",          compression="snappy",
                sql="SELECT film_id, title, description, release_year, "
                    "rental_duration, rental_rate, length, replacement_cost, "
                    "rating, last_update FROM {alias}"),
    TableConfig("rental",        compression="gzip"),
    TableConfig("category",      compression="gzip"),
]

DATABASE       = "dvdrentals"
CATALOG        = "glue_catalog"
WAREHOUSE      = "s3://terraform-data-lake-bucket/"
LANDING_PREFIX = "landing-layer"
CONNECTION     = "postgres_connection"
DQ_RULESET     = "Rules = [ ColumnCount > 0 ]"


# ── Helpers ───────────────────────────────────────────────────────────────────

def iceberg_path(table: TableConfig) -> str:
    return f"s3://terraform-data-lake-bucket/{LANDING_PREFIX}/{DATABASE}/{table.name}"


def get_sql(table: TableConfig, alias: str = "src") -> str:
    return table.sql.format(alias=alias) if table.sql else f"SELECT * FROM {alias}"


# ── ETL ───────────────────────────────────────────────────────────────────────

def run_extraction(glueContext, spark) -> None:
    from awsgluedq.transforms import EvaluateDataQuality

    for table in TABLES:
        alias = f"src_{table.name}"
        frame = glueContext.create_dynamic_frame.from_options(
            connection_type="postgresql",
            connection_options={
                "useConnectionProperties": "true",
                "dbtable": f"{table.source_schema}.{table.name}",
                "connectionName": CONNECTION,
            },
            transformation_ctx=f"extract_{table.name}",
        )
        EvaluateDataQuality().process_rows(
            frame=frame,
            ruleset=DQ_RULESET,
            publishing_options={
                "dataQualityEvaluationContext": f"dq_{table.name}",
                "enableDataQualityResultsPublishing": True,
            },
            additional_options={
                "dataQualityResultsPublishing.strategy": "BEST_EFFORT",
                "observations.scope": "ALL",
            },
        )
        frame.toDF().createOrReplaceTempView(alias)
        result_df = spark.sql(get_sql(table, alias))

        exists = table.name in {t.name for t in spark.catalog.listTables(DATABASE)}
        writer = (
            result_df.writeTo(f"{CATALOG}.{DATABASE}.{table.name}")
            .tableProperty("format-version", "2")
            .tableProperty("location", iceberg_path(table))
            .tableProperty("write.parquet.compression-codec", table.compression)
        )
        writer.append() if exists else writer.create()


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    from awsglue.utils import getResolvedOptions
    from pyspark.context import SparkContext
    from awsglue.context import GlueContext
    from awsglue.job import Job

    args = getResolvedOptions(sys.argv, ["JOB_NAME"])
    sc = SparkContext()
    glueContext = GlueContext(sc)
    spark = glueContext.spark_session
    job = Job(glueContext)
    job.init(args["JOB_NAME"], args)

    for key, val in {
        "spark.sql.catalog.glue_catalog":              "org.apache.iceberg.spark.SparkCatalog",
        "spark.sql.catalog.glue_catalog.warehouse":    WAREHOUSE,
        "spark.sql.catalog.glue_catalog.catalog-impl": "org.apache.iceberg.aws.glue.GlueCatalog",
        "spark.sql.catalog.glue_catalog.io-impl":      "org.apache.iceberg.aws.s3.S3FileIO",
    }.items():
        spark.conf.set(key, val)

    run_extraction(glueContext, spark)
    job.commit()
