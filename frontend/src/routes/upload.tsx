import { createFileRoute } from '@tanstack/react-router';
import { useCallback, useEffect, useRef, useState } from 'react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Download } from 'lucide-react';

const API_URL = '/api';

const ACCEPTED_EXTENSIONS = ['.pdf', '.docx', '.txt'];
const ACCEPTED_MIME_TYPES = [
  'application/pdf',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
  'text/plain',
];

type HealthStatus = 'checking' | 'connected' | 'disconnected';

interface QuestionOption {
  label: string;
  text: string;
}

interface Chapter {
  level: number;
  title: string;
  children: Chapter[];
}

interface KnowledgePointTag {
  value: string;
  category: string;
}

interface KnowledgePoint {
  name: string;
  description: string;
  tags: KnowledgePointTag[];
}

interface Question {
  id: number;
  stem_text: string;
  options: QuestionOption[];
  correct_answer?: string | null;
  reference_answer?: string | null;
  explanation?: string | null;
  difficulty?: string;
  knowledge_point_name: string;
  question_type: string;
  status: string;
}

interface GenerationStats {
  total: number;
  successful: number;
  failed: number;
}

interface GenerationResult {
  chapters: Chapter[];
  knowledge_points: KnowledgePoint[];
  questions: Question[];
  generation_stats: GenerationStats;
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function isAcceptedFile(file: File): boolean {
  const ext = file.name.substring(file.name.lastIndexOf('.')).toLowerCase();
  return ACCEPTED_EXTENSIONS.includes(ext) || ACCEPTED_MIME_TYPES.includes(file.type);
}

export const Route = createFileRoute('/upload')({
  component: HomePage,
});

function HomePage() {
  const [healthStatus, setHealthStatus] = useState<HealthStatus>('checking');

  useEffect(() => {
    fetch(`${API_URL}/health`)
      .then((res) => (res.ok ? setHealthStatus('connected') : setHealthStatus('disconnected')))
      .catch(() => setHealthStatus('disconnected'));
  }, []);

  return (
    <>
      <HealthIndicator status={healthStatus} />
      <FileUpload healthStatus={healthStatus} />
    </>
  );
}

function HealthIndicator({ status }: { status: HealthStatus }) {
  const config: Record<HealthStatus, { label: string; dot: string }> = {
    checking: { label: '连接中...', dot: 'bg-yellow-500' },
    connected: { label: '后端已连接', dot: 'bg-green-500' },
    disconnected: { label: '后端未连接', dot: 'bg-red-500' },
  };

  const { label, dot } = config[status];

  return (
    <div className="mb-4 flex items-center gap-2 text-sm text-muted-foreground">
      <span className={`inline-block size-2 rounded-full ${dot}`} />
      <span>{label}</span>
    </div>
  );
}

function FileUpload({ healthStatus }: { healthStatus: HealthStatus }) {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isDragOver, setIsDragOver] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [result, setResult] = useState<GenerationResult | null>(null);
  const [apiError, setApiError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFile = useCallback((file: File) => {
    setError(null);
    setApiError(null);
    setResult(null);
    if (!isAcceptedFile(file)) {
      setSelectedFile(null);
      setError('不支持的文件格式，请选择 PDF、Word 或纯文本文件');
      return;
    }
    setSelectedFile(file);
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragOver(false);
      const file = e.dataTransfer.files[0];
      if (file) handleFile(file);
    },
    [handleFile],
  );

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
  }, []);

  const handleInputChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file) handleFile(file);
    },
    [handleFile],
  );

  const handleClear = useCallback(() => {
    setSelectedFile(null);
    setError(null);
    setApiError(null);
    setResult(null);
    if (inputRef.current) inputRef.current.value = '';
  }, []);

  const handleGenerate = useCallback(async () => {
    if (!selectedFile) return;
    if (healthStatus === 'disconnected') {
      setApiError('无法连接后端服务，请确认后端已启动');
      return;
    }
    setIsLoading(true);
    setApiError(null);
    setResult(null);

    try {
      const formData = new FormData();
      formData.append('file', selectedFile);
      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), 120_000);
      let res: Response;
      try {
        res = await fetch(`${API_URL}/questions/generate/from-file`, {
          method: 'POST',
          body: formData,
          signal: controller.signal,
        });
      } finally {
        clearTimeout(timeout);
      }
      if (!res.ok) {
        throw res;
      }
      const data: GenerationResult = await res.json();
      setResult(data);
    } catch (err) {
      if (err instanceof DOMException && err.name === 'AbortError') {
        setApiError('请求超时，文件可能过大或内容过多，请稍后重试');
      } else if (err instanceof TypeError && err.message === 'Failed to fetch') {
        setApiError('无法连接后端服务，请确认后端已启动');
      } else if (err instanceof Response) {
        let detail = '';
        try {
          detail = await err.text();
        } catch {
          // ignore text extraction failure
        }
        switch (err.status) {
          case 413:
            setApiError('文件过大，请选择更小的文件');
            break;
          case 422:
            setApiError('文件格式无法解析，请检查文件内容');
            break;
          case 500:
            setApiError('后端处理出错，请稍后重试');
            break;
          default:
            setApiError(detail || `请求失败 (${err.status})`);
        }
      } else {
        setApiError(err instanceof Error ? err.message : '生成题目时发生未知错误');
      }
    } finally {
      setIsLoading(false);
    }
  }, [selectedFile, healthStatus]);

  return (
    <div>
      {result ? (
        <StructuredResult result={result} onReset={handleClear} />
      ) : (
        <>
          <div
            onDrop={handleDrop}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            className={`flex cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed py-12 sm:py-20 text-center transition-colors ${
              isDragOver
                ? 'border-primary bg-primary/5'
                : 'border-border hover:border-primary/50'
            }`}
            onClick={() => inputRef.current?.click()}
            role="button"
            tabIndex={0}
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') inputRef.current?.click();
            }}
          >
            <input
              ref={inputRef}
              type="file"
              accept=".pdf,.docx,.txt"
              className="hidden"
              onChange={handleInputChange}
            />
            <div className="mb-4 text-muted-foreground/50">
              <svg
                xmlns="http://www.w3.org/2000/svg"
                width="48"
                height="48"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                <polyline points="17 8 12 3 7 8" />
                <line x1="12" y1="3" x2="12" y2="15" />
              </svg>
            </div>
            <p className="mb-2 text-lg font-medium text-foreground">
              {isDragOver ? '释放文件以上传' : '上传教材文件开始出题'}
            </p>
            <p className="mb-6 text-sm text-muted-foreground">支持 PDF、Word、纯文本格式</p>
            <Button variant="outline" type="button" onClick={(e) => e.stopPropagation()}>
              选择文件
            </Button>
          </div>

          {error && (
            <Card className="mt-4 border-destructive/50 bg-destructive/5">
              <CardContent className="py-3 text-sm text-destructive">{error}</CardContent>
            </Card>
          )}

          {selectedFile && (
            <Card className="mt-4">
              <CardContent className="flex flex-col gap-3 py-3 sm:flex-row sm:items-center sm:justify-between">
                <div className="flex items-center gap-3 min-w-0">
                  <span className="inline-flex size-8 shrink-0 items-center justify-center rounded bg-primary/10 text-xs font-medium text-primary">
                    {selectedFile.name.split('.').pop()?.toUpperCase()}
                  </span>
                  <div className="min-w-0">
                    <p className="truncate text-sm font-medium text-foreground">{selectedFile.name}</p>
                    <p className="text-xs text-muted-foreground">{formatFileSize(selectedFile.size)}</p>
                  </div>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <Button
                    size="sm"
                    onClick={handleGenerate}
                    disabled={isLoading || healthStatus === 'disconnected'}
                  >
                    {isLoading ? '生成中...' : '生成题目'}
                  </Button>
                  <Button variant="ghost" size="sm" onClick={handleClear}>
                    移除
                  </Button>
                </div>
              </CardContent>
            </Card>
          )}

          {isLoading && (
            <div className="mt-6 text-center text-sm text-muted-foreground">
              <span className="inline-block animate-pulse">正在生成题目，请稍候（可能需要 10-30 秒）...</span>
            </div>
          )}

          {apiError && (
            <Card className="mt-4 border-destructive/50 bg-destructive/5">
              <CardContent className="flex flex-col gap-3 py-3 sm:flex-row sm:items-center sm:justify-between">
                <p className="text-sm text-destructive break-words">{apiError}</p>
                <Button variant="outline" size="sm" onClick={handleGenerate} disabled={isLoading}>
                  重试
                </Button>
              </CardContent>
            </Card>
          )}
        </>
      )}
    </div>
  );
}

