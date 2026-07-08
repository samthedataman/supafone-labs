"""Hosted Supafone agent provisioning client.

This is separate from ``supercharge(my_agent)``:

* ``supercharge`` attaches the Supafone Labs watcher to an agent you already run.
* ``Supafone(...).labs.agents`` provisions a new hosted Supafone voice agent.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Callable, Iterator, Mapping, Optional
from urllib import error, parse, request

DEFAULT_SUPAFONE_API_BASE = "https://api.supafone.ai"
DEFAULT_LABS_API_BASE = "https://api.labs.supafone.ai"

Transport = Callable[[str, str, Optional[dict[str, Any]]], Any]


class SupafoneError(RuntimeError):
    """Raised when the hosted Supafone API returns an error."""

    def __init__(self, message: str, *, status: Optional[int] = None, body: Any = None) -> None:
        super().__init__(message)
        self.status = status
        self.body = body


@dataclass
class VoicePreview:
    """Audio bytes returned by Supafone Labs voice preview/TTS."""

    content: bytes
    media_type: str = "application/octet-stream"

    def write(self, path: str) -> str:
        with open(path, "wb") as handle:
            handle.write(self.content)
        return path


class Supafone:
    """Python client for hosted Supafone agent provisioning."""

    def __init__(
        self,
        *,
        api_key: Optional[str] = None,
        supafone_api_key: Optional[str] = None,
        supafone_api_base_url: str = DEFAULT_SUPAFONE_API_BASE,
        labs_api_key: Optional[str] = None,
        labs_api_base_url: str = DEFAULT_LABS_API_BASE,
        timeout: float = 30.0,
        transport: Optional[Transport] = None,
    ) -> None:
        self.api_key = (
            api_key
            or os.getenv("SUPAFONE_API_KEY")
            or os.getenv("SUPAFONE_LABS_API_KEY")
            or ""
        )
        if not self.api_key:
            raise ValueError("api_key is required, or set SUPAFONE_API_KEY")
        self.supafone_api_key = supafone_api_key or self.api_key
        self.supafone_api_base_url = supafone_api_base_url.rstrip("/")
        self.labs_api_key = labs_api_key or os.getenv("SUPAFONE_LABS_API_KEY") or self.api_key
        self.labs_api_base_url = labs_api_base_url.rstrip("/")
        self.timeout = timeout
        self._transport = transport
        self.labs = LabsNamespace(self)

    def _request_supafone_api(
        self, method: str, path: str, payload: Optional[dict[str, Any]] = None
    ) -> Any:
        if self._transport:
            return self._transport(method, path, payload)

        body = None
        headers = {
            "Authorization": f"Bearer {self.supafone_api_key}",
            "Accept": "application/json",
        }
        if payload is not None:
            body = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"
        req = request.Request(
            self.supafone_api_base_url + path,
            data=body,
            headers=headers,
            method=method,
        )
        try:
            with request.urlopen(req, timeout=self.timeout) as resp:
                data = resp.read().decode("utf-8")
                return json.loads(data) if data else {}
        except error.HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace")
            try:
                parsed: Any = json.loads(raw)
            except json.JSONDecodeError:
                parsed = raw
            detail = parsed.get("detail") if isinstance(parsed, dict) else parsed
            raise SupafoneError(str(detail or exc.reason), status=exc.code, body=parsed) from exc

    def _request_labs_api(
        self, method: str, path: str, payload: Optional[dict[str, Any]] = None
    ) -> Any:
        body = None
        headers = {
            "Authorization": f"Bearer {self.labs_api_key}",
            "Accept": "application/json",
        }
        if payload is not None:
            body = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"
        req = request.Request(
            self.labs_api_base_url + path,
            data=body,
            headers=headers,
            method=method,
        )
        try:
            with request.urlopen(req, timeout=self.timeout) as resp:
                data = resp.read().decode("utf-8")
                return json.loads(data) if data else {}
        except error.HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace")
            try:
                parsed: Any = json.loads(raw)
            except json.JSONDecodeError:
                parsed = raw
            detail = parsed.get("detail") if isinstance(parsed, dict) else parsed
            raise SupafoneError(str(detail or exc.reason), status=exc.code, body=parsed) from exc

    def _request_labs_api_bytes(
        self, method: str, path: str, payload: Optional[dict[str, Any]] = None
    ) -> VoicePreview:
        body = None
        headers = {
            "Authorization": f"Bearer {self.labs_api_key}",
            "Accept": "audio/*",
        }
        if payload is not None:
            body = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"
        req = request.Request(
            self.labs_api_base_url + path,
            data=body,
            headers=headers,
            method=method,
        )
        try:
            with request.urlopen(req, timeout=self.timeout) as resp:
                media_type = resp.headers.get("content-type") or "application/octet-stream"
                return VoicePreview(content=resp.read(), media_type=media_type)
        except error.HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace")
            try:
                parsed: Any = json.loads(raw)
            except json.JSONDecodeError:
                parsed = raw
            detail = parsed.get("detail") if isinstance(parsed, dict) else parsed
            raise SupafoneError(str(detail or exc.reason), status=exc.code, body=parsed) from exc

    def usage(self) -> Any:
        """Today's Labs usage across oracle/TTS/STT/loggable services."""
        return self._request_labs_api("GET", "/v1/usage")

    def balance(self) -> Any:
        """Remaining prepaid Supafone Labs minute balance."""
        return self._request_labs_api("GET", "/v1/billing/balance")

    def logs(self, limit: int = 100) -> Any:
        """Snapshot of the auditable Supafone Labs log feed."""
        return self._request_labs_api("GET", f"/v1/logs?{parse.urlencode({'limit': limit})}")

    def voices(self) -> Any:
        """Full hosted voice catalog with provider live/configured flags."""
        return self._request_labs_api("GET", "/v1/voices")

    def tts(self, text: str, voice: str = "supafone-labs-calm-en") -> VoicePreview:
        """Hosted TTS/voice preview as audio bytes."""
        return self._request_labs_api_bytes("POST", "/v1/tts", {"text": text, "voice": voice})

    def preview_voice(
        self,
        voice: str = "supafone-labs-calm-en",
        text: str = "Hi, this is your Supafone agent voice preview.",
    ) -> VoicePreview:
        """Convenience alias for previewing one voice from the catalog."""
        return self.tts(text=text, voice=voice)

    def stream_logs(
        self,
        *,
        limit: int = 100,
        after_id: int = 0,
        poll_ms: int = 1000,
        snapshot: bool = True,
    ) -> Iterator[dict[str, Any]]:
        """Yield live log entries from the Labs SSE stream."""
        query = parse.urlencode(
            {
                "limit": limit,
                "after_id": after_id,
                "poll_ms": poll_ms,
                "snapshot": str(snapshot).lower(),
            }
        )
        req = request.Request(
            f"{self.labs_api_base_url}/v1/logs/stream?{query}",
            headers={"Authorization": f"Bearer {self.labs_api_key}", "Accept": "text/event-stream"},
            method="GET",
        )
        try:
            with request.urlopen(req, timeout=self.timeout) as resp:
                buffer: list[str] = []
                for raw in resp:
                    line = raw.decode("utf-8", errors="replace").rstrip("\r\n")
                    if line == "":
                        parsed = _parse_sse_log(buffer)
                        buffer = []
                        if parsed is not None:
                            yield parsed
                    else:
                        buffer.append(line)
        except error.HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace")
            raise SupafoneError(raw or exc.reason, status=exc.code, body=raw) from exc

    streamLogs = stream_logs


