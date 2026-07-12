# specs/README.md — How Specs Work

## Two Levels of Context

| Source | Scope | When to Read |
|---|---|---|
| `README.md` (root) | Product-level: purpose, users, architecture, tech stack | Always, before any task |
| `specs/*.md` | Feature-level: goal, behavior, acceptance criteria, implementation notes | Before any non-trivial code edit |

---

## The Rule

**Every meaningful feature or change gets a spec before code is written.**

"Meaningful" means: new behavior, changed behavior, refactors, new endpoints, prompt changes, shared context changes, or anything that touches more than one file in a non-obvious way.

Trivial exceptions: one-line typo fixes, comment corrections, minor formatting.

---

## Spec Lifecycle

1. **Create** — copy `_template.md`, name it clearly (e.g., `specs/interruption-handling.md`)
2. **Fill in** — write goal, desired behavior, acceptance criteria, verification plan before coding
3. **Keep updated** — if scope changes mid-implementation, update the spec first, then continue
4. **Leave in place** — completed specs serve as a record of why a decision was made

---

## Specs are Short and Practical

A spec is not a design doc. It should take 5–10 minutes to write.
If it's taking longer, the goal is not clear enough yet — clarify the goal first.

---

## Current Specs

| File | Feature |
|---|---|
| `MVP.md` | Overall MVP scope derived from README.md |
| `_template.md` | Blank template for new specs |
