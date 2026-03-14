"use client";

interface Props {
  chunkSummaries: { index: number; summary: string }[];
  finalSummary: string;
  insights: string;
  progress: number;
  phase: string;
}

const PHASE_LABELS: Record<string, string> = {
  extracting: "자막 추출 중...",
  summarizing: "요약 생성 중...",
  finalizing: "통합 분석 중...",
  complete: "분석 완료",
};

export default function InsightPanel({
  chunkSummaries,
  finalSummary,
  insights,
  progress,
  phase,
}: Props) {
  return (
    <div className="bg-gray-800 rounded-lg p-4 h-full overflow-y-auto flex flex-col gap-4">
      {/* 진행률 */}
      {phase && phase !== "complete" && (
        <div>
          <div className="flex justify-between text-xs text-gray-400 mb-1">
            <span>{PHASE_LABELS[phase] || phase}</span>
            <span>{Math.round(progress * 100)}%</span>
          </div>
          <div className="w-full bg-gray-700 rounded-full h-2">
            <div
              className="bg-blue-500 h-2 rounded-full transition-all duration-300"
              style={{ width: `${progress * 100}%` }}
            />
          </div>
        </div>
      )}

      {/* 청크별 요약 */}
      {chunkSummaries.length > 0 && !finalSummary && (
        <div>
          <h2 className="text-sm font-semibold text-gray-400 mb-2 uppercase tracking-wide">
            파트별 요약
          </h2>
          <div className="space-y-2">
            {chunkSummaries.map((cs) => (
              <div key={cs.index} className="text-sm text-gray-300 border-l-2 border-blue-500 pl-3">
                <span className="text-blue-400 text-xs">파트 {cs.index + 1}</span>
                <p className="mt-1">{cs.summary}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 통합 요약 */}
      {finalSummary && (
        <div>
          <h2 className="text-sm font-semibold text-gray-400 mb-2 uppercase tracking-wide">
            통합 요약
          </h2>
          <div className="text-sm text-gray-300 whitespace-pre-wrap">{finalSummary}</div>
        </div>
      )}

      {/* 인사이트 */}
      {insights && (
        <div>
          <h2 className="text-sm font-semibold text-blue-400 mb-2 uppercase tracking-wide">
            인사이트
          </h2>
          <div className="text-sm text-gray-300 whitespace-pre-wrap">{insights}</div>
        </div>
      )}

      {/* 대기 상태 */}
      {!phase && chunkSummaries.length === 0 && (
        <p className="text-gray-500 text-sm">URL을 입력하면 분석이 시작됩니다</p>
      )}
    </div>
  );
}
