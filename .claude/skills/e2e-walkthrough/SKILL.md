---
name: e2e-walkthrough
description: Simulates human web usage by reading project docs, constructing realistic user journeys, verifying each step via Playwright screenshots and DOM inspection, and fixing any broken behavior found.
triggers:
  - e2e walkthrough
  - e2e walk
  - end to end test
  - e2e测试
  - 端到端测试
  - 模拟使用
  - walkthrough
---

<Purpose>
  Simulate a real human user interacting with the web application end-to-end.
  Read project documentation to understand implemented features, construct realistic
  user journeys, drive the browser via Playwright to verify each step works, capture
  screenshots for visual validation, and fix any broken behavior discovered along the way.
</Purpose>

<Use_When>
  - User says "e2e walkthrough", "walkthrough", "模拟使用", "端到端测试"
  - User wants to verify the web app works as a human would experience it
  - After completing a feature iteration, to validate the full user flow
  - User wants to catch UI/UX regressions that unit tests miss
  - User says "试一下", "跑一下流程", "验证一下功能"
</Use_When>

<Do_Not_Use_When>
  - User wants unit tests only — use /tdd or /fix
  - User wants to test a single API endpoint — use direct curl or httpx test
  - User wants code review — use /review
  - The backend and frontend servers are not running and user doesn't want to start them
</Do_Not_Use_When>

<Why_This_Exists>
  Unit tests and integration tests verify code paths in isolation. They cannot catch:
  broken CSS that hides a button, a misconfigured route that 404s, a WebSocket that
  silently disconnects, or a form that submits but shows no feedback. Only a real browser
  session — with screenshots and DOM inspection — can confirm the app actually works as
  a human experiences it. This skill automates that human-level verification loop.
</Why_This_Exists>

<Execution_Policy>
  - Each journey must be derived from project documentation, not assumed
  - Every step must be visually verified (screenshot) before moving on
  - Failures trigger: write a reproducing E2E test → fix the bug → re-verify
  - Fix loop repeats until the step passes; max 5 fix attempts per step
  - If 5 attempts fail on one step, stop and report the fundamental issue
  - Screenshots are saved to /tmp/e2e-walkthrough/ for review
  - All E2E test files go into tests/e2e/ directory
</Execution_Policy>

<Steps>

### Phase 1: Reconnaissance — Learn the Project

**Step 1.1 — Read project documentation**

Read the following files in order to understand what features exist and are implemented:
1. `docs/superpowers/state.md` — current iteration, completed items
2. `docs/superpowers/specs/2026-04-29-ai-question-agent.md` — full feature spec
3. `docs/superpowers/plans/2026-04-29-ai-question-agent.md` — roadmap with status markers
4. Latest iteration file in `docs/superpowers/iterations/` — current work context
5. `.harness/ai-question-agent-toolchain.md` — tech stack details

From these docs, extract:
- **Completed features** (those marked ✅ or with completed iteration items)
- **User-facing pages and routes** (from frontend/src/routes/)
- **Key user interactions** (what a human would click, type, submit)

**Step 1.2 — Inspect the running application**

Ensure both servers are running:
```bash
# Backend
curl -s http://localhost:8000/docs > /dev/null && echo "Backend OK" || echo "Backend DOWN"
# Frontend
curl -s http://localhost:5173 > /dev/null && echo "Frontend OK" || echo "Frontend DOWN"
```

If either is down, start them:
```bash
# Terminal 1: Backend
uv run question-agent &
# Terminal 2: Frontend
cd frontend && npm run dev &
```

Use the webapp-testing helper to launch both servers if needed:
```bash
python ~/.claude/skills/webapp-testing/scripts/with_server.py \
  --server "uv run question-agent" --port 8000 \
  --server "cd frontend && npm run dev" --port 5173 \
  -- python your_script.py
```

**Step 1.3 — Screenshot each page**

Navigate to each route and take a full-page screenshot:
- `/` (home/index)
- `/chat` (chat interface)
- `/knowledge-bases` (KB management)
- `/upload` (file upload)

Save screenshots to `/tmp/e2e-walkthrough/phase1/`.

