"use client";

import Image from "next/image";
import Link from "next/link";
import { useState } from "react";
import styles from "./website.module.css";

const copy = {
  zh: {
    navWork: "作品与体验", navHow: "如何创作", navFilm: "演示影片", open: "进入工作台", eyebrow: "PAIPAIDA / SPACE CREATION STUDIO",
    heroA: "把家的想法，", heroB: "放进真实空间。", intro: "从一张房间照片出发，在效果图里直接换家具、改颜色、删软装。满意后，再看同版的 2.5D 空间示意。",
    viewFilm: "观看 15 秒演示", explore: "向下了解", proof: "已验收的产品演示画面", proofSub: "真实生成结果 · 方案 01 · 软装可交互",
    filmOver: "先看一遍，再亲手试", filmTitle: "一段稳定的演示，讲清楚最重要的事。", filmDesc: "视频将已验收的效果图、软装交互界面和对应 2.5D 剪成一段导览。它是预录的画面剪辑，不是实时生图成功率展示。",
    interactionOver: "01 / EDIT IN THE IMAGE", interactionTitle: "家具就在画面里改。", interactionDesc: "鼠标移到已识别的家具上，会出现整件反馈与替换、改色、删除。选品窗从家具旁出现，还能拖到顺手的位置。",
    productNote: "当前本机演示目录：28 件，9 类。商品主图只用于本机展示，不代表精确复刻或实时库存。",
    isoOver: "02 / SEE THE SPACE", isoTitle: "这一版满意了，再看 2.5D。", isoDesc: "2.5D 与确认的正面版本对应，帮助理解摆放关系；它是空间示意，不是精确户型图。",
    stepsOver: "FROM IDEA TO SPACE", stepsTitle: "创作只需沿着一个方向走。", steps: ["上传真实房间与参考", "生成正面效果图", "在图上修改软装", "确认后查看 2.5D"],
    finalA: "你的空间，", finalB: "由你来定。", finalDesc: "业主和设计师，都能从同一个工作台开始。", footer: "拍拍搭 · AI 软装创作工作台", github: "查看源码", lang: "English",
  },
  en: {
    navWork: "The experience", navHow: "How it works", navFilm: "Demo film", open: "Open studio", eyebrow: "PAIPAIDA / SPACE CREATION STUDIO",
    heroA: "Make room for", heroB: "your ideas.", intro: "Start with a real room photo. Replace furniture, change colors, and remove decor directly in the image. Once it feels right, explore a matching 2.5D concept.",
    viewFilm: "Watch the 15s demo", explore: "Explore", proof: "Approved demo imagery", proofSub: "Real generated result · Concept 01 · Interactive decor",
    filmOver: "WATCH FIRST, THEN CREATE", filmTitle: "A clear preview of what matters.", filmDesc: "This prerecorded edit combines the approved room result, the decor editing interface, and its 2.5D view. It is a guided montage, not a claim about live generation reliability.",
    interactionOver: "01 / EDIT IN THE IMAGE", interactionTitle: "Edit furniture where you see it.", interactionDesc: "Hover over a recognized item for whole-object feedback and options to replace, recolor, or remove it. The product picker opens beside the item and can be moved.",
    productNote: "The local demo catalog currently has 28 items across 9 categories. Product imagery is for local demonstration; exact product replication and live stock are not promised.",
    isoOver: "02 / SEE THE SPACE", isoTitle: "Approve the image. Then see 2.5D.", isoDesc: "The 2.5D concept corresponds to the approved front view and helps show placement. It is an illustration, not a measured floor plan.",
    stepsOver: "FROM IDEA TO SPACE", stepsTitle: "One continuous creative flow.", steps: ["Upload a room and references", "Generate the front view", "Edit decor in the image", "Approve and explore 2.5D"],
    finalA: "Your space,", finalB: "your call.", finalDesc: "One creative studio for homeowners and designers.", footer: "Paipaida · AI decor creation studio", github: "View source", lang: "中文",
  },
} as const;

