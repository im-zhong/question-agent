import { createFileRoute } from '@tanstack/react-router';
import { useCallback, useRef, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Button } from '@/components/ui/button';
import { useWebSocket, type ConnectionStatus } from '@/hooks/use-websocket';
import { useChat, createMessageId } from '@/lib/chat-context';
import type { ChatMessage } from '@/lib/chat-context';
import { SendHorizonal, Wifi, WifiOff, Loader2 } from 'lucide-react';

export const Route = createFileRoute('/chat')({
  component: ChatPage,
});

const WS_URL = `ws://localhost:8000/ws/chat`;

function ChatPage() {
  const { activeConversation, activeId, addMessage, createConversation } = useChat();
  const [input, setInput] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const handleWebSocketMessage = useCallback(
    (data: { type: string; content: string }) => {
      if (data.type === 'message' && activeId) {
        const assistantMsg: ChatMessage = { id: createMessageId(), role: 'assistant', content: data.content };
        addMessage(activeId, assistantMsg);
      }
    },
    [activeId, addMessage],
  );

  const { status, send } = useWebSocket({
    url: WS_URL,
    onMessage: handleWebSocketMessage,
  });

  const sendMessage = useCallback(() => {
    const text = input.trim();
    if (!text || status !== 'connected') return;

    // Create conversation if none active
    const convId = activeId ?? createConversation();
    const userMsg: ChatMessage = { id: createMessageId(), role: 'user', content: text };
    addMessage(convId, userMsg);
    send({ type: 'message', content: text });
    setInput('');
  }, [input, status, activeId, createConversation, addMessage, send]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
      }
    },
    [sendMessage],
  );

  const messages = activeConversation?.messages ?? [];

  return (
    <div className="flex h-full flex-col">
      {/* Connection status */}
      <div className="flex items-center gap-1.5 border-b border-border px-4 py-1.5 text-xs text-muted-foreground">
        <ConnectionIcon status={status} />
        <span>{statusLabel(status)}</span>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto">
        <div className="mx-auto max-w-3xl px-4 py-6">
          {messages.length === 0 && (
            <div className="flex justify-center py-12 text-sm text-muted-foreground">
              上传教材或输入问题开始对话
            </div>
          )}
          {messages.map((msg) => (
            <MessageBubble key={msg.id} message={msg} />
          ))}
          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Input */}
      <div className="border-t border-border px-4 py-3">
        <div className="mx-auto flex max-w-3xl items-end gap-2">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={
              status === 'connected'
                ? '输入消息... (Enter 发送, Shift+Enter 换行)'
                : '等待连接...'
            }
            aria-label="消息输入"
            rows={1}
            disabled={status !== 'connected'}
            className="max-h-32 min-h-[2.5rem] flex-1 resize-none rounded-lg border border-input bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring disabled:opacity-50"
          />
          <Button
            size="icon"
            onClick={sendMessage}
            disabled={!input.trim() || status !== 'connected'}
            aria-label="发送"
          >
            <SendHorizonal className="size-4" />
          </Button>
        </div>
      </div>
    </div>
  );
}

function ConnectionIcon({ status }: { status: ConnectionStatus }) {
  if (status === 'connected') return <Wifi className="size-3 text-green-500" />;
  if (status === 'connecting') return <Loader2 className="size-3 animate-spin text-yellow-500" />;
  return <WifiOff className="size-3 text-red-500" />;
}

function statusLabel(status: ConnectionStatus): string {
  if (status === 'connected') return '已连接';
  if (status === 'connecting') return '连接中...';
  return '未连接';
}

function MessageBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === 'user';

  return (
    <div className={`mb-4 flex gap-3 ${isUser ? 'flex-row-reverse' : ''}`}>
      <div
        className={`flex size-8 shrink-0 items-center justify-center rounded-full text-xs font-medium ${
          isUser
            ? 'bg-primary text-primary-foreground'
            : 'bg-muted text-muted-foreground'
        }`}
      >
        {isUser ? '你' : 'AI'}
      </div>
      <div
        className={`max-w-[80%] rounded-2xl px-4 py-2.5 text-sm ${
          isUser
            ? 'bg-primary text-primary-foreground'
            : 'bg-muted text-foreground'
        }`}
      >
        {isUser ? (
          <p className="whitespace-pre-wrap break-words">{message.content}</p>
        ) : (
          <div className="prose prose-sm max-w-none break-words dark:prose-invert [&_pre]:rounded-md [&_pre]:bg-background [&_pre]:p-3 [&_code]:text-xs">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content}</ReactMarkdown>
          </div>
        )}
      </div>
    </div>
  );
}
