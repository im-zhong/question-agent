# Fix Skill

<Purpose>
  Fix a bug following strict TDD discipline: write a failing test that reproduces
  the error FIRST, then make the minimal code change to pass the test. Never fix
  first and test later.
</Purpose>

<Use_When>
  - User reports a runtime error or unexpected behavior
  - User says "fix", "修复", "bug", or provides an error traceback
  - A test is failing and needs investigation + fix
  - CI is red and the root cause is unclear
</Use_When>

<Do_Not_Use_When>
  - The fix is trivial (typo, obvious one-line change) — just fix it directly
  - User wants a feature added, not a bug fixed — use progressive-plan + dev-loop
  - User explicitly says "just fix it" or "skip the test" — respect their wish, but mention the risk
</Do_Not_Use_When>

<Execution_Policy>
  Strict two-phase approach. Phase 1 (reproduce) MUST complete before Phase 2 (fix).
  The failing test is the gate — no code changes to production code until the test exists.
</Execution_Policy>

<Steps>

### Phase 1: Reproduce

**Step 1.1 — Understand the error**

Read the error message / traceback provided by the user. If insufficient:
- Ask for: full traceback, steps to reproduce, expected vs actual behavior
- Check logs: `git log --oneline -5`, recent file changes
- Read the relevant source file(s)

**Step 1.2 — Locate the bug**

Use grep, Read, and explore to find the exact line(s) causing the error.
Narrow down to the specific function and code path.

**Step 1.3 — Write a failing test**

Create a test file (or add to an existing one) that:
- Reproduces the exact error reported by the user
- Is isolated — doesn't depend on external services or running servers
- Is minimal — removes all unrelated setup
- Uses the same code path as the production code
- Asserts the EXPECTED (correct) behavior, not the broken behavior

File naming: `tests/test_<bug_area>.py` or append to an existing test file.

Run the test to confirm it FAILS:
```bash
uv run pytest tests/test_<bug_area>.py -v
```

If the test passes unexpectedly:
- The reproduction is wrong — the test isn't hitting the bug
- Re-examine the error and adjust the test
- Do NOT proceed to Phase 2 until you have a genuinely failing test

**Step 1.4 — Gate: Confirm reproduction**

Show the user:
```
## Bug Reproduced

**Error:** <one-line summary>
**Test:** tests/test_<bug_area>.py::<test_name>
**Result:** FAILED — <error message from test output>

Root cause: <your analysis in 1-2 sentences>

→ Proceeding to fix...
```

### Phase 2: Fix

**Step 2.1 — Make the minimal fix**

Change ONLY the production code needed to make the test pass.
- No refactoring, no "while I'm here" changes
- No adding features or improving error messages unrelated to the bug
- Keep the diff small and focused

**Step 2.2 — Verify the fix**

Run the failing test:
```bash
uv run pytest tests/test_<bug_area>.py -v
```

It must now PASS. If it doesn't, iterate on the fix (not the test).

**Step 2.3 — Run the full test suite**

```bash
uv run pytest --ignore=tests/integration/ -q
```

If other tests break, the fix introduced a regression. Investigate and adjust.

**Step 2.4 — Run lint and type checks**

```bash
uv run ruff check . && uv run ruff format --check . && uv run mypy question_agent/
```

Fix any issues.

**Step 2.5 — Summary**

Show the user:
```
## Fix Complete

**Bug:** <one-line summary>
**Root cause:** <1-2 sentences>
**Fix:** <what changed, in one sentence>
**Test:** tests/test_<bug_area>.py::<test_name> ✅
**Full suite:** <pass/fail count>

Changed files:
  - <file>: <one-line description>
```

</Steps>

<Constraints>
- NEVER modify production code before the failing test exists
- NEVER modify the test to make it pass — fix the production code
- NEVER skip running the failing test to confirm it actually fails
- NEVER bundle unrelated changes with the fix
- If the bug is in test code (not production code), say so and fix the test directly
- If the bug cannot be reproduced in isolation (requires running server, external API),
  document why and use a mock-based test that simulates the failure condition
</Constraints>

<Tool_Usage>
  - Read: understand source code and existing tests
  - Bash: run tests, git log, grep for bug location
  - Write: create the failing test file
  - Edit: make the minimal production code fix
</Tool_Usage>
