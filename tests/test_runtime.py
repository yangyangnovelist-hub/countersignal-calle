import pytest

from countersignal.models import parse_request
from countersignal.runtime import DEFAULT_BASE_URL, execute, validate_base_url
from tests.test_policy import RAW, provider


class Calls:
    def __init__(self, request, *, create_id="call-001", result=None):
        self.request = request
        self.create_id = create_id
        self.result = result if result is not None else provider(request)
        self.created = None

    def create(self, **kwargs):
        self.created = kwargs
        return {"id": self.create_id}

    def wait_for_result(self, call_id, *, timeout_seconds, interval_seconds):
        assert call_id == self.create_id
        assert timeout_seconds == 9
        assert interval_seconds == 2
        return self.result


def test_execute_calls_sdk_and_routes_bound_result():
    request = parse_request(RAW)
    calls = Calls(request)
    accepted = []
    result = execute(request, calls, 9, accepted.append)
    assert accepted == ["call-001"]
    assert calls.created["idempotency_key"].startswith("countersignal-")
    assert result["decision"]["outcome"] == "contradiction"
    assert result["creates_phone_call"] is True


def test_execute_rejects_missing_id_and_non_object_result():
    request = parse_request(RAW)
    with pytest.raises(RuntimeError, match="call id"):
        execute(request, Calls(request, create_id=""), 9)
    bad = Calls(request, result={**provider(request), "structured_result": "bad"})
    with pytest.raises(RuntimeError, match="not an object"):
        execute(request, bad, 9)


@pytest.mark.parametrize(
    "value",
    [
        "https://evil.example",
        "http://api.heycall-e.com",
        "https://user:pass@api.heycall-e.com",
        "https://api.heycall-e.com/path",
        "http://localhost",
    ],
)
def test_base_url_rejects_untrusted_origins(value):
    with pytest.raises(ValueError, match="official HTTPS"):
        validate_base_url(value)


def test_base_url_allows_only_official_or_explicit_loopback():
    assert validate_base_url("https://api.heycall-e.com/") == DEFAULT_BASE_URL
    assert validate_base_url("http://127.0.0.1:8123/") == "http://127.0.0.1:8123"
