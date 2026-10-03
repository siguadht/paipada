"use client";

import Image from "next/image";
import Link from "next/link";
import { useState } from "react";
import styles from "./website.module.css";

type Language = "zh" | "en";
type DemoView = "base" | "replace" | "recolor" | "remove";
type DemoAction = Exclude<DemoView, "base">;

const demoImages: Record<DemoView, string> = {
  base: "/site/website-demo/base.jpg",
  replace: "/site/website-demo/replace.jpg",
  recolor: "/site/website-demo/recolor.jpg",
  remove: "/site/website-demo/remove.jpg",
};

const copy = {
  zh: {
    nav: ["体验软装编辑", "演示视频", "空间示意"],
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
    proofTitle: "从真实房间出发，\n让想法落在眼前。",
    proofBody: "不是从一张空白画布开始。保留房间的视角与主要结构，在已有空间里讨论软装。",
    approved: "已验收空间方案 01",
    filmTitle: "交互是什么感觉？\n看一遍真实操作。",
    filmBody: "真实录屏展示家具悬停、旁边出现操作、移动选品窗与改色入口。",
    filmNote: "视频展示已验收样例的实际界面操作。生成新图仍需等待，画质因原图和模型结果而异。",
    spatialTitle: "效果图满意了，\n再看 2.5D。",
    spatialBody: "正面图确定后，才生成对应版本的空间示意。它帮助理解摆放，不作为精确户型或施工图。",
    spatialTag: "与方案 01 对应的 2.5D 示意",
    finalTitle: "从你的空间，开始创作。", footer: "AI 软装创作工作台", source: "查看源码",
  },
  en: {
    nav: ["Try decor editing", "Demo film", "Spatial view"],
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
    proofTitle: "Start with a real room.\nSee the idea take shape.",
    proofBody: "Work with the room you already have. Keep its viewpoint and main structure while exploring decor ideas.",
    approved: "Approved spatial concept 01",
    filmTitle: "What does it feel like?\nWatch a real session.",
    filmBody: "A real recording of furniture hover, nearby actions, a movable product picker, and the recolor entry.",
    filmNote: "The video shows an approved example in the real interface. Generating a new image takes time, and quality varies by photo and model result.",
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
        <a href="#experience">{t.nav[0]}</a><a href="#film">{t.nav[1]}</a><a href="#spatial">{t.nav[2]}</a>
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

    <section className={styles.proof}>
      <div className={styles.sectionCopy}><h2><BreakLines text={t.proofTitle} /></h2><p>{t.proofBody}</p></div>
      <div className={styles.proofImage}><Image src="/site/approved-front.webp" alt={t.approved} fill sizes="100vw" /><span>{t.approved}</span></div>
    </section>

    <section className={styles.film} id="film">
      <div className={styles.filmCopy}><span className={styles.sectionNumber}>01 / 02</span><h2><BreakLines text={t.filmTitle} /></h2><p>{t.filmBody}</p></div>
      <div className={styles.filmFrame}><video controls playsInline preload="metadata" poster="/site/approved-interaction.webp" aria-label={language === "zh" ? "播放真实操作录屏" : "Play real interaction recording"}><source src="/site/obs-interaction-demo.mp4" type="video/mp4" /></video></div>
      <p className={styles.filmNote}>{t.filmNote}</p>
    </section>

    <section className={styles.spatial} id="spatial">
      <div className={styles.spatialImage}><Image src="/site/approved-25d.webp" alt={t.spatialTag} fill sizes="(max-width: 900px) 100vw, 56vw" /></div>
      <div className={styles.spatialCopy}><span className={styles.sectionNumber}>02 / 02</span><h2><BreakLines text={t.spatialTitle} /></h2><p>{t.spatialBody}</p><span className={styles.spatialTag}>{t.spatialTag}</span></div>
    </section>

    <footer className={styles.footer}><div><strong>拍拍搭</strong><span>{t.footer}</span></div><p>{t.finalTitle}</p><div className={styles.footerLinks}><a href="https://github.com/siguadht/paipada" target="_blank" rel="noreferrer">{t.source} ↗</a><Link href="/">{t.enter} ↗</Link></div></footer>
  </main>;
}
