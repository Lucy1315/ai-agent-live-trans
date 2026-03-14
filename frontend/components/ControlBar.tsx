"use client";

interface Props {
  isConnected: boolean;
  isComplete: boolean;
  onStop: () => void;
  onSummarizeNow: () => void;
  finalSummary: string;
  insights: string;
}

export default function ControlBar({
  isConnected,
  isComplete,
  onStop,
  onSummarizeNow,
  finalSummary,
  insights,
}: Props) {
  const handleExportMarkdown = () => {
    let md = `# 영상 분석 노트\n\n`;
    md += `**분석일:** ${new Date().toISOString().split("T")[0]}\n\n---\n\n`;
    if (finalSummary) {
      md += `## 통합 요약\n\n${finalSummary}\n\n---\n\n`;
    }
    if (insights) {
      md += `${insights}\n\n`;
    }

    const blob = new Blob([md], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `analysis-${Date.now()}.md`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="flex items-center justify-between px-4 py-3 bg-gray-800 rounded-lg">
      <div className="flex items-center gap-2">
        <div
          className={`w-2 h-2 rounded-full ${
            isConnected ? "bg-green-400 animate-pulse" : isComplete ? "bg-blue-400" : "bg-gray-500"
          }`}
        />
        <span className="text-sm text-gray-400">
          {isConnected ? "분석 중" : isComplete ? "분석 완료" : "대기 중"}
        </span>
      </div>
      <div className="flex gap-2">
        {isConnected && (
          <>
            <button
              onClick={onSummarizeNow}
              className="px-4 py-1.5 bg-blue-600 rounded text-sm hover:bg-blue-500"
            >
              지금 요약
            </button>
            <button
              onClick={onStop}
              className="px-4 py-1.5 bg-red-600 rounded text-sm hover:bg-red-500"
            >
              정지
            </button>
          </>
        )}
        {(isComplete || finalSummary) && (
          <button
            onClick={handleExportMarkdown}
            className="px-4 py-1.5 bg-gray-600 rounded text-sm hover:bg-gray-500"
          >
            내보내기 (MD)
          </button>
        )}
      </div>
    </div>
  );
}
