# Deterministic Turn-Taking

## Goal
Enforce deterministic turn-taking by introducing centralized turn coordination within the shared session state. This ensures that only one participant speaks at a time, preventing overlapping responses and creating a predictable, synchronized conversation flow.

## Context
Currently, debater agents (`Aarav` and `Priya`) use independent, parallel instances of `livekit-agents` which automatically trigger response generation whenever the user finishes speaking. This leads to both agents attempting to respond simultaneously. To orchestrate a human-like group discussion, the moderator must assign turns via `next_speaker` events, and the shared context (`GDContextManager`) must track and enforce turn ownership.

## Current State
- `SharedGDContext` does not strictly enforce turn ownership.
- Participant agents (`Aarav`, `Priya`) update their instruction context but do not check if it is actually their turn before responding to the user.
- The moderator does not explicitly assign turns to specific agents.

## Desired Behavior
1. `SharedGDContext` maintains `turn_owner` (str) and `is_agent_speaking` (bool).
2. `GDContextManager` provides `acquire_turn(agent_name)` and `release_turn(agent_name)`.
3. The moderator publishes a `next_speaker` data event to assign turns (e.g., after the user speaks, assigning it to `Aarav`, then `Priya`, etc.).
4. Debater agents verify turn ownership before processing a response in `on_user_turn_completed`. If they do not own the turn, they abort generation (e.g., by clearing `turn_ctx.messages` or raising a cancellation exception).
5. Debater agents call `release_turn()` when they finish speaking.

## Acceptance Criteria
- [ ] `SharedGDContext` includes `turn_owner` and `is_agent_speaking`.
- [ ] `GDContextManager` provides `acquire_turn` and `release_turn`.
- [ ] `moderator` agent assigns `next_speaker` via data channel events.
- [ ] `aarav` and `priya` check `acquire_turn` and remain silent if it returns `False`.
- [ ] Agents do not speak over each other; only one agent speaks per turn.

## Implementation Notes
- **Files to touch**:
  - `shared_context.py`: Add new fields and helper methods to manage the central state.
  - `agents/debater_aarav.py`, `agents/debater_priya.py`: Update `on_user_turn_completed` to check turn ownership. Intercept data channel for `next_speaker` events. Add `on_agent_speech_finished` (or hook `on_exit` / `_publish_transcript`) to release turns.
  - `agents/moderator.py`: Implement logic to orchestrate turns and publish `next_speaker`.

## Verification Plan
- Run `python server.py` and `python run_agents.py`.
- Connect via frontend, speak as a user.
- Observe that only one agent responds (the assigned `turn_owner`).
- Observe that the moderator successfully orchestrates the turn queue.
