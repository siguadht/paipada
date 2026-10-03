"use client";

import Image from "next/image";
import Link from "next/link";
import { useState } from "react";
import styles from "./website.module.css";

type Language = "zh" | "en";
type DemoView = "base" | "replace" | "recolor" | "remove";
type DemoAction = Exclude<DemoView, "base">;
type JourneyStep = 0 | 1 | 2 | 3 | 4;

const demoImages: Record<DemoView, string> = {
  base: "/site/website-demo/base.jpg",
  replace: "/site/website-demo/replace.jpg",
  recolor: "/site/website-demo/recolor.jpg",
  remove: "/site/website-demo/remove.jpg",
};

const copy = {
  zh: {
    nav: ["体验软装编辑", "完整流程", "演示视频"],
    switchLanguage: "EN", enter: "进入工作台",
    eyebrow: "拍拍搭 · 空间设计工作台",
    title: "在图上改软装，\n直到满意。",
    intro: "上传真实房间照片，直接在效果图上替换、改色或删除家具。满意后，再看对应的空间示意。",
    watch: "观看真实操作", demoTag: "可点击的真实样例",
    demoHint: "把鼠标移到沙发上，或点一下试试", demoHintTouch: "点一下沙发试试",
    sample: "以下为已生成的演示样例，切换图片不代表即时生图。",
    sofa: "沙发", selected: "已选中沙发",
    actions: { replace: "替换", recolor: "改色", remove: "删除" },
    actionTitles: { replace: "换一件沙发", recolor: "试试另一种颜色", remove: "移除这件沙发" },
    actionDescriptions: {
      replace: "查看弧形沙发的已生成效果",
      recolor: "查看墨绿色沙发的已生成效果",
      remove: "查看移除沙发后的已生成效果",
    },
    apply: "查看结果", close: "关闭", reset: "回到原版",
    stateLabels: { base: "原版", replace: "替换结果", recolor: "改色结果", remove: "删除结果" },
    journeyEyebrow: "完整流程 / 01—05", journeyTitle: "一张照片，走到完整方案。",
    journeyIntro: "从上传房间到查看 2.5D，每一步都保留决定权。点击步骤，看看作品如何推进。",
    journeySteps: [
      { title: "上传房间", body: "放入原始房间照片；风格图和指定家具图按需添加。" },
      { title: "生成效果图", body: "写下想要的风格与约束，先得到可讨论的正面效果图。" },
      { title: "直接改软装", body: "在图里选中家具，替换、改色或删除；不满意也能描述整张图的问题。" },
      { title: "确认这一版", body: "对照原照片检查门窗、墙地面和视角；有问题就继续修改。" },
      { title: "查看 2.5D", body: "只在正面图满意后，生成与这一版对应的空间摆放示意。" },
    ],
    journeyPreview: ["创作输入示意", "已验收结果接续 · 非现场生图", "软装交互样例", "核对项示意 · 原图对照在工作台完成", "对应版本的 2.5D 示意"],
    journeyRoom: "原始房间照片", journeyStyle: "整体风格参考", journeyFurniture: "指定家具参考", journeyOptional: "可选",
    journeyPrompt: "保留门窗和视角，换上简洁温暖的软装。", journeyApproved: "正面图满意，再进入下一步", journeyCheck: ["门窗位置", "墙面与地面", "拍摄视角"],
    proofTitle: "同一个空间，\n换一件就不一样。",
    proofBody: "拖动滑块，对比同一客厅替换沙发前后的已生成结果。这是软装修改对比，不是原始房间与装修效果图的对比。",
    compareBefore: "替换前", compareAfter: "替换后", compareControl: "拖动查看沙发替换前后的对比",
    filmTitle: "从上传到 2.5D，\n看完整流程。",
    filmBody: "真实工作台录屏：从邀请码登录、上传照片与填写要求，到效果图上选家具、拖动选品窗、核对结构、查看 2.5D，再看版本记录与多空间项目。",
    filmNote: "上传画面使用公开房间样例；之后接续另一份已验收的 01 方案。本片未现场生图，也未提交付费编辑。确认页来自历史方案，原图细节已遮蔽；2.5D 来自已验收的 01 方案。",
    filmQuality: "1080P · OBS 工作台录屏", filmDownload: "下载高清原片", filmChapters: ["登录与上传", "效果图编辑", "结构与 2.5D", "历史版本", "多空间项目"],
    spatialTitle: "效果图满意了，\n再看 2.5D。",
    spatialBody: "正面图确定后，才生成对应版本的空间示意。它帮助理解摆放，不作为精确户型或施工图。",
    spatialTag: "与方案 01 对应的 2.5D 示意",
    finalTitle: "从你的空间，开始创作。", footer: "AI 软装创作工作台", source: "查看源码",
  },
  en: {
    nav: ["Try decor editing", "Full workflow", "Demo film"],
    switchLanguage: "中文", enter: "Open studio",
    eyebrow: "Paipaida · Spatial design studio",
    title: "Edit the room itself,\nuntil it feels right.",
    intro: "Upload a real room, then replace, recolor, or remove furniture directly in the image. Explore its spatial view after you approve it.",
    watch: "Watch a real session", demoTag: "Interactive real example",
    demoHint: "Hover over the sofa or click to try", demoHintTouch: "Tap the sofa to try",
    sample: "These images were generated in advance. Switching between them is not live generation.",
    sofa: "Sofa", selected: "Sofa selected",
    actions: { replace: "Replace", recolor: "Recolor", remove: "Remove" },
    actionTitles: { replace: "Choose another sofa", recolor: "Try another color", remove: "Remove this sofa" },
    actionDescriptions: {
      replace: "See the generated curved sofa result",
      recolor: "See the generated deep green result",
      remove: "See the generated room without the sofa",
    },
    apply: "View result", close: "Close", reset: "Back to original",
    stateLabels: { base: "Original", replace: "Replaced", recolor: "Recolored", remove: "Removed" },
    journeyEyebrow: "THE WORKFLOW / 01—05", journeyTitle: "From one photo to a complete concept.",
    journeyIntro: "You stay in control from the room upload to the 2.5D view. Select a step to see how the project moves forward.",
    journeySteps: [
      { title: "Upload the room", body: "Add the original room photo. Style and product references are optional." },
      { title: "Generate a front view", body: "Describe the style and constraints to get a front view you can discuss." },
      { title: "Edit decor in place", body: "Select furniture to replace, recolor, or remove it, or describe a wider issue." },
      { title: "Approve this version", body: "Compare with the original and check windows, walls, floor, and viewpoint." },
      { title: "Explore 2.5D", body: "Only after approval, create a matching spatial placement concept." },
    ],
    journeyPreview: ["Creation input illustration", "Approved result · not live generation", "Interactive decor example", "Review illustration · compare the original in the studio", "Matching 2.5D concept"],
    journeyRoom: "Original room photo", journeyStyle: "Style reference", journeyFurniture: "Furniture reference", journeyOptional: "Optional",
    journeyPrompt: "Keep the windows and viewpoint; use calm, warm furnishings.", journeyApproved: "Approve the front view first", journeyCheck: ["Windows and doors", "Walls and floor", "Viewpoint"],
    proofTitle: "Same room.\nA different sofa.",
    proofBody: "Drag to compare generated views of the same living room before and after replacing the sofa. This compares a decor edit, not the original room with a renovation result.",
    compareBefore: "Before replacement", compareAfter: "After replacement", compareControl: "Drag to compare before and after replacing the sofa",
    filmTitle: "From upload to 2.5D.\nSee the full workflow.",
    filmBody: "An actual studio recording: invite login, photo upload, design prompt, furniture selection and movable product picker, structure review, 2.5D, version history, and a multi-room project.",
    filmNote: "The upload uses a public sample room. The later edit footage continues with a different approved design 01. No live image generation or paid edit was submitted. The review screen is from a historical design with original-photo details blurred; the 2.5D belongs to approved design 01.",
    filmQuality: "1080p · OBS studio recording", filmDownload: "Download HD video", filmChapters: ["Login & upload", "Edit decor", "Review & 2.5D", "Versions", "Multi-room project"],
    spatialTitle: "Approve the image.\nThen explore its 2.5D view.",
    spatialBody: "The matching spatial concept is generated after the front view is approved. It illustrates placement, not a measured floor plan.",
    spatialTag: "2.5D concept for approved version 01",
    finalTitle: "Start with your space.", footer: "AI decor creation studio", source: "Source code",
  },
} as const;

