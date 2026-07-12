# AI_WORKFLOW.md — Agent Workflow for PlaceMe GD Arena

This document defines the step-by-step process an AI agent must follow for every task in this repo.
Follow it in order. Do not skip steps to save tokens — skipping steps causes more wasted tokens downstream.

---

## Workflow Steps

### Step 1 — Read for Context
- Read `README.md` for product purpose, architecture, and tech stack
- Read `AGENTS.md` for behavioral rules
- Read `lessons.md` for known project-specific gotchas
- Identify which `specs/` file is relevant (or whether one needs to be created)

### Step 2 — Understand the Goal
- Restate the user's goal in one clear sentence before proceeding
- If the goal is ambiguous, ask one precise question rather than assuming

### Step 3 — Find or Create the Spec
- Search `specs/` for an existing spec that covers this feature or change
- If none exists and the task is non-trivial, create one from `specs/_template.md`
- The spec must capture: goal, desired behavior, acceptance criteria, verification plan
- Do not proceed to coding until the spec is written and reviewed

### Step 4 — Write a Concise Implementation Plan
- List the files you expect to touch and why
- Note any risks, constraints, or unknowns
- Keep it to a short paragraph or bullet list — not a design doc

### Step 5 — Identify Files to Touch
- Limit your working set to only the files the implementation plan names
- Avoid opening files speculatively; read only what you need

### Step 6 — Edit Only Those Files
- Make changes that are scoped to the spec
- Do not fix unrelated code you notice along the way (log it in `lessons.md` instead)
- Prefer small, complete changes over large partial rewrites

### Step 7 — Run Minimal Verification First
- Run the smallest check that can catch obvious breakage
  - For Python: `python -m py_compile <file>` or a relevant unit test
  - For the server: `python server.py` briefly to catch import errors
  - For agents: `python agents/<agent>.py dev` if the environment allows
- Fix only failures directly caused by your changes

### Step 8 — Run Full Verification When Complete
- Once the implementation is done, run the full relevant test suite or integration check
- If running the full stack, verify: server starts, agents connect, frontend loads
- Document the verification results in your completion summary

### Step 9 — Update lessons.md
- **MANDATORY:** If you discovered a new project rule, a bug pattern, a quirk of LiveKit or the agent SDK, or corrected a wrong assumption — you MUST write it to `lessons.md`.
- Use the template in `lessons.md` (if applicable) and maintain an ongoing log of every issue faced.
- Keep each lesson short and actionable.

---

## Token / Loop Control

These rules exist to prevent wasteful, circular work.

- **Start focused**: Begin with `README.md`, then only the relevant spec and the files you plan to edit. Do not explore the whole codebase upfront.
- **Limit exploration time**: Form a plan after brief inspection. If you need more context, name the specific file you need before opening it.
- **Do not reopen files repeatedly**: Once you have read a file, use what you learned. Re-read only if the file was changed.
- **Do not chase unrelated errors**: If a failure is not caused by your change, note it and move on.
- **Two-attempt limit**: If you have tried two meaningfully different approaches and both failed, stop. Write a blocker summary with: what you tried, the exact failure, and what you need from the user.
- **One precise question beats many guesses**: If something is unclear, ask a single, specific question instead of iterating blindly through possibilities.
- **Keep summaries short and decision-focused**: Your completion summary should help the user make decisions, not document every step you took.
