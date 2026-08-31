"""Run one consented synthetic contradiction interview and emit public-safe proof."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

from countersignal.cli import execute_once
from countersignal.models import parse_request
from countersignal.runtime import DEFAULT_BASE_URL

CONSENT_PHRASE = "I HAVE EXPLICIT CONSENT"
FROZEN_PHRASE = "THE PROTOCOL IS FROZEN"
DEFAULT_DATABASE = Path("data/consented-live-demo.sqlite3")
DEFAULT_FAILURE_OUTPUT = Path("data/consented-live-last-result.json")
DEFAULT_PUBLIC_OUTPUT = Path("artifacts/consented-live-contradiction.json")


def synthetic_request(phone: str, region: str = "US", locale: str = "en-US") -> dict[str, Any]:
    return {
        "experiment_id": "exp-permit-status-001",
        "caller_business_name": "CounterSignal Research",
        "hypothesis": (
            "Small contractors repeatedly lose productive time calling permit offices for status."
        ),
        "participant_segment": "Small construction contractors who manage active permits",
        "participant_phone": phone,
        "authorized_research_contact": True,
        "questions": [
            "How did you check the status of your most recent permit?",
            "What part of that process took the most active time?",
            "What workaround do you already use today?",
            "When would a delegated status call be unacceptable?",
        ],
        "decision_rule": {
            "target_completed_interviews": 8,
            "support_minimum": 5,
            "contradiction_limit": 3,
        },
        "region": region,
        "locale": locale,
    }


def public_proof(result: dict[str, Any]) -> dict[str, Any]:
    decision = result.get("decision")
    structured = result.get("structured_result")
    if not isinstance(decision, dict) or decision.get("outcome") != "contradiction":
        raise ValueError("public proof requires a real contradiction outcome")
    if decision.get("counts_toward_completed") is not True:
        raise ValueError("public proof requires countable consent-bound evidence")
    if not isinstance(structured, dict):
        raise ValueError("public proof requires a structured result")
    return {
        "evidence_type": "consented_live_contradiction_synthetic_experiment",
        "provider": "CALL-E",
        "call_id": result.get("call_id"),
        "status": result.get("status"),
        "task_completed": result.get("task_completed"),
        "completion_confidence": result.get("completion_confidence"),
        "classification": "contradiction",
        "decision": decision,
        "privacy": {
            "real_phone_number_published": False,
            "participant_identity_published": False,
            "transcript_published": False,
            "recording_published": False,
        },
        "claim_boundary": (
            "Real CALL-E transport and CounterSignal evidence routing in a synthetic experiment; "
            "one interview is not product-market-fit evidence."
        ),
    }


def write_exclusive(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def write_replace(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--phone",
        required=True,
        help="Owned or explicitly authorized E.164 number",
    )
    parser.add_argument("--region", default="US")
    parser.add_argument("--locale", default="en-US")
    parser.add_argument("--confirm-consent", required=True)
    parser.add_argument("--confirm-frozen-protocol", required=True)
    parser.add_argument("--timeout-seconds", type=int, default=600)
    parser.add_argument("--base-url", default=os.environ.get("CALLE_BASE_URL", DEFAULT_BASE_URL))
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    parser.add_argument("--public-output", type=Path, default=DEFAULT_PUBLIC_OUTPUT)
    parser.add_argument("--failure-output", type=Path, default=DEFAULT_FAILURE_OUTPUT)
    return parser.parse_args(argv)


def run(args: argparse.Namespace) -> dict[str, Any]:
    if args.confirm_consent != CONSENT_PHRASE:
        raise ValueError(f"--confirm-consent must equal: {CONSENT_PHRASE}")
    if args.confirm_frozen_protocol != FROZEN_PHRASE:
        raise ValueError(f"--confirm-frozen-protocol must equal: {FROZEN_PHRASE}")
    if args.timeout_seconds <= 0:
        raise ValueError("--timeout-seconds must be positive")
    if args.public_output.exists():
        raise ValueError(f"refusing to overwrite existing public proof: {args.public_output}")
    request = parse_request(synthetic_request(args.phone, args.region, args.locale))
    execute_args = argparse.Namespace(
        confirm_authorized_recipient=True,
        confirm_frozen_protocol=True,
        allow=[args.phone],
        timeout_seconds=args.timeout_seconds,
        base_url=args.base_url,
        database=args.database,
    )
    result = execute_once(request, execute_args)
    if result.get("decision", {}).get("outcome") != "contradiction":
        write_replace(args.failure_output, result)
        raise RuntimeError(
            "CALL-E completed without a contradiction; inspect the local result and do not retry"
        )
    proof = public_proof(result)
    write_exclusive(args.public_output, proof)
    return proof


def main(argv: list[str] | None = None) -> int:
    try:
        args = parse_args(argv)
        proof = run(args)
        sys.stdout.write(
            f"Consented contradiction proof created: {args.public_output}\n"
            f"call_id={proof.get('call_id')}\n"
        )
        return 0
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        sys.stderr.write(f"error: {exc}\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
