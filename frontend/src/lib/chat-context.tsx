import { createContext, useCallback, useContext, useState, type ReactNode } from 'react';

export interface ChatMessage {
  id: number;
  role: 'user' | 'assistant';
  content: string;
}

export interface Conversation {
  id: string;
  title: string;
  messages: ChatMessage[];
}

interface ChatState {
  conversations: Conversation[];
  activeId: string | null;
  activeConversation: Conversation | null;
  streamingMessageId: number | null;
  createConversation: () => string;
  selectConversation: (id: string) => void;
  addMessage: (conversationId: string, message: ChatMessage) => void;
  appendToMessage: (conversationId: string, messageId: number, token: string) => void;
  setStreamingMessageId: (id: number | null) => void;
}

const ChatContext = createContext<ChatState | null>(null);

let nextMsgId = 1;
let nextConvId = 1;

export function ChatProvider({ children }: { children: ReactNode }) {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [streamingMessageId, setStreamingMessageId] = useState<number | null>(null);

  const createConversation = useCallback(() => {
    const id = String(nextConvId++);
    const conv: Conversation = { id, title: `新对话`, messages: [] };
    setConversations((prev) => [conv, ...prev]);
    setActiveId(id);
    return id;
  }, []);

  const selectConversation = useCallback((id: string) => {
    setActiveId(id);
  }, []);

  const addMessage = useCallback((conversationId: string, message: ChatMessage) => {
    setConversations((prev) =>
      prev.map((c) => {
        if (c.id !== conversationId) return c;
        const updated = { ...c, messages: [...c.messages, message] };
        // Auto-title: use first user message as title
        if (c.messages.length === 0 && message.role === 'user') {
          updated.title = message.content.slice(0, 20) + (message.content.length > 20 ? '...' : '');
        }
        return updated;
      }),
    );
  }, []);

  const appendToMessage = useCallback(
    (conversationId: string, messageId: number, token: string) => {
      setConversations((prev) =>
        prev.map((c) => {
          if (c.id !== conversationId) return c;
          return {
            ...c,
            messages: c.messages.map((m) =>
              m.id === messageId ? { ...m, content: m.content + token } : m,
            ),
          };
        }),
      );
    },
    [],
  );

  const activeConversation = conversations.find((c) => c.id === activeId) ?? null;

  return (
    <ChatContext.Provider
      value={{
        conversations,
        activeId,
        activeConversation,
        streamingMessageId,
        createConversation,
        selectConversation,
        addMessage,
        appendToMessage,
        setStreamingMessageId,
      }}
    >
      {children}
    </ChatContext.Provider>
  );
}

export function useChat(): ChatState {
  const ctx = useContext(ChatContext);
  if (!ctx) throw new Error('useChat must be used within ChatProvider');
  return ctx;
}

export { nextMsgId as _nextMsgId };

export function createMessageId(): number {
  return nextMsgId++;
}

export function createConversationId(): string {
  return String(nextConvId++);
}
