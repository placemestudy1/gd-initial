# AGENTS.md — Rules for AI Coding Agents

This file governs how AI agents must behave when working in this repository.
Read this before touching any file.

---

## 1. Read Before You Write

Before editing any code, always read:
1. `README.md` — primary product context and architecture overview
2. `AGENTS.md` — this file; behavioral rules
3. `AI_WORKFLOW.md` — the step-by-step workflow
4. `lessons.md` — known project-specific gotchas and corrections
5. The relevant spec in `specs/` for the feature you are working on

**README.md is the source of truth for product context** unless a spec in `specs/` explicitly overrides a specific detail.

**MANDATORY:** You must maintain the `lessons.md` file to log every issue faced, ensuring new learnings are carried forward.

---

## 2. Write a Spec Before You Code

For any non-trivial change (new feature, refactor, behavior change, architecture decision):

- Find or create the relevant spec in `specs/` using `specs/_template.md`
- Do not start coding until the spec captures: **goal, desired behavior, acceptance criteria, and a verification plan**
- Trivial one-line fixes or typo corrections are exempt from this rule

---

## 3. Scope Discipline

- Implement the **smallest safe version** that satisfies the spec
- Do **not** refactor unrelated code
- Do **not** introduce new libraries unless clearly justified in the spec's Implementation Notes
- Do **not** rewrite architecture unless the spec explicitly requires it
- Do **not** modify files unrelated to the current spec/task
- Preserve existing files and human-authored changes

---

## 4. Loop & Token Control

- If stuck after **two serious attempts**, stop — do not loop
- Write a short blocker summary: what you tried, why it failed, and what you need
- Do not keep retrying the same command or the same fix repeatedly
- Do not chase unrelated errors; fix only failures directly caused by your change
- If tests or the build fail for reasons unrelated to your change, note them but do not fix them

---

## 5. Completion Standard

Every task must end with a short summary containing:
- **Changed files** (list with one-line reason each)
- **What was implemented** (vs. what was planned)
- **Verification results** (commands run, outputs observed)
- **Remaining risks** (known gaps, untested paths, assumptions made)

---

## 6. Project-Specific Context

This is the **PlaceMe GD Arena** — a real-time AI-powered Group Discussion practice tool for college students preparing for campus placements.

Key architectural facts to keep in mind:
- **Backend**: Python 3.11, FastAPI, Uvicorn
- **Real-time layer**: LiveKit (WebRTC) — agents run as LiveKit workers
- **AI agents**: Kavya (Moderator), Aarav (Debater), Priya (Debater) — each in `agents/`
- **Shared state**: `shared_context.py` backs all agents via LiveKit Room Metadata; token-optimized (70%+ reduction by summarizing old turns)
- **LLMs**: Groq API + Google Gemini (Google API)
- **VAD**: Silero (voice activity detection)
- **Frontend**: Vanilla HTML/CSS/JS in `frontend/`
- **Entry points**: `server.py` (FastAPI), `run_agents.py` (launches all 3 agents)
- **No package.json** — this is a pure Python project; use `pip` and `venv`

Do not assume Node.js tooling, TypeScript, or build pipelines exist.
