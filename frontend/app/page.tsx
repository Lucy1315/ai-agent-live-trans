"use client";

import { useState } from "react";
import { useSSE } from "@/hooks/useSSE";
import SourceInput from "@/components/SourceInput";
import SubtitleDisplay from "@/components/SubtitleDisplay";
import type { SubtitleSize } from "@/components/SubtitleDisplay";
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

const SIZE_LABELS: { value: SubtitleSize; label: string }[] = [
  { value: "sm", label: "작게" },
  { value: "md", label: "일반" },
  { value: "lg", label: "크게" },
];

const DOMAINS = [
  { value: "general", label: "일반" },
  { value: "pharma", label: "제약/바이오" },
  { value: "tech", label: "IT/AI" },
  { value: "finance", label: "금융" },
];

const LANGUAGES = [
  { value: "ko", label: "한국어" },
  { value: "ja", label: "日本語" },
  { value: "zh", label: "中文" },
];

const GPT_MODELS = [
  { value: "gpt-4o", label: "GPT-4o" },
  { value: "gpt-4o-mini", label: "GPT-4o-mini" },
];

const WHISPER_MODELS = [
  { value: "base", label: "Base" },
  { value: "small", label: "Small" },
  { value: "medium", label: "Medium" },
  { value: "large-v3", label: "Large" },
];

export default function Home() {
  const [activeUrl, setActiveUrl] = useState<string | null>(null);
  const [subtitleSize, setSubtitleSize] = useState<SubtitleSize>("md");
  const [domain, setDomain] = useState("general");
  const [targetLang, setTargetLang] = useState("ko");
  const [gptModel, setGptModel] = useState("gpt-4o");
  const [whisperModel, setWhisperModel] = useState("base");
  const [glossary, setGlossary] = useState<Record<string, string>>({});

  const { enText, koText, insights, transcript, isConnected, hasFirstSubtitle, disconnect } =
    useSSE(activeUrl, { domain, targetLang, gptModel, whisperModel });

  const videoId = activeUrl ? extractYouTubeId(activeUrl) : null;

  const handleStart = (url: string) => {
    setActiveUrl(url);
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

  const handleGlossaryUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const formData = new FormData();
    formData.append("file", file);
    const backendUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    const res = await fetch(`${backendUrl}/api/glossary`, { method: "POST", body: formData });
    const data = await res.json();
    setGlossary(data.glossary || {});
  };

  return (
    <main className="h-screen flex flex-col p-4 gap-4">
      <div className="flex flex-col gap-3">
        <div className="flex items-center gap-4">
          <h1 className="text-xl font-bold shrink-0">Live-Trans</h1>
          <SourceInput onSubmit={handleStart} disabled={isConnected} />
          <select
            value={domain}
            onChange={(e) => setDomain(e.target.value)}
            disabled={isConnected}
            className="px-2 py-1.5 text-xs bg-gray-700 text-gray-200 rounded border border-gray-600 shrink-0 disabled:opacity-50"
          >
            {DOMAINS.map(({ value, label }) => (
              <option key={value} value={value}>{label}</option>
            ))}
          </select>
          <div className="flex gap-1 shrink-0">
            {SIZE_LABELS.map(({ value, label }) => (
              <button
                key={value}
                onClick={() => setSubtitleSize(value)}
                className={`px-2 py-1 text-xs rounded ${
                  subtitleSize === value
                    ? "bg-blue-600 text-white"
                    : "bg-gray-700 text-gray-300 hover:bg-gray-600"
                }`}
              >
                {label}
              </button>
            ))}
          </div>
        </div>

        {/* Second row: model & language settings */}
        <div className="flex items-center gap-3 flex-wrap">
          <div className="flex items-center gap-1.5">
            <span className="text-xs text-gray-500">번역 언어</span>
            <select
              value={targetLang}
              onChange={(e) => setTargetLang(e.target.value)}
              disabled={isConnected}
              className="px-2 py-1.5 text-xs bg-gray-700 text-gray-200 rounded border border-gray-600 disabled:opacity-50"
            >
              {LANGUAGES.map(({ value, label }) => (
                <option key={value} value={value}>{label}</option>
              ))}
            </select>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="text-xs text-gray-500">GPT 모델</span>
            <select
              value={gptModel}
              onChange={(e) => setGptModel(e.target.value)}
              disabled={isConnected}
              className="px-2 py-1.5 text-xs bg-gray-700 text-gray-200 rounded border border-gray-600 disabled:opacity-50"
            >
              {GPT_MODELS.map(({ value, label }) => (
                <option key={value} value={value}>{label}</option>
              ))}
            </select>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="text-xs text-gray-500">Whisper</span>
            <select
              value={whisperModel}
              onChange={(e) => setWhisperModel(e.target.value)}
              disabled={isConnected}
              className="px-2 py-1.5 text-xs bg-gray-700 text-gray-200 rounded border border-gray-600 disabled:opacity-50"
            >
              {WHISPER_MODELS.map(({ value, label }) => (
                <option key={value} value={value}>{label}</option>
              ))}
            </select>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="text-xs text-gray-500">용어집</span>
            <label className="px-2 py-1.5 text-xs bg-gray-700 text-gray-200 rounded border border-gray-600 cursor-pointer hover:bg-gray-600">
              {Object.keys(glossary).length > 0 ? `${Object.keys(glossary).length}개 용어` : "CSV 업로드"}
              <input type="file" accept=".csv" className="hidden" onChange={handleGlossaryUpload} disabled={isConnected} />
            </label>
          </div>
        </div>
      </div>

      <div className="flex-1 flex gap-4 min-h-0">
        <div className="flex-1 relative bg-gray-800 rounded-lg flex items-center justify-center overflow-hidden">
          {!isConnected && !koText && (
            <p className="text-gray-500">URL을 입력하여 시작하세요</p>
          )}
          {videoId && hasFirstSubtitle && (
            <iframe
              className="absolute inset-0 w-full h-full"
              src={`https://www.youtube.com/embed/${videoId}?autoplay=1`}
              allow="autoplay; encrypted-media; fullscreen"
              allowFullScreen
            />
          )}
          {videoId && !hasFirstSubtitle && isConnected && (
            <p className="text-gray-400 text-sm">오디오 분석 중...</p>
          )}
          <SubtitleDisplay en={enText} ko={koText} size={subtitleSize} />
        </div>

        <div className="w-80 flex flex-col gap-4">
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
        transcript={transcript}
      />
    </main>
  );
}
