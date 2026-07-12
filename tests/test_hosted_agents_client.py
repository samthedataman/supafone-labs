import json

from supafone_labs import Supafone


def test_create_inbound_serializes_hosted_agent_payload():
    calls = []

    def transport(method, path, payload):
        calls.append((method, path, payload))
        return {"success": True, "agent": {"agent_key": payload["agent_key"]}, "runtime": {}}

    supafone = Supafone(api_key="sf_test", transport=transport)
    result = supafone.labs.agents.create_inbound(
        {
            "agentKey": "northline-intake",
            "name": "Northline intake",
            "assistantName": "Maya",
            "websiteUrl": "https://northline.example",
            "labs": {"enabled": True, "model": "gemma"},
            "voice": {"provider": "cartesia", "voiceId": "sonic-warm"},
        }
    )

    assert result["agent"]["agent_key"] == "northline-intake"
    payload = calls[0][2]
    assert calls[0][:2] == ("POST", "/api/v1/labs/agents")
    assert payload["agent_key"] == "northline-intake"
    assert payload["agent_type"] == "phone"
    assert payload["style"] == "inbound"
    assert payload["direction"] == "inbound"
    assert payload["preset_key"] == "general_intake_receptionist"
    assert payload["voice"] == {"provider": "cartesia", "voice_id": "sonic-warm"}
    assert payload["telephony"] == {"mode": "supafone_managed", "provider": "supafone"}
    # voice_watcher defaults on and is mirrored into the labs block.
    assert payload["voice_watcher"] is True
    assert payload["labs"] == {"enabled": True, "model": "gemma", "voice_watcher": True}
    assert payload["call_stages"][0]["key"] == "greeting"
    assert payload["call_stages"][-1]["key"] == "close"


def test_create_inbound_with_number_searches_and_assigns_number():
    calls = []

    def transport(method, path, payload):
        calls.append((method, path, payload))
        if path == "/api/v1/labs/agents":
            return {"success": True, "agent": {"agent_key": payload["agent_key"]}, "runtime": {}}
        if path == "/api/v1/labs/phone-numbers/search":
            return {"numbers": [{"phone_number": "+14155550123"}]}
        if path == "/api/v1/labs/phone-numbers":
            return {"success": True, "number": {"phone_number": payload["phone_number"]}}
        raise AssertionError(path)

    supafone = Supafone(api_key="sf_test", transport=transport)
    result = supafone.labs.agents.create_inbound_with_number(
        {
            "agentKey": "northline-intake",
            "name": "Northline intake",
            "assistantName": "Maya",
            "number": {"search": {"areaCode": "415"}},
            "labs": {"enabled": True},
        }
    )

    assert result["number"]["number"]["phone_number"] == "+14155550123"
    assert calls[0][1] == "/api/v1/labs/agents"
    assert calls[1] == (
        "POST",
        "/api/v1/labs/phone-numbers/search",
        {"area_code": "415", "limit": 1},
    )
    assert calls[2] == (
        "POST",
        "/api/v1/labs/phone-numbers",
        {
            "phone_number": "+14155550123",
            "friendly_name": "Northline intake",
            "agent_key": "northline-intake",
            "agent_name": "Maya",
            "preset_key": "general_intake_receptionist",
            "style": "inbound",
            "telephony": {"mode": "supafone_managed", "provider": "supafone"},
        },
    )


def test_byok_labs_payload_matches_typescript_contract():
    calls = []

    def transport(method, path, payload):
        calls.append((method, path, payload))
        return {"success": True, "agent": {"agent_key": payload["agent_key"]}, "runtime": {}}

    supafone = Supafone(api_key="sf_test", transport=transport)
    supafone.labs.agents.create_outbound(
        {
            "agentKey": "speed-to-lead",
            "name": "Speed to lead",
            "providerKeys": {"cartesiaApiKey": "cartesia-key", "inworldApiKey": "inworld-key"},
            "labs": {
                "enabled": True,
                "voiceWatcher": True,
                "mode": "byok",
                "managedInfrastructure": False,
                "stt": {"provider": "deepgram"},
                "llm": {"provider": "anthropic", "model": "claude-haiku-4-5-20251001"},
                "tts": {"provider": "cartesia"},
                "providerKeys": {"deepgram": "deepgram-key"},
            },
        }
    )

    payload = calls[0][2]
    assert payload["style"] == "outbound"
    assert payload["direction"] == "outbound"
    assert payload["provider_keys"] == {
        "cartesia_api_key": "cartesia-key",
        "inworld_api_key": "inworld-key",
    }
    assert payload["labs"] == {
        "enabled": True,
        "voice_watcher": True,
        "mode": "byok",
        "managed_infrastructure": False,
        "stt": {"provider": "deepgram"},
        "llm": {"provider": "anthropic", "model": "claude-haiku-4-5-20251001"},
        "tts": {"provider": "cartesia"},
        "provider_keys": {"deepgram": "deepgram-key"},
    }


