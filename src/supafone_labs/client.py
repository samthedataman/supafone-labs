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
        # Account (app.supafone.ai) auth — powers campaigns + real calls.
        # Provide a JWT directly, or email+password and the client logs in
        # lazily (and re-logs-in once when the token expires).
        token: Optional[str] = None,
        email: Optional[str] = None,
        password: Optional[str] = None,
        timeout: float = 30.0,
        transport: Optional[Transport] = None,
        # Automatic post-call analysis. When True, report_call() with a
        # transcript (or structured messages) first classifies the finished
        # call against the agent's objective — generating labels
        # (achieved/missed, per-criterion verdicts, failure reasons) — and
        # files the enriched report server-side. Billed one oracle call per
        # analyzed call; reports without a transcript fall back to the plain
        # zero-billed report.
        post_call_analysis: bool = False,
        # voice_watcher (default True): run provisioned agents under Supafone's
        # Voice Watcher framework — live supervision, QA, and call scoring. Set
        # False for a raw agent with no watcher.
        voice_watcher: bool = True,
        # Deprecated alias for voice_watcher — old `labs=` callers keep working.
        labs: Optional[bool] = None,
    ) -> None:
        self.api_key = (
            api_key
            or os.getenv("SUPAFONE_API_KEY")
            or os.getenv("SUPAFONE_LABS_API_KEY")
            or ""
        )
        self.token = token or os.getenv("SUPAFONE_TOKEN") or os.getenv("SUPAFONE_ACCESS_TOKEN") or ""
        self.email = email or os.getenv("SUPAFONE_EMAIL") or ""
        self.password = password or os.getenv("SUPAFONE_PASSWORD") or ""
        # One-key auth: the product API accepts `sl_` Labs keys as bearer
        # credentials, so a lone sl_ credential fills whichever lane wasn't
        # given explicitly. SUPAFONE_TOKEN=sl_live_... is enough for everything.
        if not self.api_key and self.token.startswith("sl_"):
            self.api_key = self.token
        if not self.token and self.api_key.startswith("sl_"):
            self.token = self.api_key
        if not self.api_key and not (self.token or (self.email and self.password)):
            raise ValueError(
                "api_key is required (or set SUPAFONE_API_KEY) — or, for campaigns/calls, "
                "pass token, or email + password (SUPAFONE_TOKEN / SUPAFONE_EMAIL + SUPAFONE_PASSWORD)"
            )
        self.supafone_api_key = supafone_api_key or self.api_key
        self.supafone_api_base_url = supafone_api_base_url.rstrip("/")
        self.labs_api_key = labs_api_key or os.getenv("SUPAFONE_LABS_API_KEY") or self.api_key
        self.labs_api_base_url = labs_api_base_url.rstrip("/")
        self.timeout = timeout
        self._transport = transport
        self.post_call_analysis = post_call_analysis
        # `labs=` is the deprecated alias; an explicit value on it wins.
        self.voice_watcher = bool(voice_watcher if labs is None else labs)
        self._session_token: str = ""  # minted from email/password, refreshed on 401
        self._labs_session_token: str = ""  # minted by labs_login() for session-scoped QA
        self.labs = LabsNamespace(self)
        self.campaigns = CampaignsNamespace(self)
        self.qa = QANamespace(self)

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

    # --- account API (campaigns + real calls) --------------------------------
    # Same product base URL as _request_supafone_api but authenticated with the
    # ACCOUNT JWT (app.supafone.ai login), not an API key. Honors the same
    # `transport` test seam.

    def login(self, email: Optional[str] = None, password: Optional[str] = None) -> str:
        """Log in to the Supafone account and cache the JWT. Called lazily by
        the campaign/call methods — call it directly only to fail fast."""
        email = email or self.email
        password = password or self.password
        if not (email and password):
            raise SupafoneError(
                "Not authenticated: pass token=..., or email= + password= "
                "(or set SUPAFONE_TOKEN / SUPAFONE_EMAIL + SUPAFONE_PASSWORD)"
            )
        body = self._request_account_http(
            "POST", "/api/v1/auth/login", {"email": email, "password": password}, token=""
        )
        token = body.get("access_token") or body.get("token") if isinstance(body, dict) else None
        if not token:
            raise SupafoneError("Login succeeded but no token was returned", body=body)
        self._session_token = str(token)
        return self._session_token

    def _request_account_api(
        self, method: str, path: str, payload: Optional[dict[str, Any]] = None
    ) -> Any:
        if self._transport:
            return self._transport(method, path, payload)
        token = self.token or self._session_token or self.login()
        try:
            return self._request_account_http(method, path, payload, token=token)
        except SupafoneError as exc:
            # A minted token that expired gets one transparent re-login; an
            # explicit token is the caller's to refresh.
            if exc.status == 401 and not self.token and self.email and self.password:
                self._session_token = ""
                return self._request_account_http(method, path, payload, token=self.login())
            raise

    def _request_account_upload(self, path: str, *, filename: str, data: bytes) -> Any:
        """Multipart file POST with the same auth/re-login behavior as
        _request_account_api. Honors the `transport` test seam (method "UPLOAD")."""
        if self._transport:
            return self._transport("UPLOAD", path, {"filename": filename, "size": len(data)})
        token = self.token or self._session_token or self.login()
        try:
            return self._account_upload_http(path, filename, data, token=token)
        except SupafoneError as exc:
            if exc.status == 401 and not self.token and self.email and self.password:
                self._session_token = ""
                return self._account_upload_http(path, filename, data, token=self.login())
            raise

    def _account_upload_http(self, path: str, filename: str, data: bytes, *, token: str) -> Any:
        boundary = f"----supafone{os.urandom(12).hex()}"
        safe_name = filename.replace('"', "").replace("\\", "")[:120] or "document.pdf"
        body = b"".join(
            [
                f"--{boundary}\r\n".encode(),
                f'Content-Disposition: form-data; name="file"; filename="{safe_name}"\r\n'.encode(),
                b"Content-Type: application/pdf\r\n\r\n",
                data,
                f"\r\n--{boundary}--\r\n".encode(),
            ]
        )
        headers = {
            "Accept": "application/json",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"
        req = request.Request(
            self.supafone_api_base_url + path, data=body, headers=headers, method="POST"
        )
        try:
            with request.urlopen(req, timeout=max(self.timeout, 120.0)) as resp:
                raw = resp.read().decode("utf-8")
                return json.loads(raw) if raw else {}
        except error.HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace")
            try:
                parsed: Any = json.loads(raw)
            except json.JSONDecodeError:
                parsed = raw
            detail = parsed.get("detail") if isinstance(parsed, dict) else parsed
            raise SupafoneError(str(detail or exc.reason), status=exc.code, body=parsed) from exc

    def _request_account_http(
        self, method: str, path: str, payload: Optional[dict[str, Any]], *, token: str
    ) -> Any:
        body = None
        headers = {"Accept": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
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

    def place_call(
        self,
        *,
        agent_id: Optional[str] = None,
        agentId: Optional[str] = None,
        to_number: Optional[str] = None,
        toNumber: Optional[str] = None,
    ) -> Any:
        """Place a REAL outbound phone call: dials to_number from the account's
        calling provider and bridges the voice agent onto the line."""
        agent = agent_id or agentId
        number = to_number or toNumber
        if not agent:
            raise SupafoneError("agent_id is required (see list_voice_agents())")
        if not number:
            raise SupafoneError("to_number is required (E.164, e.g. +15551234567)")
        return self._request_account_api(
            "POST", "/api/v1/phone/test-call", {"agent_id": agent, "to_number": number}
        )

    # camelCase alias
    placeCall = place_call

    def list_voice_agents(self) -> Any:
        """The account's voice agents — pick an agent id for campaigns/calls."""
        return self._request_account_api("GET", "/api/v1/agents")

    listVoiceAgents = list_voice_agents

    def scan_brand(self, url: str) -> Any:
        """Scan a website for its branding: business name, brand colors, logo,
        favicon, Open Graph metadata, page images, and key same-domain pages."""
        if not (url or "").strip():
            raise SupafoneError("url is required (the website to scan)")
        return self._request_account_api("POST", "/api/v1/agents/brand-scan", {"url": url.strip()})

    scanBrand = scan_brand

    def generate_intake_form(
        self,
        description: str,
        *,
        agent_id: Optional[str] = None,
        agentId: Optional[str] = None,
        industry: str = "",
        apply: bool = False,
    ) -> Any:
        """Generate a guided intake form (IntakeConfig) from a plain-language
        description. Pass agent_id to ground it in that agent's business, and
        apply=True to write it onto the agent."""
        if not (description or "").strip():
            raise SupafoneError("description is required — what should the form collect?")
        agent = agent_id or agentId
        if apply and not agent:
            raise SupafoneError("apply=True needs an agent_id (see list_voice_agents())")
        payload: dict[str, Any] = {"description": description.strip()}
        if industry:
            payload["industry"] = industry
        if agent:
            payload["apply"] = bool(apply)
            return self._request_account_api(
                "POST", f"/api/v1/agents/{parse.quote(str(agent))}/generate-intake", payload
            )
        return self._request_account_api("POST", "/api/v1/agents/generate-intake", payload)

    generateIntakeForm = generate_intake_form

    def labs_login(self, email: Optional[str] = None, password: Optional[str] = None) -> str:
        """Log in to the Labs cloud console and cache the session token.
        Required by the session-scoped QA methods (qa.run / qa.suite)."""
        email = email or self.email
        password = password or self.password
        if not (email and password):
            raise SupafoneError(
                "labs_login needs email + password (or set SUPAFONE_EMAIL + SUPAFONE_PASSWORD)"
            )
        body = self._request_labs_api("POST", "/v1/auth/login", {"email": email, "password": password})
        token = body.get("token") if isinstance(body, dict) else None
        if not token:
            raise SupafoneError("Labs login succeeded but no token was returned", body=body)
        self._labs_session_token = str(token)
        return self._labs_session_token

    def _request_labs_api(
        self,
        method: str,
        path: str,
        payload: Optional[dict[str, Any]] = None,
        *,
        use_session: bool = False,
    ) -> Any:
        token = (
            self._labs_session_token
            if use_session and self._labs_session_token
            else self.labs_api_key
        )
        body = None
        headers = {
            "Authorization": f"Bearer {token}",
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

    def report_call(self, report: dict[str, Any]) -> dict[str, Any]:
        """File a post-call report — the fuel the optimizer improves against.

        With ``post_call_analysis=True`` on the client and a ``transcript``
        (or ``messages``) in the report, the call is automatically classified
        first: the oracle labels it against the agent's objective
        (achieved/missed, per-criterion verdicts, failure reasons) and the
        enriched report is filed server-side. The generated labels come back
        under ``"analysis"``. Analysis is best-effort — on any failure the
        plain zero-billed report still lands.
        """
        report = dict(report)
        transcript = report.pop("transcript", None)
        messages = report.pop("messages", None)
        ground_truth = report.pop("ground_truth", None)
        if self.post_call_analysis and (transcript or messages):
            try:
                analysis = self.classify_call(
                    session_id=report.get("session_id"),
                    agent=report.get("agent"),
                    transcript=transcript,
                    messages=messages,
                    ground_truth=ground_truth,
                    nudges=report.get("nudges", 0),
                )
                # classify_call files the enriched report server-side — don't double-file.
                return {"recorded": True, "analysis": analysis}
            except SupafoneError:
                pass  # analysis is best-effort — fall through to the plain report
        out = self._request_labs_api("POST", "/v1/events/call_report", report)
        result = {"recorded": True}
        if isinstance(out, dict):
            result.update(out)
        return result

    def classify_call(
        self,
        *,
        transcript: Optional[str] = None,
        messages: Optional[list[dict[str, Any]]] = None,
        session_id: Optional[str] = None,
        agent: Optional[str] = None,
        ground_truth: Optional[dict[str, Any]] = None,
        nudges: int = 0,
    ) -> dict[str, Any]:
        """Post-call analysis for one finished call: classify it against the
        agent's objective and get labels back — achieved/missed, per-criterion
        verdicts, failure reasons, and the blended objective value. Files an
        enriched call report server-side. Billed one oracle call."""
        payload: dict[str, Any] = {"agent": agent or "builder", "nudges": nudges}
        if session_id:
            payload["session_id"] = session_id
        if transcript:
            payload["transcript"] = transcript
        if messages:
            payload["messages"] = messages
        if ground_truth is not None:
            payload["ground_truth"] = ground_truth
        return self._request_labs_api("POST", "/v1/calls/classify", payload)

    reportCall = report_call
    classifyCall = classify_call

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


class QANamespace:
    """Adversarial QA against the Labs cloud — parity with the TS SDK's `qa.*`."""

    def __init__(self, client: "Supafone") -> None:
        self._client = client

    def generate(self, agent_prompt: str, count: int = 5) -> dict[str, Any]:
        """Auto-generate adversarial test scenarios from the agent's own prompt
        (key-scoped). Each scenario carries a persona, an opener, and the one
        assertion the agent must (or must not) satisfy."""
        return self._client._request_labs_api(
            "POST", "/v1/qa/generate", {"agent_prompt": agent_prompt, "count": count}
        )

    def run(self, scenarios: Optional[list[str]] = None, turns: int = 2) -> dict[str, Any]:
        """Run the adversarial QA suite A/B — every scenario plays once
        unsupervised and once with the Labs watcher whispering; the delta is
        the measured supervision lift. Session-scoped — labs_login() first."""
        return self._client._request_labs_api(
            "POST",
            "/v1/qa/run",
            {"scenarios": scenarios or [], "turns": turns},
            use_session=True,
        )

    def suite(self, count: int = 4, turns: int = 2, supervised: bool = False) -> dict[str, Any]:
        """Build + run a bespoke adversarial suite in one call: scenarios are
        generated from the agent's own objective, each is played as a mock
        call against the REAL configured agent, and every call is judged
        twice — pass/fail on the scenario's assertion AND an SSR grade
        (poorly/ok/good/great/perfectly) against the objective.
        Session-scoped — labs_login() first."""
        return self._client._request_labs_api(
            "POST",
            "/v1/qa/suite",
            {"count": count, "turns": turns, "supervised": supervised},
            use_session=True,
        )

    def history(self, agent: str = "builder", limit: int = 40) -> dict[str, Any]:
        """Past QA runs (works with the API key)."""
        query = parse.urlencode({"agent": agent, "limit": limit})
        return self._client._request_labs_api("GET", f"/v1/qa/runs?{query}")


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


class CampaignsNamespace:
    """Outbound AI campaigns — the same campaign engine the app.supafone.ai
    builder drives, packaged: create a campaign, add consented leads, apply a
    preset (built-in or your saved custom preset), launch, and monitor the
    calls as they happen. Authenticated with the ACCOUNT login (token or
    email/password on the client), not an API key.

    Typical flow:
        sf = Supafone(email=..., password=...)
        agent = sf.list_voice_agents()["agents"][0]
        c = sf.campaigns.create(name="Q3 win-back", goal="reengage", agent_id=agent["id"])
        sf.campaigns.apply_preset(c["campaign"]["id"], "win_back")
        sf.campaigns.add_recipients(c["campaign"]["id"], [
            {"name": "Jane Doe", "phone": "+15551234567", "outreach_consent": "yes"},
        ])
        sf.campaigns.launch(c["campaign"]["id"])
        live = sf.campaigns.live(c["campaign"]["id"])   # in-flight calls + portal links
    """

    def __init__(self, client: Supafone) -> None:
        self._client = client

    # -- CRUD ------------------------------------------------------------

    def list(self, *, account_id: Optional[str] = None, accountId: Optional[str] = None) -> Any:
        query = _list_query(account_id=account_id or accountId)
        return self._client._request_account_api("GET", f"/api/v1/campaigns{query}")

    def create(
        self,
        *,
        name: str = "New campaign",
        goal: str = "book",
        agent_id: Optional[str] = None,
        agentId: Optional[str] = None,
        account_id: Optional[str] = None,
        accountId: Optional[str] = None,
    ) -> Any:
        payload: dict[str, Any] = {"name": name, "goal": goal}
        if agent_id or agentId:
            payload["agent_id"] = agent_id or agentId
        if account_id or accountId:
            payload["account_id"] = account_id or accountId
        return self._client._request_account_api("POST", "/api/v1/campaigns", payload)

    def get(self, campaign_id: str) -> Any:
        return self._client._request_account_api("GET", f"/api/v1/campaigns/{parse.quote(campaign_id)}")

    def update(self, campaign_id: str, **fields: Any) -> Any:
        """Patch a campaign: name, goal, agent_id, email_subject, email_body,
        cadence ([{channel, delay_hours}]), settings (merged server-side)."""
        payload: dict[str, Any] = {}
        for keys, api_key in (
            (("name",), "name"),
            (("goal",), "goal"),
            (("agent_id", "agentId"), "agent_id"),
            (("email_subject", "emailSubject"), "email_subject"),
            (("email_body", "emailBody"), "email_body"),
            (("cadence",), "cadence"),
            (("settings",), "settings"),
        ):
            value = _pick(fields, *keys)
            if value is not None:
                payload[api_key] = value
        if not payload:
            raise SupafoneError(
                "Nothing to update — pass name, goal, agent_id, email_subject, email_body, cadence, or settings"
            )
        return self._client._request_account_api(
            "PUT", f"/api/v1/campaigns/{parse.quote(campaign_id)}", payload
        )

    # -- recipients --------------------------------------------------------

    def add_recipients(self, campaign_id: str, recipients: list[dict[str, Any]]) -> Any:
        """Add consented leads: [{name, phone, email, outreach_consent: 'yes', ...}]."""
        if not isinstance(recipients, list) or not recipients:
            raise SupafoneError("recipients must be a non-empty list of lead dicts")
        return self._client._request_account_api(
            "POST",
            f"/api/v1/campaigns/{parse.quote(campaign_id)}/recipients",
            {"recipients": recipients},
        )

    def recipients(self, campaign_id: str) -> Any:
        return self._client._request_account_api(
            "GET", f"/api/v1/campaigns/{parse.quote(campaign_id)}/recipients"
        )

    # -- lifecycle -----------------------------------------------------------

    def launch(self, campaign_id: str) -> Any:
        """Starts REAL calls/emails on the cadence immediately."""
        return self._client._request_account_api(
            "POST", f"/api/v1/campaigns/{parse.quote(campaign_id)}/launch", {}
        )

    def pause(self, campaign_id: str) -> Any:
        return self._client._request_account_api(
            "POST", f"/api/v1/campaigns/{parse.quote(campaign_id)}/pause", {}
        )

    # -- presets --------------------------------------------------------------

    def presets(self) -> Any:
        """Built-in playbooks + the account's saved custom presets."""
        built_in = self._client._request_account_api("GET", "/api/v1/campaigns/outbound-presets")
        result: dict[str, Any] = {
            "built_in": built_in.get("presets", built_in) if isinstance(built_in, dict) else built_in
        }
        try:
            custom = self._client._request_account_api("GET", "/api/v1/campaigns/custom-presets")
            result["custom"] = custom.get("presets", custom) if isinstance(custom, dict) else custom
        except SupafoneError:
            result["custom"] = []
        return result

    def apply_preset(self, campaign_id: str, preset_id: str) -> Any:
        """Materialize a preset (goal, questions, scripts, signing doc) in one write."""
        return self._client._request_account_api(
            "POST",
            f"/api/v1/campaigns/{parse.quote(campaign_id)}/apply-preset",
            {"preset_id": preset_id},
        )

    # -- monitoring ------------------------------------------------------------

    def stats(self, campaign_id: str) -> Any:
        return self._client._request_account_api(
            "GET", f"/api/v1/campaigns/{parse.quote(campaign_id)}/stats"
        )

    def activity(self, campaign_id: str) -> Any:
        """The live funnel + the campaign's most recent calls (newest first)."""
        return self._client._request_account_api(
            "GET", f"/api/v1/campaigns/{parse.quote(campaign_id)}/activity"
        )

    def live(self, campaign_id: str, *, app_url: str = "https://app.supafone.ai") -> Any:
        """In-flight calls right now, each with a portal link to watch/listen.
        Poll get_call(call_id) (or open the portal link) for the transcript as
        it grows during the call."""
        activity = self.activity(campaign_id)
        calls = activity.get("calls") if isinstance(activity, dict) else None
        live_calls = []
        for call in calls or []:
            if not isinstance(call, dict):
                continue
            if str(call.get("status") or "") in ("initiated", "dialing", "in_progress"):
                live_calls.append(
                    {
                        **call,
                        "listen_url": f"{app_url.rstrip('/')}/app/calls?call={parse.quote(str(call.get('id') or ''))}",
                    }
                )
        return {
            "campaign_id": campaign_id,
            "in_flight": live_calls,
            "portal_url": f"{app_url.rstrip('/')}/app/developer?campaign={parse.quote(campaign_id)}",
            "stats": activity.get("stats") if isinstance(activity, dict) else None,
        }

    def get_call(self, call_id: str) -> Any:
        """One call — while in_progress the transcript grows on each poll."""
        return self._client._request_account_api("GET", f"/api/v1/calls/{parse.quote(call_id)}")

    def create_sign_link(
        self, campaign_id: str, recipient_id: str, *, title: str = "", message: str = ""
    ) -> Any:
        payload: dict[str, Any] = {}
        if title:
            payload["title"] = title
        if message:
            payload["message"] = message
        return self._client._request_account_api(
            "POST",
            f"/api/v1/campaigns/{parse.quote(campaign_id)}/recipients/{parse.quote(recipient_id)}/sign-link",
            payload,
        )

    # -- e-sign document (upload + place fields) ------------------------------

    def upload_signing_document(self, campaign_id: str, file_path: str) -> Any:
        """Upload the PDF this campaign sends for e-signature. The server
        auto-detects signature/date/initials lines and returns their placements
        (PDF points, origin bottom-left) — apply them with set_signature_fields."""
        path = os.path.expanduser(str(file_path))
        with open(path, "rb") as handle:
            data = handle.read()
        filename = os.path.basename(path) or "document.pdf"
        return self._client._request_account_upload(
            f"/api/v1/campaigns/{parse.quote(campaign_id)}/signing/document",
            filename=filename,
            data=data,
        )

    def detect_signature_fields(self, campaign_id: str) -> Any:
        return self._client._request_account_api(
            "POST", f"/api/v1/campaigns/{parse.quote(campaign_id)}/signing/detect-fields", {}
        )

    def set_signature_fields(self, campaign_id: str, fields: list[dict[str, Any]]) -> Any:
        """Place the signing fields: [{key, type: signature|date|initials|text,
        label, required, placement: {page, x, y, width, height}}] in PDF points
        (origin bottom-left, 612x792 page). Merges onto the stored doc config."""
        if not isinstance(fields, list) or not fields:
            raise SupafoneError("fields must be a non-empty list of placed fields")
        current = self.get(campaign_id)
        campaign = current.get("campaign") if isinstance(current, dict) else {}
        settings_bag = dict((campaign or {}).get("settings") or {})
        native = dict(settings_bag.get("native_signing") or {})
        if not (native.get("pdfUrl") or native.get("storedName")):
            raise SupafoneError("Upload the signing PDF first (upload_signing_document)")
        native["enabled"] = True
        native["fields"] = [dict(f) for f in fields]
        return self.update(campaign_id, settings={**settings_bag, "native_signing": native})

    # -- campaign-as-code (one YAML/JSON document per campaign) ---------------

    def _config_payload(
        self,
        config: Optional[str],
        file_path: Optional[str],
        account_id: Optional[str],
        launch: Optional[bool],
    ) -> dict[str, Any]:
        text = config
        if not (isinstance(text, str) and text.strip()):
            if not file_path:
                raise SupafoneError("Pass config (YAML/JSON document text) or file_path (a local file)")
            with open(os.path.expanduser(str(file_path)), "r", encoding="utf-8") as handle:
                text = handle.read()
            if not text.strip():
                raise SupafoneError(f"{file_path} is empty")
        payload: dict[str, Any] = {"config": text}
        if account_id:
            payload["account_id"] = account_id
        if isinstance(launch, bool):
            payload["launch"] = launch
        return payload

    def validate_config(
        self,
        config: Optional[str] = None,
        *,
        file_path: Optional[str] = None,
        account_id: Optional[str] = None,
        launch: Optional[bool] = None,
    ) -> Any:
        """Pure dry-run: {valid, errors[], warnings[], summary} — no side effects."""
        return self._client._request_account_api(
            "POST",
            "/api/v1/campaigns/config/validate",
            self._config_payload(config, file_path, account_id, launch),
        )

    def apply_config(
        self,
        config: Optional[str] = None,
        *,
        file_path: Optional[str] = None,
        account_id: Optional[str] = None,
        launch: Optional[bool] = None,
    ) -> Any:
        """Upsert a campaign from a campaign-as-code document (by slug). The
        doc's branding:/intake_form: blocks restyle the campaign's agent and
        generate its intake form on apply. launch=True starts REAL calls."""
        return self._client._request_account_api(
            "POST",
            "/api/v1/campaigns/config/apply",
            self._config_payload(config, file_path, account_id, launch),
        )

    def export_config(self, campaign_id: str) -> Any:
        """The campaign as its canonical YAML document — round-trips through
        apply_config (same slug, launch stays false)."""
        return self._client._request_account_api(
            "GET", f"/api/v1/campaigns/{parse.quote(campaign_id)}/config"
        )

    def generate_config(
        self,
        prompt: str,
        *,
        csv: Optional[str] = None,
        agent_id: Optional[str] = None,
        account_id: Optional[str] = None,
    ) -> Any:
        """Draft a campaign-as-code YAML document from a plain-language
        description (+ optional CSV of leads). No side effects — review, then
        apply_config."""
        if not (prompt or "").strip():
            raise SupafoneError("prompt is required — describe the campaign to draft")
        payload: dict[str, Any] = {"prompt": prompt.strip()}
        if csv:
            payload["csv"] = csv
        if agent_id:
            payload["agent_id"] = agent_id
        if account_id:
            payload["account_id"] = account_id
        return self._client._request_account_api(
            "POST", "/api/v1/campaigns/config/generate", payload
        )

    # camelCase aliases
    addRecipients = add_recipients
    applyPreset = apply_preset
    createSignLink = create_sign_link
    getCall = get_call
    uploadSigningDocument = upload_signing_document
    detectSignatureFields = detect_signature_fields
    setSignatureFields = set_signature_fields
    validateConfig = validate_config
    applyConfig = apply_config
    exportConfig = export_config
    generateConfig = generate_config


class LabsAgentsNamespace:
    def __init__(self, client: Supafone) -> None:
        self._client = client

    def create(self, config: Optional[Mapping[str, Any]] = None, **kwargs: Any) -> Any:
        data = _merge(config, kwargs)
        self._apply_voice_watcher(data)
        return self._client._request_supafone_api(
            "POST",
            "/api/v1/labs/agents",
            _labs_agent_payload(data),
        )

    def _apply_voice_watcher(self, data: dict[str, Any]) -> None:
        """Default the agent onto the client's Voice Watcher setting (live
        supervision + QA + scoring) unless the caller set voice_watcher
        explicitly (either casing). Mirrored into labs.voice_watcher when a labs
        block exists. Never overwrites a caller value."""
        if "voice_watcher" not in data and "voiceWatcher" not in data:
            data["voice_watcher"] = self._client.voice_watcher
        labs = data.get("labs")
        if isinstance(labs, dict) and "voice_watcher" not in labs and "voiceWatcher" not in labs:
            labs["voice_watcher"] = self._client.voice_watcher

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
                # Native (BYOK) Ultravox runtime key — forwarded verbatim so
                # byok.ultravox = {api_key, base_url?} round-trips even when the
                # block also carries an agent_provider / telephony / *tts etc.
                "ultravox": data.get("ultravox"),
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
