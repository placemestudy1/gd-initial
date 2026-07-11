"""
agents/debater_aarav.py — Aarav the Analytical Debater

Personality: Data-driven, energetic, tech-optimist from Mumbai.
LLM: Groq (llama-3.3-70b-versatile) — ultra-fast inference for natural turn-taking
TTS: Groq TTS — confident male voice

Key behaviors:
- Waits for moderator to finish opening before entering debate
- Responds to what was JUST said (context-aware, reactive)
- Uses data and examples with spontaneous filler language
- Yields when user or moderator speaks (natural barge-in)
- Coordinates with Priya via staggered delays to avoid simultaneous speech
"""

import asyncio
import json
import logging
import random
import os
from dotenv import load_dotenv

load_dotenv()

from livekit.agents import Agent, AgentSession, JobContext, WorkerOptions, cli
from livekit.agents import llm as agents_llm
from livekit.plugins import groq, google
from .frontend_tts import FrontendTTS

from .prompts import AARAV_SYSTEM_PROMPT

logger = logging.getLogger("aarav")


class AaravDebater(Agent):
    def __init__(self, topic: str, user_name: str, context_mgr=None):
        self.topic = topic
        self.user_name = user_name
        self.context_mgr = context_mgr

        instructions = AARAV_SYSTEM_PROMPT.format(context="", user_name=self.user_name)
        super().__init__(instructions=instructions)

    async def on_enter(self):
        """Aarav joins the room silently — the moderator manages intros."""
        # Wait longer than moderator's opening to avoid speaking over it
        await asyncio.sleep(5.0)
        logger.info("[Aarav] Joined the discussion room, ready to participate")

    async def on_user_turn_completed(
        self,
        turn_ctx: agents_llm.ChatContext,
        new_message: agents_llm.ChatMessage,
    ) -> None:
        """
        Called when the user finishes speaking, right before the LLM responds.
        We update Aarav's instructions with fresh shared context so his reply
        is grounded in the full conversation so far.
        """
        user_text = new_message.text_content or ""

        # Add the user's utterance to shared context
        if self.context_mgr and user_text:
            try:
                await self.context_mgr.add_utterance(self.user_name, user_text)
            except Exception:
                pass

        # Aarav is impulsive — short thinking pause before updating context
        await asyncio.sleep(random.uniform(0.3, 0.8))

        # Inject fresh conversation context into instructions so LLM reacts
        # to what was actually just said
        if self.context_mgr:
            try:
                ctx_prompt = await self.context_mgr.build_context_prompt("Aarav")
                await self.update_instructions(
                    AARAV_SYSTEM_PROMPT.format(context=ctx_prompt, user_name=self.user_name)
                )
            except Exception as e:
                logger.warning(f"[Aarav] Context update failed: {e}")

    async def on_exit(self):
        """Called when Aarav leaves the room — publish final transcript note."""
        logger.info("[Aarav] Left the discussion room")

    async def _publish_transcript(self, speaker: str, text: str):
        """Push a transcript event to the frontend UI via LiveKit data channel."""
        try:
            payload = json.dumps({
                "event": "transcript",
                "speaker": speaker,
                "text": text,
                "role": "agent_aarav"
            })
            room = self.session.room_io.room
            await room.local_participant.publish_data(
                payload.encode(), reliable=True
            )
        except Exception as e:
            logger.warning(f"Could not publish transcript: {e}")


async def aarav_entrypoint(ctx: JobContext):
    await ctx.connect()

    topic = "Is Artificial Intelligence a threat to jobs or a creator of opportunities?"
    user_name = "You"

    try:
        if ctx.room.metadata:
            meta = json.loads(ctx.room.metadata)
            session_cfg = meta.get("session_config", {})
            topic = session_cfg.get("topic", topic)
            user_name = session_cfg.get("user_name", user_name)
    except Exception:
        pass

    logger.info(f"[Aarav] Joining session — Topic: {topic}")

    session = AgentSession(
        stt=groq.STT(model="whisper-large-v3-turbo"),
        llm=groq.LLM(model="llama-3.3-70b-versatile"),
        tts=FrontendTTS(room=ctx.room, speaker_name="Aarav", role="agent_aarav"),
        # VAD is bundled automatically in livekit-agents >= 1.6
    )

    agent = AaravDebater(
        topic=topic,
        user_name=user_name,
    )

    await session.start(agent=agent, room=ctx.room)
    # session.start() blocks until the session ends in livekit-agents >= 1.0


if __name__ == "__main__":
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=aarav_entrypoint,
            agent_name="aarav-agent",
        )
    )
