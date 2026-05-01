# Run Skill Walkthrough Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a "start system + functional walkthrough" step as the final gate in the run skill, ensuring the system actually runs and all endpoints respond correctly before committing.

**Architecture:** Insert a new Step 6 (启动系统 + 功能走查) after edge tests and before feature verification. Integration tests live in `tests/integration/` with their own conftest.py that hits a live server. The run skill manages the server lifecycle (start, health check, walkthrough, shutdown). Toolchain doc provides server config via a `## Walkthrough` section.

**Tech Stack:** pytest, httpx, FastAPI, uvicorn

---

### Task 1: Add Walkthrough config to toolchain doc

**Files:**
- Modify: `.harness/ai-question-agent-toolchain.md`

- [ ] **Step 1: Add Walkthrough section**

Append the following after the `## All Checks` section:

```markdown
## Walkthrough

| 配置项 | 值 |
|--------|-----|
| Start Command | `uv run question-agent` |
| Health Check | `GET /docs` → 200 |
| Shutdown Signal | SIGTERM |
| Port | 8000 |
```

- [ ] **Step 2: Verify the edit**

Run: `grep -A8 '## Walkthrough' .harness/ai-question-agent-toolchain.md`
Expected: The Walkthrough table with all 4 rows visible.

- [ ] **Step 3: Commit**

```bash
git add .harness/ai-question-agent-toolchain.md
git commit -m "docs(toolchain): add Walkthrough config section for run skill"
```

---

### Task 2: Register integration marker in pyproject.toml

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: Add integration marker**

Find the `[tool.pytest.ini_options]` section and add the `markers` key:

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
markers = [
    "integration: marks tests as integration tests (require running server)",
]
```

- [ ] **Step 2: Verify config loads**

Run: `uv run pytest --co -q 2>&1 | head -5`
Expected: No errors about unknown markers. Test collection output begins.

- [ ] **Step 3: Commit**

```bash
git add pyproject.toml
git commit -m "chore(pytest): register integration test marker"
```

---

### Task 3: Create integration test infrastructure

**Files:**
- Create: `tests/integration/__init__.py`
- Create: `tests/integration/conftest.py`
- Create: `tests/integration/fixtures/` (directory, with a .gitkeep)

- [ ] **Step 1: Create directory structure**

```bash
mkdir -p tests/integration/fixtures
touch tests/integration/__init__.py
touch tests/integration/fixtures/.gitkeep
```

- [ ] **Step 2: Write integration conftest.py**

Create `tests/integration/conftest.py`:

```python
"""Shared fixtures for integration tests — require a running server."""

from collections.abc import AsyncGenerator

import httpx
import pytest

BASE_URL = "http://localhost:8000"
TIMEOUT = 60.0


@pytest.fixture(scope="session")
def base_url() -> str:
    """Base URL for the running server."""
    return BASE_URL


@pytest.fixture
async def client(base_url: str) -> AsyncGenerator[httpx.AsyncClient, None]:
    """Async HTTP client pointing at the live server."""
    async with httpx.AsyncClient(base_url=base_url, timeout=TIMEOUT) as c:
        yield c


