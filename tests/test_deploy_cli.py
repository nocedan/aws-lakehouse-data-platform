import io
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))
sys.path.insert(0, str(REPO_ROOT / "lambda" / "restore_db"))

import handler  # lambda/restore_db/handler.py
from deploylib import dbt, glue, redshift, restore, tf


# ── tf: terraform output parsing ──────────────────────────────────────────────

def test_parse_outputs():
    raw = json.dumps({
        "glue_job_name": {"sensitive": False, "type": "string",
                          "value": "dvdrentals-extraction-tf"},
        "region": {"sensitive": False, "type": "string", "value": "us-west-2"},
    })
    assert tf.parse_outputs(raw) == {
        "glue_job_name": "dvdrentals-extraction-tf",
        "region": "us-west-2",
    }


def test_parse_outputs_empty():
    assert tf.parse_outputs("{}") == {}


# ── dbt: profiles.yml templating ──────────────────────────────────────────────

def test_render_profiles_replaces_host_and_keeps_other_keys():
    template = (REPO_ROOT / "profiles.yml").read_text()
    rendered = dbt.render_profiles(template, "my-host.amazonaws.com")
    import yaml
    profile = yaml.safe_load(rendered)["dvdrentals"]["outputs"]["dev"]
    assert profile["host"] == "my-host.amazonaws.com"
    assert profile["port"] == 5439
    assert profile["workgroup"] == "redshift-serverless-workgroup"
    assert dbt.HOST_PLACEHOLDER not in rendered


def test_repo_profiles_has_placeholder():
    template = (REPO_ROOT / "profiles.yml").read_text()
    assert dbt.HOST_PLACEHOLDER in template


def test_configure_profiles_writes_to_dir(tmp_path):
    target = dbt.configure_profiles("h.example.com", dbt_dir=tmp_path / ".dbt")
    assert target == tmp_path / ".dbt" / "profiles.yml"
    assert "h.example.com" in target.read_text()


# ── glue: job polling ─────────────────────────────────────────────────────────

def _glue_client(states):
    client = MagicMock()
    client.start_job_run.return_value = {"JobRunId": "run-1"}
    client.get_job_run.side_effect = [
        {"JobRun": {"JobRunState": s}} for s in states
    ]
    return client


def test_run_glue_job_succeeds():
    client = _glue_client(["RUNNING", "RUNNING", "SUCCEEDED"])
    run_id = glue.run_glue_job(
        "job", "us-west-2", glue_client=client, sleep=lambda s: None,
        log=lambda m: None,
    )
    assert run_id == "run-1"


def test_run_glue_job_fails():
    client = _glue_client(["RUNNING", "FAILED"])
    with pytest.raises(RuntimeError, match="FAILED"):
        glue.run_glue_job(
            "job", "us-west-2", glue_client=client, sleep=lambda s: None,
            log=lambda m: None,
        )


def test_run_glue_job_times_out():
    client = _glue_client(["RUNNING"] * 10)
    with pytest.raises(TimeoutError):
        glue.run_glue_job(
            "job", "us-west-2", glue_client=client, sleep=lambda s: None,
            log=lambda m: None, poll_seconds=30, timeout_seconds=60,
        )


# ── restore: lambda invoke handling ───────────────────────────────────────────

def _invoke_response(payload, function_error=None):
    response = {"Payload": io.BytesIO(json.dumps(payload).encode())}
    if function_error:
        response["FunctionError"] = function_error
    return response


def test_invoke_restore_lambda_ok():
    client = MagicMock()
    client.invoke.return_value = _invoke_response(
        {"status": "ok", "table_count": 15}
    )
    result = restore.invoke_restore_lambda("fn", "us-west-2",
                                           lambda_client=client)
    assert result["table_count"] == 15


def test_invoke_restore_lambda_function_error():
    client = MagicMock()
    client.invoke.return_value = _invoke_response(
        {"errorMessage": "pg_restore failed"}, function_error="Unhandled"
    )
    with pytest.raises(RuntimeError, match="pg_restore failed"):
        restore.invoke_restore_lambda("fn", "us-west-2", lambda_client=client)


# ── redshift: lake formation smoke test ──────────────────────────────────────

def _redshift_client(statuses, error=None):
    client = MagicMock()
    client.execute_statement.return_value = {"Id": "stmt-1"}
    descs = []
    for status in statuses:
        desc = {"Status": status}
        if error and status in ("FAILED", "ABORTED"):
            desc["Error"] = error
        descs.append(desc)
    client.describe_statement.side_effect = descs
    return client


def test_verify_lf_finished():
    client = _redshift_client(["STARTED", "FINISHED"])
    redshift.verify_lake_formation_access(
        "wg", "us-west-2", redshift_data_client=client, sleep=lambda s: None
    )


def test_verify_lf_failed_raises_not_granted():
    client = _redshift_client(["STARTED", "FAILED"],
                              error="permission denied")
    with pytest.raises(redshift.LakeFormationNotGranted,
                       match="permission denied"):
        redshift.verify_lake_formation_access(
            "wg", "us-west-2", redshift_data_client=client,
            sleep=lambda s: None,
        )


# ── lambda handler ────────────────────────────────────────────────────────────

@pytest.fixture
def handler_env(monkeypatch):
    for key, value in {
        "DB_HOST": "db.example.com", "DB_PORT": "5432", "DB_USER": "u",
        "DB_PASSWORD": "secret", "DB_NAME": "dvdrentals",
        "BACKUP_BUCKET": "bucket", "BACKUP_KEY": "k/dvdrental.zip",
    }.items():
        monkeypatch.setenv(key, value)


def test_handler_conninfo(handler_env):
    info = handler.conninfo()
    assert "host=db.example.com" in info
    assert "sslmode=verify-full" in info
    assert "secret" not in info  # password goes via PGPASSWORD, not conninfo


def test_handler_pg_restore_flags(handler_env, monkeypatch):
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append((cmd, kwargs))
        return MagicMock(returncode=0, stdout="15\n")

    monkeypatch.setattr(handler.subprocess, "run", fake_run)
    handler.run_pg_restore(Path("/tmp/dvdrental.tar"))
    cmd, kwargs = calls[0]
    for flag in ("--no-owner", "--no-privileges", "--clean", "--if-exists"):
        assert flag in cmd
    assert kwargs["env"]["PGPASSWORD"] == "secret"


def test_handler_pg_restore_failure(handler_env, monkeypatch):
    monkeypatch.setattr(
        handler.subprocess, "run",
        lambda *a, **k: MagicMock(returncode=1, stderr="boom"),
    )
    with pytest.raises(RuntimeError, match="boom"):
        handler.run_pg_restore(Path("/tmp/dvdrental.tar"))


def test_handler_fails_on_low_table_count(handler_env, monkeypatch):
    monkeypatch.setattr(handler, "download_backup",
                        lambda b, k: Path("/tmp/dvdrental.tar"))
    monkeypatch.setattr(handler, "run_pg_restore", lambda p: None)
    monkeypatch.setattr(handler, "count_public_tables", lambda: 3)
    with pytest.raises(RuntimeError, match="found 3"):
        handler.lambda_handler({}, None)


def test_handler_returns_table_count(handler_env, monkeypatch):
    monkeypatch.setattr(handler, "download_backup",
                        lambda b, k: Path("/tmp/dvdrental.tar"))
    monkeypatch.setattr(handler, "run_pg_restore", lambda p: None)
    monkeypatch.setattr(handler, "count_public_tables", lambda: 15)
    assert handler.lambda_handler({}, None) == {
        "status": "ok", "table_count": 15,
    }
