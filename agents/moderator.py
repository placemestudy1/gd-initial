"""
agents/moderator.py — Kavya the Moderator Agent

The Moderator orchestrates the Group Discussion:
- Opens with topic introduction and rules (warm, casual tone)
- Manages turn-taking via LiveKit data messages
- Tracks time and announces phase transitions
- Closes the session with a summary

LLM: Groq (llama-3.3-70b-versatile) — fast response for smooth flow
TTS: Groq TTS — distinct, clear moderator voice
STT: Groq Whisper — listens to all participants
"""

import asyncio
import json
import logging
import os
import random
from dotenv import load_dotenv

load_dotenv()

from livekit.agents import Agent, AgentSession, JobContext, WorkerOptions, cli
from livekit.agents import llm as agents_llm
from livekit.plugins import groq, google
from .frontend_tts import FrontendTTS

from .prompts import MODERATOR_SYSTEM_PROMPT, MODERATOR_OPENING_SCRIPT

logger = logging.getLogger("moderator")

# ─────────────────────────────────────────────────────────────────────────────
# Moderator Agent
# ─────────────────────────────────────────────────────────────────────────────

class ModeratorAgent(Agent):
    def __init__(self, topic: str, user_name: str, context_mgr=None, duration_seconds: int = 600):
        self.topic = topic
        self.user_name = user_name
        self.context_mgr = context_mgr
        self.duration_seconds = duration_seconds
        self._timer_task = None
        self._phase_announced = set()

        instructions = MODERATOR_SYSTEM_PROMPT.format(context="", user_name=self.user_name)
        super().__init__(instructions=instructions)

    async def on_enter(self):
        """Fired when moderator first joins the room — deliver opening."""
        # Give LiveKit room time to fully establish connections
        await asyncio.sleep(3.0)

        opening = MODERATOR_OPENING_SCRIPT.format(
            user_name=self.user_name,
            topic=self.topic,
            duration=self.duration_seconds // 60,
        )

        # Speak the opening
        handle = self.session.say(opening, allow_interruptions=False)
        await handle.wait_for_playout()
        
        # Signal that session is ready for debaters to start
        await self._publish_event("session_ready", {})

        # Publish the topic to room data for UI display
        await self._publish_event("topic_set", {
            "topic": self.topic,
            "duration": self.duration_seconds,
            "participants": ["Moderator (Kavya)", "Aarav", "Priya"]
        })

        # Start timer
        self._timer_task = asyncio.create_task(self._run_timer())

    async def _run_timer(self):
        """Countdown timer that announces phase transitions."""
        remaining = self.duration_seconds
        try:
            while remaining > 0:
                await asyncio.sleep(1)
                remaining -= 1

                # Publish timer tick to UI
                if remaining % 5 == 0:
                    await self._publish_event("timer_tick", {"remaining": remaining})

                # Phase announcements — sound natural, not scripted
                if remaining == 300 and "halfway" not in self._phase_announced:
                    self._phase_announced.add("halfway")
                    phrases = [
                        "Okay, we're at the halfway mark. Let's make sure everyone's had a proper say — especially on the opposing side.",
                        "Alright, five minutes in. Good arguments so far — let's dig a little deeper now.",
                        "Halfway through! I want to hear more on the counterarguments — we've been a bit one-sided.",
                    ]
                    self.session.say(random.choice(phrases), allow_interruptions=True)

                elif remaining == 120 and "rebuttal" not in self._phase_announced:
                    self._phase_announced.add("rebuttal")
                    phrases = [
                        "Two minutes left — let's get into rebuttals. Pick the strongest point from the other side and push back.",
                        "Okay, two minutes. Rebuttal time — what's the ONE argument from the other side that you think is weakest?",
                    ]
                    self.session.say(random.choice(phrases), allow_interruptions=True)

                elif remaining == 30 and "closing" not in self._phase_announced:
                    self._phase_announced.add("closing")
                    self.session.say(
                        "Thirty seconds — wrap it up with your final thought.",
                        allow_interruptions=True
                    )

                elif remaining == 0:
                    await self._end_session()

        except asyncio.CancelledError:
            pass

    async def _end_session(self):
        """Deliver closing remarks."""
        self.session.say(
            f"And that's time! Really great discussion on '{self.topic}' today. "
            f"{self.user_name}, you made some strong points — your feedback report is being put together now. Well done, everyone!",
            allow_interruptions=False
        )
        await self._publish_event("session_ended", {})

    async def _publish_event(self, event_type: str, data: dict):
        """Send a data message to the frontend UI."""
        try:
            payload = json.dumps({"event": event_type, **data})
            room = self.session.room_io.room
            await room.local_participant.publish_data(
                payload.encode(),
                reliable=True,
            )
        except Exception as e:
            logger.warning(f"Could not publish event {event_type}: {e}")

    async def on_user_turn_completed(
        self,
        turn_ctx: agents_llm.ChatContext,
        new_message: agents_llm.ChatMessage,
    ) -> None:
        """Called when user finishes speaking — update shared context and publish transcript."""
        user_text = new_message.text_content or ""
        if not user_text:
            return

        if self.context_mgr:
            try:
                await self.context_mgr.add_utterance(self.user_name, user_text)
            except Exception as e:
                logger.warning(f"Context update failed: {e}")

        await self._publish_event("transcript", {
            "speaker": self.user_name,
            "text": user_text,
            "role": "user"
        })


# ─────────────────────────────────────────────────────────────────────────────
# Worker Entry Point
# ─────────────────────────────────────────────────────────────────────────────

async def moderator_entrypoint(ctx: JobContext):
    await ctx.connect()

    # Read session config from room metadata
    topic = "Is Artificial Intelligence a threat to jobs or a creator of opportunities?"
    user_name = "You"
    duration = 600

    try:
        if ctx.room.metadata:
            meta = json.loads(ctx.room.metadata)
            session_cfg = meta.get("session_config", {})
            topic = session_cfg.get("topic", topic)
            user_name = session_cfg.get("user_name", user_name)
            duration = session_cfg.get("duration", duration)
    except Exception:
        pass

    logger.info(f"[Moderator] Starting session — Topic: {topic}")

    session = AgentSession(
        stt=groq.STT(model="whisper-large-v3-turbo"),
        llm=groq.LLM(model="llama-3.3-70b-versatile"),
        tts=FrontendTTS(room=ctx.room, speaker_name="Kavya", role="moderator"),
        # VAD is bundled automatically in livekit-agents >= 1.6
    )

    agent = ModeratorAgent(
        topic=topic,
        user_name=user_name,
        duration_seconds=duration,
    )

    await session.start(agent=agent, room=ctx.room)
    # session.start() blocks until the session ends in livekit-agents >= 1.0


if __name__ == "__main__":
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=moderator_entrypoint,
            agent_name="moderator-agent",
        )
    )
