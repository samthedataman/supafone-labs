"""Shared test fixtures: an offline provider and a sample Ultravox transcript event."""
import pytest

from supafone_labs.llm import FakeLLMProvider
from supafone_labs.runtime.core.state import build_initial_state


@pytest.fixture
def fake_provider() -> FakeLLMProvider:
    return FakeLLMProvider()


@pytest.fixture
def ultravox_event() -> dict:
    return {
        "type": "transcript",
        "speaker": "caller",
        "text": "I was rear-ended at a red light yesterday and my neck hurts.",
        "final": True,
        "call_id": "call_test_1",
    }


@pytest.fixture
def ultravox_state():
    return build_initial_state(provider="ultravox", session_id="call_test_1")
