"use client";

export type SubtitleSize = "small" | "standard" | "large";

const sizeClasses: Record<SubtitleSize, string> = {
  small: "text-sm px-3 py-1.5",
  standard: "text-base px-4 py-2",
  large: "text-xl px-5 py-3",
};

interface Props {
  text: string;
  isRefined: boolean;
  size: SubtitleSize;
  onSizeChange: (size: SubtitleSize) => void;
}

export default function SubtitleDisplay({ text, isRefined, size, onSizeChange }: Props) {
  return (
    <>
      {/* 자막 크기 조절 탭 */}
      <div className="absolute top-3 right-3 z-20 flex items-center bg-gray-900/80 rounded-md overflow-hidden text-xs pointer-events-auto">
        <span className="px-2.5 py-1 text-gray-400">자막크기</span>
        {(["small", "standard", "large"] as SubtitleSize[]).map((s) => (
          <button
            key={s}
            onClick={() => onSizeChange(s)}
            className={`px-2.5 py-1 transition-colors ${
              size === s
                ? "bg-blue-600 text-white"
                : "text-gray-400 hover:text-white hover:bg-gray-700"
            }`}
          >
            {s === "small" ? "작게" : s === "standard" ? "표준" : "크게"}
          </button>
        ))}
      </div>

      {/* 자막 표시 — pointer-events-none so YouTube controls remain clickable */}
      {text && (
        <div className="absolute bottom-8 left-1/2 -translate-x-1/2 max-w-[80%] z-10 pointer-events-none">
          <div
            className={`subtitle-container ${sizeClasses[size]} ${isRefined ? "subtitle-fade-enter border-l-2 border-blue-400" : ""}`}
            key={isRefined ? "refined" : "fast"}
          >
            {text}
          </div>
        </div>
      )}
    </>
  );
}
