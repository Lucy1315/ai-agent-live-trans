"use client";

import { useState, useRef, useMemo } from "react";
import { useSSE } from "@/hooks/useSSE";
import SourceInput from "@/components/SourceInput";
import SubtitleDisplay, { type SubtitleSize } from "@/components/SubtitleDisplay";
import GlossaryPanel from "@/components/GlossaryPanel";
import InsightPanel from "@/components/InsightPanel";
import ControlBar from "@/components/ControlBar";
import YouTubePlayer, { type YouTubePlayerHandle } from "@/components/YouTubePlayer";

function extractYouTubeId(url: string): string | null {
  const patterns = [
    /(?:youtube\.com\/watch\?v=)([a-zA-Z0-9_-]{11})/,
    /(?:youtu\.be\/)([a-zA-Z0-9_-]{11})/,
    /(?:youtube\.com\/embed\/)([a-zA-Z0-9_-]{11})/,
    /(?:youtube\.com\/live\/)([a-zA-Z0-9_-]{11})/,
  ];
  for (const pattern of patterns) {
    const match = url.match(pattern);
    if (match) return match[1];
  }
  return null;
}

interface FinalSummary {
  final_summary?: string;
  key_insights?: string[];
  trends?: string[];
  action_items?: string[];
}

export default function Home() {
  const [activeUrl, setActiveUrl] = useState<string | null>(null);
  const [sessionKey, setSessionKey] = useState(0);
  const [finalSummary, setFinalSummary] = useState<FinalSummary | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [subtitleSize, setSubtitleSize] = useState<SubtitleSize>("standard");

  const playerRef = useRef<YouTubePlayerHandle>(null);

  const { subtitle, isRefined, glossary, insights, isConnected, disconnect } =
    useSSE(activeUrl, sessionKey);

  // Only show video after clicking Start
  const videoId = useMemo(
    () => (activeUrl ? extractYouTubeId(activeUrl) : null),
    [activeUrl]
  );

  const handleStart = (url: string) => {
    setFinalSummary(null);
    setSessionKey((k) => k + 1);
    setActiveUrl(url);
    // Unmute in the same click handler (user gesture) so browser allows audio
    playerRef.current?.unmute();
  };

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

  const handleGenerateFinalSummary = async () => {
    if (!activeUrl && insights.length === 0) return;
    setIsGenerating(true);
    try {
      const targetUrl = activeUrl || "";
      const res = await fetch(
        `/api/final-summary?url=${encodeURIComponent(targetUrl)}`,
        { method: "POST" }
      );
      const data = await res.json();
      if (data.status === "ok") {
        setFinalSummary({
          final_summary: data.final_summary,
          key_insights: data.key_insights,
          trends: data.trends,
          action_items: data.action_items,
        });
      }
    } catch (err) {
      console.error("Failed to generate final summary:", err);
    } finally {
      setIsGenerating(false);
    }
  };

  return (
    <main className="h-screen flex flex-col p-4 gap-4">
      <div className="flex items-center gap-4">
        <h1 className="text-xl font-bold shrink-0">Live-Trans</h1>
        <SourceInput
          onSubmit={handleStart}
          disabled={false}
        />
      </div>

      <div className="flex-1 flex gap-4 min-h-0">
        <div className="flex-1 relative bg-gray-800 rounded-lg flex items-center justify-center overflow-hidden">
          {!videoId && !subtitle && (
            <p className="text-gray-500">URL을 입력하여 시작하세요</p>
          )}
          {videoId && (
            <YouTubePlayer key={videoId} ref={playerRef} videoId={videoId} muted={false} />
          )}
          <SubtitleDisplay text={subtitle} isRefined={isRefined} size={subtitleSize} onSizeChange={setSubtitleSize} />
        </div>

        {/* 분석 패널 */}
        <div className="w-96 flex flex-col gap-4">
          <div className="flex-1 min-h-0">
            <GlossaryPanel glossary={glossary} />
          </div>
          <div className="flex-1 min-h-0">
            <InsightPanel insights={insights} finalSummary={finalSummary} />
          </div>
        </div>
      </div>

      <ControlBar
        isConnected={isConnected}
        isComplete={false}
        onStop={handleStop}
        onGenerateFinalSummary={handleGenerateFinalSummary}
        glossary={glossary}
        insights={insights}
        finalSummary={finalSummary}
        isGenerating={isGenerating}
      />
    </main>
  );
}