class LabsNamespace:
    def __init__(self, client: Supafone) -> None:
        self.agents = LabsAgentsNamespace(client)
        self.phone_numbers = LabsPhoneNumbersNamespace(client)
        self.phoneNumbers = self.phone_numbers
        self.telephony = LabsTelephonyNamespace(client)
        self.calls = LabsCallsNamespace(client)
        self.recordings = LabsRecordingsNamespace(client)
        self.transcripts = LabsTranscriptsNamespace(client)

    def capabilities(self) -> Any:
        return self.agents._client._request_supafone_api("GET", "/api/v1/labs/capabilities")


class LabsAgentsNamespace:
    def __init__(self, client: Supafone) -> None:
        self._client = client

    def create(self, config: Optional[Mapping[str, Any]] = None, **kwargs: Any) -> Any:
        return self._client._request_supafone_api(
            "POST",
            "/api/v1/labs/agents",
            _labs_agent_payload(_merge(config, kwargs)),
        )

    def create_inbound(self, config: Optional[Mapping[str, Any]] = None, **kwargs: Any) -> Any:
        data = _merge(config, kwargs)
        data.setdefault("style", "inbound")
        data.setdefault("direction", "inbound")
        data.setdefault("agentType", data.get("agent_type", "phone"))
        data.setdefault("presetKey", data.get("preset_key", "general_intake_receptionist"))
        data.setdefault("telephony", {"mode": "supafone_managed", "provider": "supafone"})
        return self.create(data)

    def create_outbound(self, config: Optional[Mapping[str, Any]] = None, **kwargs: Any) -> Any:
        data = _merge(config, kwargs)
        data.setdefault("style", "outbound")
        data.setdefault("direction", "outbound")
        data.setdefault("agentType", data.get("agent_type", "campaign"))
        data.setdefault("presetKey", data.get("preset_key", "speed_to_lead_caller"))
        data.setdefault("telephony", {"mode": "supafone_managed", "provider": "supafone"})
        return self.create(data)

    def create_inbound_with_number(
        self, config: Optional[Mapping[str, Any]] = None, **kwargs: Any
    ) -> Any:
        data = _merge(config, kwargs)
        agent = self.create_inbound(data)
        agent_key = _agent_key(agent, data)
        number = LabsPhoneNumbersNamespace(self._client).buy_and_assign(
            {
                **dict(data.get("number") or {}),
                "agentKey": agent_key,
                "agentName": data.get("assistantName") or data.get("assistant_name") or data.get("name"),
                "friendlyName": (data.get("number") or {}).get("friendlyName")
                or (data.get("number") or {}).get("friendly_name")
                or data.get("name"),
                "style": "inbound",
                "presetKey": data.get("presetKey")
                or data.get("preset_key")
                or "general_intake_receptionist",
                "telephony": (data.get("number") or {}).get("telephony")
                or {"mode": "supafone_managed", "provider": "supafone"},
            }
        )
        return {**agent, "number": number}

    def create_outbound_with_number(
        self, config: Optional[Mapping[str, Any]] = None, **kwargs: Any
    ) -> Any:
        data = _merge(config, kwargs)
        agent = self.create_outbound(data)
        agent_key = _agent_key(agent, data)
        number = LabsPhoneNumbersNamespace(self._client).buy_and_assign(
            {
                **dict(data.get("number") or {}),
                "agentKey": agent_key,
                "agentName": data.get("assistantName") or data.get("assistant_name") or data.get("name"),
                "friendlyName": (data.get("number") or {}).get("friendlyName")
                or (data.get("number") or {}).get("friendly_name")
                or data.get("name"),
                "style": "outbound",
                "presetKey": data.get("presetKey")
                or data.get("preset_key")
                or "speed_to_lead_caller",
                "telephony": (data.get("number") or {}).get("telephony")
                or {"mode": "supafone_managed", "provider": "supafone"},
            }
        )
        return {**agent, "number": number}

    createInbound = create_inbound
    createOutbound = create_outbound
    createInboundWithNumber = create_inbound_with_number
    createOutboundWithNumber = create_outbound_with_number

    def list(self, *, agency_id: Optional[str] = None, agent_type: Optional[str] = None) -> Any:
        query: dict[str, str] = {}
        if agency_id:
            query["agency_id"] = agency_id
        if agent_type:
            query["agent_type"] = agent_type
        suffix = f"?{parse.urlencode(query)}" if query else ""
        return self._client._request_supafone_api("GET", f"/api/v1/labs/agents{suffix}")

    def get(self, agent_key: str, *, agency_id: Optional[str] = None) -> Any:
        query = {"agency_id": agency_id} if agency_id else {}
        suffix = f"?{parse.urlencode(query)}" if query else ""
        return self._client._request_supafone_api(
            "GET", f"/api/v1/labs/agents/{parse.quote(agent_key)}{suffix}"
        )

    def delete(
        self,
        agent_key: str,
        *,
        agency_id: Optional[str] = None,
        agencyId: Optional[str] = None,
        release_numbers: Optional[bool] = None,
        releaseNumbers: Optional[bool] = None,
    ) -> Any:
        query: dict[str, str] = {}
        agency = agency_id or agencyId
        release = release_numbers if release_numbers is not None else releaseNumbers
        if agency:
            query["agency_id"] = agency
        if release is not None:
            query["release_numbers"] = str(release).lower()
        suffix = f"?{parse.urlencode(query)}" if query else ""
        return self._client._request_supafone_api(
            "DELETE", f"/api/v1/labs/agents/{parse.quote(agent_key)}{suffix}"
        )