def test_python_client_reads_labs_logs_and_stream(monkeypatch):
    requests = []

    class FakeResponse:
        def __init__(self, payload=None, lines=None):
            self.payload = payload
            self.lines = lines or []

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def read(self):
            return json.dumps(self.payload).encode()

        def __iter__(self):
            return iter(self.lines)

    def fake_urlopen(req, timeout):
        requests.append((req, timeout))
        if req.full_url.endswith("/v1/logs?limit=25"):
            return FakeResponse({"logs": [{"id": 7, "endpoint": "oracle"}]})
        return FakeResponse(
            lines=[
                b"id: 7\n",
                b"event: log\n",
                b'data: {\"id\": 7, \"endpoint\": \"oracle\"}\n',
                b"\n",
            ]
        )

    from supafone_labs import client as client_module

    monkeypatch.setattr(client_module.request, "urlopen", fake_urlopen)
    supafone = Supafone(api_key="sf_test", labs_api_key="sl_test", timeout=3)

    assert supafone.logs(25) == {"logs": [{"id": 7, "endpoint": "oracle"}]}
    assert next(supafone.stream_logs(limit=1, snapshot=True)) == {"id": 7, "endpoint": "oracle"}
    assert requests[0][0].get_header("Authorization") == "Bearer sl_test"
    assert requests[1][0].get_header("Authorization") == "Bearer sl_test"


def test_python_client_reads_voices_and_previews_audio(monkeypatch):
    requests = []

    class Headers(dict):
        def get(self, key, default=None):
            return super().get(key.lower(), default)

    class FakeResponse:
        def __init__(self, payload=None, audio=b"", media_type="audio/wav"):
            self.payload = payload
            self.audio = audio
            self.headers = Headers({"content-type": media_type})

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def read(self):
            if self.payload is not None:
                return json.dumps(self.payload).encode()
            return self.audio

    def fake_urlopen(req, timeout):
        requests.append((req, timeout))
        if req.full_url.endswith("/v1/voices"):
            return FakeResponse({"voices": [{"voice": "cartesia:voice-a", "live": True}]})
        assert req.full_url.endswith("/v1/tts")
        assert json.loads(req.data.decode()) == {"text": "hello", "voice": "cartesia:voice-a"}
        return FakeResponse(audio=b"RIFFdemo", media_type="audio/wav")

    from supafone_labs import client as client_module

    monkeypatch.setattr(client_module.request, "urlopen", fake_urlopen)
    supafone = Supafone(api_key="sf_test", labs_api_key="sl_test", timeout=3)

    assert supafone.voices()["voices"][0]["voice"] == "cartesia:voice-a"
    preview = supafone.preview_voice("cartesia:voice-a", "hello")
    assert preview.content == b"RIFFdemo"
    assert preview.media_type == "audio/wav"
    assert requests[0][0].get_header("Authorization") == "Bearer sl_test"
    assert requests[1][0].get_header("Authorization") == "Bearer sl_test"


