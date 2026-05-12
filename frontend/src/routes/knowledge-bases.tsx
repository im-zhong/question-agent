import { createFileRoute } from '@tanstack/react-router';
import { useCallback, useEffect, useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Database, Plus, Loader2, FolderOpen } from 'lucide-react';

const API_URL = '/api/v1';

interface KnowledgeBase {
  id: string;
  name: string;
  description: string | null;
  subject: string | null;
  grade_level: string | null;
  document_count: number;
  created_at: string;
  updated_at: string;
}

export const Route = createFileRoute('/knowledge-bases')({
  component: KnowledgeBasesPage,
});

function KnowledgeBasesPage() {
  const [kbs, setKbs] = useState<KnowledgeBase[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [creating, setCreating] = useState(false);
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [error, setError] = useState<string | null>(null);

  const fetchKbs = useCallback(async () => {
    try {
      const res = await fetch(`${API_URL}/knowledge-bases`);
      if (res.ok) {
        const data: KnowledgeBase[] = await res.json();
        setKbs(data);
      }
    } catch {
      // ignore fetch errors
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchKbs();
  }, [fetchKbs]);

  const handleCreate = useCallback(async () => {
    if (!name.trim()) return;
    setCreating(true);
    setError(null);
    try {
      const res = await fetch(`${API_URL}/knowledge-bases`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: name.trim(), description: description.trim() || null }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => null);
        throw new Error(body?.detail?.[0]?.msg ?? `创建失败 (${res.status})`);
      }
      setName('');
      setDescription('');
      setShowCreate(false);
      await fetchKbs();
    } catch (err) {
      setError(err instanceof Error ? err.message : '创建失败');
    } finally {
      setCreating(false);
    }
  }, [name, description, fetchKbs]);

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center justify-between border-b border-border px-6 py-4">
        <div className="flex items-center gap-2">
          <Database className="size-5 text-muted-foreground" />
          <h2 className="text-lg font-semibold">知识库</h2>
          <Badge variant="secondary" className="text-xs">{kbs.length}</Badge>
        </div>
        <Button size="sm" onClick={() => setShowCreate(true)} disabled={showCreate}>
          <Plus className="mr-1 size-4" />
          新建知识库
        </Button>
      </div>

      <div className="flex-1 overflow-y-auto px-6 py-4">
        {showCreate && (
          <Card className="mb-4 border-primary/30">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm">创建知识库</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="知识库名称"
                className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"
                autoFocus
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && name.trim()) handleCreate();
                  if (e.key === 'Escape') setShowCreate(false);
                }}
              />
              <textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="描述（可选）"
                rows={2}
                className="w-full resize-none rounded-md border border-input bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"
              />
              {error && <p className="text-xs text-destructive">{error}</p>}
              <div className="flex gap-2">
                <Button size="sm" onClick={handleCreate} disabled={!name.trim() || creating}>
                  {creating ? <Loader2 className="mr-1 size-3 animate-spin" /> : null}
                  {creating ? '创建中...' : '创建'}
                </Button>
                <Button size="sm" variant="ghost" onClick={() => { setShowCreate(false); setError(null); }}>
                  取消
                </Button>
              </div>
            </CardContent>
          </Card>
        )}

        {loading ? (
          <div className="flex items-center justify-center py-12 text-muted-foreground">
            <Loader2 className="mr-2 size-4 animate-spin" />
            加载中...
          </div>
        ) : kbs.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-20 text-muted-foreground">
            <FolderOpen className="mb-3 size-10 opacity-40" />
            <p className="text-sm">暂无知识库</p>
            <p className="text-xs">点击上方"新建知识库"开始</p>
          </div>
        ) : (
          <div className="space-y-3">
            {kbs.map((kb) => (
              <Card key={kb.id}>
                <CardContent className="flex items-center justify-between py-3">
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <h3 className="truncate text-sm font-medium">{kb.name}</h3>
                      {kb.subject && (
                        <Badge variant="secondary" className="shrink-0 text-xs">{kb.subject}</Badge>
                      )}
                    </div>
                    {kb.description && (
                      <p className="mt-0.5 truncate text-xs text-muted-foreground">{kb.description}</p>
                    )}
                  </div>
                  <div className="shrink-0 text-right text-xs text-muted-foreground">
                    <p>{kb.document_count} 个文档</p>
                    <p>{new Date(kb.created_at).toLocaleDateString()}</p>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
