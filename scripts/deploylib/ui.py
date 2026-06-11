"""Console output helpers, including the Lake Formation checkpoint message."""

import boto3


def banner(text: str) -> None:
    line = "=" * max(len(text) + 4, 60)
    print(f"\n{line}\n  {text}\n{line}")


def current_identity_arn(region: str) -> str:
    return boto3.client("sts", region_name=region).get_caller_identity()["Arn"]


def lake_formation_checkpoint(outputs: dict) -> str:
    """The manual Lake Formation steps, mirroring deployment-instructions.md
    Step 5, with the real principal ARNs filled in."""
    region = outputs["region"]
    bucket = outputs["bucket_id"]
    spectrum_role_arn = outputs["redshift_spectrum_role_arn"]
    try:
        user_arn = current_identity_arn(region)
    except Exception:
        user_arn = "<your current IAM user>"

    return f"""
MANUAL STEP REQUIRED — Lake Formation permissions
(cannot be automated; see deployment-instructions.md Step 5)

In the AWS Console (region {region}):

1. Lake Formation > Data permissions > Data locations
   Grant access to  s3://{bucket}  for BOTH principals:
     - {user_arn}
     - {spectrum_role_arn}

2. Lake Formation > Data permissions > Grant
   For BOTH principals above, grant on database `dvdrentals`:
     - Database permissions: DESCRIBE
     - Table permissions: SELECT + DESCRIBE on ALL tables, all columns

When done, continue with:

    python scripts/deploy.py resume
"""
