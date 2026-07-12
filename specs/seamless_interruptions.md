# Seamless User Interruptions

## Goal
The system must support seamless user interruptions, allowing users to take control of the conversation at any time. The AI agents should instantly stop speaking, cancel queued responses, and the moderator should re-establish the flow.

## Context
In a real-world group discussion, participants frequently interrupt each other. Our AI agents currently use `allow_interruptions=False` in some places, preventing users from barging in. Furthermore, when users interrupt, agents must cancel stale replies rather than speaking over the user.

## Current State
- Some `session.say()` calls in `moderator.py` are hardcoded to `allow_interruptions=False`.
- The moderator updates context when the user speaks but doesn't explicitly re-establish the conversation flow if an interruption occurs.

## Desired Behavior
1. All `session.say()` calls must be configured with `allow_interruptions=True`.
2. When the user speaks, ongoing TTS is immediately interrupted.
3. The moderator agent must recognize user input and appropriately acknowledge/re-queue the discussion flow, ensuring it reacts to the user's interruption contextually.

## Acceptance Criteria
- [ ] `allow_interruptions=True` is used in all `session.say()` calls.
- [ ] User can interrupt the moderator's opening and phase announcements.
- [ ] The moderator acknowledges user input and re-establishes the flow when the user finishes speaking.

## Implementation Notes
- Touch `agents/moderator.py`.
- Update `session.say` calls.
- In `moderator.py`'s `on_user_turn_completed`, after updating context, we can prompt the moderator's LLM to generate a contextual acknowledgement or re-queue the conversation (e.g., using `self.session.generate_reply()` or by injecting a system prompt update).

## Verification Plan
- Run `python server.py` and `python run_agents.py`.
- Join the session, interrupt Kavya's opening script.
- Kavya should stop speaking immediately.
- Once user stops speaking, Kavya should acknowledge the user and re-establish the discussion flow.
