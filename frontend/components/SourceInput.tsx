"use client";

import { useState } from "react";

interface Props {
  onSubmit: (url: string) => void;
  onUrlChange?: (url: string) => void;
  disabled: boolean;
}

export default function SourceInput({ onSubmit, onUrlChange, disabled }: Props) {
  const [url, setUrl] = useState("");

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setUrl(e.target.value);
    onUrlChange?.(e.target.value);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (url.trim()) onSubmit(url.trim());
  };

  return (
    <form onSubmit={handleSubmit} className="flex gap-2">
      <input
        type="text"
        value={url}
        onChange={handleChange}
        placeholder="YouTube URL을 입력하세요"
        disabled={disabled}
        className="flex-1 px-4 py-2 bg-gray-800 border border-gray-600 rounded-lg
                   text-white placeholder-gray-400 focus:outline-none focus:border-blue-500"
      />
      <button
        type="submit"
        disabled={disabled || !url.trim()}
        className="px-6 py-2 bg-blue-600 rounded-lg font-medium
                   hover:bg-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
      >
        시작
      </button>
    </form>
  );
}
