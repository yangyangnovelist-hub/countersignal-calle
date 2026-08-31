"""Validated input for one frozen customer-discovery experiment call."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Any

E164 = re.compile(r"^\+[1-9]\d{7,14}$")
SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{2,63}$")
LOCALE = re.compile(r"^[a-z]{2,3}(?:-[A-Z]{2})?$")
REGION = re.compile(r"^[A-Z]{2}$")
PHONE_LIKE = re.compile(r"(?<!\w)\+?[1-9]\d{7,14}(?!\w)")
EMAIL_LIKE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
SECRET_LIKE = re.compile(
    r"(?i)\b(api[_ -]?key|access[_ -]?token|password|private[_ -]?key|"
    r"client[_ -]?secret|credential|bearer)\b"
)


@dataclass(frozen=True)
class DecisionRule:
    target_completed_interviews: int
    support_minimum: int
    contradiction_limit: int


@dataclass(frozen=True)
class ExperimentRequest:
    experiment_id: str
    caller_business_name: str
    hypothesis: str
    participant_segment: str
    participant_phone: str
    authorized_research_contact: bool
    questions: tuple[str, ...]
    decision_rule: DecisionRule
    region: str
    locale: str

    def public_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["participant_phone"] = mask_phone(self.participant_phone)
        return value


def clean_text(value: Any, field: str, minimum: int, maximum: int) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be a string")
    cleaned = " ".join(value.split())
    if not minimum <= len(cleaned) <= maximum:
        raise ValueError(f"{field} must contain {minimum}-{maximum} characters")
    return cleaned


def clean_spoken_text(value: Any, field: str, minimum: int, maximum: int) -> str:
    cleaned = clean_text(value, field, minimum, maximum)
    if SECRET_LIKE.search(cleaned) or PHONE_LIKE.search(cleaned) or EMAIL_LIKE.search(cleaned):
        raise ValueError(f"{field} appears to contain credentials or personal contact data")
    return cleaned


def bounded_integer(value: Any, field: str, minimum: int, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
        raise ValueError(f"{field} must be an integer from {minimum} to {maximum}")
    return value


def parse_rule(raw: Any) -> DecisionRule:
    if not isinstance(raw, dict):
        raise ValueError("decision_rule must be an object")
    expected = {"target_completed_interviews", "support_minimum", "contradiction_limit"}
    if set(raw) != expected:
        raise ValueError("decision_rule must contain only the three frozen thresholds")
    target = bounded_integer(raw["target_completed_interviews"], "target", 3, 30)
    support = bounded_integer(raw["support_minimum"], "support_minimum", 1, target)
    contradiction = bounded_integer(
        raw["contradiction_limit"], "contradiction_limit", 1, target
    )
    if support + contradiction > target:
        raise ValueError("support_minimum plus contradiction_limit cannot exceed target")
    return DecisionRule(target, support, contradiction)


def parse_request(raw: Any) -> ExperimentRequest:
    if not isinstance(raw, dict):
        raise ValueError("request must be a JSON object")

    experiment_id = clean_text(raw.get("experiment_id"), "experiment_id", 3, 64)
    if not SAFE_ID.fullmatch(experiment_id):
        raise ValueError("experiment_id contains unsupported characters")

    phone = clean_text(raw.get("participant_phone"), "participant_phone", 1, 32)
    if not E164.fullmatch(phone):
        raise ValueError("participant_phone must use E.164 format")
    if raw.get("authorized_research_contact") is not True:
        raise ValueError("authorized_research_contact must be true")

    questions = raw.get("questions")
    if not isinstance(questions, list) or len(questions) != 4:
        raise ValueError("questions must contain exactly four pre-registered questions")
    cleaned_questions = tuple(
        clean_spoken_text(value, f"questions[{index}]", 8, 180)
        for index, value in enumerate(questions)
    )
    if len({question.casefold() for question in cleaned_questions}) != len(cleaned_questions):
        raise ValueError("questions must be unique")

    region = clean_text(raw.get("region"), "region", 1, 16)
    if not REGION.fullmatch(region):
        raise ValueError("region must be a two-letter uppercase country code")
    locale = clean_text(raw.get("locale", "en-US"), "locale", 2, 16)
    if not LOCALE.fullmatch(locale):
        raise ValueError("locale must look like en-US")

    return ExperimentRequest(
        experiment_id=experiment_id,
        caller_business_name=clean_spoken_text(
            raw.get("caller_business_name"), "caller_business_name", 2, 80
        ),
        hypothesis=clean_spoken_text(raw.get("hypothesis"), "hypothesis", 12, 300),
        participant_segment=clean_spoken_text(
            raw.get("participant_segment"), "participant_segment", 8, 180
        ),
        participant_phone=phone,
        authorized_research_contact=True,
        questions=cleaned_questions,
        decision_rule=parse_rule(raw.get("decision_rule")),
        region=region,
        locale=locale,
    )


def mask_phone(phone: str) -> str:
    return f"{phone[:3]}{'*' * max(4, len(phone) - 6)}{phone[-3:]}"
