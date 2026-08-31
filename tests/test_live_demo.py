import argparse
import json
from pathlib import Path

import pytest

from countersignal import live_demo


def args(tmp_path: Path):
    return argparse.Namespace(
        phone="+15555550123",
        region="US",
        locale="en-US",
        confirm_consent=live_demo.CONSENT_PHRASE,
        confirm_frozen_protocol=live_demo.FROZEN_PHRASE,
        timeout_seconds=5,
        base_url="http://127.0.0.1:8123",
        database=tmp_path / "ledger.sqlite3",
        public_output=tmp_path / "proof.json",
        failure_output=tmp_path / "failure.json",
    )


def successful_result():
    return {
        "call_id": "call-live-001",
        "status": "completed",
        "task_completed": True,
        "completion_confidence": {"score": 0.96},
        "structured_result": {"answer_class": "contradiction"},
        "decision": {
            "outcome": "contradiction",
            "counts_toward_completed": True,
            "claim_boundary": "not product-market-fit evidence",
        },
    }


def test_public_proof_is_minimal_and_privacy_safe():
    proof = live_demo.public_proof(successful_result())
    rendered = json.dumps(proof)
    assert proof["classification"] == "contradiction"
    assert "+15555550123" not in rendered
    assert "transcript" not in rendered.lower() or proof["privacy"]["transcript_published"] is False


def test_public_proof_rejects_non_contradiction_and_uncounted_result():
    value = successful_result()
    value["decision"]["outcome"] = "confirmation"
    with pytest.raises(ValueError, match="contradiction"):
        live_demo.public_proof(value)
    value = successful_result()
    value["decision"]["counts_toward_completed"] = False
    with pytest.raises(ValueError, match="countable"):
        live_demo.public_proof(value)
    value = successful_result()
    value["structured_result"] = None
    with pytest.raises(ValueError, match="structured"):
        live_demo.public_proof(value)


def test_live_demo_enforces_consent_freeze_and_fresh_output(tmp_path, monkeypatch):
    value = args(tmp_path)
    value.confirm_consent = "yes"
    with pytest.raises(ValueError, match="EXPLICIT CONSENT"):
        live_demo.run(value)
    value = args(tmp_path)
    value.confirm_frozen_protocol = "yes"
    with pytest.raises(ValueError, match="PROTOCOL IS FROZEN"):
        live_demo.run(value)
    value = args(tmp_path)
    value.timeout_seconds = 0
    with pytest.raises(ValueError, match="positive"):
        live_demo.run(value)
    value = args(tmp_path)
    value.public_output.write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="overwrite"):
        live_demo.run(value)


def test_live_demo_writes_public_success_or_local_failure(tmp_path, monkeypatch):
    monkeypatch.setattr(
        live_demo,
        "execute_once",
        lambda request, execute_args: successful_result(),
    )
    proof = live_demo.run(args(tmp_path))
    assert proof["call_id"] == "call-live-001"
    assert json.loads((tmp_path / "proof.json").read_text())["classification"] == "contradiction"

    value = args(tmp_path / "failure-case")
    failed = successful_result()
    failed["decision"]["outcome"] = "unknown"
    monkeypatch.setattr(live_demo, "execute_once", lambda request, execute_args: failed)
    with pytest.raises(RuntimeError, match="do not retry"):
        live_demo.run(value)
    assert json.loads(value.failure_output.read_text())["decision"]["outcome"] == "unknown"


def test_parse_args_and_main_paths(tmp_path, monkeypatch, capsys):
    parsed = live_demo.parse_args(
        [
            "--phone",
            "+442079460123",
            "--region",
            "GB",
            "--locale",
            "en-GB",
            "--confirm-consent",
            live_demo.CONSENT_PHRASE,
            "--confirm-frozen-protocol",
            live_demo.FROZEN_PHRASE,
            "--public-output",
            str(tmp_path / "proof.json"),
        ]
    )
    assert parsed.region == "GB"
    assert parsed.locale == "en-GB"
    assert parsed.timeout_seconds == 600

    monkeypatch.setattr(live_demo, "run", lambda value: {"call_id": "call-main-001"})
    assert (
        live_demo.main(
            [
                "--phone",
                "+15555550123",
                "--confirm-consent",
                live_demo.CONSENT_PHRASE,
                "--confirm-frozen-protocol",
                live_demo.FROZEN_PHRASE,
                "--public-output",
                str(tmp_path / "main-proof.json"),
            ]
        )
        == 0
    )
    assert "call-main-001" in capsys.readouterr().out

    def fail(value):
        raise ValueError("blocked")

    monkeypatch.setattr(live_demo, "run", fail)
    assert (
        live_demo.main(
            [
                "--phone",
                "+15555550123",
                "--confirm-consent",
                live_demo.CONSENT_PHRASE,
                "--confirm-frozen-protocol",
                live_demo.FROZEN_PHRASE,
            ]
        )
        == 2
    )
    assert "blocked" in capsys.readouterr().err
