"""Release gate for the fourteen provider/framework injection contracts.

This suite is deterministic and credential-free: a real provider event enters
the public facade, the Watcher forms a directive, and the resulting action is
validated against the provider's current native message or framework API.
Credentialed network acceptance lives in test_live_injection_contracts.py.
"""
from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

import pytest

from supafone_labs import SupafoneLabs
from supafone_labs.llm import FakeLLMProvider
from supafone_labs.oracle.session import OracleSession
from supafone_labs.runtime.provider_contracts import (
    CONTRACT_BY_PROVIDER,
    PROVIDER_INJECTION_CONTRACTS,
    ProviderInjectionContract,
)

from tests.test_adapters import CASES

PUBLIC_PROVIDER_IDS = {
    "supafone",
    "ultravox",
    "vapi",
    "retell",
    "bland",
    "gpt_realtime",
    "grok",
    "gemini_live",
    "elevenlabs",
    "deepgram",
    "livekit",
    "pipecat",
    "cartesia",
    "inworld",
}
REPO_ROOT = Path(__file__).resolve().parents[1]


def _instruction_text(payload: dict) -> str:
    return json.dumps(payload, sort_keys=True)


def _assert_native_shape(
    contract: ProviderInjectionContract,
    payload: dict,
    expected_text: str,
) -> None:
    provider = contract.provider_id
    if provider in {"supafone", "ultravox"}:
        assert payload["type"] == "user_text_message"
        assert payload["urgency"] == "later"
        assert payload["text"] == f"<instruction>{expected_text}</instruction>"
        return
    if provider == "vapi":
        assert payload == {
            "type": "add-message",
            "message": {"role": "system", "content": expected_text},
            "triggerResponseEnabled": False,
        }
        return
    if provider == "retell":
        assert payload["role"] == "system"
        assert payload["content"] == expected_text
        return
    if provider in {"gpt_realtime", "inworld"}:
        assert payload["type"] == "conversation.item.create"
        item = payload["item"]
        assert item["type"] == "message" and item["role"] == "system"
        assert item["content"] == [
            {"type": "input_text", "text": expected_text}
        ]
        return
    if provider == "grok":
        assert payload == {
            "type": "response.create",
            "response": {"instructions": expected_text},
        }
        return
    if provider == "gemini_live":
        content = payload["clientContent"]
        assert content["turnComplete"] is False
        assert content["turns"] == [
            {
                "role": "user",
                "parts": [{"text": expected_text}],
            }
        ]
        return
    if provider == "elevenlabs":
        assert payload == {
            "type": "contextual_update",
            "text": expected_text,
        }
        return
    if provider == "deepgram":
        assert payload == {
            "type": "UpdatePrompt",
            "prompt": expected_text,
        }
        return
    if provider == "livekit":
        assert payload == {
            "role": "system",
            "content": expected_text,
        }
        return
    if provider == "pipecat":
        assert payload == {
            "frame": "LLMMessagesAppendFrame",
            "messages": [
                {
                    "role": "developer",
                    "content": expected_text,
                }
            ],
            "run_llm": False,
        }
        return
    raise AssertionError(f"{provider}: injectable contract has no shape assertion")


def test_public_matrix_is_exactly_fourteen_unique_runtimes():
    ids = [contract.provider_id for contract in PROVIDER_INJECTION_CONTRACTS]
    assert len(ids) == 14
    assert len(set(ids)) == 14
    assert set(ids) == PUBLIC_PROVIDER_IDS
    assert set(CONTRACT_BY_PROVIDER) == PUBLIC_PROVIDER_IDS


@pytest.mark.parametrize("contract", PROVIDER_INJECTION_CONTRACTS, ids=lambda c: c.provider_id)
def test_contracts_have_current_primary_source_and_acceptance_criteria(contract):
    parsed = urlparse(contract.official_docs)
    assert parsed.scheme == "https" and parsed.netloc
    assert contract.acknowledgement.strip()
    verified = date.fromisoformat(contract.verified_on)
    age_days = (date.today() - verified).days
    assert 0 <= age_days <= 90, f"{contract.provider_id}: contract audit is {age_days} days old"


