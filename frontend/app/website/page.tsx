"use client";

import Image from "next/image";
import Link from "next/link";
import { useState } from "react";
import styles from "./website.module.css";

type Language = "zh" | "en";
const copy = {
  zh: {
    nav: ["创作流程", "软装交互", "演示视频"], switch: "EN", enter: "进入工作台", eyebrow: "PAIPAIDA  /  AI SPACE STUDIO",
    hero: "让每个想法\n都在家里发生。", heroSub: "一张真实房间照片，开启可以反复修改的软装方案。", heroPrimary: "开始创作", heroSecondary: "观看演示", orbitA: "从真实空间开始", orbitB: "选中家具，直接修改", orbitC: "确认后看 2.5D", scroll: "向下探索",
    flowEyebrow: "/ CREATIVE FLOW", flowTitle: "从一张照片，\n走到满意的空间。", flowDesc: "让描述、效果图、软装修改和空间示意连成一条自然的创作路线。",
    cards: [
      { n: "01 / 03", tag: "开始创作", title: "上传真实房间，\n说出你想改变的。", body: "原照片必传；风格图与指定家具图按需添加。", image: "/site/approved-front.webp" },
      { n: "02 / 03", tag: "在图上修改", title: "选中一件家具，\n直接替换、改色或删除。", body: "家具在画面里反馈，选品窗跟着家具出现，并能拖动。", image: "/site/approved-interaction.webp" },
      { n: "03 / 03", tag: "确认后看空间", title: "满意这一版，\n再打开对应的 2.5D。", body: "空间示意帮助理解摆放，不冒充精确户型。", image: "/site/approved-25d-ui.webp" },
    ],
    prev: "上一步", next: "下一步", featureEyebrow: "/ IMAGE-FIRST EDITING", featureTitle: "软装不是清单。\n它就在画面里。", featureBody: "移到已识别家具上，整件物品会给出清楚的反馈；替换、改色、删除就在旁边。选品窗可以拖动，创作过程不必离开效果图。", featureSmall: "已验收方案 01 · 15 件可交互图层 · 本机商品目录 28 件 / 9 类",
    filmEyebrow: "/ WATCH THE WORKFLOW", filmTitle: "先看一次真实操作。", filmBody: "用 OBS 连续录下已验收方案中的家具悬停、选品窗移动和改色操作，再配上原创轻音乐。", filmBadge: "OBS 真实录屏", filmAction: "播放操作录屏", filmNote: "录屏展示已验收方案的页面交互；没有把生成过程剪成即时生图，也不代表任意照片都能得到同样效果。",
    isoEyebrow: "/ SEE THE SPACE", isoTitle: "效果图满意了，\n空间自然接上。", isoBody: "对应版本的 2.5D 让家具摆放更容易理解。它是视觉示意，不是精确施工图。", end: "从你的空间开始。", endBody: "给业主一个看得见的想法，给设计师一个可讨论的方案。", github: "GitHub 源码", footer: "拍拍搭 · AI 软装创作工作台",
  },
  en: {
    nav: ["Creative flow", "Edit decor", "Demo film"], switch: "中文", enter: "Open studio", eyebrow: "PAIPAIDA  /  AI SPACE STUDIO",
    hero: "Make every idea\nfeel at home.", heroSub: "One real room photo becomes a decor concept you can keep refining.", heroPrimary: "Start creating", heroSecondary: "Watch the demo", orbitA: "Start with a real space", orbitB: "Select and edit furniture", orbitC: "Approve, then see 2.5D", scroll: "Scroll to explore",
    flowEyebrow: "/ CREATIVE FLOW", flowTitle: "From one photo\nto a room you love.", flowDesc: "A connected path from your idea to an image, decor edits, and a spatial concept.",
    cards: [
      { n: "01 / 03", tag: "Create", title: "Upload a real room.\nDescribe the change.", body: "The room photo is required; style and furniture references are optional.", image: "/site/approved-front.webp" },
      { n: "02 / 03", tag: "Edit in image", title: "Select furniture.\nReplace, recolor, remove.", body: "The item responds in the image. The nearby product picker can be moved.", image: "/site/approved-interaction.webp" },
      { n: "03 / 03", tag: "See the space", title: "Approve this version.\nThen open its 2.5D view.", body: "An illustration of placement, not a measured floor plan.", image: "/site/approved-25d-ui.webp" },
    ],
    prev: "Previous", next: "Next", featureEyebrow: "/ IMAGE-FIRST EDITING", featureTitle: "Decor is not a list.\nIt's in the image.", featureBody: "Hover over a recognized item to see clear whole-object feedback. Replace, recolor, or remove it right there. Move the product picker wherever it works for you.", featureSmall: "Approved concept 01 · 15 interactive layers · 28 local demo items / 9 categories",
    filmEyebrow: "/ WATCH THE WORKFLOW", filmTitle: "See the real interaction.", filmBody: "A continuous OBS recording of furniture hover, a movable product picker, and recolor on an approved concept, with original ambient music.", filmBadge: "OBS screen recording", filmAction: "Play the recording", filmNote: "This demonstrates the interface on an approved concept. It does not present generation as instant or promise identical results for any uploaded photo.",
    isoEyebrow: "/ SEE THE SPACE", isoTitle: "Approve the image.\nThen explore the room.", isoBody: "The matching 2.5D view makes furniture placement easier to understand. It is a visual concept, not a construction drawing.", end: "Start with your space.", endBody: "A visible idea for homeowners, a discussable concept for designers.", github: "Source on GitHub", footer: "Paipaida · AI decor creation studio",
  },
} as const;

