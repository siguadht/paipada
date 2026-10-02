"use client";

import {
  ArrowRight,
  ArrowsClockwise,
  ClockCounterClockwise,
  House,
  Lightbulb,
  List,
  PaintBrush,
  Plus,
  Trash,
  UploadSimple,
  X,
} from "@phosphor-icons/react";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import styles from "./ui-preview.module.css";

type Screen = "create" | "edit";
type RefKind = "room" | "style" | "furniture";
type EditTool = "select" | "replace" | "recolor" | "remove";

const initial = {
  room: "/ui-preview/room.jpg",
  style: "/ui-preview/style.png",
  furniture: "",
};

const templates = [
  {
    name: "保留结构，更新软装",
    detail: "最稳妥的起点",
    prompt: "保留房间的门窗、墙体和拍摄角度。换掉旧沙发与茶几，选圆润但不过分夸张的造型，保持真实的尺寸和自然采光。",
  },
  {
    name: "参照喜欢的风格",
    detail: "调整材质与氛围",
    prompt: "严格保留原房间结构。参考风格图的材质、光线与整体气质，更换软装，不要复制参考图中的房间布局。",
  },
  {
    name: "指定一件家具",
    detail: "让造型更可控",
    prompt: "保留原房间结构与视角。将沙发替换成家具参考图中的造型，颜色与比例贴近参考，其余家具保持协调。",
  },
];

const toolLabels: Record<EditTool, string> = {
  select: "点选家具",
  replace: "替换家具",
  recolor: "调整颜色",
  remove: "删除家具",
};

