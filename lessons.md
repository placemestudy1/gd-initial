# lessons.md — Project Memory

This file stores project-specific lessons discovered during development.
It is a living document — append new lessons as they are discovered.
AI agents should read this file before starting any task.

---

## How to Add a Lesson

Use this template:

```
### [YYYY-MM-DD] — Short title

**Situation**: What were you trying to do?

**Lesson**: What did you learn — the specific gotcha, pattern, or correction?

**Future Rule**: One sentence rule that prevents this mistake again.
```

---

## Lessons

### [2026-07-12] — Initial project setup

**Situation**: Setting up agent workflow files for the GD Arena repo.

**Lesson**: This is a pure Python project (FastAPI + LiveKit Agents SDK). There is no Node.js, no `package.json`, no build pipeline, and no TypeScript. The frontend is vanilla HTML/CSS/JS in `frontend/`. Do not assume frontend tooling.

**Future Rule**: Always confirm the tech stack from `README.md` before suggesting or using Node/npm/pip commands.

---

### [2026-07-12] — Shared context is LiveKit Room Metadata, not a DB

**Situation**: Understanding how agents share state.

**Lesson**: `shared_context.py` uses LiveKit Room Metadata as the backing store for all shared agent state (phase, transcript summary, scores). There is no database, no Redis, no file-based state. Any agent that modifies shared state must go through `shared_context.py`. Token optimization is built in: only the last 3 raw utterances + a key-arguments summary are passed to each agent.

**Future Rule**: Never add a second source of shared state. Route all inter-agent context through `shared_context.py`.

---

### [2026-07-12] — Three agents, each a separate LiveKit worker

**Situation**: Understanding agent launch and structure.

**Lesson**: Kavya (Moderator), Aarav (Debater), and Priya (Debater) are each a separate LiveKit agent worker, launched together by `run_agents.py`. Each lives in `agents/`. Changes to one agent's prompt or logic do not affect the others unless `shared_context.py` or `agents/prompts.py` is touched.

**Future Rule**: When modifying one agent, check if the change requires a matching update in `agents/prompts.py` or `shared_context.py`.
