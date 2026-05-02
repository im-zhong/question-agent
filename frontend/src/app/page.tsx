"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";

const API_URL = "/api";

type HealthStatus = "checking" | "connected" | "disconnected";

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
        <UploadPlaceholder />
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

function UploadPlaceholder() {
  return (
    <div className="flex flex-col items-center justify-center rounded-lg border-2 border-dashed border-border py-20 text-center">
      <div className="mb-4 text-4xl text-muted-foreground/50">
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
      <p className="mb-2 text-lg font-medium text-foreground">上传教材文件开始出题</p>
      <p className="mb-6 text-sm text-muted-foreground">支持 PDF、Word、纯文本格式</p>
      <Button variant="outline">选择文件</Button>
    </div>
  );
}
