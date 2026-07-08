from __future__ import annotations

from pydantic import BaseModel


class ProviderCapabilities(BaseModel):
    supports_hidden_instruction_injection: bool = False
    supports_mid_call_prompt_patch: bool = False
    supports_stageful_session_updates: bool = False
    supports_tool_call_interception: bool = False
    supports_server_side_transcript_stream: bool = False
    supports_native_recording: bool = False
    supports_native_webhooks: bool = False
    supports_realtime_bidirectional_ws: bool = False
    supports_post_call_artifact_fetch: bool = False
