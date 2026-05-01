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
