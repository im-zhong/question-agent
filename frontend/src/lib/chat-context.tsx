import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from 'react';

export interface StructuredData {
  tool: 'extract_knowledge_points' | 'generate_questions';
  content: string; // JSON string of tool result
}

export interface ChatMessage {
  id: number;
  role: 'user' | 'assistant';
  content: string;
  structuredData?: StructuredData[];
}

export interface Conversation {
  id: string;
  title: string;
  messages: ChatMessage[];
}

interface ConversationMeta {
  id: string;
  title: string;
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
  addStructuredData: (conversationId: string, messageId: number, data: StructuredData) => void;
  setStreamingMessageId: (id: number | null) => void;
  loadHistoryMessages: (conversationId: string, messages: ChatMessage[]) => void;
}

const ChatContext = createContext<ChatState | null>(null);

const STORAGE_KEY = 'chat-conversations';
const ACTIVE_KEY = 'chat-active-id';

let nextMsgId = 1;

function generateId(): string {
  return crypto.randomUUID();
}

function loadConversations(): Conversation[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const metas: ConversationMeta[] = JSON.parse(raw);
    return metas.map((m) => ({ ...m, messages: [] }));
  } catch {
    return [];
  }
}

function loadActiveId(): string | null {
  return localStorage.getItem(ACTIVE_KEY);
}

function saveConversations(conversations: Conversation[]) {
  const metas: ConversationMeta[] = conversations.map((c) => ({
    id: c.id,
    title: c.title,
  }));
  localStorage.setItem(STORAGE_KEY, JSON.stringify(metas));
}

function saveActiveId(id: string | null) {
  if (id) {
    localStorage.setItem(ACTIVE_KEY, id);
  } else {
    localStorage.removeItem(ACTIVE_KEY);
  }
}

export function ChatProvider({ children }: { children: ReactNode }) {
  const [conversations, setConversations] = useState<Conversation[]>(() => loadConversations());
  const [activeId, setActiveId] = useState<string | null>(() => loadActiveId());
  const [streamingMessageId, setStreamingMessageId] = useState<number | null>(null);

  // Persist conversation list on change
  useEffect(() => {
    saveConversations(conversations);
  }, [conversations]);

  // Persist active conversation ID on change
  useEffect(() => {
    saveActiveId(activeId);
  }, [activeId]);

  const createConversation = useCallback(() => {
    const id = generateId();
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

  const loadHistoryMessages = useCallback((conversationId: string, messages: ChatMessage[]) => {
    setConversations((prev) =>
      prev.map((c) => {
        if (c.id !== conversationId) return c;
        // Only load if currently empty (avoid overwriting active streaming)
        if (c.messages.length > 0) return c;
        return { ...c, messages };
      }),
    );
  }, []);

  const addStructuredData = useCallback(
    (conversationId: string, messageId: number, data: StructuredData) => {
      setConversations((prev) =>
        prev.map((c) => {
          if (c.id !== conversationId) return c;
          return {
            ...c,
            messages: c.messages.map((m) =>
              m.id === messageId
                ? { ...m, structuredData: [...(m.structuredData ?? []), data] }
                : m,
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
        addStructuredData,
        setStreamingMessageId,
        loadHistoryMessages,
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

export function createMessageId(): number {
  return nextMsgId++;
}
