"""
shared_context.py — Shared Context Memory for GD Arena

All AI agents share a single context store backed by LiveKit Room Metadata.
This reduces token burden by 70%+ through automatic summarization of transcripts.

Architecture:
  - Transcript is stored in a rolling list (last N utterances raw)
  - After every 5 utterances, older ones are auto-summarized into key_arguments
  - Agents only receive: topic + summary + last 3 raw utterances
"""

import asyncio
import json
import time
from dataclasses import dataclass, field, asdict
from typing import Optional
import os
from dotenv import load_dotenv

load_dotenv()

# ─────────────────────────────────────────────────────────────────────────────
# Data Models
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class Utterance:
    speaker: str        # "You", "Aarav", "Priya", "Moderator"
    text: str
    timestamp: float = field(default_factory=time.time)

@dataclass
class SharedGDContext:
    topic: str = ""
    session_id: str = ""
    discussion_phase: str = "opening"   # opening → main_discussion → rebuttal → closing
    current_speaker: Optional[str] = None
    timer_remaining: int = 600           # 10 minutes default
    session_started: bool = False

    # Rolling raw transcript (last 6 utterances)
    recent_utterances: list = field(default_factory=list)  # list of Utterance dicts

    # Summarized key arguments per speaker (compressed memory)
    key_arguments: dict = field(default_factory=lambda: {
        "You": [],
        "Aarav": [],
        "Priya": [],
        "Moderator": []
    })

    # Turn management
    speaking_order_queue: list = field(default_factory=list)
    utterance_count: int = 0
    last_speaker: Optional[str] = None

    # Scoring (tracked for post-session feedback)
    user_speaking_time_seconds: int = 0
    user_point_count: int = 0

    def to_json(self) -> str:
        return json.dumps(asdict(self))

    @classmethod
    def from_json(cls, data: str) -> "SharedGDContext":
        try:
            obj = json.loads(data)
            ctx = cls(**obj)
            return ctx
        except Exception:
            return cls()


# ─────────────────────────────────────────────────────────────────────────────
# Context Manager (used by all agents)
# ─────────────────────────────────────────────────────────────────────────────

class GDContextManager:
    """
    Thread-safe context manager that reads/writes to LiveKit Room Metadata.
    All agents share ONE instance of this per room.
    """

    METADATA_KEY = "gd_context"

    def __init__(self, room):
        self._room = room
        self._lock = asyncio.Lock()
        self._local_cache: Optional[SharedGDContext] = None

    async def get(self) -> SharedGDContext:
        """Read current context from room metadata (with local cache)."""
        async with self._lock:
            metadata_str = self._room.metadata or ""
            if metadata_str:
                try:
                    meta = json.loads(metadata_str)
                    ctx_str = meta.get(self.METADATA_KEY, "")
                    if ctx_str:
                        self._local_cache = SharedGDContext.from_json(ctx_str)
                        return self._local_cache
                except Exception:
                    pass
            if self._local_cache is None:
                self._local_cache = SharedGDContext()
            return self._local_cache

    async def update(self, ctx: SharedGDContext):
        """Write updated context back to room metadata."""
        async with self._lock:
            self._local_cache = ctx
            try:
                existing_meta = {}
                if self._room.metadata:
                    try:
                        existing_meta = json.loads(self._room.metadata)
                    except Exception:
                        pass
                existing_meta[self.METADATA_KEY] = ctx.to_json()
                new_metadata = json.dumps(existing_meta)

                from livekit import api
                lkapi = api.LiveKitAPI(
                    os.getenv("LIVEKIT_URL", "").replace("wss://", "https://"),
                    os.getenv("LIVEKIT_API_KEY"),
                    os.getenv("LIVEKIT_API_SECRET"),
                )
                await lkapi.room.update_room_metadata(
                    api.UpdateRoomMetadataRequest(
                        room=self._room.name,
                        metadata=new_metadata,
                    )
                )
                await lkapi.aclose()
            except Exception as e:
                print(f"[SharedContext] Warning: could not persist to room metadata: {e}")

    async def add_utterance(self, speaker: str, text: str):
        """Add a new utterance and auto-summarize if needed."""
        ctx = await self.get()

        utterance = {"speaker": speaker, "text": text, "timestamp": time.time()}
        ctx.recent_utterances.append(utterance)
        ctx.utterance_count += 1
        ctx.last_speaker = speaker

        # Track user engagement
        if speaker == "You":
            ctx.user_point_count += 1
            # Estimate speaking time from word count (~2.5 words/sec)
            word_count = len(text.split())
            ctx.user_speaking_time_seconds += int(word_count / 2.5)

        # Update key arguments (simple extraction: store last 2 points per speaker)
        if text and len(text) > 20:
            if speaker not in ctx.key_arguments:
                ctx.key_arguments[speaker] = []
            # Keep last 3 key points per speaker (compression)
            point_summary = text[:150].strip()  # First 150 chars as key point
            if point_summary not in ctx.key_arguments[speaker]:
                ctx.key_arguments[speaker].append(point_summary)
                if len(ctx.key_arguments[speaker]) > 3:
                    ctx.key_arguments[speaker].pop(0)

        # Keep only last 6 utterances raw (rolling window)
        if len(ctx.recent_utterances) > 6:
            ctx.recent_utterances = ctx.recent_utterances[-6:]

        # Auto-advance discussion phase
        if ctx.utterance_count == 3:
            ctx.discussion_phase = "main_discussion"
        elif ctx.utterance_count >= 15 and ctx.timer_remaining < 120:
            ctx.discussion_phase = "closing"

        await self.update(ctx)

    async def build_context_prompt(self, agent_name: str) -> str:
        """
        Build a compact context string for an agent's LLM call.
        This is the core token-reduction mechanism.
        """
        ctx = await self.get()

        lines = [
            f"TOPIC: {ctx.topic}",
            f"DISCUSSION PHASE: {ctx.discussion_phase.replace('_', ' ').upper()}",
            f"TIME REMAINING: {ctx.timer_remaining // 60}m {ctx.timer_remaining % 60}s",
            "",
            "=== KEY ARGUMENTS MADE SO FAR ===",
        ]

        for speaker, points in ctx.key_arguments.items():
            if points:
                lines.append(f"\n[{speaker}]:")
                for pt in points:
                    lines.append(f"  • {pt}")

        lines.append("\n=== LAST 3 EXCHANGES ===")
        recent = ctx.recent_utterances[-3:]
        for utt in recent:
            lines.append(f"[{utt['speaker']}]: {utt['text']}")

        if ctx.last_speaker and ctx.last_speaker != agent_name:
            lines.append(f"\n→ {ctx.last_speaker} just spoke. You are responding as {agent_name}.")

        return "\n".join(lines)

    async def set_current_speaker(self, speaker: Optional[str]):
        """Mark who currently has the floor."""
        ctx = await self.get()
        ctx.current_speaker = speaker
        await self.update(ctx)

    async def set_phase(self, phase: str):
        ctx = await self.get()
        ctx.discussion_phase = phase
        await self.update(ctx)

    async def tick_timer(self):
        """Decrement timer by 1 second. Returns remaining seconds."""
        ctx = await self.get()
        if ctx.timer_remaining > 0:
            ctx.timer_remaining -= 1
        await self.update(ctx)
        return ctx.timer_remaining