export default function UiPreviewPage() {
  const [screen, setScreen] = useState<Screen>("create");
  const [refs, setRefs] = useState(initial);
  const [prompt, setPrompt] = useState(templates[0].prompt);
  const [template, setTemplate] = useState(0);
  const [tool, setTool] = useState<EditTool>("select");
  const [hovered, setHovered] = useState(false);
  const [selected, setSelected] = useState(false);
  const [feedback, setFeedback] = useState("");
  const [activePanel, setActivePanel] = useState<"object" | "request">("request");
  const [objectRequest, setObjectRequest] = useState("");
  const [chosenColor, setChosenColor] = useState("");
  const [notice, setNotice] = useState("");
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const inputs = useRef<Record<RefKind, HTMLInputElement | null>>({ room: null, style: null, furniture: null });
  const objectUrls = useRef<string[]>([]);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const editInputRef = useRef<HTMLTextAreaElement | null>(null);

  useEffect(() => {
    const urls = objectUrls.current;
    const image = new Image();
    image.onload = () => {
      const canvas = document.createElement("canvas");
      canvas.width = image.naturalWidth;
      canvas.height = image.naturalHeight;
      canvas.getContext("2d", { willReadFrequently: true })?.drawImage(image, 0, 0);
      canvasRef.current = canvas;
    };
    image.src = "/ui-preview/sofa.png";
    return () => { urls.forEach((url) => URL.revokeObjectURL(url)); };
  }, []);

  function pick(kind: RefKind, file?: File) {
    if (!file) return;
    if (!["image/jpeg", "image/png", "image/webp"].includes(file.type) || file.size > 10 * 1024 * 1024) {
      setNotice("请选择 10 MB 以内的 JPG、PNG 或 WebP 图片");
      return;
    }
    const url = URL.createObjectURL(file);
    objectUrls.current.push(url);
    setRefs((value) => ({ ...value, [kind]: url }));
    setNotice(kind === "room" ? "房间照片已加入本地预览" : "参考图已加入本地预览");
  }

  function isSofaAt(clientX: number, clientY: number, element: HTMLDivElement) {
    const mask = canvasRef.current;
    if (!mask) return false;
    const rect = element.getBoundingClientRect();
    const x = (clientX - rect.left) / rect.width;
    const y = (clientY - rect.top) / rect.height;
    const px = Math.floor(((x - 0.155) / 0.769) * mask.width);
    const py = Math.floor(((y - 0.529) / 0.329) * mask.height);
    if (px < 0 || py < 0 || px >= mask.width || py >= mask.height) return false;
    return (mask.getContext("2d", { willReadFrequently: true })?.getImageData(px, py, 1, 1).data[3] ?? 0) > 50;
  }

  function onCanvasMove(event: React.PointerEvent<HTMLDivElement>) {
    if (event.pointerType === "touch") return;
    const opaque = isSofaAt(event.clientX, event.clientY, event.currentTarget);
    setHovered((current) => current === opaque ? current : opaque);
  }

  function selectSofa() {
    setSelected(true);
    setTool("select");
    setActivePanel("object");
  }

  function setAction(next: EditTool) {
    if (next === "select") { setTool(next); setActivePanel("object"); return; }
    if (!selected) { setNotice("请先点选画面中的沙发"); return; }
    setTool(next);
    setActivePanel("object");
    if (window.innerWidth <= 760) requestAnimationFrame(() => editInputRef.current?.scrollIntoView({ behavior: "smooth", block: "center" }));
  }

  function openRequest() {
    setSelected(false);
    setHovered(false);
    setTool("select");
    setActivePanel("request");
    if (window.innerWidth <= 760) requestAnimationFrame(() => editInputRef.current?.scrollIntoView({ behavior: "smooth", block: "center" }));
  }

  const isObjectEdit = activePanel === "object" && selected;

  function switchScreen(next: Screen) {
    setScreen(next);
    setSidebarOpen(false);
  }

  return <main className={styles.app}>
    <header className={styles.topbar}>
      <div className={styles.identity}><button className={styles.menuToggle} aria-label="打开侧边栏" aria-expanded={sidebarOpen} onClick={() => setSidebarOpen(true)}><List size={20} /></button><strong>拍拍搭</strong><span>空间设计工作台</span></div>
      <div className={styles.topRight}><span>UI 体验稿</span><Link href="/">返回现有页面 <ArrowRight size={15} /></Link></div>
    </header>

    <div className={styles.layout}>
      {sidebarOpen && <button className={styles.sidebarBackdrop} aria-label="关闭侧边栏" onClick={() => setSidebarOpen(false)} />}
      <aside className={`${styles.sidebar} ${sidebarOpen ? styles.sidebarOpen : ""}`} aria-label="工作台侧边栏">
        <div className={styles.sidebarTop}><span>工作空间</span><button className={styles.sidebarClose} aria-label="关闭侧边栏" onClick={() => setSidebarOpen(false)}><X size={18} /></button></div>
        <button className={styles.newCreation} onClick={() => { setPrompt(templates[0].prompt); setTemplate(0); switchScreen("create"); }}><Plus size={17} weight="bold" /> 新建创作</button>
        <div className={styles.sidebarGroup}><span className={styles.sidebarLabel}>创作</span>
          <button className={screen === "create" ? styles.sidebarActive : ""} onClick={() => switchScreen("create")}><House size={18} />开始创作</button>
          <button className={screen === "edit" ? styles.sidebarActive : ""} onClick={() => switchScreen("edit")}><PaintBrush size={18} />效果图编辑</button>
          <button onClick={() => { setSidebarOpen(false); document.getElementById("preview-examples")?.scrollIntoView({ behavior: "smooth", block: "start" }); }}><Lightbulb size={18} />灵感示例</button>
        </div>
        <div className={styles.sidebarGroup}><span className={styles.sidebarLabel}>项目</span>
          <div className={styles.projectCard}><img src={refs.room} alt="" /><span><strong>我的客厅</strong><small>单空间演示</small></span></div>
          <Link className={styles.sidebarLink} href="/history"><ClockCounterClockwise size={18} />历史记录 <ArrowRight size={14} /></Link>
        </div>
        <div className={styles.sidebarFoot}><span className={styles.previewDot} /> UI 体验稿 <small>本地预览</small></div>
      </aside>
      <div className={styles.workspace}>
      <div className={styles.intro}><span>我的客厅 <span className={styles.slash}>/</span> {screen === "create" ? "开始创作" : "效果图编辑"}</span><span>{screen === "create" ? "把房间、参考图和要求放在一起" : "直接在画面里点家具，或描述整张图的问题"}</span></div>

      <section className={styles.hero} aria-label={screen === "create" ? "原始房间" : "效果图"}>
        <div className={styles.heroTop}><span>{screen === "create" ? "原始房间" : "效果图 · 首版"}</span><span>{screen === "create" ? "保留空间结构与视角" : "点选沙发试试局部编辑"}</span></div>
        {screen === "create" ? <div className={styles.heroImage}><img src={refs.room} alt="待改造的原始房间" /></div> : <div className={styles.canvasFrame}>
          <div className={`${styles.canvas} ${hovered || selected ? styles.canvasLifted : ""} ${selected ? styles.canvasSelected : ""}`} onPointerMove={onCanvasMove} onPointerLeave={() => setHovered(false)} onClick={(event) => { if (isSofaAt(event.clientX, event.clientY, event.currentTarget)) selectSofa(); else { setSelected(false); setActivePanel("request"); setTool("select"); } }} role="button" tabIndex={0} onKeyDown={(event) => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); selectSofa(); } }} aria-label="房间效果图，沙发可点选或悬停">
            <img className={styles.sceneImage} src="/ui-preview/room.jpg" alt="效果图交互示例" />
            <img className={styles.sofaLayer} src="/ui-preview/sofa.png" alt="" />
            <span className={styles.selectedHint}>{selected ? "已选中沙发" : "点击编辑沙发"}</span>
          </div>
          {selected && <div className={styles.selectionToolbar} aria-label="沙发操作">
            <button className={tool === "replace" && isObjectEdit ? styles.toolbarActive : ""} onClick={() => setAction("replace")}><ArrowsClockwise size={16} />替换</button>
            <button className={tool === "recolor" && isObjectEdit ? styles.toolbarActive : ""} onClick={() => setAction("recolor")}><PaintBrush size={16} />改色</button>
            <button className={tool === "remove" && isObjectEdit ? styles.toolbarActive : ""} onClick={() => setAction("remove")}><Trash size={16} />删除</button>
          </div>}
        </div>}
        {screen === "create" ? <button className={styles.heroAction} onClick={() => inputs.current.room?.click()}><UploadSimple size={17} /> 更换房间照片</button> : <button className={styles.heroAction} onClick={() => setNotice("UI 体验稿暂不调用 2.5D 生成。现有正式流程仍可使用。")}>满意，生成 2.5D <ArrowRight size={16} /></button>}
      </section>

      <nav className={styles.modeTabs} aria-label="创作模式"><button className={screen === "create" ? styles.modeActive : ""} onClick={() => switchScreen("create")}>开始创作</button><button className={screen === "edit" ? styles.modeActive : ""} onClick={() => switchScreen("edit")}>效果图编辑</button></nav>

      <section className={styles.composer} aria-label={screen === "create" ? "创作要求" : "效果图修改要求"}>
        <div className={styles.composerTop}><span>{screen === "create" ? "描述你的理想空间" : isObjectEdit ? tool === "select" ? "沙发已选中，选择修改方式" : `修改沙发 · ${toolLabels[tool]}` : "哪里还不满意？"}</span>{isObjectEdit && <button onClick={openRequest}>改整张效果图 <ArrowRight size={14} /></button>}</div>
        {screen === "create" ? <textarea id="create-prompt" aria-label="创作描述" maxLength={500} value={prompt} onChange={(event) => setPrompt(event.target.value)} placeholder="例如：保留门窗和视角，换成自然温暖的软装。" /> : <textarea id="edit-prompt" aria-label="修改描述" ref={editInputRef} maxLength={500} value={isObjectEdit ? objectRequest : feedback} onChange={(event) => isObjectEdit ? setObjectRequest(event.target.value) : setFeedback(event.target.value)} placeholder={isObjectEdit ? tool === "recolor" ? "例如：把沙发改成浅灰色，保留布艺质感和造型。" : tool === "remove" ? "例如：删除沙发，保留地毯和窗户。" : "例如：换成家具参考图中的圆润沙发，尺寸不要太大。" : "例如：沙发太大、窗户位置不对。保留原房间结构，重新生成一版。"} />}
        {screen === "edit" && (!isObjectEdit || tool === "recolor") && <div className={styles.suggestions}><span>{isObjectEdit && tool === "recolor" ? "快速选色" : "常见修改"}</span>{(isObjectEdit && tool === "recolor" ? ["奶油白", "浅灰", "焦糖棕", "墨绿"] : ["沙发比例太大", "窗户位置不对", "整体风格不对"]).map((sample) => <button className={chosenColor === sample ? styles.chipActive : ""} key={sample} onClick={() => { if (isObjectEdit) { setChosenColor(sample); setObjectRequest(`把沙发改成${sample}，保留原来的造型和材质质感。`); } else { setFeedback(sample + "。请保留原房间的门窗与视角。"); } editInputRef.current?.focus(); }}>{sample}</button>)}</div>}
        <div className={styles.composerBottom}>
          <div className={styles.sourcePills}>
            <button onClick={() => inputs.current.room?.click()}><img src={refs.room} alt="" />原始房间 <span>更换</span></button>
            <button onClick={() => inputs.current.style?.click()}>{refs.style ? <img src={refs.style} alt="" /> : <Plus size={18} />}风格参考 <span>{refs.style ? "更换" : "添加"}</span></button>
            <button onClick={() => inputs.current.furniture?.click()}>{refs.furniture ? <img src={refs.furniture} alt="" /> : <Plus size={18} />}家具参考 <span>{refs.furniture ? "更换" : "添加"}</span></button>
          </div>
          {screen === "create" ? <button className={styles.primary} onClick={() => { if (!prompt.trim()) { setNotice("请先描述改造想法"); return; } switchScreen("edit"); }}>预览效果图编辑 <ArrowRight size={18} /></button> : <button className={styles.primary} disabled={isObjectEdit && tool === "select"} onClick={() => { if (!isObjectEdit && !feedback.trim()) { setNotice("先描述这一版哪里不满意。"); return; } if (isObjectEdit && tool !== "remove" && !objectRequest.trim()) { setNotice("先描述沙发要怎么改。"); return; } setNotice("修改要求已记录在 UI 预览中；这里不会实际生成新图。"); }}>{isObjectEdit ? tool === "select" ? "先选修改方式" : `确认${toolLabels[tool]}要求` : "重新生成一版"} <ArrowRight size={18} /></button>}
        </div>
        <input ref={(node) => { inputs.current.room = node; }} type="file" hidden accept="image/jpeg,image/png,image/webp" onChange={(event) => pick("room", event.target.files?.[0])} />
        <input ref={(node) => { inputs.current.style = node; }} type="file" hidden accept="image/jpeg,image/png,image/webp" onChange={(event) => pick("style", event.target.files?.[0])} />
        <input ref={(node) => { inputs.current.furniture = node; }} type="file" hidden accept="image/jpeg,image/png,image/webp" onChange={(event) => pick("furniture", event.target.files?.[0])} />
      </section>

      <section className={styles.examples} id="preview-examples"><div className={styles.examplesHead}><div><span>灵感示例</span><h2>{screen === "create" ? "从一个清楚的要求开始" : "每次只改你想改的地方"}</h2></div><span>{screen === "create" ? "点击示例，填入创作框" : "先说哪里不对，再生成下一版"}</span></div><div className={styles.exampleStrip}>{templates.map((item, index) => <button key={item.name} className={template === index && screen === "create" ? styles.exampleActive : ""} onClick={() => { setTemplate(index); if (screen === "create") setPrompt(item.prompt); else setFeedback(item.prompt); }}><span className={styles.exampleIndex}>0{index + 1}</span><strong>{item.name}</strong><small>{item.detail}</small><ArrowRight size={18} /></button>)}</div></section>
      <p className={styles.localNote}>此页只展示 UI 交互。图片仅在当前浏览器预览，不调用模型，也不会保存上传的参考图。</p>
    </div>
    </div>
    {notice && <div className={styles.toast} role="status"><span>{notice}</span><button aria-label="关闭提示" onClick={() => setNotice("")}><X size={14} /></button></div>}
  </main>;
}
