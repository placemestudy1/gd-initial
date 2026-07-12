# specs/MVP.md — PlaceMe GD Arena: MVP Scope

> Derived from `README.md`. Do not invent details not present there.
> Items marked **[TODO]** or **[ASSUMPTION]** need clarification from the product owner.

---

## Product Purpose

PlaceMe GD Arena is a real-time, AI-powered Group Discussion practice tool for college students preparing for campus placements. It simulates a real-world GD environment — the user speaks out loud, AI agents respond, and the session ends with actionable feedback.

**Core problem solved**: Engineering students lack practical rehearsal for the high-pressure GD round of campus placements. Reading about GDs is not the same as participating in one.

---

## Target Users

- College students (primarily engineering) preparing for campus placement drives
- Students who want a safe, on-demand environment to rehearse GD skills

---

## Core Workflows

### 1. AI Voice Practice
- User selects a topic and a timer duration (e.g., 5 or 10 minutes)
- User is placed in a virtual room with 3 AI participants
- User speaks out loud; AI agents respond in real-time
- Session ends when the timer expires

### 2. Multiplayer Practice
- User invites classmates to a private room
- PlaceMe provides the topic and timer
- Students practice together; AI handles facilitation

### 3. Post-Session Feedback
- After the session, the system generates a simple report
- Feedback covers: speaking clarity, topic relevance, turn-taking behavior

---

## AI Participants

| Agent | Role | Behavior |
|---|---|---|
| **Kavya** (Moderator) | Guides the discussion | Introduces topic, manages transitions, tracks time, provides closing summary |
| **Aarav** (Debater) | Argumentative voice | Strong arguments and counter-points; distinct personality |
| **Priya** (Debater) | Balanced voice | Unique perspectives; balances discussion dynamics |

---

## Architecture (MVP)

| Layer | Technology |
|---|---|
| Backend | Python 3.11, FastAPI, Uvicorn |
| Real-time | LiveKit (WebRTC) |
| Agent SDK | `livekit-agents` |
| LLMs | Groq API, Google Gemini (Google API) |
| VAD | Silero |
| Frontend | Vanilla HTML, CSS, JavaScript |
| Shared State | `shared_context.py` → LiveKit Room Metadata |
| Entry points | `server.py` (web + API), `run_agents.py` (launches all agents) |

### Key Architecture Decisions (from README.md)
- **Token optimization**: `shared_context.py` summarizes old turns; agents receive only the topic, current phase, key-argument summary, and last 3 raw utterances (~70% token reduction)
- **Phase management**: Discussion auto-advances through `opening → main_discussion → closing` based on utterance count and time
- **Scoring**: User engagement tracked (speaking time, point count) for post-session feedback
- **Human-like dynamics**: Responsive interruptions (acknowledged immediately, not queued); natural pacing to prevent agent domination at session start

---

## MVP Scope

### In Scope
- [x] Real-time voice GD with 3 AI agents (Kavya, Aarav, Priya)
- [x] Topic selection + timer selection before session start
- [x] Shared context via LiveKit Room Metadata
- [x] Phase-based discussion progression (opening → main → closing)
- [x] Post-session feedback report (speaking clarity, topic relevance, turn-taking)
- [x] Responsive interruption handling
- [x] Token-optimized context passing to agents
- [x] Multiplayer room support (invite classmates)
- [x] Vanilla HTML/CSS/JS frontend served by FastAPI

### Out of Scope (not mentioned in README.md)
- User accounts / authentication / login
- Persistent session history / score tracking across sessions
- Mobile app
- Payment / subscription
- Topic bank management UI
- Admin dashboard

---

## Open Questions / TODOs

- **[TODO]** What topics are available for selection? Is there a curated list or free-text input?
- **[TODO]** What does the feedback report look like exactly? Is it a score, a paragraph, or structured categories?
- **[TODO]** How is the multiplayer room invitation handled (link, code)?
- **[ASSUMPTION]** Timer options are 5 and 10 minutes, as stated in README.md. Other durations may also be valid.
- **[ASSUMPTION]** Feedback is generated from `shared_context.py` scoring data, but the exact output format is not specified.
- **[ASSUMPTION]** `agents/frontend_tts.py` suggests there may be a TTS component for the frontend — exact role unclear.
