"""Edge case tests for chat layout — verify build pipeline and route structure."""

import subprocess
from pathlib import Path

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"


class TestFrontendBuildPipeline:
    """Verify frontend build still succeeds after chat layout changes."""

    def test_typescript_compiles(self) -> None:
        result = subprocess.run(
            ["npx", "tsc", "-b"],
            cwd=FRONTEND_DIR,
            capture_output=True,
            text=True,
            timeout=60,
        )
        assert result.returncode == 0, f"TypeScript errors:\n{result.stdout}\n{result.stderr}"

    def test_vite_build_succeeds(self) -> None:
        result = subprocess.run(
            ["npm", "run", "build"],
            cwd=FRONTEND_DIR,
            capture_output=True,
            text=True,
            timeout=60,
        )
        assert result.returncode == 0, f"Vite build failed:\n{result.stdout}\n{result.stderr}"

    def test_chat_route_file_exists(self) -> None:
        assert (FRONTEND_DIR / "src" / "routes" / "chat.tsx").exists()

    def test_upload_route_file_exists(self) -> None:
        assert (FRONTEND_DIR / "src" / "routes" / "upload.tsx").exists()

    def test_sidebar_component_exists(self) -> None:
        assert (FRONTEND_DIR / "src" / "components" / "chat-sidebar.tsx").exists()

    def test_index_redirects_to_chat(self) -> None:
        content = (FRONTEND_DIR / "src" / "routes" / "index.tsx").read_text()
        assert "/chat" in content, "index.tsx should redirect to /chat"

    def test_upload_route_uses_upload_path(self) -> None:
        content = (FRONTEND_DIR / "src" / "routes" / "upload.tsx").read_text()
        assert "/upload" in content, "upload.tsx should use /upload route path"


class TestChatSidebarAccessibility:
    """Verify chat sidebar has proper accessibility attributes."""

    def test_sidebar_toggle_has_aria_label(self) -> None:
        content = (FRONTEND_DIR / "src" / "routes" / "__root.tsx").read_text()
        assert "aria-label" in content, "Toggle button should have aria-label"

    def test_conversation_buttons_have_aria_current(self) -> None:
        content = (FRONTEND_DIR / "src" / "components" / "chat-sidebar.tsx").read_text()
        assert "aria-current" in content, "Active conversation should have aria-current"

    def test_chat_input_has_aria_label(self) -> None:
        content = (FRONTEND_DIR / "src" / "routes" / "chat.tsx").read_text()
        assert 'aria-label="消息输入"' in content, "Chat input should have aria-label"

    def test_send_button_has_aria_label(self) -> None:
        content = (FRONTEND_DIR / "src" / "routes" / "chat.tsx").read_text()
        assert 'aria-label="发送"' in content, "Send button should have aria-label"


class TestChatMessageRendering:
    """Verify chat message components exist and use correct patterns."""

    def test_uses_textarea_not_input(self) -> None:
        content = (FRONTEND_DIR / "src" / "routes" / "chat.tsx").read_text()
        assert "<textarea" in content, "Chat input should use textarea for multiline"

    def test_has_markdown_rendering(self) -> None:
        content = (FRONTEND_DIR / "src" / "routes" / "chat.tsx").read_text()
        assert "ReactMarkdown" in content, "Assistant messages should render markdown"

    def test_uses_websocket_for_messaging(self) -> None:
        content = (FRONTEND_DIR / "src" / "routes" / "chat.tsx").read_text()
        assert "useWebSocket" in content, "Should use WebSocket hook for messaging"
        assert "send" in content, "Should call send via WebSocket"

    def test_has_connection_status(self) -> None:
        content = (FRONTEND_DIR / "src" / "routes" / "chat.tsx").read_text()
        assert "ConnectionStatus" in content, "Should show connection status"
        assert "已连接" in content, "Should have connected label"
        assert "未连接" in content, "Should have disconnected label"

    def test_enter_sends_shift_enter_newline(self) -> None:
        content = (FRONTEND_DIR / "src" / "routes" / "chat.tsx").read_text()
        assert "Shift" in content, "Should handle Shift+Enter for newline"
        assert "Enter" in content, "Should handle Enter for send"

    def test_message_roles(self) -> None:
        content = (FRONTEND_DIR / "src" / "routes" / "chat.tsx").read_text()
        assert "'user'" in content, "Should have user message role"
        assert "'assistant'" in content, "Should have assistant message role"

    def test_react_markdown_installed(self) -> None:
        pkg = (FRONTEND_DIR / "package.json").read_text()
        assert "react-markdown" in pkg, "react-markdown should be in dependencies"

    def test_websocket_hook_exists(self) -> None:
        assert (FRONTEND_DIR / "src" / "hooks" / "use-websocket.ts").exists()

    def test_websocket_hook_exports_status(self) -> None:
        content = (FRONTEND_DIR / "src" / "hooks" / "use-websocket.ts").read_text()
        assert "ConnectionStatus" in content, "Hook should export ConnectionStatus type"
        assert "send" in content, "Hook should return send function"


class TestWebSocketBackendEndpoint:
    """Verify backend WebSocket endpoint exists and is properly defined."""

    def test_ws_endpoint_in_main(self) -> None:
        content = (Path(__file__).resolve().parent.parent / "question_agent" / "main.py").read_text()
        assert "/ws/chat" in content, "Backend should have /ws/chat WebSocket endpoint"
        assert "WebSocket" in content, "Should import WebSocket from FastAPI"
        assert "websocket.accept" in content, "Should accept WebSocket connections"
        assert "websocket.receive_json" in content, "Should receive JSON messages"
        assert "websocket.send_json" in content, "Should send JSON messages"
