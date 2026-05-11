import { createFileRoute } from '@tanstack/react-router';

export const Route = createFileRoute('/chat')({
  component: ChatPage,
});

function ChatPage() {
  return (
    <div className="flex h-full flex-col">
      {/* Messages area */}
      <div className="flex-1 overflow-y-auto">
        <div className="mx-auto flex max-w-3xl flex-col gap-4 px-4 py-6">
          <div className="flex justify-center py-12 text-sm text-muted-foreground">
            上传教材或输入问题开始对话
          </div>
        </div>
      </div>

      {/* Input area */}
      <div className="border-t border-border px-4 py-3">
        <div className="mx-auto flex max-w-3xl gap-2">
          <input
            type="text"
            placeholder="输入消息..."
            aria-label="消息输入"
            className="flex-1 rounded-md border border-input bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"
          />
          <button
            className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90"
            aria-label="发送"
          >
            发送
          </button>
        </div>
      </div>
    </div>
  );
}
