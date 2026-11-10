import { useEffect, useRef } from 'react';

/** 固定间隔轮询；组件卸载或 enabled=false 时停止。 */
export function usePolling(callback: () => void, intervalMs: number, enabled = true): void {
  const saved = useRef(callback);
  saved.current = callback;

  useEffect(() => {
    if (!enabled || intervalMs <= 0) return;
    const timer = window.setInterval(() => saved.current(), intervalMs);
    return () => window.clearInterval(timer);
  }, [intervalMs, enabled]);
}
