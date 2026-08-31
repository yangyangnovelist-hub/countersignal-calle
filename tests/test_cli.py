import argparse
import json
from pathlib import Path

import calle
import pytest

from countersignal import cli
from countersignal.models import parse_request
from tests.test_policy import RAW, provider


class FakeClient:
    response = None

    def __init__(self, *, api_key, base_url):
        assert api_key == "calle_test_key"
        assert base_url == "http://127.0.0.1:8123"
        self.calls = self

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None

    def create(self, **kwargs):
        return {"id": "call-001"}

    def wait_for_result(self, call_id, *, timeout_seconds, interval_seconds):
        assert call_id == "call-001"
        return self.response


def args(tmp_path: Path):
    return argparse.Namespace(
        confirm_authorized_recipient=True,
        confirm_frozen_protocol=True,
        allow=[RAW["participant_phone"]],
        timeout_seconds=5,
        base_url="http://127.0.0.1:8123",
        database=tmp_path / "ledger.sqlite3",
    )


def test_execute_once_uses_sdk_and_durable_duplicate_lock(tmp_path, monkeypatch):
    request = parse_request(RAW)
    FakeClient.response = provider(request)
    monkeypatch.setattr(calle, "CalleClient", FakeClient)
    monkeypatch.setenv("CALLE_LIVE_CALLS_ENABLED", "true")
    monkeypatch.setenv("CALLE_API_KEY", "calle_test_key")
    result = cli.execute_once(request, args(tmp_path))
    assert result["decision"]["outcome"] == "contradiction"
    with pytest.raises(RuntimeError, match="already reserved"):
        cli.execute_once(request, args(tmp_path))


@pytest.mark.parametrize(
    ("change", "message"),
    [
        (lambda value: setattr(value, "confirm_authorized_recipient", False), "authorized"),
        (lambda value: setattr(value, "confirm_frozen_protocol", False), "frozen"),
        (lambda value: setattr(value, "allow", []), "exact participant"),
        (lambda value: setattr(value, "timeout_seconds", 0), "positive"),
    ],
)
def test_execute_gates_before_external_call(tmp_path, monkeypatch, change, message):
    monkeypatch.setenv("CALLE_LIVE_CALLS_ENABLED", "true")
    monkeypatch.setenv("CALLE_API_KEY", "calle_test_key")
    value = args(tmp_path)
    change(value)
    with pytest.raises(ValueError, match=message):
        cli.execute_once(parse_request(RAW), value)


def test_execute_requires_explicit_environment_and_key(tmp_path, monkeypatch):
    monkeypatch.delenv("CALLE_LIVE_CALLS_ENABLED", raising=False)
    monkeypatch.delenv("CALLE_API_KEY", raising=False)
    with pytest.raises(ValueError, match="LIVE_CALLS"):
        cli.execute_once(parse_request(RAW), args(tmp_path))
    monkeypatch.setenv("CALLE_LIVE_CALLS_ENABLED", "true")
    with pytest.raises(ValueError, match="API_KEY"):
        cli.execute_once(parse_request(RAW), args(tmp_path))


def test_provider_exception_becomes_unknown_and_blocks_retry(tmp_path, monkeypatch):
    request = parse_request(RAW)
    FakeClient.response = provider(request)
    monkeypatch.setattr(calle, "CalleClient", FakeClient)
    monkeypatch.setenv("CALLE_LIVE_CALLS_ENABLED", "true")
    monkeypatch.setenv("CALLE_API_KEY", "calle_test_key")

    def fail(**kwargs):
        raise OSError("network")

    monkeypatch.setattr(FakeClient, "create", fail)
    with pytest.raises(RuntimeError, match="outcome is unknown"):
        cli.execute_once(request, args(tmp_path))


def test_cli_preview_simulate_and_exclusive_output(tmp_path, capsys):
    request_path = tmp_path / "request.json"
    request_path.write_text(json.dumps(RAW), encoding="utf-8")
    assert cli.main(["--request", str(request_path)]) == 0
    assert '"creates_phone_call": false' in capsys.readouterr().out
    output = tmp_path / "result.json"
    assert (
        cli.main(
            [
                "--request",
                str(request_path),
                "--simulate",
                "confirmation",
                "--output",
                str(output),
            ]
        )
        == 0
    )
    assert json.loads(output.read_text())["decision"]["outcome"] == "confirmation"
    assert cli.main(["--request", str(request_path), "--output", str(output)]) == 2
    assert "File exists" in capsys.readouterr().err
