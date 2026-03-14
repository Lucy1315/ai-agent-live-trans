"use client";

import { useState, useEffect, useCallback, useRef } from "react";

interface SSEOptions {
  domain: string;
  targetLang: string;
  gptModel: string;
  whisperModel: string;
}

interface SSEState {
  enText: string;
  koText: string;
  chunkId: number;
  insights: string[];
  transcript: Array<{ chunkId: number; en: string; ko: string }>;
  isConnected: boolean;
  hasFirstSubtitle: boolean;
  error: string | null;
}

export type { SSEOptions };

export function useSSE(url: string | null, options: SSEOptions) {
  const [state, setState] = useState<SSEState>({
    enText: "",
    koText: "",
    chunkId: 0,
    insights: [],
    transcript: [],
    isConnected: false,
    hasFirstSubtitle: false,
    error: null,
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

    const backendUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    const source = new EventSource(
      `${backendUrl}/api/stream?url=${encodeURIComponent(url)}&domain=${encodeURIComponent(options.domain)}&target_lang=${encodeURIComponent(options.targetLang)}&gpt_model=${encodeURIComponent(options.gptModel)}&whisper_model=${encodeURIComponent(options.whisperModel)}`
    );
    sourceRef.current = source;

    source.onopen = () => {
      setState((prev) => ({ ...prev, isConnected: true, error: null }));
    };

    source.addEventListener("subtitle", (e) => {
      const data = JSON.parse(e.data);
      setState((prev) => ({
        ...prev,
        enText: data.en,
        koText: data.ko,
        chunkId: data.chunk_id,
        hasFirstSubtitle: true,
        transcript: [...prev.transcript, { chunkId: data.chunk_id, en: data.en, ko: data.ko }],
      }));
    });

    source.addEventListener("summary", (e) => {
      const data = JSON.parse(e.data);
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
  }, [url, options.domain, options.targetLang, options.gptModel, options.whisperModel, disconnect]);

  return { ...state, disconnect };
}
