"use client";

import { useState } from "react";
import { useSSE } from "@/hooks/useSSE";
import SourceInput from "@/components/SourceInput";
import SubtitleDisplay from "@/components/SubtitleDisplay";
import GlossaryPanel from "@/components/GlossaryPanel";
import InsightPanel from "@/components/InsightPanel";
import ControlBar from "@/components/ControlBar";

export default function Home() {
  const [activeUrl, setActiveUrl] = useState<string | null>(null);
  const { subtitle, isRefined, glossary, insights, isConnected, disconnect } =
    useSSE(activeUrl);

  const handleStart = (url: string) => {
    setActiveUrl(url);
  };

  const handleStop = async () => {
    if (activeUrl) {
      await fetch(`/api/stop?url=${encodeURIComponent(activeUrl)}`, {
        method: "POST",
      });
    }
    disconnect();
    setActiveUrl(null);
  };

  return (
    <main className="h-screen flex flex-col p-4 gap-4">
      <div className="flex items-center gap-4">
        <h1 className="text-xl font-bold shrink-0">Live-Trans</h1>
        <SourceInput onSubmit={handleStart} disabled={isConnected} />
      </div>

      <div className="flex-1 flex gap-4 min-h-0">
        <div className="flex-1 relative bg-gray-800 rounded-lg flex items-center justify-center">
          {!isConnected && !subtitle && (
            <p className="text-gray-500">URL을 입력하여 시작하세요</p>
          )}
          <SubtitleDisplay text={subtitle} isRefined={isRefined} />
        </div>

        <div className="w-80 flex flex-col gap-4">
          <div className="flex-1 min-h-0">
            <GlossaryPanel glossary={glossary} />
          </div>
          <div className="flex-1 min-h-0">
            <InsightPanel insights={insights} />
          </div>
        </div>
      </div>

      <ControlBar
        isConnected={isConnected}
        onStop={handleStop}
        glossary={glossary}
        insights={insights}
      />
    </main>
  );
}