/* ── Structured result display components ── */

const CATEGORY_COLORS: Record<string, string> = {
  concept: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
  formula: 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200',
  procedure: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
  fact: 'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200',
  principle: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
};

const CATEGORY_LABELS: Record<string, string> = {
  concept: '概念',
  formula: '公式',
  procedure: '过程',
  fact: '事实',
  principle: '原理',
};

const QUESTION_TYPE_LABELS: Record<string, string> = {
  definition: '定义',
  calculation: '计算',
  analysis: '分析',
  verification: '验证',
  application: '应用',
  procedure: '过程',
  recall: '回忆',
  short_answer: '简答',
  essay: '论述',
};

const QUESTION_TYPE_COLORS: Record<string, string> = {
  definition: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
  calculation: 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200',
  analysis: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
  verification: 'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200',
  application: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
  procedure: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
  recall: 'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200',
  short_answer: 'bg-cyan-100 text-cyan-800 dark:bg-cyan-900 dark:text-cyan-200',
  essay: 'bg-indigo-100 text-indigo-800 dark:bg-indigo-900 dark:text-indigo-200',
};

const DIFFICULTY_LABELS: Record<string, string> = {
  basic: '基础',
  intermediate: '中等',
  advanced: '提高',
};

const DIFFICULTY_COLORS: Record<string, string> = {
  basic: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900 dark:text-emerald-200',
  intermediate: 'bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-200',
  advanced: 'bg-rose-100 text-rose-800 dark:bg-rose-900 dark:text-rose-200',
};

