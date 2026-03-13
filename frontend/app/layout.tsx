import type { Metadata } from "next";
import "pretendard/dist/web/static/pretendard.css";
import "./globals.css";

export const metadata: Metadata = {
  title: "Live-Trans",
  description: "실시간 웨비나 통번역 시스템",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="ko">
      <body className="font-pretendard bg-gray-900 text-white min-h-screen">
        {children}
      </body>
    </html>
  );
}
