import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "拍拍搭 · 看见家的另一种可能",
  description: "上传房间照片，编辑软装，确认后生成 2.5D 方案。",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="zh-CN">
      <body>{children}</body>
    </html>
  );
}
