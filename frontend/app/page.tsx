"use client";

import { ArrowRight, ClockCounterClockwise, ImageSquare, Plus, Sparkle } from "@phosphor-icons/react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { ApiError, HomeProject, api, getToken, setToken } from "@/lib/api";
import { WorkbenchSidebar } from "@/components/workbench-sidebar";

const promptExamples = [
  { title: "保留结构，更新软装", text: "保留门窗、墙体和拍摄角度，换掉旧沙发与茶几，采用自然材质和真实比例。" },
  { title: "参考整体风格", text: "保留原房间布局，只参考风格图的材质、配色和光线，软装保持协调。" },
  { title: "指定一件家具", text: "保留空间结构，参考家具图替换一件主要家具，颜色与尺寸贴近参考。" },
];

export default function Home() {
  const router = useRouter();
  const fileRef = useRef<HTMLInputElement>(null);
  const previewRef = useRef("");
  const [ready, setReady] = useState(false);
  const [loggedIn, setLoggedIn] = useState(false);
  const [invite, setInvite] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState("");
  const [referenceFiles, setReferenceFiles] = useState<{ style?: File; furniture?: File }>({});
  const [referencePreviews, setReferencePreviews] = useState<{ style?: string; furniture?: string }>({});
  const referenceUrls = useRef<string[]>([]);
  const styleRef = useRef<HTMLInputElement>(null);
  const furnitureRef = useRef<HTMLInputElement>(null);
  const [description, setDescription] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [home, setHome] = useState<HomeProject | null>(null);
  const [requestedHomeId, setRequestedHomeId] = useState("");
  const [roomName, setRoomName] = useState("");
  const [roomCostAccepted, setRoomCostAccepted] = useState(false);

  useEffect(() => {
    if (!getToken()) { queueMicrotask(() => setReady(true)); return; }
    api.me().then(() => setLoggedIn(true)).catch(() => setLoggedIn(false)).finally(() => setReady(true));
  }, []);

  useEffect(() => {
    const homeId = new URLSearchParams(window.location.search).get("home");
    if (!homeId) return;
    queueMicrotask(() => setRequestedHomeId(homeId));
    if (!getToken()) return;
    api.getHome(homeId).then(setHome).catch((error) => setMessage(error instanceof Error ? error.message : "无法打开项目"));
  }, [loggedIn]);

  useEffect(() => {
    const urls = referenceUrls.current;
    return () => { if (previewRef.current) URL.revokeObjectURL(previewRef.current); urls.forEach((url) => URL.revokeObjectURL(url)); };
  }, []);

  async function login(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setMessage("");
    try {
      const result = await api.login(invite);
      setToken(result.token);
      setLoggedIn(true);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "登录失败");
    } finally { setBusy(false); }
  }

  function chooseFile(chosen?: File) {
    if (!chosen) return;
    if (!["image/jpeg", "image/png", "image/webp"].includes(chosen.type)) {
      setMessage("请选择 JPG、PNG 或 WebP 图片"); return;
    }
    if (chosen.size > 10 * 1024 * 1024) {
      setMessage("图片不能超过 10MB"); return;
    }
    setMessage("");
    if (previewRef.current) URL.revokeObjectURL(previewRef.current);
    previewRef.current = URL.createObjectURL(chosen);
    setPreview(previewRef.current);
    setFile(chosen);
  }

  function chooseReference(kind: "style" | "furniture", chosen?: File) {
    if (!chosen) return;
    if (!["image/jpeg", "image/png", "image/webp"].includes(chosen.type) || chosen.size > 10 * 1024 * 1024) {
      setMessage("参考图请选择 10 MB 以内的 JPG、PNG 或 WebP 图片"); return;
    }
    const url = URL.createObjectURL(chosen);
    referenceUrls.current.push(url);
    setReferenceFiles((current) => ({ ...current, [kind]: chosen }));
    setReferencePreviews((current) => ({ ...current, [kind]: url }));
    setMessage("");
  }

  async function start(event: React.FormEvent) {
    event.preventDefault();
    if (!file || !description.trim()) { setMessage("请添加房间照片和改造想法"); return; }
    if (requestedHomeId && !home) { setMessage("项目尚未加载，请稍后重试或返回我的项目"); return; }
    if (home && !roomName.trim()) { setMessage("请给这个房间取个名字"); return; }
    if (home && !roomCostAccepted) { setMessage("请先确认本次生成费用提示"); return; }
    setBusy(true);
    setMessage("");
    try {
      const uploaded = await api.upload(file);
      const style = referenceFiles.style ? await api.upload(referenceFiles.style) : null;
      const furniture = referenceFiles.furniture ? await api.upload(referenceFiles.furniture) : null;
      const design = await api.createDesign(uploaded.photo_id, description.trim(), {
        style_photo_id: style?.photo_id, furniture_photo_id: furniture?.photo_id,
        home_id: home?.id, room_name: home ? roomName.trim() : undefined,
        cost_confirmed: home ? roomCostAccepted : undefined,
      });
      router.push(`/design/${design.design_id}`);
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) setLoggedIn(false);
      setMessage(error instanceof Error ? error.message : "创建失败");
    } finally { setBusy(false); }
  }

  return (
    <main className={`site-shell workbench-shell ${loggedIn ? "" : "login-shell"}`}>
      <header className="site-header">
        <Link href="/" className="brand">拍拍搭<span className="brand-dot">.</span></Link>
        <nav className="header-nav" aria-label="主导航">
          {loggedIn ? <Link href="/history"><ClockCounterClockwise size={19} /> 我的方案</Link> : <span className="login-header-label">邀请码登录</span>}
        </nav>
      </header>
      <div className={loggedIn ? "workbench-body" : ""}>
      {loggedIn && <WorkbenchSidebar active="create" onExamples={() => document.getElementById("creation-examples")?.scrollIntoView({ behavior: "smooth" })} />}
      <div className="home-layout">
        <section className="home-copy">
          <p className="eyebrow">空间灵感，从你家开始</p>
          <h1>看见家的<br /><em>另一种可能。</em></h1>
          <p className="home-lead">上传一张真实的房间照片，说说你想怎么改变。先把效果图改到满意，再看完整的 2.5D 软装方案。</p>
          <div className="journey"><span>上传照片</span><ArrowRight size={15} /><span>编辑效果图</span><ArrowRight size={15} /><span>生成 2.5D</span></div>
          <div className="example-frame" role="img" aria-label="软装效果图视觉示例">
            {preview && <img src={preview} alt="原始房间预览" />}
            <div className="example-caption"><ImageSquare size={16} /> {preview ? "原始房间 · 将保留空间结构" : "视觉示例 · 请上传你的房间照片"}</div>
          </div>
        </section>
        {loggedIn && <nav className="formal-mode-tabs" aria-label="创作模式"><span aria-current="page">开始创作</span><Link href="/history">继续编辑方案</Link></nav>}
        <section className="creation-panel" aria-labelledby="create-title">
          {!ready ? <p className="muted">正在检查登录状态…</p> : !loggedIn ? (
            <form key="login" onSubmit={login} className="login-form">
              <div className="panel-mark"><Sparkle size={25} /></div>
              <p className="eyebrow">开启你的空间</p>
              <h2 id="create-title">先输入邀请码</h2>
              <p className="muted">你的照片与方案只会出现在自己的账号里。</p>
              <label htmlFor="invite">邀请码</label>
              <input id="invite" type="password" value={invite} onChange={(e) => setInvite(e.target.value)} placeholder="输入收到的邀请码" autoComplete="off" required minLength={4} />
              <button className="primary-button" disabled={busy}>{busy ? "验证中…" : "进入拍拍搭"}<ArrowRight size={18} /></button>
            </form>
          ) : (
            <form key="create" onSubmit={start} className="create-form">
              <div className="composer-heading"><p className="eyebrow">{home ? `我的项目 / ${home.name}` : "新建方案"}</p><h2 id="create-title">描述你想要的空间</h2></div>
              {requestedHomeId && !home && <p className="muted">正在读取项目… <Link href="/homes">返回我的项目</Link></p>}
              {home && <div className="home-context"><label htmlFor="room-name">空间名称</label><input id="room-name" value={roomName} maxLength={40} onChange={(event) => setRoomName(event.target.value)} placeholder="例如：客厅、主卧、书房" /><p>全屋风格：{home.style_text || "尚未设置"}。{home.style_photo_id ? "已附全屋风格参考图。" : ""}本房间可以另外上传风格参考图覆盖全屋参考图。</p></div>}
              {home && <label className="room-cost-confirm"><input type="checkbox" checked={roomCostAccepted} onChange={(event) => setRoomCostAccepted(event.target.checked)} /><span>确认生成这个房间的正面效果图。Seedream 5.0 Pro 当前约 ¥0.30～0.34/次；服务端失败最多重试一次，图片费用上限约 ¥0.68，另有少量文字模型与临时存储费用。后续 2.5D 须另行确认生成。<a href="https://docs.volcengine.com/docs/ark/model-pricing?lang=zh" target="_blank" rel="noreferrer">查看火山官方价格</a></span></label>}
              <div className="creator-composer">
                <div className="composer-attachments" aria-label="创作图片素材">
                  <button type="button" className={`composer-tile ${preview ? "has-image" : ""}`} onClick={() => fileRef.current?.click()} onDragOver={(event) => event.preventDefault()} onDrop={(event) => { event.preventDefault(); chooseFile(event.dataTransfer.files[0]); }} aria-label={preview ? "更换原始房间照片" : "上传原始房间照片，必传"} title={file?.name || "上传原始房间照片"}>
                    {preview ? <img src={preview} alt="" /> : <Plus size={25} weight="light" />}
                    <span>原图</span>
                  </button>
                  <button type="button" className={`composer-tile ${referencePreviews.style ? "has-image" : ""}`} onClick={() => styleRef.current?.click()} aria-label={referencePreviews.style ? "更换整体风格参考图" : "添加整体风格参考图，可选"} title="整体风格参考：材质、配色和光线">
                    {referencePreviews.style ? <img src={referencePreviews.style} alt="" /> : <Plus size={25} weight="light" />}
                    <span>风格</span>
                  </button>
                  <button type="button" className={`composer-tile ${referencePreviews.furniture ? "has-image" : ""}`} onClick={() => furnitureRef.current?.click()} aria-label={referencePreviews.furniture ? "更换指定家具参考图" : "添加指定家具参考图，可选"} title="指定家具参考：单件造型和颜色">
                    {referencePreviews.furniture ? <img src={referencePreviews.furniture} alt="" /> : <Plus size={25} weight="light" />}
                    <span>家具</span>
                  </button>
                  <span className="composer-attachment-help">上传原图，再按需添加风格或家具参考图</span>
                </div>
                <label htmlFor="description" className="composer-label">改造描述</label>
                <textarea id="description" maxLength={200} rows={4} value={description} onChange={(e) => setDescription(e.target.value)} placeholder="描述你想怎么改这个空间。例如：保留门窗与采光，换浅米色沙发，整体采用温暖的原木风…" />
                <div className="composer-toolbar"><span>原图必传 · 参考图可选 <small>{description.length}/200</small></span><button className="primary-button" disabled={busy || !file || !description.trim() || Boolean(requestedHomeId && !home) || Boolean(home && !roomCostAccepted)}>{busy ? "正在创建方案…" : "生成效果图"}<ArrowRight size={18} /></button></div>
              </div>
              <input ref={fileRef} type="file" hidden accept="image/jpeg,image/png,image/webp" onChange={(e) => chooseFile(e.target.files?.[0])} />
              <input ref={styleRef} type="file" hidden accept="image/jpeg,image/png,image/webp" onChange={(event) => chooseReference("style", event.target.files?.[0])} />
              <input ref={furnitureRef} type="file" hidden accept="image/jpeg,image/png,image/webp" onChange={(event) => chooseReference("furniture", event.target.files?.[0])} />
              <div className="formal-examples" id="creation-examples"><span>从示例开始</span><div>{promptExamples.map((example) => <button type="button" key={example.title} onClick={() => setDescription(example.text)}>{example.title}<ArrowRight size={15} /></button>)}</div></div>
              <p className="privacy-note">上传前请确认照片中没有不愿提供给生图服务的私人信息。</p>
            </form>
          )}
          {message && <p className="error-message" role="alert">{message}</p>}
        </section>
      </div>
      </div>
    </main>
  );
}
