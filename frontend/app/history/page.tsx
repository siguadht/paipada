"use client";

import { ArrowRight, ClockCounterClockwise, HouseLine, SpinnerGap } from "@phosphor-icons/react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { ApiError, api, Design, getToken } from "@/lib/api";
import { useProtectedImage } from "@/lib/use-protected-image";
import { WorkbenchSidebar } from "@/components/workbench-sidebar";

function HistoryCard({ design }: { design: Design }) {
  const image = useProtectedImage(design.front_image_url || design.photo_url);
  return <Link href={`/design/${design.design_id}`} className="history-card">
    <div className="history-thumb">{image.url ? <img src={image.url} alt="方案缩略图" /> : <HouseLine size={28} />}</div>
    <div className="history-info"><small>{design.created_at ? new Date(design.created_at).toLocaleDateString("zh-CN") : "最近创建"}</small><strong>{design.user_input}</strong><span>{design.current_step}</span></div>
    <ArrowRight size={20} />
  </Link>;
}

export default function HistoryPage() {
  const router = useRouter();
  const [designs, setDesigns] = useState<Design[] | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    if (!getToken()) { router.push("/"); return; }
    api.listDesigns().then((result) => setDesigns(result.designs)).catch((failure) => {
      if (failure instanceof ApiError && failure.status === 401) router.push("/");
      else setError(failure instanceof Error ? failure.message : "历史方案加载失败");
    });
  }, [router]);
  return <main className="site-shell history-page workbench-shell">
    <header className="site-header"><Link href="/" className="brand">拍拍搭<span className="brand-dot">.</span></Link><nav className="header-nav"><Link href="/">新建方案 <ArrowRight size={18} /></Link></nav></header>
    <div className="workbench-body"><WorkbenchSidebar active="history" /><div className="workbench-content history-content">
    <div className="history-heading"><p className="eyebrow">你的空间灵感</p><h1>我的方案<span className="heading-dot">.</span></h1><p>每一次尝试，都在离喜欢的家更近一步。</p></div>
    {error && <p className="error-message" role="alert">{error}</p>}
    {!designs ? <div className="page-loading"><SpinnerGap size={27} className="spin" /> 正在读取方案…</div> : designs.length === 0 ?
      <div className="empty-history"><ClockCounterClockwise size={33} /><h2>还没有方案</h2><p>从一张房间照片开始，做你的第一套软装方案。</p><Link className="primary-button" href="/">新建方案 <ArrowRight size={17} /></Link></div> :
      <div className="history-list">{designs.map((design) => <HistoryCard key={design.design_id} design={design} />)}</div>}
    </div></div>
  </main>;
}
