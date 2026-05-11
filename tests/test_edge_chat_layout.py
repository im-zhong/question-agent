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

    def test_has_mock_reply_logic(self) -> None:
        content = (FRONTEND_DIR / "src" / "routes" / "chat.tsx").read_text()
        assert "MOCK_REPLIES" in content, "Should have mock reply data"
        assert "setTimeout" in content, "Should delay mock reply"

    def test_has_typing_indicator(self) -> None:
        content = (FRONTEND_DIR / "src" / "routes" / "chat.tsx").read_text()
        assert "isTyping" in content, "Should have typing indicator state"
        assert "正在输入" in content, "Should show typing indicator text"

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
