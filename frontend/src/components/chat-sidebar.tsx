import { Button } from '@/components/ui/button';
import { type Conversation } from '@/lib/chat-context';
import { MessageSquare, Plus } from 'lucide-react';

interface ChatSidebarProps {
  collapsed: boolean;
  conversations: Conversation[];
  activeId: string | null;
  onNewChat: () => void;
  onSelectConversation: (id: string) => void;
}

export function ChatSidebar({ collapsed, conversations, activeId, onNewChat, onSelectConversation }: ChatSidebarProps) {
  if (collapsed) return null;

  return (
    <aside className="flex w-64 shrink-0 flex-col bg-zinc-900 border-r border-zinc-800">
      <div className="p-3">
        <Button variant="outline" className="w-full justify-start gap-2 border-zinc-700 bg-transparent text-zinc-300 hover:bg-zinc-800 hover:text-zinc-100" onClick={onNewChat}>
          <Plus className="size-4" />
          新建对话
        </Button>
      </div>
      <nav className="flex-1 overflow-y-auto px-2 pb-2">
        {conversations.length === 0 && (
          <p className="px-3 py-4 text-center text-xs text-zinc-600">暂无对话</p>
        )}
        {conversations.map((conv) => (
          <button
            key={conv.id}
            onClick={() => onSelectConversation(conv.id)}
            aria-current={conv.id === activeId ? 'true' : undefined}
            className={`flex w-full items-center gap-2 rounded-lg px-3 py-2.5 text-left text-sm transition-colors ${
              conv.id === activeId
                ? 'bg-zinc-700 text-zinc-100'
                : 'text-zinc-400 hover:bg-zinc-800 hover:text-zinc-200'
            }`}
          >
            <MessageSquare className="size-4 shrink-0" />
            <span className="truncate">{conv.title}</span>
          </button>
        ))}
      </nav>
    </aside>
  );
}
