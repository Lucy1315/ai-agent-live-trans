"use client";

interface Props {
  isConnected: boolean;
  onStop: () => void;
  glossary: Record<string, string>;
  insights: string[];
}

export default function ControlBar({
  isConnected,
  onStop,
  glossary,
  insights,
}: Props) {
  const handleExport = () => {
    const data = {
      glossary,
      insights,
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
        <button
          onClick={handleExport}
          className="px-4 py-1.5 bg-gray-600 rounded text-sm hover:bg-gray-500"
        >
          내보내기
        </button>
      </div>
    </div>
  );
}
