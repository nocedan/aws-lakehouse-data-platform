"""Restore the dvdrental sample database into the private-subnet RDS instance.

Runs as a container-image Lambda inside the VPC (terraform/lambda_restore.tf),
which is what makes the private RDS endpoint reachable. Downloads the backup
zip from S3 (via the S3 gateway endpoint), extracts the .tar dump, runs
pg_restore, then verifies the expected tables exist.

Invoked synchronously by `scripts/deploy.py restore-db`.
"""

import os
import subprocess
import zipfile
from pathlib import Path

WORK_DIR = Path("/tmp")
CA_BUNDLE = "/certs/global-bundle.pem"
# The dvdrental sample DB ships 15 tables in schema public
MIN_EXPECTED_TABLES = 15


def conninfo() -> str:
    return (
        f"host={os.environ['DB_HOST']} "
        f"port={os.environ['DB_PORT']} "
        f"user={os.environ['DB_USER']} "
        f"dbname={os.environ['DB_NAME']} "
        f"sslmode=verify-full "
        f"sslrootcert={CA_BUNDLE}"
    )


def _pg_env() -> dict:
    return {**os.environ, "PGPASSWORD": os.environ["DB_PASSWORD"]}


def download_backup(bucket: str, key: str) -> Path:
    import boto3  # deferred so tests can import this module without boto3

    zip_path = WORK_DIR / "dvdrental.zip"
    boto3.client("s3").download_file(bucket, key, str(zip_path))
    with zipfile.ZipFile(zip_path) as zf:
        tar_names = [n for n in zf.namelist() if n.endswith(".tar")]
        if not tar_names:
            raise RuntimeError(f"no .tar dump found in s3://{bucket}/{key}")
        zf.extract(tar_names[0], WORK_DIR)
    return WORK_DIR / tar_names[0]


def run_pg_restore(dump_path: Path) -> None:
    proc = subprocess.run(
        [
            "pg_restore",
            "--no-owner",
            "--no-privileges",
            "--clean",
            "--if-exists",
            "-d",
            conninfo(),
            str(dump_path),
        ],
        env=_pg_env(),
        capture_output=True,
        text=True,
    )
    # --clean --if-exists emits ignorable warnings on a fresh DB; only the
    # exit code is authoritative
    if proc.returncode != 0:
        raise RuntimeError(
            f"pg_restore failed (exit {proc.returncode}): {proc.stderr[-2000:]}"
        )


def count_public_tables() -> int:
    proc = subprocess.run(
        [
            "psql",
            "-tA",
            "-d",
            conninfo(),
            "-c",
            "SELECT count(*) FROM information_schema.tables"
            " WHERE table_schema = 'public'",
        ],
        env=_pg_env(),
        capture_output=True,
        text=True,
        check=True,
    )
    return int(proc.stdout.strip())


def lambda_handler(event, context):
    dump_path = download_backup(
        os.environ["BACKUP_BUCKET"], os.environ["BACKUP_KEY"]
    )
    run_pg_restore(dump_path)
    table_count = count_public_tables()
    if table_count < MIN_EXPECTED_TABLES:
        raise RuntimeError(
            f"restore verification failed: expected >= {MIN_EXPECTED_TABLES}"
            f" tables in schema public, found {table_count}"
        )
    return {"status": "ok", "table_count": table_count}
