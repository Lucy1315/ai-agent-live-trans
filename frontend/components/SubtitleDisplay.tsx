"use client";

export type SubtitleSize = "sm" | "md" | "lg";

const sizeMap: Record<SubtitleSize, { en: string; ko: string }> = {
  sm: { en: "text-[11px]", ko: "text-[14px]" },
  md: { en: "text-[14px]", ko: "text-[18px]" },
  lg: { en: "text-[18px]", ko: "text-[24px]" },
};

interface Props {
  en: string;
  ko: string;
  size: SubtitleSize;
}

export default function SubtitleDisplay({ en, ko, size }: Props) {
  if (!ko) return null;

  const s = sizeMap[size];

  return (
    <div className="absolute bottom-6 left-1/2 -translate-x-1/2 max-w-[85%] z-10 pointer-events-none">
      <div className="px-4 py-2 rounded-md bg-black/75 text-center space-y-1">
        <p className={`${s.en} text-gray-400`}>{en}</p>
        <p className={`${s.ko} text-white leading-relaxed`}>{ko}</p>
      </div>
    </div>
  );
}
