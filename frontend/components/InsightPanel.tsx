"use client";

interface FinalSummary {
  final_summary?: string;
  key_insights?: string[];
  trends?: string[];
  action_items?: string[];
}

interface Props {
  insights: string[];
  finalSummary: FinalSummary | null;
}

export default function InsightPanel({ insights, finalSummary }: Props) {
  return (
    <div className="bg-gray-800 rounded-lg p-4 h-full overflow-y-auto flex flex-col gap-4">
      {/* 최종 인사이트 요약 */}
      {finalSummary && (
        <>
          {finalSummary.final_summary && (
            <div>
              <h2 className="text-sm font-semibold text-blue-400 mb-2 uppercase tracking-wide">
                통합 요약
              </h2>
              <p className="text-sm text-gray-300">{finalSummary.final_summary}</p>
            </div>
          )}

          {finalSummary.key_insights && finalSummary.key_insights.length > 0 && (
            <div>
              <h2 className="text-sm font-semibold text-blue-400 mb-2 uppercase tracking-wide">
                핵심 시사점
              </h2>
              <ul className="space-y-1">
                {finalSummary.key_insights.map((item, i) => (
                  <li key={i} className="text-sm text-gray-300 flex gap-2">
                    <span className="text-blue-400 shrink-0">•</span>
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {finalSummary.trends && finalSummary.trends.length > 0 && (
            <div>
              <h2 className="text-sm font-semibold text-green-400 mb-2 uppercase tracking-wide">
                향후 전망
              </h2>
              <ul className="space-y-1">
                {finalSummary.trends.map((item, i) => (
                  <li key={i} className="text-sm text-gray-300 flex gap-2">
                    <span className="text-green-400 shrink-0">•</span>
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {finalSummary.action_items && finalSummary.action_items.length > 0 && (
            <div>
              <h2 className="text-sm font-semibold text-yellow-400 mb-2 uppercase tracking-wide">
                액션 아이템
              </h2>
              <ul className="space-y-1">
                {finalSummary.action_items.map((item, i) => (
                  <li key={i} className="text-sm text-gray-300 flex gap-2">
                    <span className="text-yellow-400 shrink-0">•</span>
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          <hr className="border-gray-700" />
        </>
      )}

      {/* 실시간 요약 포인트 */}
      <div>
        <h2 className="text-sm font-semibold text-gray-400 mb-3 uppercase tracking-wide">
          실시간 요약
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
    </div>
  );
}