export default function WebsitePage() {
  const [language, setLanguage] = useState<"zh" | "en">("zh");
  const t = copy[language];
  return (
    <main className={styles.site} lang={language === "zh" ? "zh-CN" : "en"}>
      <header className={styles.header}>
        <a className={styles.brand} href="#top" aria-label="拍拍搭 Paipaida">拍拍搭<span className={styles.brandDot}>.</span></a>
        <nav className={styles.nav} aria-label="Website navigation">
          <a href="#experience">{t.navWork}</a><a href="#process">{t.navHow}</a><a href="#film">{t.navFilm}</a>
        </nav>
        <div className={styles.headerActions}><button className={styles.language} onClick={() => setLanguage(language === "zh" ? "en" : "zh")} type="button">{t.lang}</button><Link className={styles.openButton} href="/">{t.open}<span aria-hidden="true">↗</span></Link></div>
      </header>

      <section className={styles.hero} id="top">
        <div className={styles.heroCopy}><p className={styles.overline}>{t.eyebrow}</p><h1>{t.heroA}<br /><span>{t.heroB}</span></h1><p className={styles.intro}>{t.intro}</p><div className={styles.heroActions}><a className={styles.pillDark} href="#film">{t.viewFilm}<span aria-hidden="true">↗</span></a><a className={styles.textLink} href="#experience">{t.explore} ↓</a></div></div>
        <div className={styles.heroMedia}><Image src="/site/approved-front.webp" alt={language === "zh" ? "已验收的客厅正面效果图" : "Approved living room front view"} fill priority sizes="(max-width: 900px) 100vw, 54vw" /><div className={styles.imageMark}><span className={styles.markCircle}>01</span><span>{t.proofSub}</span></div></div>
        <div className={styles.heroBottom}><span>{t.proof}</span><span>SCROLL TO EXPLORE ↓</span></div>
      </section>

      <section className={styles.filmSection} id="film"><div className={styles.sectionLead}><p className={styles.overline}>{t.filmOver}</p><h2>{t.filmTitle}</h2><p>{t.filmDesc}</p></div><div className={styles.filmBox}><video controls playsInline preload="metadata" poster="/site/approved-interaction.webp" aria-label={t.navFilm}><source src="/site/approved-demo-tour.mp4" type="video/mp4" /></video><span className={styles.filmBadge}>01 / DEMO TOUR · 00:15</span></div></section>

      <section className={styles.feature} id="experience"><div className={styles.featureText}><p className={styles.overline}>{t.interactionOver}</p><h2>{t.interactionTitle}</h2><p>{t.interactionDesc}</p><div className={styles.featureFoot}>{t.productNote}</div></div><div className={styles.featureImage}><Image src="/site/approved-interaction.webp" alt={language === "zh" ? "家具悬停和替换面板的真实产品界面" : "Actual furniture hover and replace interface"} fill sizes="(max-width: 900px) 100vw, 60vw" /></div></section>

      <section className={`${styles.feature} ${styles.featureReverse}`}><div className={styles.featureText}><p className={styles.overline}>{t.isoOver}</p><h2>{t.isoTitle}</h2><p>{t.isoDesc}</p></div><div className={styles.featureImage}><Image src="/site/approved-25d-ui.webp" alt={language === "zh" ? "已验收的 2.5D 方案页面" : "Approved 2.5D concept page"} fill sizes="(max-width: 900px) 100vw, 60vw" /></div></section>

      <section className={styles.process} id="process"><div><p className={styles.overline}>{t.stepsOver}</p><h2>{t.stepsTitle}</h2></div><ol>{t.steps.map((step, index) => <li key={step}><span>0{index + 1}</span><strong>{step}</strong><span aria-hidden="true">↗</span></li>)}</ol></section>
      <section className={styles.final}><p className={styles.overline}>MAKE SPACE FOR MORE</p><h2>{t.finalA}<br />{t.finalB}</h2><p>{t.finalDesc}</p><Link className={styles.pillLight} href="/">{t.open}<span aria-hidden="true">↗</span></Link></section>
      <footer className={styles.footer}><span>{t.footer}</span><a href="https://github.com/siguadht/paipada" target="_blank" rel="noreferrer">{t.github} ↗</a><span>© 2026 PAIPAIDA</span></footer>
    </main>
  );
}
