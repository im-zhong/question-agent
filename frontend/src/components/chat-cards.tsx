import { Badge } from '@/components/ui/badge';
import { CheckCircle2 } from 'lucide-react';

/* ── Shared category styling ── */

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

/* ── Knowledge Point types ── */

export interface KnowledgePointTag {
  value: string;
  category: string;
}

export interface KnowledgePoint {
  name: string;
  description: string;
  tags: KnowledgePointTag[];
  confidence?: number;
  method?: string;
}

/* ── Question types ── */

export interface QuestionOption {
  label: string;
  text: string;
}

export interface Question {
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

/* ── Knowledge Point Card ── */

export function KnowledgePointCard({ kp }: { kp: KnowledgePoint }) {
  return (
    <div className="rounded-lg border bg-background p-3">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <h4 className="text-sm font-medium text-foreground break-words">{kp.name}</h4>
        <div className="flex shrink-0 flex-wrap gap-1">
          {kp.tags.map((tag, i) => (
            <span
              key={i}
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
  );
}

/* ── Knowledge Points Section ── */

export function KnowledgePointsList({ points }: { points: KnowledgePoint[] }) {
  return (
    <div className="my-2 space-y-2">
      <div className="flex items-center gap-2 text-xs font-medium text-muted-foreground">
        <span>📚</span>
        <span>提取到 {points.length} 个知识点</span>
      </div>
      <div className="space-y-1.5">
        {points.map((kp, i) => (
          <KnowledgePointCard key={i} kp={kp} />
        ))}
      </div>
    </div>
  );
}

/* ── Question Card ── */

export function QuestionCard({ question, index }: { question: Question; index: number }) {
  const isFailed = question.status === 'failed';
  const correctLabel = question.correct_answer;
  const isSubjective = question.question_type === 'short_answer' || question.question_type === 'essay';

  return (
    <div
      className={`rounded-lg border p-3 ${isFailed ? 'border-red-200 bg-red-50 dark:border-red-800 dark:bg-red-950' : ''}`}
    >
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
          {isFailed && (
            <Badge variant="destructive" className="text-xs">
              生成失败
            </Badge>
          )}
        </div>
      </div>

      {!isFailed && !isSubjective && question.options.length > 0 && (
        <div className="mt-2 space-y-1">
          {question.options.map((opt) => {
            const isCorrect = correctLabel && opt.label === correctLabel;
            return (
              <div
                key={opt.label}
                className={`flex items-start gap-1.5 text-xs ${
                  isCorrect ? 'font-medium text-green-700 dark:text-green-400' : 'text-foreground'
                }`}
              >
                <span
                  className={`inline-flex size-4 shrink-0 items-center justify-center rounded-full text-[10px] font-medium ${
                    isCorrect
                      ? 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300'
                      : 'bg-muted text-muted-foreground'
                  }`}
                >
                  {isCorrect ? <CheckCircle2 className="size-3" /> : opt.label}
                </span>
                <span className="break-words">{opt.text}</span>
              </div>
            );
          })}
        </div>
      )}

      {!isFailed && isSubjective && question.reference_answer && (
        <div className="mt-2 rounded-md border border-dashed border-muted-foreground/30 bg-muted/30 p-2">
          <div className="mb-1 text-xs font-medium text-muted-foreground">参考答案</div>
          <p className="text-xs text-foreground break-words whitespace-pre-wrap">
            {question.reference_answer}
          </p>
        </div>
      )}

      {!isFailed && question.explanation && (
        <div className="mt-2 rounded-md border border-blue-200 bg-blue-50 p-2 dark:border-blue-800 dark:bg-blue-950">
          <div className="mb-1 text-xs font-medium text-blue-600 dark:text-blue-400">解析</div>
          <p className="text-xs text-foreground break-words whitespace-pre-wrap">
            {question.explanation}
          </p>
        </div>
      )}

      <div className="mt-2 text-xs text-muted-foreground break-words">
        知识点: {question.knowledge_point_name}
      </div>
    </div>
  );
}

/* ── Questions Section ── */

export function QuestionsList({ questions }: { questions: Question[] }) {
  const stats = {
    total: questions.length,
    successful: questions.filter((q) => q.status === 'success').length,
    failed: questions.filter((q) => q.status === 'failed').length,
  };

  return (
    <div className="my-2 space-y-2">
      <div className="flex items-center gap-2 text-xs font-medium text-muted-foreground">
        <span>📝</span>
        <span>
          生成 {stats.total} 道题（成功 {stats.successful}，失败 {stats.failed}）
        </span>
      </div>
      <div className="space-y-1.5">
        {questions
          .filter((q) => q.status === 'success')
          .map((q, i) => (
            <QuestionCard key={q.id} question={q} index={i + 1} />
          ))}
        {questions
          .filter((q) => q.status === 'failed')
          .map((q, i) => (
            <QuestionCard key={`f-${q.id}`} question={q} index={stats.successful + i + 1} />
          ))}
      </div>
    </div>
  );
}
