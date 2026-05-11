import { createRootRoute, Outlet } from '@tanstack/react-router';
import { useState } from 'react';
import { ChatSidebar } from '@/components/chat-sidebar';
import { Button } from '@/components/ui/button';
import { PanelLeft, PanelLeftClose } from 'lucide-react';

export const Route = createRootRoute({
  component: RootLayout,
});

function RootLayout() {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  return (
    <div className="flex h-screen overflow-hidden bg-background">
      <ChatSidebar
        collapsed={sidebarCollapsed}
        onNewChat={() => {}}
        onSelectConversation={() => {}}
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
        </header>
        <main className="flex-1 overflow-hidden">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
