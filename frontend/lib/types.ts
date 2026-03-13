// lib/types.ts
export interface SubtitleEvent {
  text: string;
  chunk_id: number;
}

export interface GlossaryEvent {
  [term: string]: string;
}

export interface SummaryEvent {
  point: string;
  index: number;
}

export type SSEEventType =
  | "fast_subtitle"
  | "refined_subtitle"
  | "glossary"
  | "summary"
  | "error";