function BreakLines({ text }: { text: string }) {
  return <>{text.split("\n").map((line, index) => <span key={index}>{line}{index === 0 && <br />}</span>)}</>;
}

export default function WebsitePage() {
  const [language, setLanguage] = useState<Language>("zh");
  const [view, setView] = useState<DemoView>("base");
  const [selected, setSelected] = useState(false);
  const [action, setAction] = useState<DemoAction | null>(null);
  const [journeyStep, setJourneyStep] = useState<JourneyStep>(0);
  const [comparePosition, setComparePosition] = useState(27);
  const t = copy[language];

  const resetDemo = () => {
    setView("base");
    setAction(null);
    setSelected(false);
  };
  const applyAction = () => {
    if (!action) return;
    setView(action);
    setSelected(false);
    setAction(null);
  };

  return <main className={styles.site} lang={language === "zh" ? "zh-CN" : "en"}>
    <header className={styles.header}>
      <a href="#top" className={styles.logo} aria-label="拍拍搭 Paipaida">拍拍搭<span className={styles.logoDot} /></a>
      <nav aria-label={language === "zh" ? "官网导航" : "Website navigation"}>
        <a href="#experience">{t.nav[0]}</a><a href="#journey">{t.nav[1]}</a><a href="#film">{t.nav[2]}</a>
      </nav>
      <div className={styles.headerActions}>
        <button className={styles.language} type="button" onClick={() => setLanguage(language === "zh" ? "en" : "zh")} aria-label={language === "zh" ? "Switch to English" : "切换中文"}>{t.switchLanguage}</button>
        <Link className={styles.headerCta} href="/">{t.enter}<span aria-hidden="true">↗</span></Link>
      </div>
    </header>

    <section className={styles.hero} id="top">
      <div className={styles.heroCopy}>
        <p className={styles.eyebrow}>{t.eyebrow}</p>
        <h1><BreakLines text={t.title} /></h1>
        <p className={styles.heroIntro}>{t.intro}</p>
        <a className={styles.textLink} href="#film">{t.watch}<span aria-hidden="true">↗</span></a>
      </div>
      <div className={styles.demoBlock} id="experience">
        <div className={styles.demoMeta}><span>{t.demoTag}</span><span>{String((["base", "replace", "recolor", "remove"] as DemoView[]).indexOf(view) + 1).padStart(2, "0")} / 04</span></div>
        <div className={styles.demoCanvas}>
          <Image key={view} className={styles.demoImage} src={demoImages[view]} alt={(language === "zh" ? "客厅沙发" : "Living room sofa ") + t.stateLabels[view]} fill priority sizes="(max-width: 900px) 100vw, 62vw" />
          {view !== "remove" && <>
            <button type="button"
              className={[styles.sofaHotspot, selected ? styles.hotspotSelected : ""].join(" ")}
              aria-label={language === "zh" ? "选中沙发，显示替换、改色和删除操作" : "Select sofa to replace, recolor, or remove"}
              onMouseEnter={() => setSelected(true)} onFocus={() => setSelected(true)} onClick={() => setSelected(true)}
            />
            {selected && <div className={styles.actionBar} role="group" aria-label={t.selected}>
              <span className={styles.actionItemLabel}>{t.sofa}</span>
              {(["replace", "recolor", "remove"] as const).map((item) =>
                <button key={item} type="button" className={action === item ? styles.actionActive : ""} onClick={() => setAction(item)}>{t.actions[item]}</button>
              )}
            </div>}
          </>}
          {!selected && view === "base" && <div className={styles.demoHint}>{t.demoHint}</div>}
          {view !== "base" && <div className={styles.resultControls}><span aria-live="polite">{t.stateLabels[view]}</span><button type="button" onClick={resetDemo}>{t.reset}</button></div>}
        </div>
        {action && <div className={styles.actionPanel} role="dialog" aria-label={t.actionTitles[action]}>
          <div className={styles.actionPanelHead}><strong>{t.actionTitles[action]}</strong><button type="button" aria-label={t.close} onClick={() => setAction(null)}>×</button></div>
          <p>{t.actionDescriptions[action]}</p>
          <button type="button" className={styles.applyButton} onClick={applyAction}>{t.apply}<span aria-hidden="true">↗</span></button>
        </div>}
        <div className={styles.demoFoot}>{!selected && view === "base" && <span className={styles.mobileHint}>{t.demoHintTouch}</span>}<p>{t.sample}</p><span className={styles.demoIndex}>PAIPAIDA / DEMO</span></div>
      </div>
    </section>

    <section className={styles.journey} id="journey" aria-labelledby="journey-title">
      <div className={styles.journeyHeading}><div><span className={styles.sectionNumber}>{t.journeyEyebrow}</span><h2 id="journey-title">{t.journeyTitle}</h2></div><p>{t.journeyIntro}</p></div>
      <div className={styles.journeyLayout}>
        <div className={styles.journeySteps} role="tablist" aria-label={t.journeyTitle}>
          {t.journeySteps.map((step, index) => <button key={step.title} type="button" role="tab" aria-selected={journeyStep === index} className={journeyStep === index ? styles.journeyStepActive : ""} onClick={() => setJourneyStep(index as JourneyStep)}><span>{String(index + 1).padStart(2, "0")}</span><strong>{step.title}</strong><small>{step.body}</small><span className={styles.journeyArrow} aria-hidden="true">↗</span></button>)}
        </div>
        <div className={styles.journeyStage} role="tabpanel" aria-label={t.journeySteps[journeyStep].title}>
          <div className={styles.journeyStageTop}><span>PAIPAIDA / {String(journeyStep + 1).padStart(2, "0")}</span><span>{t.journeyPreview[journeyStep]}</span></div>
          {journeyStep === 0 ? <div className={styles.journeyUpload}><div className={styles.journeyUploadMain}><span>＋</span><strong>{t.journeyRoom}</strong></div><div className={styles.journeyUploadRefs}><div><span>＋</span>{t.journeyStyle}<small>{t.journeyOptional}</small></div><div><span>＋</span>{t.journeyFurniture}<small>{t.journeyOptional}</small></div></div><p>{t.journeyPrompt}</p></div> :
            <div className={styles.journeyImage}><Image src={journeyStep === 4 ? "/site/approved-25d.webp" : journeyStep === 2 ? "/site/website-demo/replace.jpg" : "/site/approved-front.webp"} alt={t.journeyPreview[journeyStep]} fill sizes="(max-width: 900px) 100vw, 58vw" />{journeyStep === 2 && <div className={styles.journeyOverlay}><strong>{t.sofa}</strong><span>{t.actions.replace}</span><span>{t.actions.recolor}</span><span>{t.actions.remove}</span></div>}{journeyStep === 3 && <div className={styles.journeyReview}>{t.journeyCheck.map((item) => <span key={item}>✓ {item}</span>)}<strong>{t.journeyApproved}</strong></div>}</div>}
          <div className={styles.journeyStageFoot}><strong>{t.journeySteps[journeyStep].title}</strong><span>{String(journeyStep + 1).padStart(2, "0")} / 05</span></div>
        </div>
      </div>
    </section>

    <section className={styles.proof} id="compare">
      <div className={styles.sectionCopy}><h2><BreakLines text={t.proofTitle} /></h2><p>{t.proofBody}</p></div>
      <div className={styles.compare}>
        <div className={styles.compareLayer}><Image src="/site/website-demo/replace.jpg" alt={t.compareAfter} fill sizes="(max-width: 1660px) 100vw, 1516px" /></div>
        <div className={styles.compareBeforeLayer} style={{ clipPath: `inset(0 ${100 - comparePosition}% 0 0)` }}><Image src="/site/website-demo/base.jpg" alt={t.compareBefore} fill sizes="(max-width: 1660px) 100vw, 1516px" /></div>
        <span className={[styles.compareLabel, styles.compareLabelBefore].join(" ")}>{t.compareBefore}</span>
        <span className={[styles.compareLabel, styles.compareLabelAfter].join(" ")}>{t.compareAfter}</span>
        <div className={styles.compareDivider} style={{ left: `${comparePosition}%` }} aria-hidden="true"><span>‹ &nbsp; ›</span></div>
        <input className={styles.compareRange} type="range" min="0" max="100" value={comparePosition} onChange={(event) => setComparePosition(Number(event.target.value))} aria-label={t.compareControl} />
      </div>
    </section>

    <section className={styles.film} id="film">
      <div className={styles.filmCopy}><span className={styles.sectionNumber}>01 / 02</span><h2><BreakLines text={t.filmTitle} /></h2><p>{t.filmBody}</p></div>
      <div className={styles.filmFrame}><video controls playsInline preload="metadata" poster="/site/product-workflow-poster.jpg" aria-label={language === "zh" ? "播放工作台完整流程录屏" : "Play studio workflow recording"}><source src="/site/product-workflow-demo.mp4" type="video/mp4" /></video></div>
      <div className={styles.filmTools}><span>{t.filmQuality}</span><a href="/site/product-workflow-demo.mp4" download>{t.filmDownload} ↗</a></div>
      <ol className={styles.filmChapters}>{t.filmChapters.map((chapter, index) => <li key={chapter}><span>{String(index + 1).padStart(2, "0")}</span>{chapter}</li>)}</ol>
      <p className={styles.filmNote}>{t.filmNote}</p>
    </section>

    <section className={styles.spatial} id="spatial">
      <div className={styles.spatialImage}><Image src="/site/approved-25d.webp" alt={t.spatialTag} fill sizes="(max-width: 900px) 100vw, 56vw" /></div>
      <div className={styles.spatialCopy}><span className={styles.sectionNumber}>02 / 02</span><h2><BreakLines text={t.spatialTitle} /></h2><p>{t.spatialBody}</p><span className={styles.spatialTag}>{t.spatialTag}</span></div>
    </section>

    <footer className={styles.footer}><div><strong>拍拍搭</strong><span>{t.footer}</span></div><p>{t.finalTitle}</p><div className={styles.footerLinks}><a href="https://github.com/siguadht/paipada" target="_blank" rel="noreferrer">{t.source} ↗</a><Link href="/">{t.enter} ↗</Link></div></footer>
  </main>;
}
