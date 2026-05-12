import { createFileRoute } from '@tanstack/react-router';
import { useCallback, useEffect, useRef, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Button } from '@/components/ui/button';
import {
  KnowledgePointsList,
  QuestionsList,
  type KnowledgePoint,
  type Question,
} from '@/components/chat-cards';
import { useWebSocket, type ConnectionStatus } from '@/hooks/use-websocket';
import { useChat, createMessageId } from '@/lib/chat-context';
import type { ChatMessage } from '@/lib/chat-context';
import { SendHorizonal, Wifi, WifiOff, Loader2, RefreshCw, Database } from 'lucide-react';

interface KbOption {
  id: string;
  name: string;
}

export const Route = createFileRoute('/chat')({
  component: ChatPage,
});

function wsBaseUrl(): string {
  return `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/ws/chat`;
}

function ChatPage() {
  const {
    activeConversation,
    activeId,
    addMessage,
    appendToMessage,
    addStructuredData,
    createConversation,
    streamingMessageId,
    setStreamingMessageId,
    loadHistoryMessages,
  } = useChat();
  const [input, setInput] = useState('');
  const [kbList, setKbList] = useState<KbOption[]>([]);
  const [selectedKbId, setSelectedKbId] = useState<string>('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const streamingMsgIdRef = useRef<number | null>(null);

  // Build WS URL with conversation_id
  const wsUrl = activeId ? `${wsBaseUrl()}?conversation_id=${encodeURIComponent(activeId)}` : wsBaseUrl();

  const handleWebSocketMessage = useCallback(
    (data: {
      type: string;
      content?: string;
      tool?: string;
      conversation_id?: string;
      messages?: { role: string; content: string }[];
    }) => {
      if (!activeId) return;

      if (data.type === 'history' && data.messages) {
        const historyMsgs: ChatMessage[] = data.messages.map((m, i) => ({
          id: -(i + 1),
          role: m.role === 'user' ? ('user' as const) : ('assistant' as const),
          content: m.content,
        }));
        loadHistoryMessages(activeId, historyMsgs);
      } else if (data.type === 'start') {
        const id = createMessageId();
        streamingMsgIdRef.current = id;
        setStreamingMessageId(id);
        const msg: ChatMessage = { id, role: 'assistant', content: '' };
        addMessage(activeId, msg);
      } else if (data.type === 'data' && streamingMsgIdRef.current !== null && data.tool && data.content) {
        addStructuredData(activeId, streamingMsgIdRef.current, {
          tool: data.tool as 'extract_knowledge_points' | 'generate_questions',
          content: data.content,
        });
      } else if (data.type === 'token' && streamingMsgIdRef.current !== null && data.content) {
        appendToMessage(activeId, streamingMsgIdRef.current, data.content);
      } else if (data.type === 'end') {
        streamingMsgIdRef.current = null;
        setStreamingMessageId(null);
      }
    },
    [activeId, addMessage, addStructuredData, appendToMessage, setStreamingMessageId, loadHistoryMessages],
  );

  const { status, send, connect } = useWebSocket({
    url: wsUrl,
    onMessage: handleWebSocketMessage,
  });

  // Auto-scroll on new content
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [activeConversation?.messages, streamingMessageId]);

  // Fetch knowledge base list on mount
  useEffect(() => {
    fetch('/api/v1/knowledge-bases')
      .then((res) => (res.ok ? res.json() : []))
      .then((data: KbOption[]) => setKbList(data))
      .catch(() => setKbList([]));
  }, []);

  const sendMessage = useCallback(() => {
    const text = input.trim();
    if (!text || status !== 'connected') return;

    const convId = activeId ?? createConversation();
    const userMsg: ChatMessage = { id: createMessageId(), role: 'user', content: text };
    addMessage(convId, userMsg);
    send({ type: 'message', content: text, ...(selectedKbId ? { kb_id: selectedKbId } : {}) });
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
        {kbList.length > 0 && (
          <div className="mx-auto mb-2 flex max-w-3xl items-center gap-2">
            <Database className="size-3.5 text-muted-foreground" />
            <select
              value={selectedKbId}
              onChange={(e) => setSelectedKbId(e.target.value)}
              className="rounded-md border border-input bg-background px-2 py-1 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-ring"
            >
              <option value="">未选择知识库</option>
              {kbList.map((kb) => (
                <option key={kb.id} value={kb.id}>{kb.name}</option>
              ))}
            </select>
            {selectedKbId && (
              <button
                onClick={() => setSelectedKbId('')}
                className="text-xs text-muted-foreground hover:text-foreground"
              >
                清除
              </button>
            )}
          </div>
        )}
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

  // Parse structured data sections
  const structuredSections: React.ReactNode[] = [];
  if (message.structuredData) {
    for (const sd of message.structuredData) {
      try {
        if (sd.tool === 'extract_knowledge_points') {
          const points: KnowledgePoint[] = JSON.parse(sd.content);
          if (points.length > 0) {
            structuredSections.push(<KnowledgePointsList key={`kp-${points.length}`} points={points} />);
          }
        } else if (sd.tool === 'generate_questions') {
          const parsed = JSON.parse(sd.content);
          const questions: Question[] = parsed.questions ?? [];
          if (questions.length > 0) {
            structuredSections.push(<QuestionsList key={`q-${questions.length}`} questions={questions} />);
          }
        }
      } catch {
        // Skip invalid JSON
      }
    }
  }

  const hasStructuredData = structuredSections.length > 0;

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
        ) : message.content || hasStructuredData ? (
          <>
            {message.content && (
              <div className="prose prose-sm max-w-none break-words dark:prose-invert [&_pre]:rounded-md [&_pre]:bg-background [&_pre]:p-3 [&_code]:text-xs">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content}</ReactMarkdown>
                {isStreaming && <span className="inline-block w-0.5 animate-pulse bg-foreground" />}
              </div>
            )}
            {structuredSections}
            {isStreaming && !message.content && !hasStructuredData && (
              <span className="inline-block animate-pulse text-muted-foreground">正在输入...</span>
            )}
          </>
        ) : (
          <span className="inline-block animate-pulse text-muted-foreground">正在输入...</span>
        )}
      </div>
    </div>
  );
}