@pytest.fixture(autouse=True, scope="session")
def _check_server(base_url: str) -> None:
    """Skip all integration tests if the server is not reachable."""
    try:
        resp = httpx.get(f"{base_url}/health", timeout=5.0)
        resp.raise_for_status()
    except httpx.ConnectError:
        pytest.skip(f"Server not running at {base_url}. Start with: uv run question-agent")


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Automatically mark all tests in this directory as integration."""
    for item in items:
        item.add_marker(pytest.mark.integration)
```

- [ ] **Step 3: Verify collection**

Run: `uv run pytest tests/integration/ --co -q 2>&1`
Expected: "0 tests collected" (no test files yet, but no import/config errors).

- [ ] **Step 4: Commit**

```bash
git add tests/integration/__init__.py tests/integration/conftest.py tests/integration/fixtures/.gitkeep
git commit -m "test(integration): add infrastructure — conftest, fixtures dir, markers"
```

---

### Task 4: Write walkthrough tests

**Files:**
- Create: `tests/integration/test_walkthrough.py`

- [ ] **Step 1: Write the walkthrough test file**

Create `tests/integration/test_walkthrough.py`:

```python
"""Walkthrough tests — verify every registered endpoint responds correctly."""

import httpx
import pytest


@pytest.mark.asyncio
async def test_health(client: httpx.AsyncClient) -> None:
    """GET /health returns 200 with status=healthy."""
    resp = await client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert "version" in data


@pytest.mark.asyncio
async def test_extract_text_mode(client: httpx.AsyncClient) -> None:
    """POST /extract with .txt file (mode=text) returns extracted text."""
    resp = await client.post(
        "/extract",
        files={"file": ("sample.txt", b"Hello walkthrough", "text/plain")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["format"] == "text"
    assert "Hello walkthrough" in data["text"]
    assert data["char_count"] > 0
    assert data["extraction_time_ms"] >= 0


@pytest.mark.asyncio
async def test_extract_structured_mode(client: httpx.AsyncClient) -> None:
    """POST /extract with .txt file (mode=structured) returns paragraph metadata."""
    resp = await client.post(
        "/extract",
        params={"mode": "structured"},
        files={"file": ("sample.txt", b"Hello walkthrough", "text/plain")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["format"] == "text"
    assert "paragraphs" in data
    assert isinstance(data["paragraphs"], list)
    assert data["paragraph_count"] >= 1


@pytest.mark.asyncio
async def test_structure(client: httpx.AsyncClient) -> None:
    """POST /structure on text with chapter headings returns chapter tree."""
    text = "第一章 引言\n引言内容。\n1.1 背景\n背景信息。\n第二章 方法\n方法描述。"
    resp = await client.post(
        "/structure",
        files={"file": ("chapters.txt", text.encode(), "text/plain")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["format"] == "text"
    assert "chapters" in data
    assert "detection_stats" in data
    assert data["detection_stats"]["method"] in ("hybrid", "rule_only")


@pytest.mark.asyncio
async def test_knowledge(client: httpx.AsyncClient) -> None:
    """POST /knowledge on text with chapter headings returns knowledge points."""
    text = "第一章 引言\n实数包括有理数和无理数。\n函数是一种特殊的对应关系。\n第二章 代数\n一元二次方程的一般形式为 ax²+bx+c=0。"
    resp = await client.post(
        "/knowledge",
        files={"file": ("knowledge.txt", text.encode(), "text/plain")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["format"] == "text"
    assert "knowledge_points" in data
    assert "extraction_stats" in data
    assert data["extraction_stats"]["method"] in ("hybrid", "rule_only")
```

- [ ] **Step 2: Run type check on the new file**

Run: `uv run mypy tests/integration/test_walkthrough.py`
Expected: PASS (no type errors).

- [ ] **Step 3: Run lint on the new file**

Run: `uv run ruff check tests/integration/test_walkthrough.py && uv run ruff format --check tests/integration/test_walkthrough.py`
Expected: PASS.

- [ ] **Step 4: Verify collection**

Run: `uv run pytest tests/integration/ --co -q`
Expected: 5 tests collected (test_health, test_extract_text_mode, test_extract_structured_mode, test_structure, test_knowledge).

- [ ] **Step 5: Commit**

```bash
git add tests/integration/test_walkthrough.py
git commit -m "test(integration): add walkthrough tests for all endpoints"
```

---

### Task 5: Write flow tests and fixture data

**Files:**
- Create: `tests/integration/fixtures/sample_chapter.txt`
- Create: `tests/integration/test_flows.py`

- [ ] **Step 1: Create fixture file**

Create `tests/integration/fixtures/sample_chapter.txt`:

```
第一章 实数与函数

本章介绍数学的基础概念。

1.1 实数的概念

实数包括有理数和无理数。有理数可以表示为两个整数的比，无理数则不能。

1.2 函数的定义

函数是一种特殊的对应关系，对于定义域中的每一个元素，都有值域中唯一的元素与之对应。

第二章 代数基础

本章讨论基本的代数运算。

2.1 一元二次方程

一元二次方程的一般形式为 ax²+bx+c=0，其中 a≠0。判别式 Δ=b²-4ac 决定了方程根的情况。

2.2 不等式的性质

不等式的基本性质包括：两边同加同减不变号，两边同乘正数不变号，同乘负数变号。
```

- [ ] **Step 2: Write flow test file**

Create `tests/integration/test_flows.py`:

```python
"""End-to-end flow tests — verify the full business pipeline works."""

from pathlib import Path

import httpx
import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.mark.asyncio
async def test_extract_then_structure_then_knowledge(client: httpx.AsyncClient) -> None:
    """Full pipeline: same document through extract → structure → knowledge."""
    sample = FIXTURES_DIR / "sample_chapter.txt"
    content = sample.read_bytes()

    # Step 1: Extract raw text
    resp_extract = await client.post(
        "/extract",
        files={"file": ("sample_chapter.txt", content, "text/plain")},
    )
    assert resp_extract.status_code == 200
    extract_data = resp_extract.json()
    assert extract_data["format"] == "text"
    assert extract_data["char_count"] > 0

    # Step 2: Structure detection
    resp_structure = await client.post(
        "/structure",
        files={"file": ("sample_chapter.txt", content, "text/plain")},
    )
    assert resp_structure.status_code == 200
    structure_data = resp_structure.json()
    assert structure_data["format"] == "text"
    assert structure_data["chapters"] is not None
    assert len(structure_data["chapters"]) >= 2  # at least 第一章 and 第二章

    # Step 3: Knowledge extraction
    resp_knowledge = await client.post(
        "/knowledge",
        files={"file": ("sample_chapter.txt", content, "text/plain")},
    )
    assert resp_knowledge.status_code == 200
    knowledge_data = resp_knowledge.json()
    assert knowledge_data["format"] == "text"
    assert isinstance(knowledge_data["knowledge_points"], list)
    assert "extraction_stats" in knowledge_data


@pytest.mark.asyncio
async def test_chapters_consistent_across_endpoints(client: httpx.AsyncClient) -> None:
    """Chapters detected by /structure match those in /knowledge response."""
    sample = FIXTURES_DIR / "sample_chapter.txt"
    content = sample.read_bytes()

    resp_structure = await client.post(
        "/structure",
        files={"file": ("sample_chapter.txt", content, "text/plain")},
    )
    resp_knowledge = await client.post(
        "/knowledge",
        files={"file": ("sample_chapter.txt", content, "text/plain")},
    )
    assert resp_structure.status_code == 200
    assert resp_knowledge.status_code == 200

    structure_chapters = resp_structure.json().get("chapters") or []
    knowledge_chapters = resp_knowledge.json().get("chapters") or []

    # Both endpoints should detect the same number of top-level chapters
    structure_titles = {ch["title"] for ch in structure_chapters}
    knowledge_titles = {ch["title"] for ch in knowledge_chapters}
    assert structure_titles == knowledge_titles
```

- [ ] **Step 3: Run type check and lint**

Run: `uv run mypy tests/integration/test_flows.py && uv run ruff check tests/integration/ && uv run ruff format --check tests/integration/`
Expected: All pass.

- [ ] **Step 4: Verify collection**

Run: `uv run pytest tests/integration/ --co -q`
Expected: 7 tests collected (5 walkthrough + 2 flow).

- [ ] **Step 5: Commit**

```bash
git add tests/integration/fixtures/sample_chapter.txt tests/integration/test_flows.py
git commit -m "test(integration): add flow tests and sample fixture"
```

---

### Task 6: Update run SKILL.md

**Files:**
- Modify: `.claude/skills/run/SKILL.md`

This is a significant rewrite. Replace the entire file content to ensure consistency across all steps.

- [ ] **Step 1: Write the updated SKILL.md**

Replace `.claude/skills/run/SKILL.md` with the following content:

```markdown
---
name: run
description: Continuous quality-gate runner — checks, edge-case tests, walkthrough, auto-fixes, and commits when green
---

# Run — 持续性质量门禁 Runner

核心目标：确保当前进度下的系统**确实可运行**，且**边缘情况已被主动覆盖**。

## 流程

```
读取上下文 → 质量门禁 → 边缘测试 → 启动系统 + 功能走查 → 功能验证 → conventional commit
                 ↓ 失败                ↓ 失败
                 └→ 失败处理 ──────────┘
                       ↓ 修复后
                    质量门禁 → ... → 功能走查
```

## Step 1: 读取上下文

必须读全以下文件，形成当前进度快照：

| 文件 | 来源 |
|------|------|
| Spec | `docs/superpowers/specs/*.md` |
| Roadmap (功能树) | `docs/superpowers/plans/*.md` |
| Item (当前功能拆解) | `docs/superpowers/items/*.md` |
| Toolchain | `.harness/*toolchain*.md`（含 `## Walkthrough` 段落） |
| Git 状态 | `git status --short && git log --oneline -3` |

**确定当前功能点**：找到 items 文档中第一个状态非 `完成` 的 F-N，打印：
```
当前功能: F-N: <名称> (状态: <待开始/进行中>)
```

## Step 2: 质量门禁

4 道检查，**全部必须通过**：

```bash
# 1. Lint
uv run ruff check .

# 2. Format
uv run ruff format --check .

# 3. Type check
uv run mypy question_agent/

# 4. 单元 + 集成测试（确保服务已启动在 localhost:8000）
uv run pytest -v
```

全部通过 → Step 3。
任一失败 → Step 5（失败处理）。

## Step 3: 边缘情况主动测试

质量门禁通过后，**Runner 必须主动分析当前已实现功能，自行编写边缘情况测试**，而不是仅依赖文档中列出的验证项。

### 3a. 分析攻击面

对当前已实现的所有端点/模块，按以下维度逐一审视：

| 维度 | 思考方向 |
|------|---------|
| 输入边界 | 空值、超长字符串、特殊字符（Unicode/emoji/零宽字符）、二进制数据伪装成文本 |
| MIME/类型欺骗 | Content-Type 与文件内容不一致、无扩展名、伪造扩展名 |
| 并发 | 同一端点并发请求、上传同名文件 |
| 编码 | 非 UTF-8 编码（GBK/Shift-JIS/Latin-1）、BOM 头、混合编码 |
| 大小 | 0 字节、1 字节、刚好等于上限、上限+1 字节 |
| HTTP 方法 | 用 GET/PUT/DELETE 调 POST 端点、OPTIONS/HEAD |
| Header | 缺失 Content-Type、畸形 multipart、超大 header |
| 资源耗尽 | 慢速上传（slowloris 式）、嵌套 ZIP bomb 式压缩文件（如适用） |

### 3b. 编写边缘测试

针对发现的每个潜在漏洞/边界，写一个最小化测试放入 `tests/`，命名 `test_edge_<描述>.py`。

测试必须：
- 能独立运行：`uv run pytest tests/test_edge_<描述>.py -v`
- 有明确的预期行为（200/422/413/...），不假设实现细节
- 优先关注**可能导致 500 或服务崩溃**的场景

### 3c. 跑新测试

```bash
uv run pytest tests/test_edge_*.py -v
```

- 全部通过 → Step 6（启动系统 + 功能走查）
- 任一失败 → Step 4（生成边缘失败报告）→ Step 5（失败处理）

## Step 4: 边缘失败报告

如果边缘测试发现**新问题**（非已有测试覆盖的失败），生成报告：

写到 `.harness/reports/edge-failure-$(date +%Y%m%d-%H%M%S).md`：

```markdown
# Edge Case Failure Report — <timestamp>

## Edge Test
<test file path>

## Test Scenario
<what edge case was being tested>

## Failure
<exact error output / stack trace>

## Severity
<critical: 导致 500/崩溃 | high: 行为不符合预期 | low: 边界模糊>

## Root Cause
<1-2 sentences>

## Fix Strategy
<1 sentence>
```

然后进入 Step 5。

## Step 5: 失败处理

### 5a. 写复现测试

为每个失败场景写一个最小化回归测试，放到 `tests/` 下。测试必须在修复前失败、修复后通过。

（Step 3/4 中新发现的边缘问题已经生成了测试，若为已有测试失败，则需额外写回归测试。）

### 5b. 生成分析报告

写到 `.harness/reports/failure-$(date +%Y%m%d-%H%M%S).md`：

```markdown
# Failure Report — <timestamp>

## Failed Check
<ruff|mypy|pytest|edge-case|walkthrough>

## Error
<exact error output>

## Root Cause
<1-2 sentences>

## Regression Test
<test file path>

## Fix Strategy
<1 sentence>
```

### 5c. 调用 autopilot 修复

将失败报告和回归测试路径传给 `/autopilot`，令其修复。修复后回到 Step 2。

**上限：** 最多循环 5 次。同一错误出现 3 次 → 停止并报告根本性问题。

**走查失败的特殊路径：** 走查失败修复后，先过 Step 2（质量门禁）→ Step 3 → Step 6（重新走查），确保修复没有引入新的静态问题。

## Step 6: 启动系统 + 功能走查

**这是最后一道门禁。** 走查不通过不 commit。

### 6a. 启动系统

从 toolchain 文档 `## Walkthrough` 段落读取启动配置：

| 配置项 | 用途 |
|--------|------|
| Start Command | 后台启动 dev server |
| Health Check | 轮询确认 server 就绪 |
| Shutdown Signal | 关停 server |
| Port | 端口检测 |

**启动流程**：

1. 检查端口是否已被占用（向 Health Check 端点发请求）
   - 已占用 → 询问用户是否复用已有实例，还是关停后重启
   - 空闲 → 继续
2. 后台启动 dev server（`Start Command`）
3. 轮询 Health Check 端点，每 2 秒一次，最长等待 30 秒
   - 就绪 → 继续
   - 超时 → 报告启动失败，进入 Step 5

### 6b. 分析端点 + 补写走查测试

与 Step 3（主动写边缘测试）同样的模式——缺测试就写，不跳过：

1. 分析代码中已注册的所有端点/功能入口
2. 对比 `tests/integration/` 中已有的走查测试
3. 缺失走查测试的端点 → **必须主动编写**对应的走查测试
4. 编写后运行确认新测试可执行

### 6c. 运行功能走查

```bash
uv run pytest tests/integration/ -v
```

- 全部通过 → Step 6d（关停 server），然后 Step 7（功能验证）
- 任一失败 → Step 6d（关停 server），然后 Step 5（失败处理）

### 6d. 关停系统

走查完成后（无论成功失败），向 server 进程发 SIGTERM。如果进程 5 秒内未退出，发 SIGKILL 强杀。

## Step 7: 功能验证

质量门禁 + 边缘测试 + 功能走查全绿后：

1. 对照当前 item 的验证标准逐条检查
2. 系统行为不满足验证标准 → 标记阻塞，输出原因，停止
3. 全部满足 → 更新 item 文档：`- [x] **状态:** 完成`；同步更新 roadmap 中对应 checkbox

## Step 8: 生成 Commit 并提交

```bash
git diff --stat
git diff
```

生成 conventional commit message：

```
<type>(<scope>): <subject>

<body>

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
```

Type: `feat` / `fix` / `refactor` / `test` / `chore`
Scope: roadmap 中的功能域名（如 `教材知识抽取`）

执行提交：
```bash
git add <改动的具体文件>
git commit -m "$(cat <<'EOF'
<commit message>
EOF
)"
```

打印：`Committed: <hash> — <subject>`

## Step 9: 下一步提示

扫描 roadmap 下一个 `[ ]` 叶子节点，提示：
```
下一个功能点: <名称>
→ /progressive-plan 拆解 或 /run 继续
```

## 关键约束

- **不跳过检查**：任何一道门禁失败都必须进入 Step 5
- **必须主动写边缘测试**：Step 3 不可跳过，Runner 必须产出至少 1 个边缘测试文件
- **必须主动写走查测试**：Step 6b 不可跳过，缺失走查测试必须补写
- **功能走查是最终门禁**：Step 6 不通过不 commit
- **修复后先过质量门禁**：走查失败修复后必须先过 Step 2，再重新走查
- **server 必须关停**：Step 6d 无论成功失败都关停，不留残留进程
- **不改需求**：修复只针对代码，不修改 spec/roadmap/item 中的功能定义
- **失败上限**：Step 2→5→2 循环最多 5 次；同一错误 3 次即停止
- **必须先读上下文再跑门禁**：不能跳过 Step 1
```

- [ ] **Step 2: Verify the file is syntactically valid markdown**

Run: `head -5 .claude/skills/run/SKILL.md && echo "---" && grep -c "^## Step" .claude/skills/run/SKILL.md`
Expected: Frontmatter visible, 9 Step headings found.

- [ ] **Step 3: Commit**

```bash
git add .claude/skills/run/SKILL.md
git commit -m "refactor(run-skill): add Step 6 walkthrough gate, renumber steps, update flow"
```

---

### Task 7: Update CLAUDE.md

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 1: Add integration test commands**

In the `## Commands` section, add after the existing `# Dev server` line:

```bash
# Integration tests only (requires running server)
uv run pytest tests/integration/ -v

# Unit tests only (no server needed)
uv run pytest --ignore=tests/integration/ -v
```

Also update the `## Testing` section. Replace the first bullet:

```
- Tests hit a running server at `http://localhost:8000` — start the dev server first (`uv run question-agent`), then run `uv run pytest` in another terminal.
```

With:

```
- Unit tests use in-process ASGI transport (no running server needed). Integration tests in `tests/integration/` require a running server at `http://localhost:8000`.
```

- [ ] **Step 2: Verify the edit**

Run: `grep -A2 'Integration tests' CLAUDE.md`
Expected: The new integration test command visible.

- [ ] **Step 3: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: add integration test commands to CLAUDE.md"
```

---

### Task 8: Update progressive-plan SKILL.md

**Files:**
- Modify: `.claude/skills/progressive-plan/SKILL.md`

- [ ] **Step 1: Add walkthrough test mention to verification specs**

Find the section under `**Constraints:**` that describes verification specs. Add after the line about verification specs being behavior descriptions:

```
- Each 交付 item's verification specs should include a walkthrough test expectation: "tests/integration/test_walkthrough.py covers POST /endpoint" or similar. The run skill will enforce this in Step 6b.
```

- [ ] **Step 2: Verify the edit**

Run: `grep -n 'walkthrough' .claude/skills/progressive-plan/SKILL.md`
Expected: At least one line mentioning walkthrough tests.

- [ ] **Step 3: Commit**

```bash
git add .claude/skills/progressive-plan/SKILL.md
git commit -m "docs(progressive-plan): add walkthrough test expectation to constraints"
```

---

### Task 9: Update scaffold SKILL.md

**Files:**
- Modify: `.claude/skills/scaffold/SKILL.md`

- [ ] **Step 1: Add integration test infrastructure to Phase 2 assessment**

In Phase 2, after the existing `ls tests/conftest.py` check, add:

```bash
# Integration test infrastructure
ls tests/integration/ 2>/dev/null && echo "EXISTS" || echo "MISSING"
ls tests/integration/conftest.py 2>/dev/null && echo "EXISTS" || echo "MISSING"
```

- [ ] **Step 2: Add integration test scaffolding to Phase 5 example plan**

In Phase 5, add an example plan item after the existing conftest.py item:

```
5. 创建 tests/integration/conftest.py — 集成测试 fixtures（live server client, base_url, reachability check）
6. 创建 tests/integration/fixtures/ — 集成测试 fixture 文件目录
```

- [ ] **Step 3: Add integration test collection to Phase 8 verification**

In Phase 8, after the existing `uv run pytest --collect-only` check, add:

```bash
uv run pytest tests/integration/ --co -q 2>&1
```

With note: "Integration test collection confirms the infrastructure is set up (tests may skip if server not running)."

- [ ] **Step 4: Verify edits**

Run: `grep -n 'integration' .claude/skills/scaffold/SKILL.md`
Expected: At least 3 lines mentioning integration test infrastructure.

- [ ] **Step 5: Commit**

```bash
git add .claude/skills/scaffold/SKILL.md
git commit -m "docs(scaffold): add integration test infrastructure to assessment, plan, and verification"
```

---

### Task 10: Run full verification

- [ ] **Step 1: Run lint**

Run: `uv run ruff check .`
Expected: PASS.

- [ ] **Step 2: Run format check**

Run: `uv run ruff format --check .`
Expected: PASS.

- [ ] **Step 3: Run type check**

Run: `uv run mypy question_agent/`
Expected: PASS.

- [ ] **Step 4: Run unit tests**

Run: `uv run pytest --ignore=tests/integration/ -v`
Expected: All existing tests PASS.

- [ ] **Step 5: Run integration test collection**

Run: `uv run pytest tests/integration/ --co -q`
Expected: 7 tests collected, no errors.

- [ ] **Step 6: If all pass, final commit if any remaining changes**

```bash
git status --short
```

If clean, no commit needed. If uncommitted changes exist, commit them.
