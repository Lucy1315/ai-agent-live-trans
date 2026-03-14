"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import type { SubtitleEvent, GlossaryEvent, SummaryEvent } from "@/lib/types";

interface SSEState {
  subtitle: string;
  isRefined: boolean;
  chunkId: number;
  glossary: Record<string, string>;
  insights: string[];
  isConnected: boolean;
  error: string | null;
  firstSubtitleAt: number | null;
}

export function useSSE(url: string | null, key?: number) {
  const [state, setState] = useState<SSEState>({
    subtitle: "",
    isRefined: false,
    chunkId: 0,
    glossary: {},
    insights: [],
    isConnected: false,
    error: null,
    firstSubtitleAt: null,
  });

  const sourceRef = useRef<EventSource | null>(null);

  const disconnect = useCallback(() => {
    if (sourceRef.current) {
      sourceRef.current.close();
      sourceRef.current = null;
      setState((prev) => ({ ...prev, isConnected: false }));
    }
  }, []);

  useEffect(() => {
    if (!url) {
      disconnect();
      return;
    }

    const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";
    const source = new EventSource(
      `${backendUrl}/api/stream?url=${encodeURIComponent(url)}`
    );
    sourceRef.current = source;

    source.onopen = () => {
      setState((prev) => ({ ...prev, isConnected: true, error: null }));
    };

    source.addEventListener("fast_subtitle", (e) => {
      const data: SubtitleEvent = JSON.parse(e.data);
      setState((prev) => ({
        ...prev,
        subtitle: data.text,
        isRefined: false,
        chunkId: data.chunk_id,
        firstSubtitleAt: prev.firstSubtitleAt ?? Date.now(),
      }));
    });

    source.addEventListener("refined_subtitle", (e) => {
      const data: SubtitleEvent = JSON.parse(e.data);
      setState((prev) => ({
        ...prev,
        subtitle: data.text,
        isRefined: true,
        chunkId: data.chunk_id,
      }));
    });

    source.addEventListener("glossary", (e) => {
      const data: GlossaryEvent = JSON.parse(e.data);
      setState((prev) => ({
        ...prev,
        glossary: { ...prev.glossary, ...data },
      }));
    });

    source.addEventListener("summary", (e) => {
      const data: SummaryEvent = JSON.parse(e.data);
      setState((prev) => ({
        ...prev,
        insights: [...prev.insights, data.point],
      }));
    });

    source.addEventListener("error", (e) => {
      if (e instanceof MessageEvent) {
        const data = JSON.parse(e.data);
        setState((prev) => ({ ...prev, error: data.message }));
      }
    });

    source.onerror = () => {
      setState((prev) => ({ ...prev, isConnected: false }));
    };

    return () => {
      source.close();
    };
  }, [url, key, disconnect]);

  return { ...state, disconnect };
}
