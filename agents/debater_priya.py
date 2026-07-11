"""
agents/debater_priya.py — Priya the Empathetic Debater

Personality: Thoughtful, socially-conscious MBA student from Bangalore.
LLM: Google Gemini (gemini-2.0-flash) — different reasoning style = richer debate
TTS: Groq TTS — warm female voice distinct from moderator

Key behaviors:
- More deliberate than Aarav — slightly longer pauses before responding
- Responds with the human/societal angle
- Frequently engages the user directly
- Respectfully disagrees with Aarav
- Asks probing questions to deepen the conversation
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

from .prompts import PRIYA_SYSTEM_PROMPT

logger = logging.getLogger("priya")


# Note: We use Groq for STT/TTS but Google Gemini for the LLM
# This creates diverse reasoning between Aarav (Groq LLM) and Priya (Gemini LLM)

class PriyaDebater(Agent):
    def __init__(self, topic: str, user_name: str, context_mgr=None):
        self.topic = topic
        self.user_name = user_name
        self.context_mgr = context_mgr

        instructions = PRIYA_SYSTEM_PROMPT.format(context="", user_name=self.user_name)
        super().__init__(instructions=instructions)

    async def on_enter(self):
        """Priya joins silently — waits for moderator to call on her."""
        # Wait a bit longer than Aarav to avoid both speaking first
        await asyncio.sleep(6.0)
        logger.info("[Priya] Joined the discussion room, ready to participate")

    async def on_user_turn_completed(
        self,
        turn_ctx: agents_llm.ChatContext,
        new_message: agents_llm.ChatMessage,
    ) -> None:
        """
        Called when the user finishes speaking, right before the LLM responds.
        We update Priya's instructions with fresh shared context so her reply
        is grounded in the full conversation so far.

        Priya is more deliberate than Aarav — longer pause before updating context.
        This creates natural turn-taking: Aarav jumps in first, then Priya follows.
        """
        user_text = new_message.text_content or ""

        # Add the user's utterance to shared context
        if self.context_mgr and user_text:
            try:
                await self.context_mgr.add_utterance(self.user_name, user_text)
            except Exception:
                pass

        # Priya thinks more before she speaks — deliberate pause
        await asyncio.sleep(random.uniform(1.0, 2.5))

        # Inject fresh conversation context into instructions
        if self.context_mgr:
            try:
                ctx_prompt = await self.context_mgr.build_context_prompt("Priya")
                await self.update_instructions(
                    PRIYA_SYSTEM_PROMPT.format(context=ctx_prompt, user_name=self.user_name)
                )
            except Exception as e:
                logger.warning(f"[Priya] Context update failed: {e}")

    async def on_exit(self):
        """Called when Priya leaves the room."""
        logger.info("[Priya] Left the discussion room")

    async def _publish_transcript(self, speaker: str, text: str):
        """Push a transcript event to the frontend UI via LiveKit data channel."""
        try:
            payload = json.dumps({
                "event": "transcript",
                "speaker": speaker,
                "text": text,
                "role": "agent_priya"
            })
            room = self.session.room_io.room
            await room.local_participant.publish_data(
                payload.encode(), reliable=True
            )
        except Exception as e:
            logger.warning(f"Could not publish transcript: {e}")


async def priya_entrypoint(ctx: JobContext):
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

    logger.info(f"[Priya] Joining session — Topic: {topic}")

    # Using Groq LLM instead of Gemini due to Free Tier API Quota issues
    llm = groq.LLM(model="llama-3.1-8b-instant")  # Different model for diversity

    session = AgentSession(
        stt=groq.STT(model="whisper-large-v3-turbo"),
        llm=llm,
        tts=FrontendTTS(room=ctx.room, speaker_name="Priya", role="agent_priya"),
        # VAD is bundled automatically in livekit-agents >= 1.6
    )

    agent = PriyaDebater(
        topic=topic,
        user_name=user_name,
    )

    await session.start(agent=agent, room=ctx.room)
    # session.start() blocks until the session ends in livekit-agents >= 1.0


if __name__ == "__main__":
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=priya_entrypoint,
            agent_name="priya-agent",
        )
    )
