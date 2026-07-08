"""LiveKit Agents + SupafoneLabs: chat-context append on session events.

    pip install supafone-labs[all] livekit-agents
"""
import asyncio

from livekit.agents import AgentSession

import supafone_labs

brain = supafone_labs.SupafoneLabs(provider="livekit", scenario="support", mode="return")


def attach_second_mind(session: AgentSession) -> None:
    @session.on("user_input_transcribed")
    def _on_transcribed(ev):
        asyncio.create_task(_handle({
            "type": "user_input_transcribed",
            "transcript": ev.transcript,
            "is_final": ev.is_final,
            "session_id": "call",
        }))

    @session.on("conversation_item_added")
    def _on_item(ev):
        if getattr(ev.item, "type", "message") != "message":
            return  # AgentHandoff etc.
        asyncio.create_task(_handle({
            "type": "conversation_item_added",
            "item": {"role": ev.item.role, "text_content": ev.item.text_content or ""},
            "session_id": "call",
        }))

    async def _handle(raw: dict) -> None:
        result = await brain.observe(raw)
        if result.actions and result.actions[0].kind == "chat_context_append":
            payload = result.actions[0].payload
            chat_ctx = session.history.copy()          # current context
            chat_ctx.add_message(role=payload["role"], content=payload["content"])
            await session.agent.update_chat_ctx(chat_ctx)
