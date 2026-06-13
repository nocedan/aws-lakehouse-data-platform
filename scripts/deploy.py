#!/usr/bin/env python
"""Deployment CLI for the AWS lakehouse platform.

Automates every step of deployment-instructions.md except the Lake Formation
grants (Step 5), which AWS requires to be done manually in the Console.

Typical flow:

    python scripts/deploy.py all      # infra -> restore RDS -> Glue ingest
    # ... do the manual Lake Formation grants (instructions are printed) ...
    python scripts/deploy.py resume   # verify grants -> configure dbt -> dbt run

Every stage is idempotent and can also be run standalone; see --help.
Full documentation: automated-deployment-instructions.md
"""

import argparse
import shutil
import subprocess
import sys

from deploylib import dbt, glue, redshift, restore, tf, ui


def stage_check(args) -> None:
    ui.banner("Preflight checks")
    failures = []

    for tool in ("terraform", "docker", "dbt", "aws"):
        if shutil.which(tool):
            print(f"  ok: {tool} on PATH")
        else:
            failures.append(f"{tool} not found on PATH")

    if shutil.which("docker"):
        if subprocess.run(
            ["docker", "info"], capture_output=True
        ).returncode == 0:
            print("  ok: docker daemon running")
        else:
            failures.append(
                "docker daemon not running (required: terraform apply"
                " builds the restore Lambda image)"
            )

    try:
        import boto3

        arn = boto3.client("sts").get_caller_identity()["Arn"]
        print(f"  ok: AWS credentials ({arn})")
    except Exception as exc:
        failures.append(f"AWS credentials not working: {exc}")

    if failures:
        for failure in failures:
            print(f"  FAIL: {failure}", file=sys.stderr)
        sys.exit(1)
    print("All preflight checks passed.")


def stage_infra(args) -> None:
    ui.banner("Terraform: init / validate / apply")
    tf.init()
    tf.validate()
    tf.apply(auto_approve=args.auto_approve)


def stage_restore_db(args) -> None:
    ui.banner("Restoring dvdrental database into RDS (via Lambda)")
    outputs = tf.get_outputs()
    result = restore.invoke_restore_lambda(
        outputs["restore_lambda_name"], outputs["region"]
    )
    print(
        f"Restore complete: {result['table_count']} tables in schema public."
    )


def stage_ingest(args) -> None:
    ui.banner("Glue ingestion: RDS -> S3 landing layer")
    outputs = tf.get_outputs()
    glue.run_glue_job(outputs["glue_job_name"], outputs["region"])
    print(ui.lake_formation_checkpoint(outputs))


def stage_verify_lf(args) -> None:
    ui.banner("Verifying Lake Formation grants (Spectrum smoke query)")
    outputs = tf.get_outputs()
    try:
        redshift.verify_lake_formation_access(
            outputs["redshift_workgroup_name"], outputs["region"]
        )
    except redshift.LakeFormationNotGranted as exc:
        print(f"\n{exc}", file=sys.stderr)
        print(ui.lake_formation_checkpoint(outputs), file=sys.stderr)
        sys.exit(1)
    print("Lake Formation grants verified — Redshift can read the catalog.")


def stage_configure_dbt(args) -> None:
    ui.banner("Configuring dbt profile from terraform outputs")
    outputs = tf.get_outputs()
    target = dbt.configure_profiles(outputs["redshift_endpoint"])
    print(f"Wrote {target} (host: {outputs['redshift_endpoint']})")
    dbt.run_dbt("debug")


def stage_run_dbt(args) -> None:
    stage_verify_lf(args)
    ui.banner("dbt: building the star schema on Redshift")
    dbt.run_dbt("deps")
    dbt.run_dbt("run", "--select", "starschemamodel")


def stage_all(args) -> None:
    stage_check(args)
    stage_infra(args)
    stage_restore_db(args)
    stage_ingest(args)
    # stops here on purpose: Lake Formation grants are manual (Step 5);
    # the checkpoint message printed by stage_ingest explains what to do


def stage_resume(args) -> None:
    stage_verify_lf(args)
    stage_configure_dbt(args)
    ui.banner("dbt: building the star schema on Redshift")
    dbt.run_dbt("deps")
    dbt.run_dbt("run", "--select", "starschemamodel")
    ui.banner("Deployment complete")


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    sub = parser.add_subparsers(dest="command", required=True)

    stages = {
        "check": (stage_check, "Preflight checks (tools, docker, AWS creds)"),
        "infra": (stage_infra, "terraform init/validate/apply"),
        "restore-db": (
            stage_restore_db,
            "Restore dvdrental dump into RDS via the in-VPC Lambda",
        ),
        "ingest": (
            stage_ingest,
            "Run the Glue job and wait; prints the Lake Formation steps",
        ),
        "verify-lf": (
            stage_verify_lf,
            "Check that the manual Lake Formation grants are in place",
        ),
        "configure-dbt": (
            stage_configure_dbt,
            "Write ~/.dbt/profiles.yml from terraform outputs + dbt debug",
        ),
        "run-dbt": (stage_run_dbt, "verify-lf, then dbt deps + dbt run"),
        "all": (
            stage_all,
            "check -> infra -> restore-db -> ingest, then stop for the"
            " manual Lake Formation step",
        ),
        "resume": (
            stage_resume,
            "verify-lf -> configure-dbt -> dbt run (after the manual step)",
        ),
    }
    for name, (func, help_text) in stages.items():
        stage_parser = sub.add_parser(name, help=help_text)
        if name in ("infra", "all"):
            stage_parser.add_argument(
                "--auto-approve",
                action="store_true",
                help="pass -auto-approve to terraform apply",
            )
        stage_parser.set_defaults(func=func)

    args = parser.parse_args()
    try:
        args.func(args)
    except subprocess.CalledProcessError as exc:
        print(f"\ncommand failed: {exc.cmd}", file=sys.stderr)
        sys.exit(exc.returncode)
    except (RuntimeError, TimeoutError) as exc:
        print(f"\nerror: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
