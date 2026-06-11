"""Invoke the in-VPC restore Lambda (lambda/restore_db) synchronously."""

import json

import boto3
from botocore.config import Config


def invoke_restore_lambda(
    function_name: str, region: str, lambda_client=None
) -> dict:
    """Run the restore Lambda and return its JSON payload.

    Raises RuntimeError if the function reports an error (pg_restore failure
    or table-count verification failure inside the handler).
    """
    client = lambda_client or boto3.client(
        "lambda",
        region_name=region,
        # the restore can take minutes (VPC cold start + pg_restore):
        # wait for the full Lambda timeout and never retry a half-done restore
        config=Config(
            read_timeout=900, connect_timeout=30, retries={"max_attempts": 0}
        ),
    )
    response = client.invoke(
        FunctionName=function_name, InvocationType="RequestResponse"
    )
    payload = json.loads(response["Payload"].read())
    if response.get("FunctionError"):
        raise RuntimeError(
            f"restore Lambda failed: {json.dumps(payload, indent=2)}"
        )
    return payload
