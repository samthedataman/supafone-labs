import json

from supafone_labs import Supafone, VoicePreview


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
    assert payload["labs"] == {
        "enabled": True,
        "model": "gemma",
        "voice_watcher": True,
    }
    assert "call_stages" not in payload  # private API generates + executes the plan


def test_language_voice_routing_serializes_only_public_preferences():
    calls = []

    def transport(method, path, payload):
        calls.append((method, path, payload))
        return {"success": True, "agent": {"agent_key": "bilingual"}, "runtime": {}}

    supafone = Supafone(api_key="sf_test", transport=transport)
    supafone.labs.agents.create_inbound(
        {
            "agentKey": "bilingual",
            "name": "Bilingual intake",
            "languageVoiceRouting": True,
            "routingLanguages": ["en-US", "es-MX"],
        }
    )

    payload = calls[0][2]
    assert payload["language_voice_routing"] is True
    assert payload["routing_languages"] == ["en-US", "es-MX"]
    assert "language_profiles" not in payload


def test_language_voice_routing_is_omitted_by_default():
    calls = []

    def transport(method, path, payload):
        calls.append((method, path, payload))
        return {"success": True, "agent": {}, "runtime": {}}

    supafone = Supafone(api_key="sf_test", transport=transport)
    supafone.labs.agents.create_inbound({"name": "Legacy agent"})

    payload = calls[0][2]
    assert "language_voice_routing" not in payload
    assert "routing_languages" not in payload
    assert "language_profiles" not in payload


def test_language_profiles_strip_private_or_unknown_nested_fields():
    calls = []

    def transport(method, path, payload):
        calls.append((method, path, payload))
        return {"success": True, "agent": {}, "runtime": {}}

    supafone = Supafone(api_key="sf_test", transport=transport)
    supafone.labs.agents.create_inbound(
        {
            "name": "Curated bilingual agent",
            "languageVoiceRouting": True,
            "languageProfiles": [
                {
                    "language": "en-US",
                    "languageHint": "en-US",
                    "privatePolicy": "must-not-serialize",
                    "voice": {
                        "provider": "cartesia",
                        "voiceId": "voice-en",
                        "model": "sonic-3.5",
                        "apiKey": "must-not-serialize",
                    },
                },
                {"language": "es-MX", "voice": {"provider": "cartesia", "voiceId": "voice-es"}},
            ],
        }
    )

    profiles = calls[0][2]["language_profiles"]
    assert profiles[0] == {
        "language": "en-US",
        "language_hint": "en-US",
        "voice": {"provider": "cartesia", "voice_id": "voice-en", "model": "sonic-3.5"},
    }
    assert "privatePolicy" not in profiles[0]


def test_language_profiles_are_not_silently_truncated_before_backend_validation():
    calls = []

    def transport(method, path, payload):
        calls.append((method, path, payload))
        return {"success": True, "agent": {}, "runtime": {}}

    supafone = Supafone(api_key="sf_test", transport=transport)
    supafone.labs.agents.create_inbound(
        {
            "name": "Too many profiles",
            "languageVoiceRouting": True,
            "languageProfiles": [
                {"language": language}
                for language in ("en-US", "es-MX", "fr-FR", "de-DE", "vi-VN")
            ],
        }
    )

    assert len(calls[0][2]["language_profiles"]) == 5


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
            "number_strategy": "default_pool",
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


def test_agent_factory_preserves_watcher_default_and_ultravox_byok():
    calls = []

    def transport(method, path, payload):
        calls.append((method, path, payload))
        return {"success": True, "agent": {"agent_key": "byok-agent"}, "runtime": {}}

    supafone = Supafone(api_key="sf_test", transport=transport)
    supafone.labs.agents.create(
        {
            "agentKey": "byok-agent",
            "byok": {
                "ultravox": {"api_key": "uv_test", "base_url": "https://api.ultravox.ai"},
                "tts": {"provider": "cartesia", "api_key": "cartesia_test"},
            },
        }
    )

    payload = calls[0][2]
    assert payload["voice_watcher"] is True
    assert payload["byok"]["ultravox"] == {
        "api_key": "uv_test",
        "base_url": "https://api.ultravox.ai",
    }


