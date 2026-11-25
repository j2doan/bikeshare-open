---
name: seed-fault
description: Deliberately introduce one described fault into src/ so we can watch the hook and tests catch it. Use when asked to seed, plant, or inject a fault. Makes the edit and stops. Never fixes it.
allowed-tools: Read, Edit
---

# Seeding a fault: $ARGUMENTS

Do exactly this, in order.

1. **Refuse unsafe targets.** Only edit files under `src/`. If the request
   touches `data/raw/`, `tests/`, or `.claude/`, say so and stop.

2. **Read the target** with Read so the edit is exact.

3. **Make the single edit** that `$ARGUMENTS` describes, and nothing else.
   Do not "improve" nearby code.

4. **Do not run tests and do not fix anything.** The PostToolUse hook runs
   `tests/test_leakage.py` after the edit. That result is the point.

5. **Report in three lines:** the file and line you changed, the diff
   (old line, new line), and the hook output copied verbatim if any came
   back. If no hook output came back, say "hook silent". Then stop.