function EmptyState({ message }: { message: string }) {
  return (
    <Card>
      <CardContent className="py-8 text-center text-sm text-muted-foreground">
        {message}
      </CardContent>
    </Card>
  );
}

function StructuredResult({
  result,
  onReset,
}: {
  result: GenerationResult;
  onReset: () => void;
}) {
  const { chapters, knowledge_points, questions, generation_stats } = result;

  const hasSuccess = questions.some((q) => q.status === 'success');
  const hasFailed = questions.some((q) => q.status === 'failed');

  const handleExport = useCallback(async () => {
    try {
      const res = await fetch(`${API_URL}/questions/export`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ questions, format: 'markdown' }),
      });
      if (!res.ok) return;
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'questions.md';
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      // silently fail
    }
  }, [questions]);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">生成结果</h2>
        <div className="flex items-center gap-2">
          {hasSuccess && (
            <Button variant="outline" size="sm" onClick={handleExport}>
              <Download className="mr-1 size-4" />
              导出 Markdown
            </Button>
          )}
          <Button variant="outline" size="sm" onClick={onReset}>
            重新上传
          </Button>
        </div>
      </div>

      <StatsCard stats={generation_stats} />

      {chapters.length > 0 && <ChaptersSection chapters={chapters} />}

      {knowledge_points.length > 0 ? (
        <KnowledgePointsSection knowledgePoints={knowledge_points} />
      ) : (
        <EmptyState message="未提取到知识点" />
      )}

      {hasSuccess || hasFailed ? (
        <QuestionsSection questions={questions} />
      ) : (
        <EmptyState message="未成功生成任何题目" />
      )}
    </div>
  );
}

