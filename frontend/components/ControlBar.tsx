"use client";

interface Props {
  isConnected: boolean;
  onStop: () => void;
  onGenerateFinalSummary: () => void;
  glossary: Record<string, string>;
  insights: string[];
  finalSummary: {
    final_summary?: string;
    key_insights?: string[];
    trends?: string[];
    action_items?: string[];
  } | null;
  isGenerating: boolean;
}

export default function ControlBar({
  isConnected,
  onStop,
  onGenerateFinalSummary,
  glossary,
  insights,
  finalSummary,
  isGenerating,
}: Props) {
  const buildTextContent = () => {
    const now = new Date().toISOString().split("T")[0];
    const lines: string[] = [];

    lines.push("═══════════════════════════════════════");
    lines.push("          영상 분석 노트");
    lines.push("═══════════════════════════════════════");
    lines.push(`분석일: ${now}`);
    lines.push("");

    if (finalSummary?.final_summary) {
      lines.push("───────────────────────────────────────");
      lines.push("■ 통합 요약");
      lines.push("───────────────────────────────────────");
      lines.push(finalSummary.final_summary);
      lines.push("");
    }

    if (finalSummary?.key_insights?.length) {
      lines.push("───────────────────────────────────────");
      lines.push("■ 핵심 시사점");
      lines.push("───────────────────────────────────────");
      finalSummary.key_insights.forEach((item, i) => {
        lines.push(`  ${i + 1}. ${item}`);
      });
      lines.push("");
    }

    if (finalSummary?.trends?.length) {
      lines.push("───────────────────────────────────────");
      lines.push("■ 향후 전망 및 트렌드");
      lines.push("───────────────────────────────────────");
      finalSummary.trends.forEach((item, i) => {
        lines.push(`  ${i + 1}. ${item}`);
      });
      lines.push("");
    }

    if (finalSummary?.action_items?.length) {
      lines.push("───────────────────────────────────────");
      lines.push("■ 액션 아이템");
      lines.push("───────────────────────────────────────");
      finalSummary.action_items.forEach((item, i) => {
        lines.push(`  ${i + 1}. ${item}`);
      });
      lines.push("");
    }

    if (insights.length > 0) {
      lines.push("───────────────────────────────────────");
      lines.push("■ 실시간 요약 포인트");
      lines.push("───────────────────────────────────────");
      insights.forEach((point, i) => {
        lines.push(`  ${i + 1}. ${point}`);
      });
      lines.push("");
    }

    if (Object.keys(glossary).length > 0) {
      lines.push("───────────────────────────────────────");
      lines.push("■ 용어집");
      lines.push("───────────────────────────────────────");
      for (const [term, def] of Object.entries(glossary)) {
        lines.push(`  • ${term}: ${def}`);
      }
      lines.push("");
    }

    lines.push("═══════════════════════════════════════");
    return lines.join("\n");
  };

  const handleExportText = () => {
    const content = buildTextContent();
    const blob = new Blob([content], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `analysis-${Date.now()}.txt`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleExportJson = () => {
    const data = {
      glossary,
      insights,
      finalSummary,
      exportedAt: new Date().toISOString(),
    };
    const blob = new Blob([JSON.stringify(data, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `live-trans-export-${Date.now()}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const hasContent = insights.length > 0 || finalSummary;

  return (
    <div className="flex items-center justify-between px-4 py-3 bg-gray-800 rounded-lg">
      <div className="flex items-center gap-2">
        <div
          className={`w-2 h-2 rounded-full ${isConnected ? "bg-green-400" : "bg-gray-500"}`}
        />
        <span className="text-sm text-gray-400">
          {isConnected ? "실시간 수신 중" : "대기 중"}
        </span>
      </div>
      <div className="flex gap-2">
        {isConnected && (
          <button
            onClick={onStop}
            className="px-4 py-1.5 bg-red-600 rounded text-sm hover:bg-red-500"
          >
            정지
          </button>
        )}
        {!isConnected && insights.length > 0 && !finalSummary && (
          <button
            onClick={onGenerateFinalSummary}
            disabled={isGenerating}
            className="px-4 py-1.5 bg-blue-600 rounded text-sm hover:bg-blue-500 disabled:opacity-50"
          >
            {isGenerating ? "생성 중..." : "최종 인사이트 생성"}
          </button>
        )}
        {hasContent && (
          <>
            <button
              onClick={handleExportText}
              className="px-4 py-1.5 bg-gray-600 rounded text-sm hover:bg-gray-500"
            >
              내보내기 (TXT)
            </button>
            <button
              onClick={handleExportJson}
              className="px-4 py-1.5 bg-gray-600 rounded text-sm hover:bg-gray-500"
            >
              내보내기 (JSON)
            </button>
          </>
        )}
      </div>
    </div>
  );
}
