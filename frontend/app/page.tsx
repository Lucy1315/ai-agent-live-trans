"use client";

import { useState } from "react";
import { useSSE } from "@/hooks/useSSE";
import SourceInput from "@/components/SourceInput";
import InsightPanel from "@/components/InsightPanel";
import ControlBar from "@/components/ControlBar";

function extractYouTubeId(url: string): string | null {
  const patterns = [
    /(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([a-zA-Z0-9_-]{11})/,
    /youtube\.com\/live\/([a-zA-Z0-9_-]{11})/,
  ];
  for (const p of patterns) {
    const m = url.match(p);
    if (m) return m[1];
  }
  return null;
}

export default function Home() {
  const [activeUrl, setActiveUrl] = useState<string | null>(null);

  const {
    subtitles,
    chunkSummaries,
    finalSummary,
    insights,
    progress,
    phase,
    isConnected,
    isComplete,
    disconnect,
  } = useSSE(activeUrl);

  const videoId = activeUrl ? extractYouTubeId(activeUrl) : null;

  const handleStart = (url: string) => setActiveUrl(url);

  const handleStop = async () => {
    if (activeUrl) {
      const backendUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      await fetch(`${backendUrl}/api/stop?url=${encodeURIComponent(activeUrl)}`, {
        method: "POST",
      });
    }
    disconnect();
    setActiveUrl(null);
  };

  const handleSummarizeNow = async () => {
    if (activeUrl) {
      const backendUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      await fetch(
        `${backendUrl}/api/summarize-now?url=${encodeURIComponent(activeUrl)}`,
        { method: "POST" }
      );
    }
  };

  return (
    <main className="h-screen flex flex-col p-4 gap-4">
      <div className="flex items-center gap-4">
        <h1 className="text-xl font-bold shrink-0">Live-Trans</h1>
        <SourceInput onSubmit={handleStart} disabled={isConnected} />
      </div>

      <div className="flex-1 flex gap-4 min-h-0">
        {/* 영상 영역 */}
        <div className="flex-1 relative bg-gray-800 rounded-lg flex items-center justify-center overflow-hidden">
          {!activeUrl && (
            <p className="text-gray-500">YouTube URL을 입력하여 시작하세요</p>
          )}
          {videoId && (
            <iframe
              className="absolute inset-0 w-full h-full"
              src={`https://www.youtube.com/embed/${videoId}?autoplay=1`}
              allow="autoplay; encrypted-media; fullscreen"
              allowFullScreen
            />
          )}
          {activeUrl && !videoId && (
            <p className="text-gray-400 text-sm">자막 추출 중...</p>
          )}
        </div>

        {/* 분석 패널 */}
        <div className="w-96 flex flex-col gap-4">
          <div className="flex-1 min-h-0">
            <InsightPanel
              chunkSummaries={chunkSummaries}
              finalSummary={finalSummary}
              insights={insights}
              progress={progress}
              phase={phase}
            />
          </div>
        </div>
      </div>

      <ControlBar
        isConnected={isConnected}
        isComplete={isComplete}
        onStop={handleStop}
        onSummarizeNow={handleSummarizeNow}
        finalSummary={finalSummary}
        insights={insights}
      />
    </main>
  );
}