def test_camelcase_agent_methods_match_typescript_contract():
    calls = []

    def transport(method, path, payload):
        calls.append((method, path, payload))
        if path == "/api/v1/labs/agents":
            return {"success": True, "agent": {"agent_key": payload["agent_key"]}, "runtime": {}}
        if path == "/api/v1/labs/phone-numbers/search":
            return {"numbers": [{"phone_number": "+14155550124"}]}
        if path == "/api/v1/labs/phone-numbers":
            return {"success": True, "number": {"phone_number": payload["phone_number"]}}
        raise AssertionError(path)

    supafone = Supafone(api_key="sf_test", transport=transport)
    result = supafone.labs.agents.createInboundWithNumber(
        {
            "agentKey": "northline-intake",
            "name": "Northline intake",
            "assistantName": "Maya",
            "websiteUrl": "https://northline.example",
            "number": {"search": {"areaCode": "415"}},
            "labs": {"enabled": True, "model": "gemma"},
        }
    )

    assert result["number"]["number"]["phone_number"] == "+14155550124"
    payload = calls[0][2]
    assert calls[0][:2] == ("POST", "/api/v1/labs/agents")
    assert payload["agent_key"] == "northline-intake"
    assert payload["agent_type"] == "phone"
    assert payload["style"] == "inbound"
    assert payload["direction"] == "inbound"
    assert payload["preset_key"] == "general_intake_receptionist"
    assert payload["telephony"] == {"mode": "supafone_managed", "provider": "supafone"}
    # voice_watcher defaults on and is mirrored into the labs block.
    assert payload["voice_watcher"] is True
    assert payload["labs"] == {"enabled": True, "model": "gemma", "voice_watcher": True}
    assert payload["call_stages"][0]["metadata"]["auto_generated"] is True
    assert calls[1] == (
        "POST",
        "/api/v1/labs/phone-numbers/search",
        {"area_code": "415", "limit": 1},
    )
    assert calls[2] == (
        "POST",
        "/api/v1/labs/phone-numbers",
        {
            "phone_number": "+14155550124",
            "friendly_name": "Northline intake",
            "agent_key": "northline-intake",
            "agent_name": "Maya",
            "preset_key": "general_intake_receptionist",
            "style": "inbound",
            "telephony": {"mode": "supafone_managed", "provider": "supafone"},
        },
    )


def test_create_outbound_serializes_byok_labs_provider_config():
    calls = []

    def transport(method, path, payload):
        calls.append((method, path, payload))
        return {"success": True, "agent": {"agent_key": payload["agent_key"]}, "runtime": {}}

    supafone = Supafone(api_key="sf_test", transport=transport)
    result = supafone.labs.agents.createOutbound(
        {
            "agentKey": "northline-speed-to-lead",
            "name": "Northline speed to lead",
            "assistantName": "Maya",
            "goal": "Call new leads within five minutes and book a consult.",
            "voice": {"provider": "elevenlabs", "voiceId": "rachel"},
            "providerKeys": {
                "cartesiaApiKey": "cartesia_test",
                "elevenlabsApiKey": "eleven_test",
                "inworldApiKey": "inworld_test",
            },
            "byok": {"deepgramApiKey": "deepgram_test"},
            "labs": {
                "enabled": True,
                "voiceWatcher": True,
                "mode": "byok",
                "managedInfrastructure": False,
                "model": "gemma",
                "stt": {"provider": "deepgram", "model": "nova-3"},
                "llm": {"provider": "anthropic", "model": "claude-3-5-sonnet"},
                "tts": {"provider": "cartesia", "voiceId": "sonic-warm"},
                "providerKeys": {"cartesiaApiKey": "cartesia_test"},
            },
            "telephony": {
                "mode": "byok",
                "provider": "twilio",
                "credentials": {
                    "accountSid": "AC_test",
                    "apiKey": "SK_test",
                    "apiSecret": "twilio_secret",
                    "fromNumber": "+14155550125",
                },
            },
        }
    )

    assert result["agent"]["agent_key"] == "northline-speed-to-lead"
    payload = calls[0][2]
    assert calls[0][:2] == ("POST", "/api/v1/labs/agents")
    assert payload["agent_key"] == "northline-speed-to-lead"
    assert payload["agent_type"] == "campaign"
    assert payload["style"] == "outbound"
    assert payload["direction"] == "outbound"
    assert payload["preset_key"] == "speed_to_lead_caller"
    assert payload["provider_keys"] == {
        "cartesia_api_key": "cartesia_test",
        "elevenlabs_api_key": "eleven_test",
        "inworld_api_key": "inworld_test",
    }
    assert payload["byok"] == {"deepgram_api_key": "deepgram_test"}
    assert payload["telephony"]["credentials"]["account_sid"] == "AC_test"
    assert payload["labs"]["mode"] == "byok"
    assert payload["labs"]["managed_infrastructure"] is False
    assert payload["call_stages"][0]["key"] == "intro_consent"
    assert payload["call_stages"][-1]["key"] == "close"


