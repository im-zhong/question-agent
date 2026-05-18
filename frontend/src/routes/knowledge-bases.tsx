import { createFileRoute } from '@tanstack/react-router';
import { useCallback, useEffect, useRef, useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import {
  Database,
  Plus,
  Loader2,
  FolderOpen,
  Upload,
  FileText,
  ChevronDown,
  ChevronRight,
  Trash2,
} from 'lucide-react';

const API_URL = '/api/v1';

const SUBJECTS = ['语文', '数学', '英语', '物理', '化学', '生物', '历史', '地理', '政治'] as const;
const GRADE_LEVELS = ['小学', '初中', '高中', '大学'] as const;

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

interface Document {
  id: string;
  kb_id: string;
  filename: string;
  format: string;
  file_path: string;
  char_count: number;
  status: string;
  error_message: string | null;
  created_at: string;
}

interface KnowledgePoint {
  id: string;
  document_id: string;
  kb_id: string;
  name: string;
  description: string;
  tags_json: string;
  confidence: number;
  method: string;
  chapter_id: string | null;
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
  const [subject, setSubject] = useState('');
  const [gradeLevel, setGradeLevel] = useState('');
  const [error, setError] = useState<string | null>(null);

  // Expansion state
  const [expandedKbId, setExpandedKbId] = useState<string | null>(null);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [knowledgePoints, setKnowledgePoints] = useState<KnowledgePoint[]>([]);
  const [loadingDetails, setLoadingDetails] = useState(false);
  const [showKps, setShowKps] = useState(false);

  // Upload state
  const [uploadingKbId, setUploadingKbId] = useState<string | null>(null);
  const fileInputRefs = useRef<Record<string, HTMLInputElement | null>>({});

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

  const fetchDetails = useCallback(async (kbId: string) => {
    setLoadingDetails(true);
    try {
      const [docsRes, kpsRes] = await Promise.all([
        fetch(`${API_URL}/knowledge-bases/${kbId}/documents`),
        fetch(`${API_URL}/knowledge-bases/${kbId}/knowledge-points`),
      ]);
      if (docsRes.ok) {
        setDocuments(await docsRes.json());
      }
      if (kpsRes.ok) {
        setKnowledgePoints(await kpsRes.json());
      }
    } catch {
      // ignore fetch errors
    } finally {
      setLoadingDetails(false);
    }
  }, []);

  const handleToggleExpand = useCallback((kbId: string) => {
    if (expandedKbId === kbId) {
      setExpandedKbId(null);
      setDocuments([]);
      setKnowledgePoints([]);
      setShowKps(false);
    } else {
      setExpandedKbId(kbId);
      setDocuments([]);
      setKnowledgePoints([]);
      setShowKps(false);
      fetchDetails(kbId);
    }
  }, [expandedKbId, fetchDetails]);

  const handleUpload = useCallback(async (kbId: string, file: File) => {
    setUploadingKbId(kbId);
    try {
      const formData = new FormData();
      formData.append('file', file);
      const res = await fetch(`${API_URL}/knowledge-bases/${kbId}/documents`, {
        method: 'POST',
        body: formData,
      });
      if (!res.ok) {
        const body = await res.json().catch(() => null);
        throw new Error(body?.detail ?? `上传失败 (${res.status})`);
      }
      await fetchKbs();
      if (expandedKbId === kbId) {
        await fetchDetails(kbId);
      }
    } catch (err) {
      // eslint-disable-next-line no-alert
      alert(err instanceof Error ? err.message : '上传失败');
    } finally {
      setUploadingKbId(null);
    }
  }, [expandedKbId, fetchKbs, fetchDetails]);

  const handleFileSelect = useCallback((kbId: string, e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      handleUpload(kbId, file);
    }
    // Reset input so re-uploading the same file triggers change
    e.target.value = '';
  }, [handleUpload]);

  const handleCreate = useCallback(async () => {
    if (!name.trim()) return;
    setCreating(true);
    setError(null);
    try {
      const res = await fetch(`${API_URL}/knowledge-bases`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: name.trim(),
          description: description.trim() || null,
          subject: subject || null,
          grade_level: gradeLevel || null,
        }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => null);
        throw new Error(body?.detail?.[0]?.msg ?? `创建失败 (${res.status})`);
      }
      setName('');
      setDescription('');
      setSubject('');
      setGradeLevel('');
      setShowCreate(false);
      await fetchKbs();
    } catch (err) {
      setError(err instanceof Error ? err.message : '创建失败');
    } finally {
      setCreating(false);
    }
  }, [name, description, subject, gradeLevel, fetchKbs]);

  // Delete state
  const [deletingKbId, setDeletingKbId] = useState<string | null>(null);

  const handleDelete = useCallback(async (kbId: string, kbName: string) => {
    // eslint-disable-next-line no-alert
    if (!window.confirm(`确定要删除知识库「${kbName}」吗？该操作不可恢复。`)) return;
    setDeletingKbId(kbId);
    try {
      const res = await fetch(`${API_URL}/knowledge-bases/${kbId}`, {
        method: 'DELETE',
      });
      if (!res.ok && res.status !== 204) {
        throw new Error(`删除失败 (${res.status})`);
      }
      if (expandedKbId === kbId) {
        setExpandedKbId(null);
        setDocuments([]);
        setKnowledgePoints([]);
        setShowKps(false);
      }
      await fetchKbs();
    } catch (err) {
      alert(err instanceof Error ? err.message : '删除失败');
    } finally {
      setDeletingKbId(null);
    }
  }, [expandedKbId, fetchKbs]);

  const statusBadge = (status: string, errorMessage: string | null) => {
    if (status === 'ready') {
      return <Badge className="bg-green-100 text-green-700 text-xs hover:bg-green-100">就绪</Badge>;
    }
    if (status === 'failed') {
      return (
        <Badge
          className="bg-red-100 text-red-700 text-xs hover:bg-red-100"
          title={errorMessage ?? ''}
        >
          失败
        </Badge>
      );
    }
    return <Badge className="bg-yellow-100 text-yellow-700 text-xs hover:bg-yellow-100">处理中</Badge>;
  };

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
              <div className="flex gap-3">
                <select
                  value={subject}
                  onChange={(e) => setSubject(e.target.value)}
                  className="flex-1 rounded-md border border-input bg-background px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
                >
                  <option value="">选择学科（可选）</option>
                  {SUBJECTS.map((s) => <option key={s} value={s}>{s}</option>)}
                </select>
                <select
                  value={gradeLevel}
                  onChange={(e) => setGradeLevel(e.target.value)}
                  className="flex-1 rounded-md border border-input bg-background px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
                >
                  <option value="">选择学段（可选）</option>
                  {GRADE_LEVELS.map((g) => <option key={g} value={g}>{g}</option>)}
                </select>
              </div>
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
                <CardContent className="py-3">
                  <div className="flex items-center justify-between">
                    <div
                      className="flex min-w-0 flex-1 cursor-pointer items-center gap-2"
                      onClick={() => handleToggleExpand(kb.id)}
                    >
                      {expandedKbId === kb.id ? (
                        <ChevronDown className="size-4 shrink-0 text-muted-foreground" />
                      ) : (
                        <ChevronRight className="size-4 shrink-0 text-muted-foreground" />
                      )}
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-2">
                          <h3 className="truncate text-sm font-medium">{kb.name}</h3>
                          {kb.subject && (
                            <Badge variant="secondary" className="shrink-0 text-xs">{kb.subject}</Badge>
                          )}
                          {kb.grade_level && (
                            <Badge variant="outline" className="shrink-0 text-xs">{kb.grade_level}</Badge>
                          )}
                        </div>
                        {kb.description && (
                          <p className="mt-0.5 truncate text-xs text-muted-foreground">{kb.description}</p>
                        )}
                      </div>
                    </div>
                    <div className="flex shrink-0 items-center gap-3">
                      <div className="text-right text-xs text-muted-foreground">
                        <p>{kb.document_count} 个文档</p>
                        <p>{new Date(kb.created_at).toLocaleDateString()}</p>
                      </div>
                      <input
                        type="file"
                        accept=".pdf,.docx,.txt"
                        className="hidden"
                        ref={(el) => { fileInputRefs.current[kb.id] = el; }}
                        onChange={(e) => handleFileSelect(kb.id, e)}
                      />
                      <Button
                        size="sm"
                        variant="outline"
                        className="h-7 px-2 text-xs"
                        disabled={uploadingKbId === kb.id}
                        onClick={() => fileInputRefs.current[kb.id]?.click()}
                      >
                        {uploadingKbId === kb.id ? (
                          <Loader2 className="mr-1 size-3 animate-spin" />
                        ) : (
                          <Upload className="mr-1 size-3" />
                        )}
                        上传
                      </Button>
                      <Button
                        size="sm"
                        variant="ghost"
                        className="h-7 px-2 text-xs text-destructive hover:text-destructive"
                        disabled={deletingKbId === kb.id}
                        onClick={() => handleDelete(kb.id, kb.name)}
                      >
                        {deletingKbId === kb.id ? (
                          <Loader2 className="size-3 animate-spin" />
                        ) : (
                          <Trash2 className="size-3" />
                        )}
                      </Button>
                    </div>
                  </div>

                  {expandedKbId === kb.id && (
                    <div className="mt-3 border-t border-border pt-3">
                      {loadingDetails ? (
                        <div className="flex items-center justify-center py-4 text-muted-foreground">
                          <Loader2 className="mr-2 size-4 animate-spin" />
                          加载详情...
                        </div>
                      ) : (
                        <>
                          {/* Documents section */}
                          <div className="mb-3">
                            <h4 className="mb-2 flex items-center gap-1.5 text-xs font-medium text-muted-foreground">
                              <FileText className="size-3.5" />
                              文档 ({documents.length})
                            </h4>
                            {documents.length === 0 ? (
                              <p className="text-xs text-muted-foreground/60">暂无文档</p>
                            ) : (
                              <div className="space-y-1.5">
                                {documents.map((doc) => (
                                  <div
                                    key={doc.id}
                                    className="flex items-center justify-between rounded-md bg-muted/50 px-3 py-1.5"
                                  >
                                    <div className="flex items-center gap-2 min-w-0">
                                      <FileText className="size-3.5 shrink-0 text-muted-foreground" />
                                      <span className="truncate text-xs">{doc.filename}</span>
                                    </div>
                                    <div className="flex items-center gap-2 shrink-0">
                                      {statusBadge(doc.status, doc.error_message)}
                                      <span className="text-xs text-muted-foreground">
                                        {new Date(doc.created_at).toLocaleDateString()}
                                      </span>
                                    </div>
                                  </div>
                                ))}
                              </div>
                            )}
                          </div>

                          {/* Knowledge Points section */}
                          <div>
                            <button
                              type="button"
                              className="mb-2 flex items-center gap-1.5 text-xs font-medium text-muted-foreground hover:text-foreground"
                              onClick={() => setShowKps(!showKps)}
                            >
                              {showKps ? (
                                <ChevronDown className="size-3.5" />
                              ) : (
                                <ChevronRight className="size-3.5" />
                              )}
                              知识点
                              <Badge variant="secondary" className="text-xs">{knowledgePoints.length}</Badge>
                            </button>
                            {showKps && (
                              <div className="space-y-1.5">
                                {knowledgePoints.length === 0 ? (
                                  <p className="text-xs text-muted-foreground/60">暂无知识点</p>
                                ) : (
                                  knowledgePoints.map((kp) => (
                                    <div
                                      key={kp.id}
                                      className="flex items-center gap-2 rounded-md bg-muted/50 px-3 py-1.5"
                                    >
                                      <span className="truncate text-xs">{kp.name}</span>
                                      <Badge variant="outline" className="shrink-0 text-xs">{kp.method}</Badge>
                                      <span className="shrink-0 text-xs text-muted-foreground">
                                        {(kp.confidence * 100).toFixed(0)}%
                                      </span>
                                    </div>
                                  ))
                                )}
                              </div>
                            )}
                          </div>
                        </>
                      )}
                    </div>
                  )}
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
