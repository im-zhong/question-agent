import { createFileRoute } from '@tanstack/react-router';
import { useCallback, useEffect, useRef, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Button } from '@/components/ui/button';
import { useWebSocket, type ConnectionStatus } from '@/hooks/use-websocket';
import { useChat, createMessageId } from '@/lib/chat-context';
import type { ChatMessage } from '@/lib/chat-context';
import { SendHorizonal, Wifi, WifiOff, Loader2, RefreshCw } from 'lucide-react';

export const Route = createFileRoute('/chat')({
  component: ChatPage,
});

const WS_URL = `ws://localhost:8000/ws/chat`;

function ChatPage() {
  const {
    activeConversation,
    activeId,
    addMessage,
    appendToMessage,
    createConversation,
    streamingMessageId,
    setStreamingMessageId,
  } = useChat();
  const [input, setInput] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const streamingMsgIdRef = useRef<number | null>(null);

  // Auto-scroll on new content
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [activeConversation?.messages, streamingMessageId]);

  const handleWebSocketMessage = useCallback(
    (data: { type: string; content?: string }) => {
      if (!activeId) return;

      if (data.type === 'start') {
        const id = createMessageId();
        streamingMsgIdRef.current = id;
        setStreamingMessageId(id);
        const msg: ChatMessage = { id, role: 'assistant', content: '' };
        addMessage(activeId, msg);
      } else if (data.type === 'token' && streamingMsgIdRef.current !== null && data.content) {
        appendToMessage(activeId, streamingMsgIdRef.current, data.content);
      } else if (data.type === 'end') {
        streamingMsgIdRef.current = null;
        setStreamingMessageId(null);
      }
    },
    [activeId, addMessage, appendToMessage, setStreamingMessageId],
  );

  const { status, send, connect } = useWebSocket({
    url: WS_URL,
    onMessage: handleWebSocketMessage,
  });

  const sendMessage = useCallback(() => {
    const text = input.trim();
    if (!text || status !== 'connected') return;

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
        {status === 'disconnected' && (
          <Button variant="ghost" size="sm" className="ml-auto h-6 gap-1 text-xs" onClick={connect}>
            <RefreshCw className="size-3" />
            重新连接
          </Button>
        )}
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto">
        <div className="mx-auto max-w-3xl px-4 py-6">
          {messages.length === 0 && (
            <div className="flex flex-col items-center justify-center py-20 text-muted-foreground">
              <div className="mb-3 text-2xl">💬</div>
              <p className="text-sm">上传教材或输入问题开始对话</p>
            </div>
          )}
          {messages.map((msg) => (
            <MessageBubble key={msg.id} message={msg} isStreaming={msg.id === streamingMessageId} />
          ))}
          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Input */}
      <div className="border-t border-border bg-background px-4 py-3">
        <div className="mx-auto flex max-w-3xl items-end gap-2 rounded-xl border border-input bg-background px-3 py-2 shadow-sm focus-within:ring-2 focus-within:ring-ring">
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
            className="max-h-32 min-h-[2.5rem] flex-1 resize-none bg-transparent text-sm placeholder:text-muted-foreground focus:outline-none disabled:opacity-50"
          />
          <Button
            size="icon"
            onClick={sendMessage}
            disabled={!input.trim() || status !== 'connected'}
            aria-label="发送"
            className="size-8 shrink-0 rounded-lg"
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

function MessageBubble({ message, isStreaming }: { message: ChatMessage; isStreaming: boolean }) {
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
        ) : message.content ? (
          <div className="prose prose-sm max-w-none break-words dark:prose-invert [&_pre]:rounded-md [&_pre]:bg-background [&_pre]:p-3 [&_code]:text-xs">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content}</ReactMarkdown>
            {isStreaming && <span className="inline-block w-0.5 animate-pulse bg-foreground" />}
          </div>
        ) : (
          <span className="inline-block animate-pulse text-muted-foreground">正在输入...</span>
        )}
      </div>
    </div>
  );
}