def test_structured_byok_lanes_stay_separate():
    calls = []

    def transport(method, path, payload):
        calls.append((method, path, payload))
        return {"success": True, "agent": {"agent_key": payload["agent_key"]}, "runtime": {}}

    supafone = Supafone(api_key="sf_test", transport=transport)
    supafone.labs.agents.createOutbound(
        {
            "agentKey": "three-lane-byok",
            "name": "Three lane BYOK",
            "byok": {
                "agentProvider": {
                    "provider": "ultravox",
                    "apiKey": "uv_test",
                    "settings": {"region": "us"},
                },
                "telephony": {
                    "mode": "byok",
                    "provider": "telnyx",
                    "credentials": {
                        "apiKey": "telnyx_test",
                        "connectionId": "conn_123",
                        "fromNumber": "+14155550123",
                    },
                    "customSip": {
                        "sipTrunkUri": "sip:trunk.example.com",
                        "headers": {"X-Team": "northline"},
                    },
                },
                "tts": {
                    "provider": "cartesia",
                    "apiKey": "cartesia_test",
                    "voiceId": "sonic-warm",
                },
            },
            "labs": {"enabled": True, "mode": "byok", "managedInfrastructure": False},
        }
    )

    payload = calls[0][2]
    assert payload["byok"]["agent_provider"] == {
        "provider": "ultravox",
        "settings": {"region": "us"},
        "api_key": "uv_test",
    }
    assert payload["byok"]["telephony"] == {
        "mode": "byok",
        "provider": "telnyx",
        "credentials": {
            "api_key": "telnyx_test",
            "connection_id": "conn_123",
            "from_number": "+14155550123",
        },
        "custom_sip": {
            "sip_trunk_uri": "sip:trunk.example.com",
            "headers": {"X-Team": "northline"},
        },
    }
    assert payload["byok"]["tts"] == {
        "provider": "cartesia",
        "api_key": "cartesia_test",
        "voice_id": "sonic-warm",
    }


def test_recording_transcription_and_artifact_policy_serializes():
    calls = []

    def transport(method, path, payload):
        calls.append((method, path, payload))
        return {"success": True, "agent": {"agent_key": payload["agent_key"]}, "runtime": {}}

    supafone = Supafone(api_key="sf_test", transport=transport)
    supafone.labs.agents.create_inbound(
        {
            "agentKey": "recorded-agent",
            "name": "Recorded agent",
            "recording": {
                "enabled": True,
                "recordAudio": True,
                "consentRequired": True,
                "announcement": "This call may be recorded.",
                "retentionDays": 30,
                "redactPii": True,
            },
            "transcription": {
                "enabled": True,
                "provider": "supafone_managed",
                "language": "multi",
                "diarization": True,
                "timestamps": True,
            },
            "artifacts": {
                "recordings": True,
                "transcripts": True,
                "summaries": True,
                "qaReports": True,
                "retentionDays": 30,
            },
        }
    )

    payload = calls[0][2]
    assert payload["recording"] == {
        "enabled": True,
        "record_audio": True,
        "consent_required": True,
        "announcement": "This call may be recorded.",
        "retention_days": 30,
        "redact_pii": True,
    }
    assert payload["transcription"] == {
        "enabled": True,
        "provider": "supafone_managed",
        "language": "multi",
        "diarization": True,
        "timestamps": True,
    }
    assert payload["artifacts"] == {
        "recordings": True,
        "transcripts": True,
        "summaries": True,
        "qa_reports": True,
        "retention_days": 30,
    }


def test_agent_delete_and_call_artifact_routes_are_exposed():
    calls = []

    def transport(method, path, payload):
        calls.append((method, path, payload))
        return {"ok": True}

    supafone = Supafone(api_key="sf_test", transport=transport)
    supafone.labs.agents.delete("agent_123", releaseNumbers=True)
    supafone.labs.calls.list(agentKey="agent_123", limit=10)
    supafone.labs.calls.get("call_123")
    supafone.labs.recordings.list(callId="call_123", limit=5)
    supafone.labs.recordings.delete("rec_123", reason="retention")
    supafone.labs.transcripts.list(agentKey="agent_123", limit=5)
    supafone.labs.transcripts.get("tr_123")

    assert calls == [
        ("DELETE", "/api/v1/labs/agents/agent_123?release_numbers=true", None),
        ("GET", "/api/v1/labs/calls?agent_key=agent_123&limit=10", None),
        ("GET", "/api/v1/labs/calls/call_123", None),
        ("GET", "/api/v1/labs/recordings?call_id=call_123&limit=5", None),
        ("DELETE", "/api/v1/labs/recordings/rec_123?reason=retention", None),
        ("GET", "/api/v1/labs/transcripts?agent_key=agent_123&limit=5", None),
        ("GET", "/api/v1/labs/transcripts/tr_123", None),
    ]