class LabsPhoneNumbersNamespace:
    def __init__(self, client: Supafone) -> None:
        self._client = client

    def list(
        self,
        *,
        agency_id: Optional[str] = None,
        agencyId: Optional[str] = None,
        active_only: Optional[bool] = None,
        activeOnly: Optional[bool] = None,
    ) -> Any:
        query: dict[str, str] = {}
        agency = agency_id or agencyId
        active = active_only if active_only is not None else activeOnly
        if agency:
            query["agency_id"] = agency
        if active is not None:
            query["active_only"] = str(active).lower()
        suffix = f"?{parse.urlencode(query)}" if query else ""
        return self._client._request_supafone_api("GET", f"/api/v1/labs/phone-numbers{suffix}")

    def search(self, config: Optional[Mapping[str, Any]] = None, **kwargs: Any) -> Any:
        return self._client._request_supafone_api(
            "POST",
            "/api/v1/labs/phone-numbers/search",
            _phone_number_search_payload(_merge(config, kwargs)),
        )

    def buy(self, config: Optional[Mapping[str, Any]] = None, **kwargs: Any) -> Any:
        data = _merge(config, kwargs)
        data.setdefault("telephony", {"mode": "supafone_managed", "provider": "supafone"})
        return self._client._request_supafone_api(
            "POST",
            "/api/v1/labs/phone-numbers",
            _phone_number_provision_payload(data),
        )

    def assign(
        self, number_id: str, config: Optional[Mapping[str, Any]] = None, **kwargs: Any
    ) -> Any:
        return self._client._request_supafone_api(
            "POST",
            f"/api/v1/labs/phone-numbers/{parse.quote(number_id)}/assign",
            _phone_number_assign_payload(_merge(config, kwargs)),
        )

    def unassign(
        self, number_id: str, config: Optional[Mapping[str, Any]] = None, **kwargs: Any
    ) -> Any:
        return self._client._request_supafone_api(
            "POST",
            f"/api/v1/labs/phone-numbers/{parse.quote(number_id)}/unassign",
            _phone_number_release_payload(_merge(config, kwargs)),
        )

    def release(
        self, number_id: str, config: Optional[Mapping[str, Any]] = None, **kwargs: Any
    ) -> Any:
        data = _merge(config, kwargs)
        data.setdefault("returnToPool", True)
        return self._client._request_supafone_api(
            "POST",
            f"/api/v1/labs/phone-numbers/{parse.quote(number_id)}/release",
            _phone_number_release_payload(data),
        )

    def return_to_pool(
        self, number_id: str, config: Optional[Mapping[str, Any]] = None, **kwargs: Any
    ) -> Any:
        data = _merge(config, kwargs)
        data["returnToPool"] = True
        return self.release(number_id, data)

    def delete(
        self, number_id: str, config: Optional[Mapping[str, Any]] = None, **kwargs: Any
    ) -> Any:
        data = _merge(config, kwargs)
        agency_id = _pick(data, "agency_id", "agencyId")
        suffix = f"?{parse.urlencode({'agency_id': agency_id})}" if agency_id else ""
        return self._client._request_supafone_api(
            "DELETE",
            f"/api/v1/labs/phone-numbers/{parse.quote(number_id)}{suffix}",
            _phone_number_release_payload(data),
        )

    def buy_and_assign(self, config: Optional[Mapping[str, Any]] = None, **kwargs: Any) -> Any:
        data = _merge(config, kwargs)
        phone_number = data.get("phoneNumber") or data.get("phone_number")
        if not phone_number:
            search = dict(data.get("search") or {})
            search.setdefault("agencyId", data.get("agencyId") or data.get("agency_id"))
            search.setdefault("limit", 1)
            found = self.search(search)
            numbers = found.get("numbers") if isinstance(found, dict) else None
            phone_number = (numbers or [{}])[0].get("phone_number")
            if not phone_number:
                raise SupafoneError("No Supafone-managed phone numbers matched the search")
        data["phoneNumber"] = phone_number
        return self.buy(data)

    buyAndAssign = buy_and_assign
    returnToPool = return_to_pool


