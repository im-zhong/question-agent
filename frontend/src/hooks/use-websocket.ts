import { useCallback, useEffect, useRef, useState } from 'react';

export type ConnectionStatus = 'connected' | 'disconnected' | 'connecting';

interface UseWebSocketOptions {
  url: string;
  onMessage?: (data: { type: string; content: string }) => void;
}

export function useWebSocket({ url, onMessage }: UseWebSocketOptions) {
  const wsRef = useRef<WebSocket | null>(null);
  const [status, setStatus] = useState<ConnectionStatus>('disconnected');
  const onMessageRef = useRef(onMessage);
  onMessageRef.current = onMessage;

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    setStatus('connecting');
    const ws = new WebSocket(url);

    ws.onopen = () => {
      setStatus('connected');
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data) as { type: string; content: string };
        onMessageRef.current?.(data);
      } catch {
        // ignore malformed messages
      }
    };

    ws.onclose = () => {
      setStatus('disconnected');
    };

    ws.onerror = () => {
      setStatus('disconnected');
    };

    wsRef.current = ws;
  }, [url]);

  const disconnect = useCallback(() => {
    wsRef.current?.close();
    wsRef.current = null;
    setStatus('disconnected');
  }, []);

  const send = useCallback((data: { type: string; content: string }) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(data));
    }
  }, []);

  useEffect(() => {
    connect();
    return () => {
      wsRef.current?.close();
      wsRef.current = null;
    };
  }, [connect]);

  return { status, send, connect, disconnect };
}