def test_agent_factory_honors_watcher_override():
    calls = []

    def transport(method, path, payload):
        calls.append((method, path, payload))
        return {"success": True, "agent": {"agent_key": "raw-agent"}, "runtime": {}}

    supafone = Supafone(api_key="sf_test", voice_watcher=False, transport=transport)
    supafone.labs.agents.create({"agentKey": "raw-agent"})

    assert calls[0][2]["voice_watcher"] is False


def test_python_voice_catalog_sdk_parity():
    calls = []

    def transport(method, path, payload):
        calls.append((method, path, payload))
        if method == "GET_BINARY":
            return VoicePreview(b"abc", "audio/mpeg")
        if path == "/api/v1/labs/voices/capabilities":
            return {
                "runtime": "ultravox",
                "runtime_spoken_language_count": 26,
                "providers": [],
            }
        if path == "/api/v1/labs/voices/recommend":
            return {"description": payload["description"], "matches": []}
        if path.startswith("/api/v1/labs/voices?"):
            query = parse_qs(urlparse(path).query)
            cursor = int(query.get("cursor", [0])[0])
            return {
                "voices": [
                    {
                        "id": f"cartesia-sonic:voice-{cursor}",
                        "provider_key": "cartesia_sonic",
                        "provider_label": "Cartesia",
                        "provider_logo_url": "https://app.supafone.ai/logos/providers/cartesia.svg",
                        "provider_brand": {"key": "cartesia_sonic", "name": "Cartesia"},
                        "model": "sonic-3.5",
                    }
                ],
                "total": 2,
                "cursor": cursor,
                "next_cursor": 1 if cursor == 0 else None,
                "providers": [],
                "provider_brands": [{"key": "cartesia_sonic", "name": "Cartesia"}],
            }
        if path == "/api/v1/labs/agents":
            return {"agent": {"id": "agent-1"}}
        raise AssertionError((method, path, payload))

    # Imported locally so existing tests keep their intentionally tiny import surface.
    from urllib.parse import parse_qs, urlparse

    supafone = Supafone(api_key="sf_test", transport=transport)
    catalog = supafone.labs.voices.list_all(
        provider="cartesia_sonic",
        language="es-MX",
        compatibleLanguage="es",
        gender="female",
        voiceType="warm empathetic",
        model="sonic-3.5",
        runtimeProvider="cartesia",
        configuredOnly=True,
        search="warm",
        page_size=1,
    )
    assert len(catalog["voices"]) == 2
    assert catalog["voices"][0]["provider_label"] == "Cartesia"
    assert catalog["voices"][0]["provider_logo_url"].endswith("cartesia.svg")
    assert catalog["provider_brands"][0]["name"] == "Cartesia"
    assert "provider=cartesia_sonic" in calls[0][1]
    assert "language=es-MX" in calls[0][1]
    assert "compatible_language=es" in calls[0][1]
    assert "gender=female" in calls[0][1]
    assert "voice_type=warm+empathetic" in calls[0][1]
    assert "model=sonic-3.5" in calls[0][1]
    assert "runtime_provider=cartesia" in calls[0][1]
    assert "configured_only=true" in calls[0][1]
    assert "search=warm" in calls[0][1]

    assert supafone.labs.voices.capabilities()["runtime_spoken_language_count"] == 26
    supafone.labs.voices.recommend(
        {
            "description": "warm Latin American support voice",
            "language": "es",
            "provider": "cartesia",
            "voiceType": "warm_empathetic",
            "model": "sonic-3.5",
            "configuredOnly": True,
            "limit": 3,
        }
    )
    recommend_call = next(call for call in calls if call[1] == "/api/v1/labs/voices/recommend")
    assert recommend_call[2] == {
        "description": "warm Latin American support voice",
        "language": "es",
        "provider": "cartesia",
        "voice_type": "warm_empathetic",
        "model": "sonic-3.5",
        "configured_only": True,
        "limit": 3,
    }

    assert supafone.labs.voices.selection(
        {
            "id": "cartesia-sonic:voice-1",
            "provider_key": "cartesia_sonic",
            "model": "sonic-3.5",
        }
    ) == {
        "provider": "cartesia_sonic",
        "voice_id": "cartesia-sonic:voice-1",
        "model": "sonic-3.5",
    }
    preview = supafone.labs.voices.preview("cartesia-sonic:voice-1")
    assert preview.content == b"abc"
    assert preview.media_type == "audio/mpeg"

    supafone.labs.agents.create(
        {
            "name": "Spanish intake",
            "preferredLanguage": "es-MX",
            "voicePreference": {
                "description": "female Spanish patient support voice",
                "configuredOnly": True,
            },
        }
    )
    agent_call = next(call for call in calls if call[1] == "/api/v1/labs/agents")
    assert agent_call[2]["voice_preference"] == {
        "description": "female Spanish patient support voice",
        "language": "es-MX",
        "configured_only": True,
    }
    assert agent_call[2]["language"] == "es-MX"


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
    assert payload["labs"] == {
        "enabled": True,
        "model": "gemma",
        "voice_watcher": True,
    }
    assert "call_stages" not in payload
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
            "number_strategy": "default_pool",
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
    assert "call_stages" not in payload


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
    supafone.labs.calls.list(agentKey="agent_123", limit=10, offset=20)
    supafone.labs.calls.get("call_123")
    supafone.labs.calls.delete("call_123", agencyId="acct_123")
    supafone.labs.activity.list(
        agencyId="acct_123",
        eventType="watcher.whispered",
        resourceType="call",
        resourceId="call_123",
        limit=25,
        offset=5,
    )
    supafone.labs.plans.list(agencyId="acct_123", limit=10)
    supafone.labs.recordings.list(callId="call_123", limit=5)
    supafone.labs.recordings.delete("rec_123", reason="retention")
    supafone.labs.transcripts.list(agentKey="agent_123", limit=5)
    supafone.labs.transcripts.get("tr_123")

    assert calls == [
        ("DELETE", "/api/v1/labs/agents/agent_123?release_numbers=true", None),
        ("GET", "/api/v1/labs/calls?agent_key=agent_123&limit=10&offset=20", None),
        ("GET", "/api/v1/labs/calls/call_123", None),
        ("DELETE", "/api/v1/labs/calls/call_123?agency_id=acct_123", None),
        (
            "GET",
            "/api/v1/labs/activity?account_id=acct_123&event_type=watcher.whispered&resource_type=call&resource_id=call_123&limit=25&offset=5",
            None,
        ),
        (
            "GET",
            "/api/v1/labs/activity?account_id=acct_123&event_type=studio.plan.created&resource_type=studio_plan&limit=10",
            None,
        ),
        ("GET", "/api/v1/labs/recordings?call_id=call_123&limit=5", None),
        ("DELETE", "/api/v1/labs/recordings/rec_123?reason=retention", None),
        ("GET", "/api/v1/labs/transcripts?agent_key=agent_123&limit=5", None),
        ("GET", "/api/v1/labs/transcripts/tr_123", None),
    ]


