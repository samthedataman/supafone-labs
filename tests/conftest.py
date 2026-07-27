"""Shared test fixtures: an offline provider and a sample Ultravox transcript event."""
from pathlib import Path

import pytest

from supafone_labs.llm import FakeLLMProvider
from supafone_labs.runtime.core.state import build_initial_state

# Cloud gateway ships separately; CI also ignores these when absent.
_CLOUD_APP = Path(__file__).resolve().parents[1] / "cloud" / "app.py"


def pytest_ignore_collect(collection_path: Path) -> bool | None:
    if collection_path.name.startswith("test_cloud_") and not _CLOUD_APP.is_file():
        return True
    return None


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
