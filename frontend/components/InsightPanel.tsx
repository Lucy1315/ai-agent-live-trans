"use client";

interface Props {
  insights: string[];
}

export default function InsightPanel({ insights }: Props) {
  return (
    <div className="bg-gray-800 rounded-lg p-4 h-full overflow-y-auto">
      <h2 className="text-sm font-semibold text-gray-400 mb-3 uppercase tracking-wide">
        핵심 요약
      </h2>
      {insights.length === 0 ? (
        <p className="text-gray-500 text-sm">요약이 곧 표시됩니다</p>
      ) : (
        <ul className="space-y-2">
          {insights.map((point, i) => (
            <li key={i} className="text-sm text-gray-300 flex gap-2">
              <span className="text-blue-400 shrink-0">#{i + 1}</span>
              <span>{point}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