@pytest.mark.parametrize("contract", PROVIDER_INJECTION_CONTRACTS, ids=lambda c: c.provider_id)
async def test_provider_event_to_exact_injection_action(contract):
    case = CASES[contract.adapter_id]
    brain = SupafoneLabs(
        provider=contract.adapter_id,
        oracle=OracleSession(provider=FakeLLMProvider()),
        mode="return",
        telemetry=False,
    )
    result = await brain.observe(case.caller)
    assert result.events, f"{contract.provider_id}: native input was not parsed"
    assert result.belief is not None, f"{contract.provider_id}: Watcher formed no belief"
    assert result.directive is not None, f"{contract.provider_id}: Watcher formed no directive"

    if not contract.injectable:
        assert result.actions == []
        assert case.adapter.capabilities().supports_hidden_instruction_injection is False
        return

    assert len(result.actions) == 1
    action = result.actions[0]
    assert action.kind == contract.action_kind
    expected_text = result.decision.payload["text"]
    assert "acknowledge the injury" in _instruction_text(action.payload).lower()
    json.dumps(action.payload)
    _assert_native_shape(contract, action.payload, expected_text)


def test_every_public_runtime_has_an_explicit_live_probe_policy():
    assert all(contract.live_probe for contract in PROVIDER_INJECTION_CONTRACTS)
    assert all(
        contract.live_probe != "not_applicable" or not contract.injectable
        for contract in PROVIDER_INJECTION_CONTRACTS
    )


def test_native_external_channels_have_eight_credentialed_acceptance_probes():
    providers = {
        contract.provider_id
        for contract in PROVIDER_INJECTION_CONTRACTS
        if contract.live_probe in {"active_call", "realtime_socket", "provider_sdk"}
    }
    assert providers == {
        "ultravox",
        "vapi",
        "gpt_realtime",
        "grok",
        "gemini_live",
        "elevenlabs",
        "deepgram",
        "inworld",
    }


def test_console_provider_picker_matches_the_release_gate_exactly():
    console_path = REPO_ROOT / "landing" / "console.html"
    if not console_path.exists():
        pytest.skip("private Labs landing application is not part of the public SDK repo")
    html = console_path.read_text(encoding="utf-8")
    select = re.search(r'<select id="harnessAi"[^>]*>(.*?)</select>', html, re.DOTALL)
    assert select, "console is missing the harness provider picker"
    values = set(re.findall(r'<option value="([^"]+)"', select.group(1)))
    assert values == PUBLIC_PROVIDER_IDS | {"custom"}


def test_copy_paste_integrations_do_not_use_retired_controls():
    paths = [
        REPO_ROOT / "README.md",
        REPO_ROOT / "docs" / "providers.md",
        REPO_ROOT / "examples" / "README.md",
        REPO_ROOT / "examples" / "full_stack_twilio_ultravox.py",
        REPO_ROOT / "examples" / "gpt_realtime.py",
        REPO_ROOT / "examples" / "vapi_webhook_server.py",
        REPO_ROOT / "landing" / "console.html",
        REPO_ROOT / "landing" / "llms.txt",
        REPO_ROOT / "sdk-ts" / "README.md",
    ]
    retired = {
        "assistant_override",
        "instructions_append",
        "input_text_message",
        "session.inject_message",
    }
    for path in paths:
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        found = sorted(token for token in retired if token in text)
        assert not found, f"{path.relative_to(REPO_ROOT)} uses retired controls: {found}"


@pytest.mark.parametrize(
    "relative_path",
    [
        "examples/full_stack_twilio_ultravox.py",
        "examples/gpt_realtime.py",
        "examples/livekit_agent.py",
        "examples/pipecat_pipeline.py",
        "examples/retell_custom_llm.py",
        "examples/ultravox_end_to_end.py",
        "examples/vapi_webhook_server.py",
    ],
)
def test_copy_paste_python_integrations_compile(relative_path):
    path = REPO_ROOT / relative_path
    compile(path.read_text(encoding="utf-8"), str(path), "exec")
