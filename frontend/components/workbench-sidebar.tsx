"use client";

import { ArrowRight, ClockCounterClockwise, FolderOpen, House, Lightbulb, List, PaintBrush, Plus, X } from "@phosphor-icons/react";
import Link from "next/link";
import { useState } from "react";

type Props = { active: "create" | "edit" | "history" | "homes"; onEdit?: () => void; onExamples?: () => void; projects?: { id: string; name: string }[]; selectedProjectId?: string; onProjectSelect?: (id: string) => void; onProjectOverview?: () => void };

export function WorkbenchSidebar({ active, onEdit, onExamples, projects, selectedProjectId, onProjectSelect, onProjectOverview }: Props) {
  const [open, setOpen] = useState(false);
  return <>
    <button className="workbench-menu-toggle" type="button" aria-label="打开侧边栏" aria-expanded={open} onClick={() => setOpen(true)}><List size={20} /></button>
    {open && <button type="button" className="workbench-sidebar-shade" aria-label="关闭侧边栏" onClick={() => setOpen(false)} />}
    <aside className={`workbench-sidebar ${open ? "is-open" : ""}`} aria-label="工作台侧边栏">
      <div className="workbench-side-top"><span>工作空间</span><button type="button" aria-label="关闭侧边栏" onClick={() => setOpen(false)}><X size={18} /></button></div>
      <Link className="workbench-new" href="/" onClick={() => setOpen(false)}><Plus size={17} weight="bold" />新建创作</Link>
      <div className="workbench-side-group"><small>创作</small>
        <Link className={active === "create" ? "active" : ""} href="/" onClick={() => setOpen(false)}><House size={18} />开始创作</Link>
        {onEdit ? <button type="button" className={active === "edit" ? "active" : ""} onClick={() => { onEdit(); setOpen(false); }}><PaintBrush size={18} />效果图编辑</button> : <Link href="/history" onClick={() => setOpen(false)}><PaintBrush size={18} />继续编辑方案</Link>}
        {onExamples && <button type="button" onClick={() => { onExamples(); setOpen(false); }}><Lightbulb size={18} />灵感示例</button>}
      </div>
      <div className="workbench-side-group"><small>项目</small><Link className={active === "homes" ? "active" : ""} href="/homes" onClick={() => { onProjectOverview?.(); setOpen(false); }}><FolderOpen size={18} />我的项目<ArrowRight className="side-trailing" size={14} /></Link>{projects?.map((project) => <button type="button" className={`workbench-project-link ${selectedProjectId === project.id ? "active" : ""}`} key={project.id} title={project.name} onClick={() => { onProjectSelect?.(project.id); setOpen(false); }}><span>{project.name}</span></button>)}<Link className={active === "history" ? "active" : ""} href="/history" onClick={() => setOpen(false)}><ClockCounterClockwise size={18} />全部方案<ArrowRight className="side-trailing" size={14} /></Link></div>
      <div className="workbench-side-foot">拍拍搭 <span>空间设计工作台</span></div>
    </aside>
  </>;
}