def test_phone_number_lifecycle_methods_are_exposed():
    calls = []

    def transport(method, path, payload):
        calls.append((method, path, payload))
        return {"success": True, "number": {"number_id": "num_123"}}

    supafone = Supafone(api_key="sf_test", transport=transport)
    supafone.labs.phone_numbers.unassign("num_123", reason="moving-agent")
    supafone.labs.phone_numbers.release("num_123", reason="done")
    supafone.labs.phone_numbers.returnToPool("num_123", metadata={"source": "test"})
    supafone.labs.phone_numbers.delete("num_123", agencyId="ag_123", reason="cancelled")

    assert calls == [
        (
            "POST",
            "/api/v1/labs/phone-numbers/num_123/unassign",
            {"reason": "moving-agent"},
        ),
        (
            "POST",
            "/api/v1/labs/phone-numbers/num_123/release",
            {"reason": "done", "return_to_pool": True},
        ),
        (
            "POST",
            "/api/v1/labs/phone-numbers/num_123/release",
            {"return_to_pool": True, "metadata": {"source": "test"}},
        ),
        (
            "DELETE",
            "/api/v1/labs/phone-numbers/num_123?agency_id=ag_123",
            {"agency_id": "ag_123", "reason": "cancelled"},
        ),
    ]


def test_call_stages_can_be_customized_or_disabled():
    calls = []

    def transport(method, path, payload):
        calls.append((method, path, payload))
        return {"success": True, "agent": {"agent_key": payload["agent_key"]}, "runtime": {}}

    supafone = Supafone(api_key="sf_test", transport=transport)
    supafone.labs.agents.create_inbound(
        {
            "agentKey": "custom-stages",
            "name": "Custom stages",
            "callStages": [{"key": "verify", "name": "Verify caller", "exitCriteria": ["done"]}],
        }
    )
    supafone.labs.agents.create_inbound(
        {
            "agentKey": "no-stages",
            "name": "No stages",
            "callStages": False,
        }
    )

    assert calls[0][2]["call_stages"] == [
        {"key": "verify", "name": "Verify caller", "exit_criteria": ["done"]}
    ]
    assert "call_stages" not in calls[1][2]


# ---------------------------------------------------------------------------
# voice_watcher client flag (Voice Watcher framework: supervision + QA + scoring)
# ---------------------------------------------------------------------------

def test_voice_watcher_defaults_on_and_injects_into_payload():
    calls = []

    def transport(method, path, payload):
        calls.append((method, path, payload))
        return {"success": True, "agent": {"agent_key": payload["agent_key"]}, "runtime": {}}

    supafone = Supafone(api_key="sf_test", transport=transport)
    assert supafone.voice_watcher is True
    supafone.labs.agents.create_inbound({"agentKey": "vw-default", "name": "VW default"})
    assert calls[0][2]["voice_watcher"] is True


def test_voice_watcher_false_stored_and_injected():
    calls = []

    def transport(method, path, payload):
        calls.append((method, path, payload))
        return {"success": True, "agent": {"agent_key": payload["agent_key"]}, "runtime": {}}

    supafone = Supafone(api_key="sf_test", transport=transport, voice_watcher=False)
    assert supafone.voice_watcher is False
    supafone.labs.agents.create_outbound({"agentKey": "vw-off", "name": "VW off"})
    assert calls[0][2]["voice_watcher"] is False


def test_voice_watcher_explicit_caller_value_preserved():
    calls = []

    def transport(method, path, payload):
        calls.append((method, path, payload))
        return {"success": True, "agent": {"agent_key": payload["agent_key"]}, "runtime": {}}

    # Client default is on, but the caller explicitly disables it on this agent.
    supafone = Supafone(api_key="sf_test", transport=transport, voice_watcher=True)
    supafone.labs.agents.create({"agentKey": "vw-explicit", "name": "VW explicit", "voice_watcher": False})
    assert calls[0][2]["voice_watcher"] is False


def test_voice_watcher_deprecated_labs_alias():
    # Old callers passing labs=False keep working (alias for voice_watcher).
    supafone = Supafone(api_key="sf_test", transport=lambda *a: {}, labs=False)
    assert supafone.voice_watcher is False
