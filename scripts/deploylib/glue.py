"""Start the Glue ingestion job and poll until it finishes."""

import time

import boto3

TERMINAL_FAILURE_STATES = {"FAILED", "ERROR", "TIMEOUT", "STOPPED"}


def run_glue_job(
    job_name: str,
    region: str,
    poll_seconds: int = 30,
    timeout_seconds: int = 3600,
    glue_client=None,
    sleep=time.sleep,
    log=print,
) -> str:
    """Start `job_name`, poll until SUCCEEDED, and return the run id.

    Raises RuntimeError on a terminal failure state and TimeoutError if the
    run is still going after `timeout_seconds`.
    """
    client = glue_client or boto3.client("glue", region_name=region)
    run_id = client.start_job_run(JobName=job_name)["JobRunId"]
    log(f"Started Glue job {job_name} (run id: {run_id})")

    waited = 0
    while True:
        state = client.get_job_run(JobName=job_name, RunId=run_id)["JobRun"][
            "JobRunState"
        ]
        if state == "SUCCEEDED":
            log(f"Glue job {job_name} succeeded after ~{waited}s")
            return run_id
        if state in TERMINAL_FAILURE_STATES:
            raise RuntimeError(
                f"Glue job {job_name} run {run_id} ended in state {state}"
            )
        if waited >= timeout_seconds:
            raise TimeoutError(
                f"Glue job {job_name} run {run_id} still {state}"
                f" after {timeout_seconds}s"
            )
        log(f"  {state}... ({waited}s elapsed)")
        sleep(poll_seconds)
        waited += poll_seconds