function StatsCard({ stats }: { stats: GenerationStats }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>生成统计</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="flex flex-wrap gap-4 sm:gap-8 text-sm">
          <div className="flex items-center gap-2">
            <span className="inline-block size-2.5 rounded-full bg-muted-foreground" />
            <span>总计: {stats.total}</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="inline-block size-2.5 rounded-full bg-green-500" />
            <span>成功: {stats.successful}</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="inline-block size-2.5 rounded-full bg-red-500" />
            <span>失败: {stats.failed}</span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function ChaptersSection({ chapters }: { chapters: Chapter[] }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>章节结构</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-1">
          {chapters.map((chapter, i) => (
            <ChapterNode key={i} chapter={chapter} />
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

function ChapterNode({ chapter }: { chapter: Chapter }) {
  const hasChildren = chapter.children.length > 0;

  if (!hasChildren) {
    return (
      <div
        className="py-1 text-sm text-foreground break-words"
        style={{ paddingLeft: `${(chapter.level - 1) * 1.25}rem` }}
      >
        {chapter.title}
      </div>
    );
  }

  return (
    <details open>
      <summary
        className="cursor-pointer py-1 text-sm font-medium text-foreground hover:text-primary break-words"
        style={{ paddingLeft: `${(chapter.level - 1) * 1.25}rem` }}
      >
        {chapter.title}
      </summary>
      <div className="space-y-0.5">
        {chapter.children.map((child, i) => (
          <ChapterNode key={i} chapter={child} />
        ))}
      </div>
    </details>
  );
}

function KnowledgePointsSection({ knowledgePoints }: { knowledgePoints: KnowledgePoint[] }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>知识点 ({knowledgePoints.length})</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {knowledgePoints.map((kp, i) => (
            <div key={i} className="rounded-lg border p-3">
              <div className="flex flex-wrap items-start justify-between gap-2">
                <h4 className="text-sm font-medium text-foreground break-words">{kp.name}</h4>
                <div className="flex shrink-0 flex-wrap gap-1">
                  {kp.tags.map((tag, j) => (
                    <span
                      key={j}
                      className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${
                        CATEGORY_COLORS[tag.category] ?? 'bg-muted text-muted-foreground'
                      }`}
                    >
                      {CATEGORY_LABELS[tag.category] ?? tag.category}
                    </span>
                  ))}
                </div>
              </div>
              {kp.description && (
                <p className="mt-1 text-xs text-muted-foreground break-words">{kp.description}</p>
              )}
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

function QuestionsSection({ questions }: { questions: Question[] }) {
  const successQuestions = questions.filter((q) => q.status === 'success');
  const failedQuestions = questions.filter((q) => q.status === 'failed');

  return (
    <div className="space-y-4">
      {successQuestions.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>题目 ({successQuestions.length})</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {successQuestions.map((q, i) => (
                <QuestionCard key={q.id} question={q} index={i + 1} />
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {failedQuestions.length > 0 && (
        <Card className="border-red-200 dark:border-red-800">
          <CardHeader>
            <CardTitle className="text-red-600 dark:text-red-400">
              生成失败 ({failedQuestions.length})
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {failedQuestions.map((q) => (
                <div
                  key={q.id}
                  className="rounded-lg border border-red-200 border-l-4 border-l-red-500 bg-red-50 p-3 dark:border-red-800 dark:border-l-red-400 dark:bg-red-950"
                >
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <p className="text-sm text-red-800 dark:text-red-200 break-words">
                      知识点「{q.knowledge_point_name}」
                    </p>
                    <Badge variant="destructive" className="shrink-0 text-xs">
                      生成失败
                    </Badge>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

function QuestionCard({ question, index }: { question: Question; index: number }) {
  const correctLabel = question.correct_answer;
  const isSubjective = question.question_type === 'short_answer' || question.question_type === 'essay';

  return (
    <div className="rounded-lg border p-4">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <h4 className="text-sm font-medium text-foreground break-words">
          {index}. {question.stem_text}
        </h4>
        <div className="flex shrink-0 flex-wrap gap-1">
          <Badge
            variant="secondary"
            className={`text-xs ${QUESTION_TYPE_COLORS[question.question_type] ?? ''}`}
          >
            {QUESTION_TYPE_LABELS[question.question_type] ?? question.question_type}
          </Badge>
          {question.difficulty && (
            <Badge
              variant="secondary"
              className={`text-xs ${DIFFICULTY_COLORS[question.difficulty] ?? ''}`}
            >
              {DIFFICULTY_LABELS[question.difficulty] ?? question.difficulty}
            </Badge>
          )}
        </div>
      </div>

      {!isSubjective && question.options.length > 0 && (
        <div className="mt-3 space-y-1.5">
          {question.options.map((opt) => {
            const isCorrect = correctLabel && opt.label === correctLabel;
            return (
              <div
                key={opt.label}
                className={`flex items-start gap-2 text-sm ${
                  isCorrect ? 'font-medium text-green-700 dark:text-green-400' : ''
                }`}
              >
                <span
                  className={`inline-flex size-5 shrink-0 items-center justify-center rounded-full text-xs font-medium ${
                    isCorrect
                      ? 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300'
                      : 'bg-muted text-muted-foreground'
                  }`}
                >
                  {isCorrect ? '✓' : opt.label}
                </span>
                <span className="text-foreground break-words">{opt.text}</span>
              </div>
            );
          })}
        </div>
      )}

      {isSubjective && question.reference_answer && (
        <div className="mt-3 rounded-md border border-dashed border-muted-foreground/30 bg-muted/30 p-2.5">
          <div className="mb-1 text-xs font-medium text-muted-foreground">参考答案</div>
          <p className="text-sm text-foreground break-words whitespace-pre-wrap">
            {question.reference_answer}
          </p>
        </div>
      )}

      {question.explanation && (
        <div className="mt-3 rounded-md border border-blue-200 bg-blue-50 p-2.5 dark:border-blue-800 dark:bg-blue-950">
          <div className="mb-1 text-xs font-medium text-blue-600 dark:text-blue-400">解析</div>
          <p className="text-sm text-foreground break-words whitespace-pre-wrap">
            {question.explanation}
          </p>
        </div>
      )}

      <div className="mt-3 text-xs text-muted-foreground break-words">
        知识点: {question.knowledge_point_name}
      </div>
    </div>
  );
}