Use Read tool to view each screenshot and assess the current state of each page.

### Phase 2: Construct User Journeys

**Step 2.1 — Define primary user journey**

Based on the completed features from Phase 1, construct the main user journey.
For this project (AI Question Agent), the primary journey is:

```
1. Open the app → see home page
2. Navigate to Knowledge Bases → see empty or existing list
3. Create a new knowledge base (fill name, subject, grade level)
4. See the new KB in the list
5. Upload a document to the knowledge base
6. Navigate to Chat
7. Select a knowledge base
8. Send a message requesting question generation
9. Receive streaming response with generated questions
10. Preview generated questions
11. Export questions
```

**Step 2.2 — Define alternative journeys**

Also plan secondary flows:
- Chat without selecting a KB (general conversation)
- View knowledge points in a KB
- Create a KB with invalid input (validation check)
- Send a message that triggers an error (error handling check)

**Step 2.3 — Write journey plan to file**

Save the journey definitions to `/tmp/e2e-walkthrough/journey-plan.md`:
```markdown
# E2E Walkthrough Journey Plan

## Primary Journey: [name]
- Step 1: [action] → [expected result]
- Step 2: [action] → [expected result]
...

## Secondary Journey: [name]
...
```

### Phase 3: Execute and Verify

**Step 3.1 — Execute each step of the primary journey**

For each step in the journey:

1. **Perform the action** via Playwright script:
   ```python
   from playwright.sync_api import sync_playwright

   with sync_playwright() as p:
       browser = p.chromium.launch(headless=True)
       page = browser.new_page(viewport={"width": 1280, "height": 720})

       # Navigate
       page.goto("http://localhost:5173/chat")
       page.wait_for_load_state("networkidle")

       # Take screenshot
       page.screenshot(path="/tmp/e2e-walkthrough/step-XX-action.png", full_page=True)

       # Interact
       page.locator("textarea").fill("请生成一道数学题")
       page.locator("button[type=submit]").click()

       # Wait for response
       page.wait_for_timeout(5000)  # or wait for specific selector
       page.screenshot(path="/tmp/e2e-walkthrough/step-XX-result.png", full_page=True)

       browser.close()
   ```

2. **Verify the result** by reading the screenshot with the Read tool and checking:
   - Did the expected UI element appear?
   - Is the content correct and readable?
   - Are there any error messages visible?
   - Does the layout look correct (no overflow, no missing styles)?

3. **If verification passes** → move to next step

4. **If verification fails** → proceed to Phase 4 (Fix Loop)

**Step 3.2 — Execute secondary journeys**

Repeat the same process for secondary journeys. These are lower priority — if they
fail, document the failure but don't block on them.

**Step 3.3 — Generate verification report**

After all journeys are executed, produce a summary:

```markdown
# E2E Walkthrough Report

## Primary Journey: [name]
| Step | Action | Expected | Actual | Status |
|------|--------|----------|--------|--------|
| 1    | ...    | ...      | ...    | ✅/❌  |

## Secondary Journeys
| Journey | Steps | Pass | Fail |
|---------|-------|------|------|

## Screenshots
- /tmp/e2e-walkthrough/step-01-home.png
- ...
```

### Phase 4: Fix Loop (triggered on failure)

When a step fails verification:

**Step 4.1 — Investigate the failure**

Use multiple investigation techniques:
1. Read the screenshot to understand what went wrong visually
2. Inspect the DOM via Playwright:
   ```python
   content = page.content()
   # Save and read the HTML
   with open("/tmp/e2e-walkthrough/debug-dom.html", "w") as f:
       f.write(content)
   ```
3. Check browser console logs:
   ```python
   logs = page.evaluate("() => window.__console_logs || []")
   ```
4. Check the backend logs for errors
5. Read the relevant frontend source code (routes, components)
6. Read the relevant backend source code (API handlers)

**Step 4.2 — Write a reproducing E2E test**

Create a test file in `tests/e2e/` that reproduces the exact failure:

