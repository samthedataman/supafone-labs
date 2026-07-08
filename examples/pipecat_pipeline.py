"""Pipecat + SupafoneLabs: an observer that appends context frames.

You own the pipeline, so the whisper is an LLMMessagesAppendFrame pushed before
the next model turn (run_llm=False — the whisper never forces a turn).

    pip install supafone-labs[all] pipecat-ai
"""
from pipecat.frames.frames import LLMMessagesAppendFrame, TranscriptionFrame, TTSTextFrame
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor

import supafone_labs


class SupafoneLabsObserver(FrameProcessor):
    """Drop this processor after your STT stage."""

    def __init__(self) -> None:
        super().__init__()
        self.brain = supafone_labs.SupafoneLabs(provider="pipecat", scenario="support", mode="return")

    async def process_frame(self, frame, direction: FrameDirection):
        await super().process_frame(frame, direction)
        raw = None
        if isinstance(frame, TranscriptionFrame):
            raw = {"frame": "TranscriptionFrame", "text": frame.text, "session_id": "call"}
        elif isinstance(frame, TTSTextFrame):
            raw = {"frame": "TTSTextFrame", "text": frame.text, "session_id": "call"}
        if raw is not None:
            result = await self.brain.observe(raw)
            if result.actions and result.actions[0].kind == "append_context_frame":
                payload = result.actions[0].payload
                await self.push_frame(
                    LLMMessagesAppendFrame(messages=payload["messages"], run_llm=False),
                    FrameDirection.DOWNSTREAM,
                )
        await self.push_frame(frame, direction)


# pipeline = Pipeline([transport.input(), stt, SupafoneLabsObserver(), context, llm, tts, transport.output()])
