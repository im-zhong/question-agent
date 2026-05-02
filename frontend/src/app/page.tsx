"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const API_URL = "/api";

const ACCEPTED_EXTENSIONS = [".pdf", ".docx", ".txt"];
const ACCEPTED_MIME_TYPES = [
  "application/pdf",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
  "text/plain",
];

type HealthStatus = "checking" | "connected" | "disconnected";

interface QuestionOption {
  label: string;
  text: string;
}

interface Question {
  id: number;
  stem_text: string;
  options: QuestionOption[];
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
  questions: Question[];
  generation_stats: GenerationStats;
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function isAcceptedFile(file: File): boolean {
  const ext = file.name.substring(file.name.lastIndexOf(".")).toLowerCase();
  return ACCEPTED_EXTENSIONS.includes(ext) || ACCEPTED_MIME_TYPES.includes(file.type);
}

export default function Home() {
  const [healthStatus, setHealthStatus] = useState<HealthStatus>("checking");

  useEffect(() => {
    fetch(`${API_URL}/health`)
      .then((res) => (res.ok ? setHealthStatus("connected") : setHealthStatus("disconnected")))
      .catch(() => setHealthStatus("disconnected"));
  }, []);

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b border-border px-6 py-4">
        <div className="mx-auto flex max-w-4xl items-center justify-between">
          <h1 className="text-xl font-semibold tracking-tight">智能出题</h1>
          <HealthIndicator status={healthStatus} />
        </div>
      </header>

      <main className="mx-auto max-w-4xl px-6 py-8">
        <FileUpload />
      </main>
    </div>
  );
}

function HealthIndicator({ status }: { status: HealthStatus }) {
  const config: Record<HealthStatus, { label: string; dot: string }> = {
    checking: { label: "连接中...", dot: "bg-yellow-500" },
    connected: { label: "后端已连接", dot: "bg-green-500" },
    disconnected: { label: "后端未连接", dot: "bg-red-500" },
  };

  const { label, dot } = config[status];

  return (
    <div className="flex items-center gap-2 text-sm text-muted-foreground">
      <span className={`inline-block size-2 rounded-full ${dot}`} />
      <span>{label}</span>
    </div>
  );
}

function FileUpload() {
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
      setError("不支持的文件格式，请选择 PDF、Word 或纯文本文件");
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
    if (inputRef.current) inputRef.current.value = "";
  }, []);

  const handleGenerate = useCallback(async () => {
    if (!selectedFile) return;
    setIsLoading(true);
    setApiError(null);
    setResult(null);

    try {
      const formData = new FormData();
      formData.append("file", selectedFile);
      const res = await fetch(`${API_URL}/questions/generate/from-file`, {
        method: "POST",
        body: formData,
      });
      if (!res.ok) {
        const text = await res.text();
        throw new Error(text || `请求失败 (${res.status})`);
      }
      const data: GenerationResult = await res.json();
      setResult(data);
    } catch (err) {
      setApiError(err instanceof Error ? err.message : "生成题目时发生未知错误");
    } finally {
      setIsLoading(false);
    }
  }, [selectedFile]);

  return (
    <div>
      <div
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        className={`flex cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed py-20 text-center transition-colors ${
          isDragOver
            ? "border-primary bg-primary/5"
            : "border-border hover:border-primary/50"
        }`}
        onClick={() => inputRef.current?.click()}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") inputRef.current?.click();
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
          {isDragOver ? "释放文件以上传" : "上传教材文件开始出题"}
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
          <CardContent className="flex items-center justify-between py-3">
            <div className="flex items-center gap-3">
              <span className="inline-flex size-8 items-center justify-center rounded bg-primary/10 text-xs font-medium text-primary">
                {selectedFile.name.split(".").pop()?.toUpperCase()}
              </span>
              <div>
                <p className="text-sm font-medium text-foreground">{selectedFile.name}</p>
                <p className="text-xs text-muted-foreground">{formatFileSize(selectedFile.size)}</p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <Button
                size="sm"
                onClick={handleGenerate}
                disabled={isLoading}
              >
                {isLoading ? "生成中..." : "生成题目"}
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
          <CardContent className="py-3 text-sm text-destructive">{apiError}</CardContent>
        </Card>
      )}

      {result && (
        <div className="mt-6 space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>生成统计</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex gap-6 text-sm">
                <span>总计: {result.generation_stats.total}</span>
                <span className="text-green-600">成功: {result.generation_stats.successful}</span>
                <span className="text-red-600">失败: {result.generation_stats.failed}</span>
              </div>
            </CardContent>
          </Card>

          {result.questions
            .filter((q) => q.status === "success")
            .map((q) => (
              <Card key={q.id}>
                <CardHeader>
                  <CardTitle className="text-base">
                    {q.id}. {q.stem_text}
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-1 text-sm">
                  {q.options.map((opt) => (
                    <div key={opt.label}>
                      <span className="font-medium">{opt.label}.</span> {opt.text}
                    </div>
                  ))}
                  <div className="mt-2 text-xs text-muted-foreground">
                    知识点: {q.knowledge_point_name} | 类型: {q.question_type}
                  </div>
                </CardContent>
              </Card>
            ))}
        </div>
      )}
    </div>
  );
}