```python
# tests/e2e/test_chat_flow.py
"""E2E test: Chat flow with question generation"""
import pytest
from playwright.sync_api import Page, expect

LIVE_URL = "http://localhost:5173"

@pytest.fixture
def page(browser):
    page = browser.new_page(viewport={"width": 1280, "height": 720})
    yield page
    page.close()

def test_chat_sends_message_and_receives_response(page: Page):
    """User can send a chat message and receive a streaming response."""
    page.goto(f"{LIVE_URL}/chat")
    page.wait_for_load_state("networkidle")

    # Find the chat input
    chat_input = page.locator("textarea")
    assert chat_input.is_visible(), "Chat input textarea should be visible"

    # Type and send a message
    chat_input.fill("请生成一道数学题")
    page.locator("button[type=submit]").click()

    # Wait for response to appear
    page.wait_for_timeout(10000)

    # Verify response is shown
    messages = page.locator("[data-testid='message'], .message, .chat-message")
    assert messages.count() >= 2, "Should have at least user message + assistant response"
```

Run the E2E test to confirm it fails:
```bash
cd frontend && npx playwright test tests/e2e/ --headed || true
# Or if using Python playwright:
uv run pytest tests/e2e/ -v --timeout=30
```

**Step 4.3 — Fix the bug**

Follow the same discipline as the /fix skill:
- Make the MINIMAL change to fix the issue
- Re-run the E2E test to confirm it passes
- Run the unit test suite to check for regressions:
  ```bash
  uv run pytest --ignore=tests/integration/ -q
  ```
- Run lint/type checks:
  ```bash
  uv run ruff check . && uv run ruff format --check . && uv run mypy question_agent/
  ```

**Step 4.4 — Re-verify visually**

After fixing, re-run the same Playwright steps that originally failed.
Take a new screenshot and verify the result passes.

**Step 4.5 — Continue or escalate**

- If the fix works → continue to the next step in the journey
- If the fix doesn't work after 5 attempts → stop and report:
  ```
  ## Blocked: Unfixable Issue

  **Step:** [description]
  **Failure:** [what went wrong]
  **Attempts:** 5
  **Root cause hypothesis:** [analysis]

  This may require manual investigation or a design change.
  ```

### Phase 5: Final Report

**Step 5.1 — Produce the walkthrough report**

Write the complete report to `/tmp/e2e-walkthrough/report.md`:

```markdown
# E2E Walkthrough Report — [date]

## Summary
- **Total journeys:** N
- **Total steps:** N
- **Passed:** N ✅
- **Failed:** N ❌
- **Fixed:** N 🔧
- **Blocked:** N 🚫

## Journey Details

### Primary Journey: [name]
| Step | Action | Status | Screenshot |
|------|--------|--------|------------|
| 1    | ...    | ✅     | step-01.png |
| 2    | ...    | ❌→✅  | step-02.png |

## Bugs Found and Fixed
1. **[Bug title]** — [root cause] → [fix description]

## Blocked Issues
1. **[Issue]** — [reason]

## E2E Test Files Created
- tests/e2e/test_[name].py
```

**Step 5.2 — Show the report to the user**

Present the key findings:
- What works as expected
- What was broken and is now fixed
- What remains broken and needs attention

</Steps>

<Tool_Usage>
  - **Read**: View screenshots, read project docs, read source code
  - **Bash**: Run Playwright scripts, run pytest, start servers, curl health checks
  - **Write**: Create E2E test files, write journey plans, write reports
  - **Edit**: Fix bugs found during walkthrough
  - **Agent (explore)**: Search codebase for selectors, component names, API endpoints
  - **Agent (debugger)**: Investigate complex failures that aren't obvious from screenshots
  - **webapp-testing skill**: Use with_server.py helper for server lifecycle management
  - **browser-use CLI**: Alternative to Python Playwright for interactive inspection (browser-use state/screenshot)
</Tool_Usage>

<Examples>

<Good>
User: "e2e walkthrough"
Why good: Direct trigger for this skill. Will read project docs, construct user journeys, and verify the app works end-to-end.

User: "模拟使用一下这个系统"
Why good: User wants to simulate real usage — exactly what this skill does.

User: "跑一下主要流程看看有没有问题"
Why good: User wants to walk through the main flow and catch issues — this skill's core purpose.
</Good>

