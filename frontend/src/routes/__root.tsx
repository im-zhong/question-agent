import { createRootRoute, Link, Outlet } from '@tanstack/react-router';
import { useState } from 'react';
import { ChatSidebar } from '@/components/chat-sidebar';
import { ChatProvider, useChat } from '@/lib/chat-context';
import { Button } from '@/components/ui/button';
import { Toaster } from '@/components/ui/sonner';
import { Database, MessageSquare, PanelLeft, PanelLeftClose } from 'lucide-react';

export const Route = createRootRoute({
  component: RootLayout,
});

function RootLayout() {
  return (
    <ChatProvider>
      <RootLayoutInner />
    </ChatProvider>
  );
}

function RootLayoutInner() {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const { conversations, activeId, createConversation, selectConversation } = useChat();

  return (
    <>
    <div className="flex h-screen overflow-hidden bg-background">
      <ChatSidebar
        collapsed={sidebarCollapsed}
        conversations={conversations}
        activeId={activeId}
        onNewChat={createConversation}
        onSelectConversation={selectConversation}
      />
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-12 shrink-0 items-center gap-2 border-b border-border px-3">
          <Button
            variant="ghost"
            size="icon"
            className="size-8"
            onClick={() => setSidebarCollapsed((c) => !c)}
            aria-label={sidebarCollapsed ? '展开侧边栏' : '收起侧边栏'}
          >
            {sidebarCollapsed ? <PanelLeft className="size-4" /> : <PanelLeftClose className="size-4" />}
          </Button>
          <h1 className="text-sm font-medium">智能出题</h1>
          <nav className="ml-4 flex gap-1">
            <Link
              to="/chat"
              className="flex items-center gap-1 rounded-md px-2 py-1 text-xs text-muted-foreground hover:bg-muted hover:text-foreground [&.active]:bg-muted [&.active]:text-foreground"
            >
              <MessageSquare className="size-3.5" />
              对话
            </Link>
            <Link
              to="/knowledge-bases"
              className="flex items-center gap-1 rounded-md px-2 py-1 text-xs text-muted-foreground hover:bg-muted hover:text-foreground [&.active]:bg-muted [&.active]:text-foreground"
            >
              <Database className="size-3.5" />
              知识库
            </Link>
          </nav>
        </header>
        <main className="flex-1 overflow-hidden">
          <Outlet />
        </main>
      </div>
    </div>
    <Toaster />
    </>
  );
}
