"use client";

import { useState, useEffect, useCallback, useRef } from "react";

interface Subtitle {
  start: number;
  end: number;
  text: string;
}

interface SSEState {
  subtitles: Subtitle[];
  chunkSummaries: { index: number; summary: string }[];
  finalSummary: string;
  insights: string;
  progress: number;
  phase: string;
  isConnected: boolean;
  isComplete: boolean;
  error: string | null;
}

export function useSSE(url: string | null) {
  const [state, setState] = useState<SSEState>({
    subtitles: [],
    chunkSummaries: [],
    finalSummary: "",
    insights: "",
    progress: 0,
    phase: "",
    isConnected: false,
    isComplete: false,
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
      `${backendUrl}/api/stream?url=${encodeURIComponent(url)}`
    );
    sourceRef.current = source;

    source.onopen = () => {
      setState((prev) => ({ ...prev, isConnected: true, error: null }));
    };

    source.addEventListener("subtitles", (e) => {
      const data = JSON.parse(e.data);
      setState((prev) => ({ ...prev, subtitles: data.subtitles }));
    });

    source.addEventListener("progress", (e) => {
      const data = JSON.parse(e.data);
      setState((prev) => ({
        ...prev,
        progress: data.progress,
        phase: data.phase,
      }));
    });

    source.addEventListener("chunk_summary", (e) => {
      const data = JSON.parse(e.data);
      setState((prev) => ({
        ...prev,
        chunkSummaries: [...prev.chunkSummaries, data],
      }));
    });

    source.addEventListener("final_summary", (e) => {
      const data = JSON.parse(e.data);
      setState((prev) => ({ ...prev, finalSummary: data.summary }));
    });

    source.addEventListener("insights", (e) => {
      const data = JSON.parse(e.data);
      setState((prev) => ({ ...prev, insights: data.insights }));
    });

    source.addEventListener("complete", () => {
      setState((prev) => ({ ...prev, isComplete: true, isConnected: false }));
      source.close();
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
  }, [url, disconnect]);

  return { ...state, disconnect };
}
