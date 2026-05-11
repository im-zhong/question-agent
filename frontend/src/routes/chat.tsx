import { createFileRoute } from '@tanstack/react-router';
import { useCallback, useRef, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Button } from '@/components/ui/button';
import { SendHorizonal } from 'lucide-react';

export const Route = createFileRoute('/chat')({
  component: ChatPage,
});

interface ChatMessage {
  id: number;
  role: 'user' | 'assistant';
  content: string;
}

const MOCK_REPLIES = [
  '你好！我是智能出题助手。请上传教材文件，我会帮你提取知识点并生成题目。',
  '好的，我来分析一下这份教材的知识点结构。',
  '已提取 **3 个核心知识点**：\n\n1. 牛顿第二定律\n2. 加速度的定义\n3. 力的合成与分解\n\n需要我基于这些知识点生成题目吗？',
  '已生成 **5 道选择题**，覆盖上述知识点。你可以查看并选择需要的题目。',

  '```python\ndef hello():\n    print("Hello, World!")\n```\n\n这是一个代码示例。',
];

let nextId = 1;

function ChatPage() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const sendMessage = useCallback(() => {
    const text = input.trim();
    if (!text || isTyping) return;

    const userMsg: ChatMessage = { id: nextId++, role: 'user', content: text };
    setMessages((prev) => [...prev, userMsg]);
    setInput('');
    setIsTyping(true);

    setTimeout(() => {
      const reply = MOCK_REPLIES[Math.floor(Math.random() * MOCK_REPLIES.length)] ?? '好的，我了解了。';
      const assistantMsg: ChatMessage = { id: nextId++, role: 'assistant', content: reply };
      setMessages((prev) => [...prev, assistantMsg]);
      setIsTyping(false);
    }, 600);
  }, [input, isTyping]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
      }
    },
    [sendMessage],
  );

  return (
    <div className="flex h-full flex-col">
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
          {isTyping && (
            <div className="mb-4 flex gap-3">
              <div className="flex size-8 shrink-0 items-center justify-center rounded-full bg-primary text-xs font-medium text-primary-foreground">
                AI
              </div>
              <div className="rounded-2xl bg-muted px-4 py-2.5 text-sm text-muted-foreground">
                <span className="inline-block animate-pulse">正在输入...</span>
              </div>
            </div>
          )}
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
            placeholder="输入消息... (Enter 发送, Shift+Enter 换行)"
            aria-label="消息输入"
            rows={1}
            className="max-h-32 min-h-[2.5rem] flex-1 resize-none rounded-lg border border-input bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"
          />
          <Button
            size="icon"
            onClick={sendMessage}
            disabled={!input.trim() || isTyping}
            aria-label="发送"
          >
            <SendHorizonal className="size-4" />
          </Button>
        </div>
      </div>
    </div>
  );
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
