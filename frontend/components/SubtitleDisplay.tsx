"use client";

interface Props {
  text: string;
  isRefined: boolean;
}

export default function SubtitleDisplay({ text, isRefined }: Props) {
  if (!text) return null;

  return (
    <div className="absolute bottom-8 left-1/2 -translate-x-1/2 max-w-[80%]">
      <div
        className={`subtitle-container ${isRefined ? "subtitle-fade-enter" : ""}`}
        key={isRefined ? "refined" : "fast"}
      >
        {text}
      </div>
      {!isRefined && (
        <div className="text-center mt-1 text-xs text-gray-400">임시 번역</div>
      )}
    </div>
  );
}