export default function WebsitePage() {
  const [language, setLanguage] = useState<Language>("zh");
  const [step, setStep] = useState(0);
  const t = copy[language];
  const card = t.cards[step];
  const lines = (value: string) => value.split("\n").map((line, index) => <span key={`${line}-${index}`}>{line}<br /></span>);
  return <main className={styles.site} lang={language === "zh" ? "zh-CN" : "en"}>
    <div className={styles.notice}><span>PAIPAIDA / SPACE DESIGN WORKFLOW</span><span>01 — 03</span></div>
    <header className={styles.header}>
      <a href="#top" className={styles.logo} aria-label="拍拍搭 Paipaida">拍拍搭<span>✳</span></a>
      <nav aria-label="Website navigation"><a href="#flow">{t.nav[0]}</a><a href="#edit">{t.nav[1]}</a><a href="#film">{t.nav[2]}</a></nav>
      <div className={styles.headerRight}><button type="button" onClick={() => setLanguage(language === "zh" ? "en" : "zh")}>{t.switch}</button><Link href="/">{t.enter} ↗</Link></div>
    </header>

    <section id="top" className={styles.hero}>
      <div className={styles.orbit} aria-hidden="true">
        <div className={`${styles.orbitCard} ${styles.orbitLeft}`}><Image src="/site/approved-front.webp" alt="" fill sizes="260px" /><span>01 / PHOTO TO SPACE</span></div>
        <div className={`${styles.orbitCard} ${styles.orbitRight}`}><Image src="/site/approved-25d.webp" alt="" fill sizes="280px" /><span>03 / 2.5D CONCEPT</span></div>
        <div className={`${styles.orbitCard} ${styles.orbitLower}`}><Image src="/site/approved-interaction.webp" alt="" fill sizes="260px" /><span>02 / EDIT ON CANVAS</span></div>
      </div>
      <div className={styles.heroCenter}><p className={styles.kicker}>{t.eyebrow}</p><div className={styles.heroGlyph} aria-hidden="true">✳</div><h1>{lines(t.hero)}</h1><p className={styles.heroSub}>{t.heroSub}</p><div className={styles.heroActions}><Link href="/" className={styles.buttonLight}>{t.heroPrimary} <span>↗</span></Link><a href="#film" className={styles.buttonGhost}>{t.heroSecondary} <span>↗</span></a></div></div>
      <div className={styles.heroLabels}><span>01 — {t.orbitA}</span><span>02 — {t.orbitB}</span><span>03 — {t.orbitC}</span></div>
      <a className={styles.scroll} href="#flow">{t.scroll} ↓</a>
    </section>

    <section className={styles.flow} id="flow"><div className={styles.flowIntro}><p className={styles.kickerDark}>{t.flowEyebrow}</p><h2>{lines(t.flowTitle)}</h2><p>{t.flowDesc}</p></div>
      <div className={styles.flowCard}><div className={styles.flowCardTop}><span>{card.n}</span><span>{card.tag} ↗</span></div><div className={styles.flowCardImage}><Image src={card.image} alt={card.tag} fill sizes="(max-width: 900px) 100vw, 58vw" /></div><div className={styles.flowCardBottom}><div><h3>{lines(card.title)}</h3><p>{card.body}</p></div><div className={styles.flowArrows}><button type="button" aria-label={t.prev} onClick={() => setStep((step + 2) % 3)}>←</button><button type="button" aria-label={t.next} onClick={() => setStep((step + 1) % 3)}>→</button></div></div></div>
      <div className={styles.flowProgress}>{t.cards.map((item, index) => <button type="button" key={item.n} className={index === step ? styles.activeStep : ""} onClick={() => setStep(index)} aria-label={`${index + 1}: ${item.tag}`}>{item.n}</button>)}</div>
    </section>

    <section className={styles.edit} id="edit"><div className={styles.editCopy}><p className={styles.kickerDark}>{t.featureEyebrow}</p><h2>{lines(t.featureTitle)}</h2><p>{t.featureBody}</p><div className={styles.editSmall}>{t.featureSmall}</div></div><div className={styles.editVisual}><div className={styles.editVisualTop}><span>PAIPAIDA / EDITOR</span><span>● &nbsp;LIVE INTERACTION</span></div><Image src="/site/approved-interaction.webp" alt={language === "zh" ? "已验收的软装交互界面" : "Approved decor editing interface"} fill sizes="(max-width: 900px) 100vw, 56vw" /></div></section>

    <section className={styles.film} id="film"><div className={styles.filmHead}><p className={styles.kicker}>{t.filmEyebrow}</p><h2>{t.filmTitle}</h2><p>{t.filmBody}</p></div><div className={styles.filmFrame}><video controls playsInline preload="metadata" poster="/site/approved-interaction.webp" aria-label={t.filmAction}><source src="/site/obs-interaction-demo.mp4" type="video/mp4" /></video><span className={styles.filmStamp}>{t.filmBadge} / 00:29</span></div><p className={styles.filmNote}>{t.filmNote}</p></section>

    <section className={styles.iso}><div className={styles.isoImage}><Image src="/site/approved-25d.webp" alt={language === "zh" ? "已验收的 2.5D 空间示意" : "Approved 2.5D spatial concept"} fill sizes="(max-width: 900px) 100vw, 58vw" /></div><div className={styles.isoCopy}><p className={styles.kickerDark}>{t.isoEyebrow}</p><h2>{lines(t.isoTitle)}</h2><p>{t.isoBody}</p><span>2.5D / VERSION 01</span></div></section>
    <section className={styles.end}><p>PAIPAIDA / MAKE SPACE FOR IDEAS</p><h2>{t.end}</h2><span>{t.endBody}</span><Link href="/">{t.enter} ↗</Link></section>
    <footer className={styles.footer}><strong>拍拍搭 ✳</strong><span>{t.footer}</span><a href="https://github.com/siguadht/paipada" target="_blank" rel="noreferrer">{t.github} ↗</a></footer>
  </main>;
}
