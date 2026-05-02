"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

const API_URL = "/api";

const ACCEPTED_EXTENSIONS = [".pdf", ".docx", ".txt"];
const ACCEPTED_MIME_TYPES = [
  "application/pdf",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
  "text/plain",
];

type HealthStatus = "checking" | "connected" | "disconnected";

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
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFile = useCallback((file: File) => {
    setError(null);
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
    if (inputRef.current) inputRef.current.value = "";
  }, []);

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
            <Button variant="ghost" size="sm" onClick={handleClear}>
              移除
            </Button>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
