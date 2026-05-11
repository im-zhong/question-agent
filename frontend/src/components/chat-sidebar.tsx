import { Button } from '@/components/ui/button';
import { MessageSquare, Plus } from 'lucide-react';

interface Conversation {
  id: string;
  title: string;
  active?: boolean;
}

const MOCK_CONVERSATIONS: Conversation[] = [
  { id: '1', title: '数学教材出题', active: true },
  { id: '2', title: '语文知识点提取' },
  { id: '3', title: '物理公式分析' },
];

interface ChatSidebarProps {
  collapsed: boolean;
  onNewChat: () => void;
  onSelectConversation: (id: string) => void;
}

export function ChatSidebar({ collapsed, onNewChat, onSelectConversation }: ChatSidebarProps) {
  if (collapsed) return null;

  return (
    <aside className="flex w-64 shrink-0 flex-col bg-muted/40 border-r border-border">
      <div className="p-3">
        <Button variant="outline" className="w-full justify-start gap-2" onClick={onNewChat}>
          <Plus className="size-4" />
          新建对话
        </Button>
      </div>
      <nav className="flex-1 overflow-y-auto px-2 pb-2">
        {MOCK_CONVERSATIONS.map((conv) => (
          <button
            key={conv.id}
            onClick={() => onSelectConversation(conv.id)}
            aria-current={conv.active ? 'true' : undefined}
            className={`flex w-full items-center gap-2 rounded-md px-3 py-2 text-left text-sm transition-colors ${
              conv.active
                ? 'bg-accent text-accent-foreground'
                : 'text-muted-foreground hover:bg-accent/50'
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
