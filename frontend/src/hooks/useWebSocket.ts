import { useEffect, useRef, useState, useCallback } from "react";

type WsStatus = "connecting" | "connected" | "disconnected";

export function useWebSocket<T = unknown>(path: string) {
  const [messages, setMessages] = useState<T[]>([]);
  const [status, setStatus] = useState<WsStatus>("connecting");
  const wsRef = useRef<WebSocket | null>(null);

  const connect = useCallback(() => {
    const wsBase = import.meta.env.VITE_WS_BASE_URL ?? `ws://${window.location.host}`;
    const ws = new WebSocket(`${wsBase}${path}`);
    wsRef.current = ws;

    ws.onopen = () => setStatus("connected");
    ws.onclose = () => {
      setStatus("disconnected");
      // 5초 후 재연결
      setTimeout(connect, 5000);
    };
    ws.onerror = () => setStatus("disconnected");
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data) as T;
        setMessages((prev) => [data, ...prev].slice(0, 50)); // 최대 50건 유지
      } catch {
        // ignore parse errors
      }
    };
  }, [path]);

  useEffect(() => {
    connect();
    return () => wsRef.current?.close();
  }, [connect]);

  return { messages, status };
}