def test_discovery_voice_and_runtime_routes_are_exposed_in_python():
    calls = []

    def transport(method, path, payload):
        calls.append((method, path, payload))
        return {"ok": True}

    supafone = Supafone(api_key="sf_test", transport=transport)
    supafone.labs.capabilities()
    supafone.labs.presets.list()
    supafone.labs.tools.list()
    supafone.labs.voices.list(
        provider="cartesia", search="warm", language="en-US", cursor=10, limit=25
    )
    supafone.labs.runtime.get(agencyId="acct_123")
    supafone.labs.runtime.configure(
        provider="ultravox",
        credentials={"apiKey": "uvx_test", "baseUrl": "https://api.ultravox.ai/api"},
    )

    assert calls == [
        ("GET", "/api/v1/labs/capabilities", None),
        ("GET", "/api/v1/labs/presets", None),
        ("GET", "/api/v1/labs/tools", None),
        (
            "GET",
            "/api/v1/labs/voices?provider=cartesia&search=warm&language=en-US&cursor=10&limit=25",
            None,
        ),
        ("GET", "/api/v1/labs/runtime?agency_id=acct_123", None),
        (
            "PUT",
            "/api/v1/labs/runtime",
            {
                "provider": "ultravox",
                "credentials": {
                    "apiKey": "uvx_test",
                    "baseUrl": "https://api.ultravox.ai/api",
                },
            },
        ),
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


def test_labs_billing_checkout_status_and_portal_are_exposed():
    calls = []

    def transport(method, path, payload):
        calls.append((method, path, payload))
        if path == "/v1/billing/checkout":
            return {
                "status": "requires_payment",
                "checkout_session_id": "cs_test_123",
                "checkout_url": "https://checkout.stripe.com/c/pay/test",
            }
        if path.endswith("cs_test_123"):
            return {"status": "paid", "checkout_session_id": "cs_test_123"}
        return {"url": "https://billing.stripe.com/p/session/test"}

    supafone = Supafone(api_key="sl_test", transport=transport)
    checkout = supafone.labs.billing.checkout(
        kind="number_addon",
        numberStrategy="premium",
        phoneNumber="+14155550123",
    )
    status = supafone.labs.billing.status(checkout["checkout_session_id"])
    portal = supafone.labs.billing.portal()

    assert checkout["status"] == "requires_payment"
    assert status["status"] == "paid"
    assert portal["url"].startswith("https://billing.stripe.com/")
    assert calls == [
        (
            "POST",
            "/v1/billing/checkout",
            {
                "kind": "number_addon",
                "number_strategy": "premium",
                "phone_number": "+14155550123",
            },
        ),
        ("GET", "/v1/billing/checkout/cs_test_123", None),
        ("POST", "/v1/billing/portal", {}),
    ]


def test_paid_phone_buy_hands_off_to_checkout_then_provisions_once_paid():
    calls = []

    def transport(method, path, payload):
        calls.append((method, path, payload))
        if path == "/v1/billing/checkout":
            return {
                "status": "requires_payment",
                "checkout_session_id": "cs_test_number",
                "checkout_url": "https://checkout.stripe.com/c/pay/test-number",
            }
        return {"success": True, "number": {"number_id": "num_123"}}

    supafone = Supafone(api_key="sl_test", transport=transport)
    checkout = supafone.labs.phone_numbers.buy(
        phoneNumber="+14155550123",
        numberStrategy="dedicated",
    )
    provisioned = supafone.labs.phone_numbers.buy(
        phoneNumber="+14155550123",
        numberStrategy="dedicated",
        billingCheckoutSessionId=checkout["checkout_session_id"],
    )

    assert checkout["status"] == "requires_payment"
    assert provisioned["number"]["number_id"] == "num_123"
    assert calls[0] == (
        "POST",
        "/v1/billing/checkout",
        {
            "kind": "number_addon",
            "number_strategy": "dedicated",
            "phone_number": "+14155550123",
        },
    )
    assert calls[1][0:2] == ("POST", "/api/v1/labs/phone-numbers")
    assert calls[1][2]["billing_checkout_session_id"] == "cs_test_number"


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
            "callStages": [
                {"key": "welcome", "name": "Welcome", "instructions": "Understand the request."},
                {"key": "verify", "name": "Verify caller", "exitCriteria": ["done"]},
                {"key": "close", "name": "Close", "instructions": "Recap the confirmed outcome."},
            ],
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
        {"key": "welcome", "name": "Welcome", "instructions": "Understand the request."},
        {"key": "verify", "name": "Verify caller", "exit_criteria": ["done"]},
        {"key": "close", "name": "Close", "instructions": "Recap the confirmed outcome."},
    ]
    assert calls[1][2]["call_stages"] is False


def test_hosted_call_plan_uses_the_same_supafone_api_key():
    calls = []

    def transport(method, path, payload):
        calls.append((method, path, payload))
        return {
            "version": "supafone_call_plan_v1",
            "summary": "Ready",
            "base_system_prompt": "Be helpful",
            "call_stages": [],
            "generated_by": "supafone_hosted_haiku",
            "model": "haiku",
            "fallback": False,
        }

    supafone = Supafone(api_key="sl_test_one_key", transport=transport)
    result = supafone.generate_call_stages(
        description="Qualify warm leads and book a demo",
        direction="outbound",
        stage_count=5,
        telephony={"credentials": {"auth_token": "must-not-enter-planner"}},
    )

    assert result["generated_by"] == "supafone_hosted_haiku"
    assert calls[0][:2] == ("POST", "/api/v1/labs/agent-plans")
    assert calls[0][2]["description"] == "Qualify warm leads and book a demo"
    assert "telephony" not in calls[0][2]