<Bad>
User: "帮我写个单元测试"
Why bad: Wants unit tests, not E2E. Use /tdd instead.

User: "review一下代码"
Why bad: Wants code review. Use /review instead.

User: "这个bug怎么修"
Why bad: Wants a specific bug fix. Use /fix instead.
</Bad>

</Examples>

<Escalation_And_Stop_Conditions>
  - Stop after 5 fix attempts on a single step — report as blocked
  - Stop if both servers cannot be started after 3 attempts
  - Stop if Playwright cannot connect to the browser after 3 attempts
  - Stop if the user says "stop", "cancel", "abort"
  - If a step requires authentication or external APIs that aren't configured, document it and skip
  - If the project docs are too incomplete to construct journeys, ask the user to describe the expected flow
</Escalation_And_Stop_Conditions>

<Final_Checklist>
  - [ ] Project documentation read and features understood
  - [ ] All pages/screenshots captured
  - [ ] Primary user journey constructed from docs
  - [ ] Each journey step executed and verified via screenshot
  - [ ] All failures investigated and fixed (or documented as blocked)
  - [ ] E2E test files created for each bug found
  - [ ] All E2E tests pass
  - [ ] Unit test suite still passes (no regressions)
  - [ ] Lint and type checks pass
  - [ ] Final report produced at /tmp/e2e-walkthrough/report.md
  - [ ] User shown the summary of findings
</Final_Checklist>

<Advanced>

## Playwright Setup

This project does not have Playwright installed. The skill handles setup automatically:

### Option A: Python Playwright (recommended for E2E tests)
```bash
# Install
uv add --dev playwright pytest-playwright
uv run playwright install chromium

# Run E2E tests
uv run pytest tests/e2e/ -v --timeout=30
```

### Option B: Node.js Playwright (if frontend team prefers)
```bash
cd frontend
npm install -D @playwright/test
npx playwright install chromium
npx playwright test tests/e2e/
```

The skill will check which is available and use it. If neither is installed, it will
install Python Playwright (uv add) as the project is Python-first.

## Selector Strategy

Prefer selectors in this order:
1. `data-testid` attributes (if they exist)
2. ARIA roles: `page.get_by_role("button", name="Submit")`
3. Text content: `page.get_by_text("生成题目")`
4. CSS selectors: `.chat-input`, `textarea`, `button[type=submit"]`
5. XPath (last resort)

When writing E2E tests, add `data-testid` attributes to components that lack them.
This improves test reliability and is a net positive for the codebase.

## Handling Streaming Responses

The chat feature uses WebSocket streaming. To verify streaming works:
```python
# Wait for the response to start appearing
page.wait_for_selector(".assistant-message, [data-role='assistant']", timeout=15000)
# Wait a bit more for streaming to complete
page.wait_for_timeout(3000)
# Verify response content
response = page.locator(".assistant-message").last
assert response.is_visible()
```

## Handling File Upload

To test file upload to knowledge bases:
```python
# Click upload button/area
upload_input = page.locator("input[type=file]")
upload_input.set_input_files("/path/to/test-document.pdf")
page.wait_for_load_state("networkidle")
```

## Screenshot Organization

```
/tmp/e2e-walkthrough/
├── phase1/               # Initial reconnaissance screenshots
│   ├── home.png
│   ├── chat.png
│   ├── knowledge-bases.png
│   └── upload.png
├── journey-primary/      # Primary journey step screenshots
│   ├── step-01-open-app.png
│   ├── step-02-nav-to-kb.png
│   └── ...
├── journey-secondary/    # Secondary journey screenshots
├── debug/                # Failure investigation screenshots
├── journey-plan.md       # Journey definitions
└── report.md             # Final walkthrough report
```

## Integration with Other Skills

- **After /run**: Use e2e-walkthrough to validate that all CI-green code actually works in the browser
- **After /fix**: Re-run the specific journey step that was broken to confirm the fix
- **Before release**: Run full walkthrough as a release gate
- **With /dev-loop**: Alternate between dev-loop (implement feature) and e2e-walkthrough (verify in browser)
</Advanced>
