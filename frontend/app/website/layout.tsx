import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "拍拍搭 Paipaida｜在真实空间里编辑软装",
  description: "从真实房间照片出发，在效果图里替换、改色、删除软装；确认后查看对应的 2.5D 空间示意。",
};

export default function WebsiteLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return children;
}
