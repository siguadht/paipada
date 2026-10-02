"use client";

import { ArrowLeft, ArrowRight, FolderOpen, MagnifyingGlass, Plus } from "@phosphor-icons/react";
import Link from "next/link";
import { useEffect, useState } from "react";
import { WorkbenchSidebar } from "@/components/workbench-sidebar";
import { HomeProject, api, getToken } from "@/lib/api";
import { useProtectedImage } from "@/lib/use-protected-image";

function ProjectCard({ project, onOpen }: { project: HomeProject; onOpen: () => void }) {
  const coverPath = project.spaces.find((space) => space.design.front_image_url)?.design.front_image_url || "";
  const cover = useProtectedImage(coverPath);
  return <button type="button" className="project-tile" onClick={onOpen} aria-label={`打开项目 ${project.name}`}>
    <span className="project-tile-visual">{cover.url ? <img src={cover.url} alt="" /> : <FolderOpen size={39} weight="thin" />}</span>
    <span className="project-tile-meta"><strong>{project.name}</strong><small>{project.spaces.length} 个空间 · {project.created_at ? new Date(project.created_at).toLocaleDateString("zh-CN") : "最近创建"}</small></span>
  </button>;
}

export default function HomesPage() {
  const [homes, setHomes] = useState<HomeProject[]>([]);
  const [selected, setSelected] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const [search, setSearch] = useState("");
  const [name, setName] = useState("");
  const [styleText, setStyleText] = useState("");
  const [styleFile, setStyleFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [ready, setReady] = useState(false);
  const [editing, setEditing] = useState(false);
  const [editName, setEditName] = useState("");
  const [editStyle, setEditStyle] = useState("");
  const [editPhoto, setEditPhoto] = useState<File | null>(null);

  useEffect(() => {
    if (!getToken()) { queueMicrotask(() => setReady(true)); return; }
    api.listHomes().then(({ homes: items }) => setHomes(items))
      .catch((error) => setMessage(error instanceof Error ? error.message : "加载失败"))
      .finally(() => setReady(true));
  }, []);

  const active = homes.find((item) => item.id === selected);
  const visibleHomes = homes.filter((item) => item.name.toLocaleLowerCase().includes(search.trim().toLocaleLowerCase()));

  async function save(event: React.FormEvent) {
    event.preventDefault();
    if (!name.trim()) { setMessage("请填写项目名称"); return; }
    if (styleFile && (!["image/jpeg", "image/png", "image/webp"].includes(styleFile.type) || styleFile.size > 10 * 1024 * 1024)) {
      setMessage("风格参考图需为 10 MB 以内的 JPG、PNG 或 WebP"); return;
    }
    setBusy(true);
    setMessage("");
    try {
      const photo = styleFile ? await api.upload(styleFile) : null;
      const payload = { name: name.trim(), style_text: styleText.trim(), style_photo_id: photo?.photo_id };
      const created = await api.createHome(payload);
      setHomes((items) => [created, ...items]);
      setSelected(created.id);
      setShowCreate(false);
      setName(""); setStyleText(""); setStyleFile(null);
    } catch (error) { setMessage(error instanceof Error ? error.message : "创建失败"); }
    finally { setBusy(false); }
  }

  function selectHome(home: HomeProject) {
    setSelected(home.id); setEditing(false); setShowCreate(false); setMessage("");
  }

  async function saveStyle(event: React.FormEvent) {
    event.preventDefault();
    if (!active || !editName.trim()) { setMessage("请填写项目名称"); return; }
    if (editPhoto && (!["image/jpeg", "image/png", "image/webp"].includes(editPhoto.type) || editPhoto.size > 10 * 1024 * 1024)) {
      setMessage("风格参考图需为 10 MB 以内的 JPG、PNG 或 WebP"); return;
    }
    setBusy(true); setMessage("");
    try {
      const photo = editPhoto ? await api.upload(editPhoto) : null;
      const updated = await api.updateHome(active.id, {
        name: editName.trim(), style_text: editStyle.trim(), style_photo_id: photo?.photo_id ?? active.style_photo_id,
      });
      setHomes((items) => items.map((item) => item.id === updated.id ? updated : item));
      setEditing(false); setEditPhoto(null);
    } catch (error) { setMessage(error instanceof Error ? error.message : "保存失败"); }
    finally { setBusy(false); }
  }

  async function applyRoomStyle(spaceId: string) {
    if (!active) return;
    setBusy(true); setMessage("");
    try {
      const updated = await api.useSpaceAsStyle(active.id, spaceId);
      setHomes((items) => items.map((item) => item.id === updated.id ? updated : item));
      setMessage("已将该空间的效果图设为后续空间的风格参考，现有方案不会改变。");
    } catch (error) { setMessage(error instanceof Error ? error.message : "设置失败"); }
    finally { setBusy(false); }
  }

  return <main className="site-shell workbench-shell">
    <header className="site-header"><Link href="/" className="brand">拍拍搭<span className="brand-dot">.</span></Link><nav className="header-nav"><Link href="/">开始创作</Link></nav></header>
    <div className="workbench-body"><WorkbenchSidebar active="homes" projects={homes.map(({ id, name: projectName }) => ({ id, name: projectName }))} selectedProjectId={selected} onProjectOverview={() => { setSelected(""); setEditing(false); setMessage(""); }} onProjectSelect={(id) => { const project = homes.find((item) => item.id === id); if (project) selectHome(project); }} /><div className="homes-layout">
      {!ready ? <p>正在加载…</p> : !getToken() ? <p>请先<Link href="/">输入邀请码登录</Link>。</p> : active ? <>
        <button type="button" className="project-back" onClick={() => { setSelected(""); setEditing(false); setMessage(""); }}><ArrowLeft size={17} /> 我的项目</button>
        <div className="project-detail-heading"><div><p className="eyebrow">项目空间</p><h1>{active.name}</h1><p className="muted">{active.spaces.length} 个空间 · 每个空间单独保存效果图与 2.5D</p></div><Link className="project-new-space" href={`/?home=${encodeURIComponent(active.id)}`}><Plus size={18} /> 添加空间</Link></div>
        <section className="project-style-panel"><div><span>全项目风格</span><p>{active.style_text || "尚未填写风格方向"}{active.style_photo_id ? " · 已有参考图" : ""}</p></div><button type="button" onClick={() => { setEditing(!editing); setEditName(active.name); setEditStyle(active.style_text); setEditPhoto(null); }}>{editing ? "收起设置" : "修改项目设置"}</button></section>
        {editing && <form onSubmit={saveStyle} className="homes-form home-edit-form">
          <label htmlFor="edit-home-name">项目名称</label><input id="edit-home-name" maxLength={60} value={editName} onChange={(event) => setEditName(event.target.value)} />
          <label htmlFor="edit-home-style">全项目风格</label><textarea id="edit-home-style" maxLength={200} rows={3} value={editStyle} onChange={(event) => setEditStyle(event.target.value)} />
          <label htmlFor="edit-home-photo">更换风格参考图（可选）</label><input id="edit-home-photo" type="file" accept="image/jpeg,image/png,image/webp" onChange={(event) => setEditPhoto(event.target.files?.[0] || null)} />
          <p className="muted">新设置只应用于之后新建的空间，已有方案不自动修改。</p><button className="primary-button" disabled={busy}>{busy ? "正在保存…" : "保存项目设置"}</button>
        </form>}
        <div className="project-spaces-heading"><h2>空间</h2><span>{active.spaces.length} 个</span></div>
        <div className="space-list">{active.spaces.length === 0 ? <p className="muted">还没有空间。添加客厅、卧室或其他房间，每个空间上传自己的原图。</p> : active.spaces.map((space) => <div key={space.id} className="space-entry"><Link href={`/design/${space.design.design_id}`} className="space-row"><span><strong>{space.name}</strong><small>{space.design.status === "completed" ? "效果图 + 2.5D" : space.design.status === "front_ready" ? "效果图待确认" : "方案进行中"} · 第 {space.design.current_version} 版</small></span><ArrowRight size={18} /></Link>{space.design.status === "completed" && <button type="button" className="space-style-action" disabled={busy} onClick={() => applyRoomStyle(space.id)}>用这个空间的效果图作为后续空间风格参考</button>}</div>)}</div>
      </> : <>
        <div className="project-overview-heading"><div><p className="eyebrow">空间工作台</p><h1>我的项目</h1><p className="muted">一个项目可以管理多个空间，适合自己的家，也适合客户委托。</p></div><label className="project-search"><MagnifyingGlass size={18} /><input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="搜索项目" aria-label="搜索项目" /></label></div>
        {showCreate && <section className="project-create-panel"><div className="project-create-title"><h2>新建项目</h2><button type="button" onClick={() => setShowCreate(false)}>取消</button></div><form onSubmit={save} className="homes-form">
          <label htmlFor="home-name">项目名称</label><input id="home-name" maxLength={60} value={name} onChange={(event) => setName(event.target.value)} placeholder="例如：我的新家 / 张女士的公寓" autoFocus />
          <label htmlFor="home-style">全项目风格</label><textarea id="home-style" maxLength={200} rows={3} value={styleText} onChange={(event) => setStyleText(event.target.value)} placeholder="例如：温暖原木风，浅米色和木色为主，保持自然光与真实比例" />
          <label htmlFor="home-image">风格参考图（可选）</label><input id="home-image" type="file" accept="image/jpeg,image/png,image/webp" onChange={(event) => setStyleFile(event.target.files?.[0] || null)} />
          <p className="muted">风格会在新建空间时固定。修改方向不会自动重生已有空间。</p><button className="primary-button" disabled={busy}>{busy ? "正在保存…" : "创建项目"}<ArrowRight size={18} /></button>
        </form></section>}
        <div className="project-overview-bar"><h2>全部项目 <span>{homes.length}</span></h2></div>
        <div className="project-tile-grid"><button type="button" className="project-create-tile" onClick={() => setShowCreate(true)}><Plus size={31} weight="light" /><strong>新建项目</strong><span>从一个空间开始</span></button>{visibleHomes.map((project) => <ProjectCard key={project.id} project={project} onOpen={() => selectHome(project)} />)}</div>
        {homes.length > 0 && visibleHomes.length === 0 && <p className="project-search-empty">没有找到匹配的项目。</p>}
      </>}
      {message && <p className="error-message" role="alert">{message}</p>}
    </div></div>
  </main>;
}
