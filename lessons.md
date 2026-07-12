# Lessons Learned

## LiveKit Agents & Session Start
**Issue**: Using fixed delays (`asyncio.sleep`) before calling `session.start()` creates race conditions. If the moderator takes longer to speak, debater agents might begin generating text and speaking over the moderator.
**Solution**: Use an event-driven approach where the moderator publishes a `session_ready` event to the LiveKit room data channel. Debater agents wait for this event before calling `session.start()`. Calling `ctx.connect()` allows agents to appear in the room immediately, so the UI is not negatively impacted while they wait.

## Deterministic Turn-Taking
**Issue**: Agents running parallel `AgentSession` loops will all attempt to respond when the user stops speaking, leading to overlapping speech and chaotic discussion.
**Solution**: Implement centralized turn coordination using LiveKit room metadata (`SharedGDContext`). Agents must verify turn ownership (using `GDContextManager.acquire_turn`) in `on_user_turn_completed` and abort their response if they do not own the turn. The moderator assigns turns by publishing `next_speaker` events.
