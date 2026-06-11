"""Lake Formation verification via the Redshift Data API.

The smoke query runs inside Redshift against the Spectrum external schema,
so it genuinely exercises the Spectrum role's Lake Formation grants. Using
the Data API (HTTPS) also avoids the local-firewall issues that direct
port-5439 connections can hit.
"""

import time

import boto3

SMOKE_TEST_SQL = 'SELECT 1 FROM "awsdatacatalog"."dvdrentals"."film" LIMIT 1'


class LakeFormationNotGranted(RuntimeError):
    """The smoke query failed — Lake Formation grants are likely missing."""


def verify_lake_formation_access(
    workgroup_name: str,
    region: str,
    database: str = "dev",
    redshift_data_client=None,
    sleep=time.sleep,
    timeout_seconds: int = 300,
    poll_seconds: int = 2,
) -> None:
    client = redshift_data_client or boto3.client(
        "redshift-data", region_name=region
    )
    statement_id = client.execute_statement(
        WorkgroupName=workgroup_name, Database=database, Sql=SMOKE_TEST_SQL
    )["Id"]

    waited = 0
    while True:
        desc = client.describe_statement(Id=statement_id)
        status = desc["Status"]
        if status == "FINISHED":
            return
        if status in ("FAILED", "ABORTED"):
            raise LakeFormationNotGranted(
                f"Lake Formation smoke test failed:"
                f" {desc.get('Error', status)}"
            )
        if waited >= timeout_seconds:
            raise TimeoutError(
                f"Lake Formation smoke test still {status}"
                f" after {timeout_seconds}s"
            )
        sleep(poll_seconds)
        waited += poll_seconds
