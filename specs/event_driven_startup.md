# Event-Driven Agent Startup

## Goal
Convert the AI agent startup sequence from a time-based (sleep) process to an event-driven workflow to prevent multiple agents from speaking simultaneously upon session initiation. The moderator should first fully complete its opening introduction (including TTS playback) and then emit a `session_ready` event before the other agents become active.

## Context
Currently, the startup synchronization relies on hardcoded `asyncio.sleep()` delays in the `on_enter` hooks of each agent (`moderator` waits 3s, `aarav` waits 5s, `priya` waits 6s). If the moderator's intro takes longer than expected, or if LiveKit connections vary in speed, the debater agents might begin generating text and speaking over the moderator, leading to chaotic starts. An event-driven approach using LiveKit data channels resolves this race condition deterministically.

## Current State
- `moderator.py`: Uses `asyncio.sleep(3.0)` in `on_enter`, then triggers `self.session.say()` without waiting for TTS completion.
- `debater_aarav.py`: Uses `asyncio.sleep(5.0)` in `on_enter` to delay activity.
- `debater_priya.py`: Uses `asyncio.sleep(6.0)` in `on_enter` to delay activity.
- Participant agents (`aarav`, `priya`) call `session.start()` immediately upon connecting to the room, meaning their STT/LLM pipelines are fully active and listening to the moderator's TTS intro, potentially causing unwanted immediate responses.

## Desired Behavior
1. The moderator connects and delivers the intro.
2. The moderator waits until its TTS output is fully played out.
3. The moderator emits a `session_ready` event to the LiveKit room data channel.
4. The participant agents (`aarav`, `priya`) connect to the room but wait for the `session_ready` event (with an optional long timeout fallback) before calling `session.start()`.
5. Once the event is received, they start their sessions and are ready to participate. Sleep-based startup delays are removed or replaced by this event wait.

## Acceptance Criteria
- [ ] Moderator waits for its own opening TTS to complete before emitting `session_ready`.
- [ ] `aarav` and `priya` do not call `session.start()` until `session_ready` is received or a 45s fallback timeout occurs.
- [ ] `aarav` and `priya` no longer use arbitrary `sleep()` calls in their `on_enter` methods to delay startup.
- [ ] Agents do not speak over each other when the session initiates.

## Implementation Notes
- **Files to touch**:
  - `agents/moderator.py`: Modify `on_enter` to `await handle.wait_for_playout()` and publish `session_ready`.
  - `agents/debater_aarav.py`: Add data channel listener in `aarav_entrypoint` before `session.start()`, and remove `asyncio.sleep()` from `on_enter`.
  - `agents/debater_priya.py`: Add data channel listener in `priya_entrypoint` before `session.start()`, and remove `asyncio.sleep()` from `on_enter`.
- **Dependencies**: Use existing `json` and `asyncio` modules, and `livekit.rtc` for data channel listening.
- **Constraints**: 
  - Ensure the moderator's introductory TTS can finish without being interrupted.
  - Keep a timeout (e.g. 45s) on the `session_ready` listener in debater entrypoints to prevent indefinite hanging if the moderator crashes.

## Verification Plan
- Run `python server.py` and `python run_agents.py`.
- Open the UI and start a session.
- Verify through logs that Aarav and Priya are waiting for the `session_ready` event.
- Verify that the moderator fully completes the welcome message.
- Verify that Aarav and Priya receive `session_ready` and call `session.start()` only after the moderator finishes speaking.
- Verify that Aarav and Priya do not interrupt the moderator's intro.
