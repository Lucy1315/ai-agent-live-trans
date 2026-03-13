"use client";

interface Props {
  glossary: Record<string, string>;
}

export default function GlossaryPanel({ glossary }: Props) {
  const entries = Object.entries(glossary);

  return (
    <div className="bg-gray-800 rounded-lg p-4 h-full overflow-y-auto">
      <h2 className="text-sm font-semibold text-gray-400 mb-3 uppercase tracking-wide">
        용어 사전
      </h2>
      {entries.length === 0 ? (
        <p className="text-gray-500 text-sm">아직 추출된 용어가 없습니다</p>
      ) : (
        <dl className="space-y-3">
          {entries.map(([term, definition]) => (
            <div key={term}>
              <dt className="term-highlight text-sm">{term}</dt>
              <dd className="text-gray-300 text-sm mt-0.5">{definition}</dd>
            </div>
          ))}
        </dl>
      )}
    </div>
  );
}