class LabsTelephonyNamespace:
    def __init__(self, client: Supafone) -> None:
        self._client = client

    def get(self, *, agency_id: Optional[str] = None) -> Any:
        suffix = f"?{parse.urlencode({'agency_id': agency_id})}" if agency_id else ""
        return self._client._request_supafone_api("GET", f"/api/v1/labs/telephony{suffix}")

    def configure(self, config: Optional[Mapping[str, Any]] = None, **kwargs: Any) -> Any:
        return self._client._request_supafone_api(
            "PUT", "/api/v1/labs/telephony", _telephony_payload(_merge(config, kwargs))
        )

    def use_supafone_managed(self, *, agency_id: Optional[str] = None) -> Any:
        return self.configure({"agencyId": agency_id, "mode": "supafone_managed", "provider": "supafone"})

    useSupafoneManaged = use_supafone_managed


class LabsCallsNamespace:
    def __init__(self, client: Supafone) -> None:
        self._client = client

    def list(
        self,
        *,
        agency_id: Optional[str] = None,
        agencyId: Optional[str] = None,
        agent_key: Optional[str] = None,
        agentKey: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> Any:
        query = _list_query(
            agency_id=agency_id or agencyId,
            agent_key=agent_key or agentKey,
            limit=limit,
        )
        return self._client._request_supafone_api("GET", f"/api/v1/labs/calls{query}")

    def get(self, call_id: str, *, agency_id: Optional[str] = None, agencyId: Optional[str] = None) -> Any:
        query = _list_query(agency_id=agency_id or agencyId)
        return self._client._request_supafone_api(
            "GET", f"/api/v1/labs/calls/{parse.quote(call_id)}{query}"
        )


class LabsRecordingsNamespace:
    def __init__(self, client: Supafone) -> None:
        self._client = client

    def list(
        self,
        *,
        agency_id: Optional[str] = None,
        agencyId: Optional[str] = None,
        agent_key: Optional[str] = None,
        agentKey: Optional[str] = None,
        call_id: Optional[str] = None,
        callId: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> Any:
        query = _list_query(
            agency_id=agency_id or agencyId,
            agent_key=agent_key or agentKey,
            call_id=call_id or callId,
            limit=limit,
        )
        return self._client._request_supafone_api("GET", f"/api/v1/labs/recordings{query}")

    def get(self, recording_id: str, *, agency_id: Optional[str] = None, agencyId: Optional[str] = None) -> Any:
        query = _list_query(agency_id=agency_id or agencyId)
        return self._client._request_supafone_api(
            "GET", f"/api/v1/labs/recordings/{parse.quote(recording_id)}{query}"
        )

    def delete(
        self,
        recording_id: str,
        *,
        agency_id: Optional[str] = None,
        agencyId: Optional[str] = None,
        reason: Optional[str] = None,
    ) -> Any:
        query = _list_query(agency_id=agency_id or agencyId, reason=reason)
        return self._client._request_supafone_api(
            "DELETE", f"/api/v1/labs/recordings/{parse.quote(recording_id)}{query}"
        )


class LabsTranscriptsNamespace:
    def __init__(self, client: Supafone) -> None:
        self._client = client

    def list(
        self,
        *,
        agency_id: Optional[str] = None,
        agencyId: Optional[str] = None,
        agent_key: Optional[str] = None,
        agentKey: Optional[str] = None,
        call_id: Optional[str] = None,
        callId: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> Any:
        query = _list_query(
            agency_id=agency_id or agencyId,
            agent_key=agent_key or agentKey,
            call_id=call_id or callId,
            limit=limit,
        )
        return self._client._request_supafone_api("GET", f"/api/v1/labs/transcripts{query}")

    def get(self, transcript_id: str, *, agency_id: Optional[str] = None, agencyId: Optional[str] = None) -> Any:
        query = _list_query(agency_id=agency_id or agencyId)
        return self._client._request_supafone_api(
            "GET", f"/api/v1/labs/transcripts/{parse.quote(transcript_id)}{query}"
        )


def _merge(config: Optional[Mapping[str, Any]], kwargs: Mapping[str, Any]) -> dict[str, Any]:
    if config is None:
        data: dict[str, Any] = {}
    elif isinstance(config, Mapping):
        data = dict(config)
    else:
        raise TypeError("config must be a mapping")
    data.update({key: value for key, value in kwargs.items() if value is not None})
    return data


def _list_query(**values: Any) -> str:
    query = {key: str(value) for key, value in values.items() if value not in (None, "")}
    return f"?{parse.urlencode(query)}" if query else ""


def _compact(value: Any) -> Any:
    if isinstance(value, list):
        out = []
        for item in value:
            next_value = _compact(item)
            if next_value is not None:
                out.append(next_value)
        return out or None
    if isinstance(value, dict):
        out = {}
        for key, val in value.items():
            next_value = _compact(val)
            if next_value is not None and next_value != "":
                out[key] = next_value
        return out or None
    return None if value is None else value


def _parse_sse_log(lines: list[str]) -> Optional[dict[str, Any]]:
    data = []
    for line in lines:
        if not line or line.startswith(":"):
            continue
        if line.startswith("data:"):
            data.append(line[5:].lstrip())
    if not data:
        return None
    try:
        parsed = json.loads("\n".join(data))
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def _pick(data: Mapping[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in data:
            return data[key]
    return None


def _agent_key(agent: Any, config: Mapping[str, Any]) -> str:
    if isinstance(agent, Mapping):
        inner = agent.get("agent")
        if isinstance(inner, Mapping):
            value = inner.get("agent_key") or inner.get("agentKey")
            if value:
                return str(value)
    return str(_pick(config, "agentKey", "agent_key") or "")


def _labs_agent_payload(data: Mapping[str, Any]) -> dict[str, Any]:
    return _compact(
        {
            "agency_id": _pick(data, "agency_id", "agencyId"),
            "agent_key": _pick(data, "agent_key", "agentKey"),
            "agent_type": _pick(data, "agent_type", "agentType"),
            "style": _pick(data, "agent_style", "agentStyle", "style"),
            "name": data.get("name"),
            "assistant_name": _pick(data, "assistant_name", "assistantName"),
            "business_name": _pick(data, "business_name", "businessName"),
            "industry": data.get("industry"),
            "website_url": _pick(data, "website_url", "websiteUrl"),
            "phone_number": _pick(data, "phone_number", "phoneNumber"),
            "number_strategy": _pick(data, "number_strategy", "numberStrategy"),
            "number_pool": _pick(data, "number_pool", "numberPool"),
            "premium": data.get("premium"),
            "direction": data.get("direction"),
            "preset_key": _pick(data, "preset_key", "presetKey"),
            "runtime_mode": _pick(data, "runtime_mode", "runtimeMode"),
            "call_stages": _call_stages_payload(data),
            "goal": data.get("goal"),
            "greeting": data.get("greeting"),
            "system_prompt": _pick(data, "system_prompt", "systemPrompt"),
            "language": data.get("language"),
            "voice": _voice_payload(data["voice"]) if data.get("voice") else None,
            "provider_keys": _provider_keys_payload(
                _pick(data, "provider_keys", "providerKeys") or {}
            ),
            "byok": _byok_payload(data.get("byok") or {}),
            "telephony": _telephony_payload(data["telephony"]) if data.get("telephony") else None,
            "recording": _recording_payload(data["recording"]) if data.get("recording") else None,
            "transcription": _transcription_payload(data["transcription"]) if data.get("transcription") else None,
            "artifacts": _artifacts_payload(data["artifacts"]) if data.get("artifacts") else None,
            "compliance": data.get("compliance"),
            "tools": _tools_payload(data["tools"]) if data.get("tools") else None,
            "labs": _labs_payload(data["labs"]) if data.get("labs") else None,
            "ultravox": _ultravox_payload(data["ultravox"]) if data.get("ultravox") else None,
            "custom_sip": _custom_sip_payload(_pick(data, "custom_sip", "customSip", "sip") or {}),
            "voice_watcher": _pick(data, "voice_watcher", "voiceWatcher"),
            "voice_watcher_model": _pick(data, "voice_watcher_model", "voiceWatcherModel"),
            "metadata": data.get("metadata"),
        }
    )


def _voice_payload(data: Mapping[str, Any]) -> dict[str, Any]:
    return _compact(
        {
            "provider": data.get("provider"),
            "voice_id": _pick(data, "voice_id", "voiceId"),
            "model": data.get("model"),
        }
    )


def _provider_keys_payload(data: Mapping[str, Any]) -> dict[str, Any]:
    return _compact(
        {
            "ultravox": data.get("ultravox"),
            "ultravox_api_key": _pick(data, "ultravox_api_key", "ultravoxApiKey"),
            "retell": data.get("retell"),
            "retell_api_key": _pick(data, "retell_api_key", "retellApiKey"),
            "vapi": data.get("vapi"),
            "vapi_api_key": _pick(data, "vapi_api_key", "vapiApiKey"),
            "bland": data.get("bland"),
            "bland_api_key": _pick(data, "bland_api_key", "blandApiKey"),
            "livekit": data.get("livekit"),
            "livekit_api_key": _pick(data, "livekit_api_key", "livekitApiKey"),
            "livekit_api_secret": _pick(data, "livekit_api_secret", "livekitApiSecret"),
            "pipecat": data.get("pipecat"),
            "pipecat_api_key": _pick(data, "pipecat_api_key", "pipecatApiKey"),
            "twilio": data.get("twilio"),
            "twilio_account_sid": _pick(data, "twilio_account_sid", "twilioAccountSid"),
            "twilio_auth_token": _pick(data, "twilio_auth_token", "twilioAuthToken"),
            "twilio_api_key_sid": _pick(data, "twilio_api_key_sid", "twilioApiKeySid"),
            "twilio_api_key_secret": _pick(data, "twilio_api_key_secret", "twilioApiKeySecret"),
            "telnyx": data.get("telnyx"),
            "telnyx_api_key": _pick(data, "telnyx_api_key", "telnyxApiKey"),
            "plivo": data.get("plivo"),
            "plivo_auth_id": _pick(data, "plivo_auth_id", "plivoAuthId"),
            "plivo_auth_token": _pick(data, "plivo_auth_token", "plivoAuthToken"),
            "signalwire": data.get("signalwire"),
            "signalwire_api_token": _pick(data, "signalwire_api_token", "signalwireApiToken"),
            "signalwire_project_id": _pick(data, "signalwire_project_id", "signalwireProjectId"),
            "elevenlabs": data.get("elevenlabs"),
            "elevenlabs_api_key": _pick(data, "elevenlabs_api_key", "elevenlabsApiKey"),
            "cartesia": data.get("cartesia"),
            "cartesia_api_key": _pick(data, "cartesia_api_key", "cartesiaApiKey"),
            "inworld": data.get("inworld"),
            "inworld_api_key": _pick(data, "inworld_api_key", "inworldApiKey"),
            "deepgram": data.get("deepgram"),
            "deepgram_api_key": _pick(data, "deepgram_api_key", "deepgramApiKey"),
            "anthropic": data.get("anthropic"),
            "anthropic_api_key": _pick(data, "anthropic_api_key", "anthropicApiKey"),
            "openai": data.get("openai"),
            "openai_api_key": _pick(data, "openai_api_key", "openaiApiKey"),
            "xai": data.get("xai"),
            "xai_api_key": _pick(data, "xai_api_key", "xaiApiKey"),
        }
    )


def _byok_payload(data: Mapping[str, Any]) -> dict[str, Any]:
    if any(
        key in data
        for key in (
            "agentProvider",
            "agent_provider",
            "runtime",
            "telephony",
            "tts",
            "stt",
            "llm",
            "providerKeys",
            "provider_keys",
            "customSip",
            "custom_sip",
            "sip",
        )
    ):
        return _compact(
            {
                "provider_keys": _provider_keys_payload(
                    _pick(data, "provider_keys", "providerKeys") or {}
                ),
                "agent_provider": _provider_config_payload(
                    _pick(data, "agent_provider", "agentProvider", "runtime") or {}
                ),
                "telephony": _telephony_payload(data["telephony"]) if data.get("telephony") else None,
                "tts": _provider_config_payload(data.get("tts") or {}),
                "stt": _provider_config_payload(data.get("stt") or {}),
                "llm": _provider_config_payload(data.get("llm") or {}),
                "custom_sip": _custom_sip_payload(_pick(data, "custom_sip", "customSip", "sip") or {}),
            }
        )
    return _provider_keys_payload(data)


def _provider_config_payload(data: Mapping[str, Any]) -> dict[str, Any]:
    payload = dict(data)
    normalized = _compact(
        {
            "provider": data.get("provider"),
            "api_key": _pick(data, "api_key", "apiKey"),
            "credentials": data.get("credentials"),
            "settings": data.get("settings"),
            "model": data.get("model"),
            "voice_id": _pick(data, "voice_id", "voiceId"),
        }
    ) or {}
    for key in ("apiKey", "api_key", "voiceId", "voice_id"):
        payload.pop(key, None)
    payload.update(normalized)
    return _compact(payload) or {}


def _telephony_payload(data: Mapping[str, Any]) -> dict[str, Any]:
    return _compact(
        {
            "agency_id": _pick(data, "agency_id", "agencyId"),
            "mode": data.get("mode"),
            "provider": data.get("provider"),
            "number_strategy": _pick(data, "number_strategy", "numberStrategy"),
            "number_pool": _pick(data, "number_pool", "numberPool"),
            "number_id": _pick(data, "number_id", "numberId"),
            "premium": data.get("premium"),
            "label": data.get("label"),
            "credentials": _telephony_credentials_payload(data["credentials"])
            if data.get("credentials")
            else None,
            "provider_settings": _pick(data, "provider_settings", "providerSettings"),
            "custom_sip": _custom_sip_payload(_pick(data, "custom_sip", "customSip") or {}),
            "metadata": data.get("metadata"),
        }
    )


def _telephony_credentials_payload(data: Mapping[str, Any]) -> dict[str, Any]:
    return _compact(
        {
            "account_sid": _pick(data, "account_sid", "accountSid"),
            "auth_token": _pick(data, "auth_token", "authToken"),
            "api_key": _pick(data, "api_key", "apiKey"),
            "api_secret": _pick(data, "api_secret", "apiSecret"),
            "auth_id": _pick(data, "auth_id", "authId"),
            "connection_id": _pick(data, "connection_id", "connectionId"),
            "telnyx_connection_id": _pick(data, "telnyx_connection_id", "telnyxConnectionId"),
            "signalwire_space_url": _pick(data, "signalwire_space_url", "signalwireSpaceUrl"),
            "project_id": _pick(data, "project_id", "projectId"),
            "application_id": _pick(data, "application_id", "applicationId"),
            "trunk_id": _pick(data, "trunk_id", "trunkId"),
            "endpoint_id": _pick(data, "endpoint_id", "endpointId"),
            "token": data.get("token"),
            "secret": data.get("secret"),
            "from_number": _pick(data, "from_number", "fromNumber"),
            "sip_trunk_uri": _pick(data, "sip_trunk_uri", "sipTrunkUri"),
            "sip_host": _pick(data, "sip_host", "sipHost"),
            "username": data.get("username"),
            "password": data.get("password"),
            "webhook_secret": _pick(data, "webhook_secret", "webhookSecret"),
            "custom_sip": _custom_sip_payload(_pick(data, "custom_sip", "customSip", "sip") or {}),
        }
    )


def _tools_payload(data: Mapping[str, Any]) -> dict[str, Any]:
    return _compact(
        {
            "call_routing": _pick(data, "call_routing", "callRouting"),
            "scheduling": data.get("scheduling"),
            "sms": data.get("sms"),
            "email": data.get("email"),
            "intake_forms": _pick(data, "intake_forms", "intakeForms"),
            "firm_knowledge": _pick(data, "firm_knowledge", "firmKnowledge"),
            "existing_client_lookup": _pick(data, "existing_client_lookup", "existingClientLookup"),
            "voicemail": data.get("voicemail"),
            "emergency_escalation": _pick(data, "emergency_escalation", "emergencyEscalation"),
            "custom_tools": _pick(data, "custom_tools", "customTools"),
        }
    )


def _recording_payload(data: Mapping[str, Any]) -> dict[str, Any]:
    return _compact(
        {
            "enabled": data.get("enabled"),
            "record_audio": _pick(data, "record_audio", "recordAudio"),
            "consent_required": _pick(data, "consent_required", "consentRequired"),
            "announcement": data.get("announcement"),
            "retention_days": _pick(data, "retention_days", "retentionDays"),
            "storage": data.get("storage"),
            "redact_pii": _pick(data, "redact_pii", "redactPii"),
            "metadata": data.get("metadata"),
        }
    )


def _transcription_payload(data: Mapping[str, Any]) -> dict[str, Any]:
    return _compact(
        {
            "enabled": data.get("enabled"),
            "provider": data.get("provider"),
            "model": data.get("model"),
            "language": data.get("language"),
            "redact_pii": _pick(data, "redact_pii", "redactPii"),
            "diarization": data.get("diarization"),
            "timestamps": data.get("timestamps"),
            "metadata": data.get("metadata"),
        }
    )


def _artifacts_payload(data: Mapping[str, Any]) -> dict[str, Any]:
    return _compact(
        {
            "recordings": data.get("recordings"),
            "transcripts": data.get("transcripts"),
            "summaries": data.get("summaries"),
            "qa_reports": _pick(data, "qa_reports", "qaReports"),
            "logs": data.get("logs"),
            "webhooks": data.get("webhooks"),
            "retention_days": _pick(data, "retention_days", "retentionDays"),
            "metadata": data.get("metadata"),
        }
    )


def _labs_payload(data: Mapping[str, Any]) -> dict[str, Any]:
    return _compact(
        {
            "enabled": data.get("enabled"),
            "voice_watcher": _pick(data, "voice_watcher", "voiceWatcher"),
            "api_key": _pick(data, "api_key", "apiKey"),
            "model": data.get("model"),
            "mode": data.get("mode"),
            "managed_infrastructure": _pick(data, "managed_infrastructure", "managedInfrastructure"),
            "stt": data.get("stt"),
            "llm": data.get("llm"),
            "tts": data.get("tts"),
            "provider_keys": _pick(data, "provider_keys", "providerKeys"),
            "label": data.get("label"),
        }
    )


def _ultravox_payload(data: Mapping[str, Any]) -> dict[str, Any]:
    return _compact(
        {
            "model": data.get("model"),
            "temperature": data.get("temperature"),
            "medium": data.get("medium"),
            "vad_settings": _pick(data, "vad_settings", "vadSettings"),
            "speaker_first": _pick(data, "speaker_first", "speakerFirst"),
            "first_speaker": _pick(data, "first_speaker", "firstSpeaker"),
            "first_speaker_settings": _pick(data, "first_speaker_settings", "firstSpeakerSettings"),
            "selected_tools": _pick(data, "selected_tools", "selectedTools"),
            "initial_messages": _pick(data, "initial_messages", "initialMessages"),
            "initial_state": _pick(data, "initial_state", "initialState"),
            "initial_output_medium": _pick(data, "initial_output_medium", "initialOutputMedium"),
            "join_timeout": _pick(data, "join_timeout", "joinTimeout"),
            "max_duration": _pick(data, "max_duration", "maxDuration"),
            "max_duration_seconds": _pick(data, "max_duration_seconds", "maxDurationSeconds"),
            "time_exceeded_message": _pick(data, "time_exceeded_message", "timeExceededMessage"),
            "inactivity_messages": _pick(data, "inactivity_messages", "inactivityMessages"),
            "data_connection": _pick(data, "data_connection", "dataConnection"),
            "callbacks": data.get("callbacks"),
            "metadata": data.get("metadata"),
            "experimental_settings": _pick(data, "experimental_settings", "experimentalSettings"),
            "voice_overrides": _pick(data, "voice_overrides", "voiceOverrides"),
            "retention_policy": _pick(data, "retention_policy", "retentionPolicy"),
            "call_template": _pick(data, "call_template", "callTemplate"),
            "custom_sip": _custom_sip_payload(_pick(data, "custom_sip", "customSip", "sip") or {}),
        }
    )


def _custom_sip_payload(data: Mapping[str, Any]) -> dict[str, Any]:
    return _compact(
        {
            "sip_trunk_uri": _pick(data, "sip_trunk_uri", "sipTrunkUri"),
            "trunk_uri": _pick(data, "trunk_uri", "trunkUri"),
            "sip_host": _pick(data, "sip_host", "sipHost"),
            "from_number": _pick(data, "from_number", "fromNumber"),
            "username": data.get("username"),
            "password": data.get("password"),
            "transport": data.get("transport"),
            "headers": data.get("headers"),
            "codecs": data.get("codecs"),
            "dtmf_mode": _pick(data, "dtmf_mode", "dtmfMode"),
            "metadata": data.get("metadata"),
        }
    )


def _phone_number_search_payload(data: Mapping[str, Any]) -> dict[str, Any]:
    return _compact(
        {
            "agency_id": _pick(data, "agency_id", "agencyId"),
            "number_pool": _pick(data, "number_pool", "numberPool"),
            "number_strategy": _pick(data, "number_strategy", "numberStrategy"),
            "country_code": _pick(data, "country_code", "countryCode"),
            "area_code": _pick(data, "area_code", "areaCode"),
            "postal_code": _pick(data, "postal_code", "postalCode"),
            "zip_code": _pick(data, "zip_code", "zipCode"),
            "contains": data.get("contains"),
            "number_type": _pick(data, "number_type", "numberType"),
            "limit": data.get("limit"),
            "capabilities": data.get("capabilities"),
        }
    )


def _phone_number_provision_payload(data: Mapping[str, Any]) -> dict[str, Any]:
    return _compact(
        {
            "agency_id": _pick(data, "agency_id", "agencyId"),
            "phone_number": _pick(data, "phone_number", "phoneNumber"),
            "friendly_name": _pick(data, "friendly_name", "friendlyName"),
            "department_id": _pick(data, "department_id", "departmentId"),
            "agent_key": _pick(data, "agent_key", "agentKey"),
            "agent_id": _pick(data, "agent_id", "agentId"),
            "agent_name": _pick(data, "agent_name", "agentName"),
            "preset_key": _pick(data, "preset_key", "presetKey"),
            "number_strategy": _pick(data, "number_strategy", "numberStrategy"),
            "number_pool": _pick(data, "number_pool", "numberPool"),
            "premium": data.get("premium"),
            "style": _pick(data, "agent_style", "agentStyle", "style"),
            "direction": data.get("direction"),
            "telephony": _telephony_payload(data["telephony"]) if data.get("telephony") else None,
            "metadata": data.get("metadata"),
        }
    )


def _phone_number_assign_payload(data: Mapping[str, Any]) -> dict[str, Any]:
    return _compact(
        {
            "agency_id": _pick(data, "agency_id", "agencyId"),
            "agent_key": _pick(data, "agent_key", "agentKey"),
            "agent_id": _pick(data, "agent_id", "agentId"),
            "agent_name": _pick(data, "agent_name", "agentName"),
            "friendly_name": _pick(data, "friendly_name", "friendlyName"),
            "preset_key": _pick(data, "preset_key", "presetKey"),
            "number_strategy": _pick(data, "number_strategy", "numberStrategy"),
            "number_pool": _pick(data, "number_pool", "numberPool"),
            "premium": data.get("premium"),
            "style": _pick(data, "agent_style", "agentStyle", "style"),
            "direction": data.get("direction"),
            "telephony": _telephony_payload(data["telephony"]) if data.get("telephony") else None,
            "metadata": data.get("metadata"),
        }
    )


def _phone_number_release_payload(data: Mapping[str, Any]) -> dict[str, Any]:
    return _compact(
        {
            "agency_id": _pick(data, "agency_id", "agencyId"),
            "reason": data.get("reason"),
            "return_to_pool": _pick(data, "return_to_pool", "returnToPool"),
            "metadata": data.get("metadata"),
        }
    )


def _call_stages_payload(data: Mapping[str, Any]) -> Optional[list[dict[str, Any]]]:
    explicit = _pick(data, "call_stages", "callStages", "stages")
    auto = _pick(data, "auto_call_stages", "autoCallStages")
    if isinstance(explicit, list):
        return [_call_stage_payload(stage) for stage in explicit if isinstance(stage, Mapping)]
    if explicit is False or auto is False:
        return None
    return [_call_stage_payload(stage) for stage in _generate_call_stages(data)]


def _call_stage_payload(data: Mapping[str, Any]) -> dict[str, Any]:
    return _compact(
        {
            "key": _pick(data, "key", "id"),
            "name": data.get("name"),
            "goal": data.get("goal"),
            "instructions": data.get("instructions"),
            "exit_criteria": _pick(data, "exit_criteria", "exitCriteria"),
            "tools": data.get("tools"),
            "metadata": data.get("metadata"),
        }
    )


def _generate_call_stages(data: Mapping[str, Any]) -> list[dict[str, Any]]:
    direction = str(_pick(data, "direction", "agent_style", "agentStyle", "style") or "inbound").lower()
    haystack = " ".join(
        str(value)
        for value in (
            data.get("name"),
            _pick(data, "assistant_name", "assistantName"),
            _pick(data, "business_name", "businessName"),
            data.get("industry"),
            data.get("goal"),
            _pick(data, "system_prompt", "systemPrompt"),
            _pick(data, "preset_key", "presetKey"),
        )
        if value
    ).lower()
    meta = {"auto_generated": True, "source": "supafone-labs-sdk"}

    if direction == "outbound" or "sales" in haystack or "lead" in haystack:
        return [
            _stage("intro_consent", "Intro and consent", "State who you are, why you are calling, and offer an immediate opt-out.", ["Caller understands purpose", "Opt-out is honored"], meta),
            _stage("qualification", "Qualification", "Confirm fit, urgency, decision process, and the best next step.", ["Need and timeline are clear"], meta),
            _stage("offer", "Offer", "Explain the next step in plain language without unsupported claims.", ["Caller understands the next step"], meta),
            _stage("booking", "Booking", "Book or route the caller only after confirming required details.", ["Next step is confirmed by a tool or human handoff"], meta),
            _stage("close", "Close", "Summarize what will happen next and end politely.", ["Caller knows the follow-up path"], meta),
        ]
    if any(word in haystack for word in ("legal", "law", "injury", "intake")):
        return [
            _stage("greeting", "Greeting", "Open warmly and acknowledge the caller before logistics.", ["Caller need is understood"], meta),
            _stage("incident", "Incident details", "Collect what happened, when it happened, injuries, insurance, and contact details.", ["Core facts are collected"], meta),
            _stage("screening", "Screening", "Identify urgency, jurisdiction, conflicts, and whether human escalation is required.", ["Escalation decision is clear"], meta),
            _stage("booking", "Consult booking", "Book the right next step without quoting fees or inventing availability.", ["Booking or handoff is tool-confirmed"], meta),
            _stage("close", "Close", "Summarize the next step and set expectations accurately.", ["Caller knows exactly what happens next"], meta),
        ]
    if any(word in haystack for word in ("medical", "clinic", "patient", "health")):
        return [
            _stage("greeting", "Greeting", "Identify the caller need and keep the tone calm and concise.", ["Caller need is understood"], meta),
            _stage("patient_context", "Patient context", "Collect non-sensitive scheduling context and avoid medical advice.", ["Required scheduling context is collected"], meta),
            _stage("routing", "Routing", "Route urgent, billing, clinical, and scheduling requests correctly.", ["Correct route is selected"], meta),
            _stage("appointment", "Appointment", "Book or request the appointment only after confirming details.", ["Appointment path is confirmed"], meta),
            _stage("close", "Close", "Recap next steps and any confirmed timing.", ["Caller knows the next step"], meta),
        ]
    return [
        _stage("greeting", "Greeting", "Open naturally, identify the caller need, and set a helpful tone.", ["Caller need is understood"], meta),
        _stage("discovery", "Discovery", "Ask one question at a time until the key details are clear.", ["Required details are collected"], meta),
        _stage("resolution", "Resolution", "Answer approved questions or route to the right workflow.", ["Resolution path is selected"], meta),
        _stage("action", "Action", "Use tools for booking, routing, messaging, or handoff before claiming success.", ["Action is confirmed by a tool or handoff"], meta),
        _stage("close", "Close", "Summarize the outcome and next step accurately.", ["Caller knows what happens next"], meta),
    ]


def generate_call_stages(config: Optional[Mapping[str, Any]] = None, **kwargs: Any) -> list[dict[str, Any]]:
    """Generate the same default call stages the hosted-agent SDK sends by default."""
    return _generate_call_stages(_merge(config, kwargs))


def _stage(
    key: str,
    name: str,
    instructions: str,
    exit_criteria: list[str],
    metadata: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "key": key,
        "name": name,
        "instructions": instructions,
        "exit_criteria": exit_criteria,
        "metadata": dict(metadata),
    }
