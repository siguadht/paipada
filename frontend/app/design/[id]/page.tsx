"use client";

import {
  ArrowLeft, ArrowRight, CaretDown, Check, ClockCounterClockwise, Images, PaintBrush,
  Palette, SpinnerGap, Swap, Trash, X, Sparkle,
} from "@phosphor-icons/react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError, api, Design, DesignHotspot, fetchProtectedImage, getToken, Product, Version } from "@/lib/api";
import { useProtectedImage } from "@/lib/use-protected-image";
import { WorkbenchSidebar } from "@/components/workbench-sidebar";

type Operation = "delete" | "replace" | "recolor" | "style" | "restore_structure";
type Point = { x: number; y: number };

const actionLabels: Record<Operation, string> = {
  delete: "删除这件软装",
  replace: "替换这件软装",
  recolor: "修改它的颜色",
  style: "调整整体风格",
  restore_structure: "修正房间结构",
};

const categoryLabels: Record<string, string> = {
  sofa: "沙发", chair: "单椅餐椅", bed: "床与卧榻", light: "灯具", plant: "绿植", table: "桌几", rug: "地毯", cabinet: "柜体", art: "墙饰",
};

function VersionCard({ version, current, disabled, onRestore }: {
  version: Version; current: boolean; disabled: boolean; onRestore: () => void;
}) {
  const image = useProtectedImage(version.image_url);
  const label = version.operation === "initial" ? "初始效果图" : version.operation === "regenerate" ? "按反馈重新生成" : version.operation === "concept_view" ? "新机位示意图" : actionLabels[version.operation as Operation] || "已修改";
  return <article className={`version-card ${current ? "is-current" : ""}`}>
    <div className="version-card-image">{image.url ? <img src={image.url} alt={`第 ${version.number} 版效果图`} /> : <span>图片加载中</span>}<b>第 {version.number} 版</b></div>
    <div className="version-card-body"><div><strong>{label}</strong>{current && <span className="version-current-tag">当前使用</span>}</div><p>{version.instruction || (version.operation === "initial" ? "最初生成的方案" : "根据当前要求修改")}</p>{!current && <button type="button" disabled={disabled} onClick={onRestore}>恢复这一版 <ArrowRight size={14} /></button>}</div>
  </article>;
}

function ProductShelf({ products, selectedId, onChoose }: {
  products: Product[]; selectedId?: string; onChoose?: (product: Product) => void;
}) {
  const [category, setCategory] = useState("all");
  const demoCatalog = products.some((product) => product.demo_only);
  const shelfProducts = demoCatalog ? products.filter((product) => product.demo_only) : products;
  const categories = Array.from(new Set(shelfProducts.map((product) => product.category)));
  const visible = category === "all" ? shelfProducts : shelfProducts.filter((product) => product.category === category);
  return <div className="product-shelf">
    <div className="product-categories" aria-label="软装分类">
      <button type="button" className={category === "all" ? "active" : ""} onClick={() => setCategory("all")}>全部</button>
      {categories.map((key) => <button type="button" key={key} className={category === key ? "active" : ""} onClick={() => setCategory(key)}>{categoryLabels[key] || key}</button>)}
    </div>
    <div className="product-cards">
      {visible.map((product) => {
        const card = <>
          <span className="product-card-visual" data-category={product.category}>
            {product.image_url ? <img src={product.image_url} alt={product.name} /> : <span>商品图待补</span>}
          </span>
          <span className="product-card-copy"><small>{product.brand}{product.demo_only ? " · 演示选品" : ""}</small><strong>{product.name}</strong><small>{product.color}{product.price == null ? "" : ` · 参考价 ¥${product.price.toLocaleString("zh-CN")}`}</small></span>
          {selectedId === product.id && <Check size={16} aria-hidden="true" />}
        </>;
        return <article key={product.id} className={`product-card ${selectedId === product.id ? "selected" : ""}`}>
          {onChoose ? <button type="button" className="product-card-select" onClick={() => onChoose(product)} aria-pressed={selectedId === product.id} aria-label={`选择${product.name}`}>{card}</button> : <div className="product-card-select">{card}</div>}
          {product.source_url && <a className="product-card-link" href={product.source_url} target="_blank" rel="noopener noreferrer" onClick={(event) => event.stopPropagation()}>查看品牌原页 <ArrowRight size={13} aria-hidden="true" /></a>}
        </article>;
      })}
    </div>
    <p className="product-shelf-note">{demoCatalog ? "本机产品演示：图片与名称对应品牌原页；未核实中国地区购买、价格或库存。效果图中的家具不保证与选中商品完全一致。" : "内置示意资料，仅供搭配灵感；暂无真实商品图、库存或购买链接，价格未经核实。生成结果也不保证与单品一致。"}</p>
  </div>;
}

function ReferenceInput({ label, hint, url, preview, onPick }: { label: string; hint: string; url?: string; preview?: string; onPick: (file?: File) => void }) {
  const stored = useProtectedImage(url || "");
  const input = useRef<HTMLInputElement>(null);
  return <><button type="button" className="design-reference-input" onClick={() => input.current?.click()}>
    {preview || stored.url ? <img src={preview || stored.url} alt="" /> : <Images size={23} />}
    <span><strong>{label}</strong><small>{preview ? "待用于下次修改" : url ? "已关联 · 点击更换" : hint}</small></span>
  </button><input ref={input} type="file" hidden accept="image/jpeg,image/png,image/webp" onChange={(event) => onPick(event.target.files?.[0])} /></>;
}

type LayerSprite = { url: string; alpha: Uint8ClampedArray; width: number; height: number };
type PickerPosition = { x: number; y: number; mode: "desktop" | "mobile" };

function EditableCanvas({ design, point, setPoint, onAction, onSelectLayer, operation, disabled, products, chosenProduct, onChooseProduct, onResetProduct, onClosePicker }: {
  design: Design; point: Point | null; setPoint: (point: Point) => void;
  onAction: (operation: Operation) => void; onSelectLayer: (index: number | null) => void;
  operation: Operation | null; disabled: boolean; products: Product[]; chosenProduct: string;
  onChooseProduct: (product: Product) => void; onResetProduct: () => void; onClosePicker: () => void;
}) {
  const image = useProtectedImage(design.front_image_url);
  const layerSet = design.layer_set?.status === "ready" ? design.layer_set : null;
  const layerKey = layerSet?.layers.map((layer) => layer.image_url).join("|") || "";
  const [sprites, setSprites] = useState<LayerSprite[]>([]);
  const [hoveredLayer, setHoveredLayer] = useState<number | null>(null);
  const [activeLayer, setActiveLayer] = useState<number | null>(null);
  const [aspect, setAspect] = useState(4 / 3);
  const [pickerPosition, setPickerPosition] = useState<PickerPosition | null>(null);
  const [pickerMoved, setPickerMoved] = useState(false);
  const [pickerMode, setPickerMode] = useState<"desktop" | "mobile">("desktop");
  const imageWrap = useRef<HTMLDivElement>(null);
  const picker = useRef<HTMLDivElement>(null);
  const hoveredPoint = useRef<Point | null>(null);
  const drag = useRef<{ pointerId: number; startX: number; startY: number; originX: number; originY: number; mode: "desktop" | "mobile" } | null>(null);

  useEffect(() => {
    const media = window.matchMedia("(max-width: 760px)");
    const update = () => setPickerMode(media.matches ? "mobile" : "desktop");
    update();
    media.addEventListener("change", update);
    return () => media.removeEventListener("change", update);
  }, []);

  function boundedPickerPosition(x: number, y: number, mode: "desktop" | "mobile"): PickerPosition {
    const panel = picker.current;
    const bounds = mode === "mobile" ? { width: window.innerWidth, height: window.innerHeight } : imageWrap.current?.getBoundingClientRect();
    const width = panel?.offsetWidth || Math.min(385, (bounds?.width || 800) * 0.9);
    const height = panel?.offsetHeight || Math.min((bounds?.height || 600) * 0.7, 450);
    return {
      x: Math.max(8, Math.min(x, Math.max(8, (bounds?.width || 800) - width - 8))),
      y: Math.max(8, Math.min(y, Math.max(8, (bounds?.height || 600) - height - 8))),
      mode,
    };
  }

  function startDrag(event: React.PointerEvent<HTMLButtonElement>) {
    if (!picker.current) return;
    const mode = window.matchMedia("(max-width: 760px)").matches ? "mobile" : "desktop";
    const rect = picker.current.getBoundingClientRect();
    const wrap = imageWrap.current?.getBoundingClientRect();
    drag.current = { pointerId: event.pointerId, startX: event.clientX, startY: event.clientY,
      originX: rect.left - (mode === "desktop" ? wrap?.left || 0 : 0),
      originY: rect.top - (mode === "desktop" ? wrap?.top || 0 : 0), mode };
    event.currentTarget.setPointerCapture(event.pointerId);
  }

  function moveDrag(event: React.PointerEvent<HTMLButtonElement>) {
    const current = drag.current;
    if (!current || current.pointerId !== event.pointerId) return;
    const dx = event.clientX - current.startX;
    const dy = event.clientY - current.startY;
    if (Math.abs(dx) + Math.abs(dy) < 3 && !pickerMoved) return;
    setPickerMoved(true);
    setPickerPosition(boundedPickerPosition(current.originX + dx, current.originY + dy, current.mode));
  }

  function movePickerByKey(event: React.KeyboardEvent<HTMLButtonElement>) {
    const delta = { ArrowLeft: [-24, 0], ArrowRight: [24, 0], ArrowUp: [0, -24], ArrowDown: [0, 24] }[event.key];
    if (!delta || !picker.current) return;
    event.preventDefault();
    const rect = picker.current.getBoundingClientRect();
    const wrap = imageWrap.current?.getBoundingClientRect();
    setPickerMoved(true);
    setPickerPosition(boundedPickerPosition(rect.left - (pickerMode === "desktop" ? wrap?.left || 0 : 0) + delta[0],
      rect.top - (pickerMode === "desktop" ? wrap?.top || 0 : 0) + delta[1], pickerMode));
  }

  function chooseAction(next: Operation) {
    const target = point || (hoveredLayer !== null ? hoveredPoint.current : null);
    if (!target) return;
    if (!point && hoveredLayer !== null) {
      setActiveLayer(hoveredLayer);
      onSelectLayer(hoveredLayer);
      setPoint(target);
    }
    if (next === "replace" && !pickerMoved && imageWrap.current) {
      const rect = imageWrap.current.getBoundingClientRect();
      const width = Math.min(385, rect.width * 0.9);
      const x = target.x * rect.width;
      const candidateX = x + 16 + width <= rect.width - 8 ? x + 16 : x - width - 16;
      setPickerPosition(boundedPickerPosition(candidateX, target.y * rect.height - 28, "desktop"));
    }
    onAction(next);
  }

  useEffect(() => {
    if (!layerSet || !layerKey) { return; }
    const controller = new AbortController();
    const urls: string[] = [];
    Promise.all(layerSet.layers.map(async (layer) => {
      const url = await fetchProtectedImage(layer.image_url, controller.signal);
      urls.push(url);
      const bitmap = new Image();
      bitmap.src = url;
      await bitmap.decode();
      const canvas = document.createElement("canvas");
      canvas.width = bitmap.naturalWidth;
      canvas.height = bitmap.naturalHeight;
      const context = canvas.getContext("2d", { willReadFrequently: true });
      if (!context) throw new Error("无法读取家具轮廓");
      context.drawImage(bitmap, 0, 0);
      return { url, alpha: context.getImageData(0, 0, canvas.width, canvas.height).data, width: canvas.width, height: canvas.height };
    })).then((next) => { if (!controller.signal.aborted) setSprites(next); }).catch(() => { if (!controller.signal.aborted) setSprites([]); });
    return () => { controller.abort(); urls.forEach((url) => URL.revokeObjectURL(url)); setSprites([]); setActiveLayer(null); setHoveredLayer(null); };
  // layerKey changes when the current version's layer URLs change.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [layerKey]);

  const layersReady = Boolean(layerSet && sprites.length === layerSet.layers.length);
  const hoverBox = hoveredLayer !== null && layersReady ? layerSet?.layers[hoveredLayer]?.box : null;
  const hoverMenuPoint = hoverBox ? { x: (hoverBox[0] + hoverBox[2]) / 2, y: hoverBox[1] } : null;
  const menuPoint = point || hoverMenuPoint;

  function hitLayer(x: number, y: number): number | null {
    if (!layersReady || !layerSet) return null;
    for (let index = sprites.length - 1; index >= 0; index--) {
      const [left, top, right, bottom] = layerSet.layers[index].box;
      if (x < left || x > right || y < top || y > bottom) continue;
      const sprite = sprites[index];
      const px = Math.min(sprite.width - 1, Math.floor((x - left) / (right - left) * sprite.width));
      const py = Math.min(sprite.height - 1, Math.floor((y - top) / (bottom - top) * sprite.height));
      if (sprite.alpha[(py * sprite.width + px) * 4 + 3] > 50) return index;
    }
    return null;
  }

  function coordinates(event: React.MouseEvent<HTMLImageElement>): Point {
    const rect = event.currentTarget.getBoundingClientRect();
    return {
      x: Math.max(0, Math.min(1, (event.clientX - rect.left) / rect.width)),
      y: Math.max(0, Math.min(1, (event.clientY - rect.top) / rect.height)),
    };
  }

  function choose(event: React.MouseEvent<HTMLImageElement>) {
    if (disabled) return;
    const next = coordinates(event);
    const index = hitLayer(next.x, next.y);
    setActiveLayer(index);
    onSelectLayer(index);
    setPoint(next);
    if (!pickerMoved) setPickerPosition(null);
  }

  function keyChoose(event: React.KeyboardEvent<HTMLImageElement>) {
    if (disabled || !["Enter", " "].includes(event.key)) return;
    event.preventDefault();
    setPoint(point || { x: 0.5, y: 0.5 });
    onSelectLayer(null);
    if (!pickerMoved) setPickerPosition(null);
  }

  if (image.error) return <div className="image-error">{image.error}</div>;
  if (!image.url) return <div className="image-loading"><SpinnerGap size={28} className="spin" /> 正在加载效果图</div>;
  return (
    <div className={`editor-canvas ${disabled ? "is-disabled" : ""}`}>
      <div ref={imageWrap} className="editor-image-wrap" style={{ "--image-ratio": aspect } as React.CSSProperties}
        onMouseLeave={() => { hoveredPoint.current = null; setHoveredLayer(null); }}>
        <img
          src={image.url} alt="生成的正面效果图，点击要修改的软装物品"
          onLoad={(event) => setAspect(event.currentTarget.naturalWidth / event.currentTarget.naturalHeight)}
          onClick={choose} onKeyDown={keyChoose}
          onMouseMove={(event) => { const next = coordinates(event); event.currentTarget.parentElement?.style.setProperty("--pointer-x", `${next.x * 100}%`); event.currentTarget.parentElement?.style.setProperty("--pointer-y", `${next.y * 100}%`); const index = hitLayer(next.x, next.y); hoveredPoint.current = index === null ? null : next; setHoveredLayer(index); }}
          tabIndex={disabled ? -1 : 0}
          className={`editor-image ${hoveredLayer !== null ? "is-object-hovered" : ""}`} draggable={false}
        />
        {layersReady && layerSet?.layers.map((layer, index) => {
          const [left, top, right, bottom] = layer.box;
          return <span key={layer.image_url} aria-hidden="true"
            className={`interactive-furniture-layer ${hoveredLayer === index ? "is-hovered" : ""} ${point && activeLayer === index ? "is-active" : ""}`}
            style={{ left: `${left * 100}%`, top: `${top * 100}%`, width: `${(right - left) * 100}%`, height: `${(bottom - top) * 100}%`, zIndex: layer.z_index,
              maskImage: `url("${sprites[index].url}")`, WebkitMaskImage: `url("${sprites[index].url}")` }} />;
        })}
        {layersReady && hoveredLayer !== null && layerSet && !disabled && <span className="furniture-hover-label" style={{ left: `${Math.min(75, Math.max(25, layerSet.layers[hoveredLayer].box[0] * 100))}%`, top: `${Math.max(4, layerSet.layers[hoveredLayer].box[1] * 100)}%` }}>{layerSet.layers[hoveredLayer].name} · 可直接操作</span>}
        {!layersReady && !point && !disabled && <span className="position-hover-hint" aria-hidden="true">点击选位置 · 可替换软装</span>}
        {menuPoint && !disabled && (
          <>
            {point && (!layersReady || activeLayer === null) && <span className="selection-ring" aria-hidden="true" style={{ left: `${point.x * 100}%`, top: `${point.y * 100}%` }} />}
            <div className={`image-selection-actions ${point ? point.y > 0.65 ? "is-above" : "" : menuPoint.y > 0.16 ? "is-above" : ""}`}
              style={{ left: `${Math.min(73, Math.max(27, menuPoint.x * 100))}%`, top: `${menuPoint.y * 100}%` }} aria-label={point ? "选中位置的修改操作" : "悬停家具的修改操作"}>
              <button type="button" className={operation === "replace" ? "active" : ""} onClick={() => chooseAction("replace")}><Swap size={15} />替换</button>
              <button type="button" className={operation === "recolor" ? "active" : ""} onClick={() => chooseAction("recolor")}><Palette size={15} />改色</button>
              <button type="button" className={operation === "delete" ? "active" : ""} onClick={() => chooseAction("delete")}><Trash size={15} />删除</button>
            </div>
            {point && operation === "replace" && <div ref={picker} className={`image-product-popover ${pickerPosition?.mode === pickerMode ? "has-position" : ""}`}
              style={pickerPosition?.mode === pickerMode ? { left: pickerPosition.x, top: pickerPosition.y } : pickerMode === "desktop" ? {
                left: point.x >= 0.5 ? `max(8px, calc(${point.x * 100}% - min(385px, 90%) - 16px))` : `min(calc(100% - min(385px, 90%) - 8px), calc(${point.x * 100}% + 16px))`,
                top: `min(calc(100% - 70% - 8px), max(8px, calc(${point.y * 100}% - 28px)))`,
              } : undefined}
              aria-label="在选中软装旁选择替换商品" onKeyDown={(event) => { if (event.key === "Escape") onClosePicker(); }}>
              <div className="image-product-popover-head"><button type="button" className="image-product-drag-handle"
                aria-label="拖动选品窗口，或用方向键移动" title="按住拖动 · 方向键移动"
                onPointerDown={startDrag} onPointerMove={moveDrag} onPointerUp={() => { drag.current = null; }} onPointerCancel={() => { drag.current = null; }} onKeyDown={movePickerByKey}>
                <span className="image-product-grip" aria-hidden="true">⠿</span><span><strong>替换这里的软装</strong><small>{chosenProduct ? "已选参考商品，继续在下方描述" : "按住这里移动 · 选择商品作参考"}</small></span>
              </button><button type="button" className="image-product-close" onClick={onClosePicker} aria-label="关闭选品面板"><X size={17} /></button></div>
              {chosenProduct ? <div className="image-product-chosen"><span>{products.find((item) => item.id === chosenProduct)?.name || "已选参考商品"}</span><button type="button" onClick={onResetProduct}>重选商品</button></div> : <ProductShelf products={products} selectedId={chosenProduct} onChoose={onChooseProduct} />}
            </div>}
          </>
        )}
      </div>
    </div>
  );
}

function IsometricCanvas({ design, products, tagging, draftPoint, onPlace, selectedId, onSelect }: {
  design: Design; products: Product[]; tagging: boolean; draftPoint: Point | null;
  onPlace: (point: Point) => void; selectedId: string; onSelect: (id: string) => void;
}) {
  const image = useProtectedImage(design.iso_image_url);
  const [aspect, setAspect] = useState(4 / 3);
  if (image.error) return <div className="image-error">{image.error}</div>;
  if (!image.url) return <div className="image-loading"><SpinnerGap size={28} className="spin" /> 正在加载 2.5D 图片</div>;
  const selected = design.hotspots?.find((hotspot) => hotspot.id === selectedId);
  const selectedProduct = products.find((product) => product.id === selected?.product_id);
  return <div className="iso-canvas">
    <div className="iso-image-wrap" style={{ "--image-ratio": aspect } as React.CSSProperties}>
      <img src={image.url} alt={tagging ? "2.5D 图片，点击要标注的商品位置" : "已确认的 2.5D 方案"}
        onLoad={(event) => setAspect(event.currentTarget.naturalWidth / event.currentTarget.naturalHeight)}
        onClick={(event) => {
          if (!tagging) return;
          const rect = event.currentTarget.getBoundingClientRect();
          onPlace({ x: Math.max(0, Math.min(1, (event.clientX - rect.left) / rect.width)), y: Math.max(0, Math.min(1, (event.clientY - rect.top) / rect.height)) });
        }}
        onKeyDown={(event) => { if (tagging && (event.key === "Enter" || event.key === " ")) { event.preventDefault(); onPlace({ x: 0.5, y: 0.5 }); } }}
        tabIndex={tagging ? 0 : -1} className={tagging ? "iso-image is-tagging" : "iso-image"} draggable={false} />
      {(design.hotspots || []).map((hotspot: DesignHotspot, index: number) => {
        const product = products.find((item) => item.id === hotspot.product_id);
        return <button key={hotspot.id} type="button" className={`iso-hotspot ${selectedId === hotspot.id ? "active" : ""}`}
          style={{ left: `${hotspot.x * 100}%`, top: `${hotspot.y * 100}%` }}
          onClick={() => onSelect(selectedId === hotspot.id ? "" : hotspot.id)}
          aria-label={`查看热点 ${index + 1}：${product?.name || "参考商品"}`}>{index + 1}</button>;
      })}
      {draftPoint && <span className="iso-draft-point" style={{ left: `${draftPoint.x * 100}%`, top: `${draftPoint.y * 100}%` }} aria-hidden="true">+</span>}
      {selected && <div className="iso-hotspot-card" role="dialog" aria-label="热点商品卡">
        <button type="button" className="iso-hotspot-close" onClick={() => onSelect("")} aria-label="关闭商品卡"><X size={16} /></button>
        <small>热点 {design.hotspots.indexOf(selected) + 1} · 搭配参考</small>
        {selectedProduct?.image_url && <img className="iso-hotspot-product-image" src={selectedProduct.image_url} alt={selectedProduct.name} />}
        <strong>{selectedProduct?.name || "原参考商品已移除"}</strong>
        <span>{selectedProduct ? `${selectedProduct.brand} · ${selectedProduct.color}${selectedProduct.price == null ? "" : ` · 参考价 ¥${selectedProduct.price.toLocaleString("zh-CN")}`}` : "请删除并重新标注"}</span>
        {selectedProduct?.source_url && <a href={selectedProduct.source_url} target="_blank" rel="noopener noreferrer">查看品牌原页 ↗</a>}
        <p>由用户在当前 2.5D 图片上标注；图中物品不保证与参考单品完全一致。</p>
      </div>}
    </div>
  </div>;
}

function Comparison({ design }: { design: Design }) {
  const photo = useProtectedImage(design.photo_url);
  const front = useProtectedImage(design.front_image_url);
  const [position, setPosition] = useState(50);
  const [photoGeometry, setPhotoGeometry] = useState({ url: "", ratio: 0 });
  const [frontGeometry, setFrontGeometry] = useState({ url: "", ratio: 0 });
  if (!photo.url || !front.url) return <div className="image-loading">正在载入对比图片…</div>;
  const geometryKnown = photoGeometry.url === photo.url && frontGeometry.url === front.url;
  const differentRatio = geometryKnown && Math.abs(photoGeometry.ratio / frontGeometry.ratio - 1) > 0.025;
  return (
    <div className="compare-wrap">
      {differentRatio ? <div className="compare-full-images">
        <figure><figcaption>原照片 · 完整画面</figcaption><img src={photo.url} alt="完整原房间照片" /></figure>
        <figure><figcaption>效果图 · 完整画面</figcaption><img src={front.url} alt="完整效果图" /></figure>
        <p>两张图片比例不同，分别展示完整画面，避免裁切影响门窗核对。</p>
      </div> : <><div className="compare-images">
        <img src={front.url} alt="改造后的效果图" onLoad={(event) => setFrontGeometry({ url: front.url, ratio: event.currentTarget.naturalWidth / event.currentTarget.naturalHeight })} />
        <img src={photo.url} alt="原房间照片" className="compare-original" style={{ clipPath: `inset(0 ${100 - position}% 0 0)` }} onLoad={(event) => setPhotoGeometry({ url: photo.url, ratio: event.currentTarget.naturalWidth / event.currentTarget.naturalHeight })} />
        <span className="compare-line" style={{ left: `${position}%` }}><span>‹ ›</span></span>
        <span className="compare-tag compare-tag-left">改造前</span><span className="compare-tag compare-tag-right">效果图</span>
      </div>
      <label className="compare-control">拖动查看变化<input type="range" min="0" max="100" value={position} onChange={(e) => setPosition(Number(e.target.value))} aria-label="前后对比位置" /></label></>}
    </div>
  );
}

const waitingGuides = [
  { label: "点选物品", title: "直接在图上选", copy: "效果图出来后，点一下沙发、灯具或其他软装，就能开始修改。" },
  { label: "修改细节", title: "一处一处调到喜欢", copy: "可以删除、替换或改色；每次成功修改都会留下可恢复的版本。" },
  { label: "确认方案", title: "满意后再看 2.5D", copy: "只有确认当前正面效果图，才会以这张图继续生成 2.5D。" },
];

function GenerationExperience({ design }: { design: Design }) {
  const photo = useProtectedImage(design.photo_url);
  const [seconds, setSeconds] = useState(0);
  const [guide, setGuide] = useState(0);
  useEffect(() => {
    const timer = setInterval(() => setSeconds((value) => value + 1), 1000);
    return () => clearInterval(timer);
  }, []);
  const stage = design.status === "pending" ? 0 : design.status === "understanding" ? 1 : 2;
  return <div className="generation-experience" aria-live="polite">
    {photo.url && <img src={photo.url} alt="你上传的原始房间照片" className="generation-photo" />}
    <div className="generation-wash" />
    <div className="generation-card">
      <span className="generation-kicker"><Sparkle size={17} /> 正在为你的空间创作</span>
      <h2>{stage < 2 ? "先读懂你的家，" : "让新家的样子，"}<br /><em>{stage < 2 ? "再慢慢动笔。" : "一点点出现。"}</em></h2>
      <p className="generation-current"><span className="generation-live-dot" />{design.current_step}</p>
      <ol className="generation-steps">
        {["照片已上传", "理解空间与需求", "生成正面效果图"].map((label, index) => <li key={label} className={index < stage ? "done" : index === stage ? "current" : ""}><span>{index < stage ? <Check size={13} weight="bold" /> : String(index + 1).padStart(2, "0")}</span>{label}</li>)}
      </ol>
      <div className="generation-guide">
        <span className="generation-guide-heading">等待时，先看看接下来能做什么</span>
        <div className="generation-guide-tabs" role="tablist" aria-label="效果图操作引导">
          {waitingGuides.map((item, index) => <button key={item.label} role="tab" aria-selected={guide === index} className={guide === index ? "active" : ""} onClick={() => setGuide(index)}>{item.label}</button>)}
        </div>
        <strong>{waitingGuides[guide].title}</strong><p>{waitingGuides[guide].copy}</p>
      </div>
      <small>已等待 {Math.floor(seconds / 60)}:{String(seconds % 60).padStart(2, "0")} · 生成会在后台继续，可稍后回到“我的方案”查看</small>
    </div>
  </div>;
}

export default function DesignPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const [design, setDesign] = useState<Design | null>(null);
  const [point, setPoint] = useState<Point | null>(null);
  const [selectedLayer, setSelectedLayer] = useState<number | null>(null);
  const [layerCostConfirmed, setLayerCostConfirmed] = useState(false);
  const [operation, setOperation] = useState<Operation | null>(null);
  const [detail, setDetail] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [view, setView] = useState<"front" | "compare" | "iso">("front");
  const [reviewOpen, setReviewOpen] = useState(false);
  const [reviewImageKey, setReviewImageKey] = useState("");
  const [reviewChecks, setReviewChecks] = useState({ doors_windows: false, walls_floor: false, camera_layout: false, concept_acknowledged: false });
  const [products, setProducts] = useState<Product[]>([]);
  const [chosenProduct, setChosenProduct] = useState("");
  const [editorOpen, setEditorOpen] = useState(true);
  const [catalogOpen, setCatalogOpen] = useState(false);
  const [tagging, setTagging] = useState(false);
  const [draftPoint, setDraftPoint] = useState<Point | null>(null);
  const [tagProduct, setTagProduct] = useState("");
  const [selectedHotspot, setSelectedHotspot] = useState("");
  const [feedbackOpen, setFeedbackOpen] = useState(false);
  const [feedback, setFeedback] = useState("");
  const [feedbackMode, setFeedbackMode] = useState<"original" | "concept">("original");
  const [referenceFiles, setReferenceFiles] = useState<{ style?: File; furniture?: File }>({});
  const [referencePreviews, setReferencePreviews] = useState<{ style?: string; furniture?: string }>({});
  const referenceUrls = useRef<string[]>([]);

  useEffect(() => { const urls = referenceUrls.current; return () => urls.forEach((url) => URL.revokeObjectURL(url)); }, []);

  function pickReference(kind: "style" | "furniture", file?: File) {
    if (!file) return;
    if (!["image/jpeg", "image/png", "image/webp"].includes(file.type) || file.size > 10 * 1024 * 1024) {
      setMessage("参考图请选择 10 MB 以内的 JPG、PNG 或 WebP 图片"); return;
    }
    const url = URL.createObjectURL(file);
    referenceUrls.current.push(url);
    setReferenceFiles((current) => ({ ...current, [kind]: file }));
    setReferencePreviews((current) => ({ ...current, [kind]: url }));
    setMessage("");
  }

  async function syncReferences(current: Design) {
    if (!referenceFiles.style && !referenceFiles.furniture) return;
    const style = referenceFiles.style ? await api.upload(referenceFiles.style) : null;
    const furniture = referenceFiles.furniture ? await api.upload(referenceFiles.furniture) : null;
    const updated = await api.updateReferences(current.design_id, {
      style_photo_id: style?.photo_id || current.reference_ids?.style,
      furniture_photo_id: furniture?.photo_id || current.reference_ids?.furniture,
    });
    setDesign(updated);
    setReferenceFiles({});
    setReferencePreviews({});
  }

  const refresh = useCallback(async () => {
    try {
      const next = await api.getDesign(params.id);
      setDesign(next);
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) router.push("/");
      else setMessage(error instanceof Error ? error.message : "加载方案失败");
    }
  }, [params.id, router]);

  useEffect(() => {
    if (!getToken()) { router.push("/"); return; }
    const start = setTimeout(() => { void refresh(); }, 0);
    return () => { clearTimeout(start); };
  }, [refresh, router]);

  useEffect(() => {
    if (!design || !(["pending", "understanding", "rendering_front", "editing", "rendering_iso"].includes(design.status) || ["queued", "processing"].includes(design.layer_set?.status || ""))) return;
    const timer = setInterval(() => { void refresh(); }, 2500);
    return () => clearInterval(timer);
  }, [design, refresh]);

  async function prepareLayers() {
    if (!design || busy || !layerCostConfirmed) return;
    setBusy(true); setMessage("");
    try { setDesign(await api.prepareLayers(design.design_id, true)); setLayerCostConfirmed(false); }
    catch (error) { setMessage(error instanceof Error ? error.message : "整件选择准备失败"); }
    finally { setBusy(false); }
  }

  useEffect(() => {
    if (!getToken()) return;
    api.listProducts().then((result) => setProducts(result.products)).catch(() => {});
  }, []);

  async function submitEdit(event: React.FormEvent) {
    event.preventDefault();
    if (!operation || !design) return;
    if (operation !== "style" && !point) { setMessage("先点选图片中要修改的位置"); return; }
    if (operation !== "delete" && !detail.trim()) { setMessage("请写清这一处应该怎样修改"); return; }
    setBusy(true); setMessage("");
    try {
      if (operation !== "restore_structure") await syncReferences(design);
      const next = await api.edit(design.design_id, {
        operation, x: point?.x, y: point?.y, detail: detail.trim(),
        layer_index: operation === "style" || operation === "restore_structure" ? undefined : selectedLayer ?? undefined,
        product_id: operation === "replace" && chosenProduct ? chosenProduct : undefined,
      });
      setDesign(next); setPoint(null); setSelectedLayer(null); setOperation(null); setDetail(""); setChosenProduct(""); setView("front"); setEditorOpen(true);
    } catch (error) { setMessage(error instanceof Error ? error.message : "修改失败"); }
    finally { setBusy(false); }
  }

  async function restore(number: number) {
    if (!design || busy) return;
    setBusy(true); setMessage("");
    try { setDesign(await api.restore(design.design_id, number)); setPoint(null); setSelectedLayer(null); setView("front"); setEditorOpen(true); }
    catch (error) { setMessage(error instanceof Error ? error.message : "恢复失败"); }
    finally { setBusy(false); }
  }

  async function confirm() {
    if (!design || busy || !reviewActive || !reviewImagesReady) return;
    if (design.is_concept_view ? !reviewChecks.concept_acknowledged : !reviewChecks.doors_windows || !reviewChecks.walls_floor || !reviewChecks.camera_layout) return;
    setBusy(true); setMessage("");
    try {
      setDesign(await api.confirm(design.design_id, {
        mode: design.is_concept_view ? "concept" : "original", ...reviewChecks,
      }));
      setReviewOpen(false); setPoint(null);
    }
    catch (error) { setMessage(error instanceof Error ? error.message : "确认失败"); }
    finally { setBusy(false); }
  }

  async function submitRegenerate(event: React.FormEvent) {
    event.preventDefault();
    if (!design || busy || generating) return;
    const issue = feedback.trim();
    if (!issue) { setMessage("请写下上一版哪里不满意"); return; }
    setBusy(true); setMessage("");
    try {
      if (feedbackMode === "original") await syncReferences(design);
      setDesign(await api.regenerate(design.design_id, issue, feedbackMode));
      setFeedbackOpen(false); setFeedback(""); setFeedbackMode("original"); setPoint(null); setSelectedLayer(null); setOperation(null);
      setEditorOpen(true); setView("front");
    } catch (error) { setMessage(error instanceof Error ? error.message : "重新生成失败"); }
    finally { setBusy(false); }
  }

  async function saveHotspot() {
    if (!design || !draftPoint || !tagProduct || busy) return;
    setBusy(true); setMessage("");
    try {
      const next = await api.addHotspot(design.design_id, { product_id: tagProduct, ...draftPoint });
      setDesign(next); setSelectedHotspot(next.added_hotspot_id);
      setTagging(false); setDraftPoint(null); setTagProduct(""); setCatalogOpen(false);
    } catch (error) { setMessage(error instanceof Error ? error.message : "保存热点失败"); }
    finally { setBusy(false); }
  }

  async function removeHotspot() {
    if (!design || !selectedHotspot || busy) return;
    setBusy(true); setMessage("");
    try { setDesign(await api.deleteHotspot(design.design_id, selectedHotspot)); setSelectedHotspot(""); }
    catch (error) { setMessage(error instanceof Error ? error.message : "删除热点失败"); }
    finally { setBusy(false); }
  }

  const generating = !design || ["pending", "understanding", "rendering_front", "editing", "rendering_iso"].includes(design.status);
  const canEdit = design && ["front_ready", "completed"].includes(design.status);
  const currentVersion = design?.versions.find((version) => version.number === design.current_version);
  const currentFrontImage = useProtectedImage(design?.front_image_url || "");
  const originalRoomImage = useProtectedImage(design?.photo_url || "");
  const reviewImagesReady = Boolean(currentFrontImage.url && originalRoomImage.url);
  const currentReviewKey = design ? `${design.design_id}:${design.current_version}:${design.front_image_url}` : "";
  const reviewActive = reviewOpen && reviewImageKey === currentReviewKey;

  return (
    <main className="site-shell editor-page workbench-shell">
      <header className="site-header">
        <Link href="/" className="brand">拍拍搭<span className="brand-dot">.</span></Link>
        <nav className="header-nav" aria-label="主导航"><Link href="/"><ArrowLeft size={18} /> 新建方案</Link><Link href="/history"><ClockCounterClockwise size={18} /> 我的方案</Link></nav>
      </header>
      <div className="workbench-body">
      <WorkbenchSidebar active="edit" onEdit={() => { setView("front"); setCatalogOpen(false); setEditorOpen(true); setFeedbackOpen(false); }} />
      <div className="workbench-content">
      <div className="editor-heading">
        <div className="editor-title"><h1>我的空间</h1><span>方案 {String(design?.current_version || 1).padStart(2, "0")}</span></div>
        <span className="status-pill"><span className={generating ? "status-dot active" : "status-dot"} />{generating ? design?.current_step || "正在载入" : "已自动保存"}</span>
      </div>
      {message && <p className="error-message" role="alert">{message}</p>}
      {design?.error && <p className="error-message" role="alert">{design.error.message}</p>}
      {design?.is_mock && <p className="mock-notice">当前是离线开发模式：图片带 MOCK 标识，不能用于验收真实编辑效果。</p>}
      {!design ? <div className="page-loading"><SpinnerGap size={30} className="spin" /> 正在载入方案…</div> : design.status === "failed" ? (
        <div className="page-loading error-state"><strong>这次生成没有完成</strong><p>{design.error?.message || "请新建方案重试"}</p><Link href="/" className="secondary-button">重新开始</Link></div>
      ) : (
        <>
          <div className="view-toolbar">
            <div className="view-tabs" role="tablist" aria-label="方案视图">
              <button role="tab" aria-selected={view === "front"} className={view === "front" ? "active" : ""} onClick={() => { setView("front"); setTagging(false); setCatalogOpen(false); }}>效果图</button>
              <button role="tab" aria-selected={view === "compare"} className={view === "compare" ? "active" : ""} disabled={!design.front_image_url} onClick={() => { setView("compare"); setTagging(false); setCatalogOpen(false); }}>前后对比</button>
              <button role="tab" aria-selected={view === "iso"} className={view === "iso" ? "active" : ""} disabled={!design.iso_image_url || design.status !== "completed"} onClick={() => setView("iso")}>2.5D 视图</button>
            </div>
            <div className="view-actions">
              {design.front_image_url && view === "front" && <button onClick={() => { setOperation("style"); setDetail(""); setEditorOpen(true); setFeedbackOpen(false); }} disabled={!canEdit}>调整整体风格</button>}
              <span className="view-hint">{design.iso_image_url && design.status === "completed" ? `对应正面图第 ${design.current_version} 版` : "确认效果图后生成 2.5D"}</span>
            </div>
          </div>
          <div className="editor-grid">
            <section className="image-stage" aria-label="方案图片">
              {view === "iso" && design.iso_image_url && design.status === "completed" ? <IsometricCanvas design={design} products={products} tagging={tagging} draftPoint={draftPoint} onPlace={(next) => { setDraftPoint(next); setSelectedHotspot(""); setCatalogOpen(true); }} selectedId={selectedHotspot} onSelect={(id) => { setSelectedHotspot(id); if (id) { setTagging(false); setDraftPoint(null); setCatalogOpen(false); } }} /> :
                view === "compare" && design.front_image_url ? <Comparison design={design} /> :
                design.front_image_url ? <EditableCanvas design={design} point={point} setPoint={(next) => { setPoint(next); setEditorOpen(true); setFeedbackOpen(false); setOperation(null); setChosenProduct(""); }} onAction={(next) => { setOperation(next); setDetail(""); setChosenProduct(""); setEditorOpen(true); setFeedbackOpen(false); }} onSelectLayer={setSelectedLayer} operation={operation} disabled={!canEdit || view !== "front"} products={products} chosenProduct={chosenProduct} onChooseProduct={(item) => { setChosenProduct(item.id); setDetail(item.demo_only ? `参考${item.name}的造型与${item.color}配色` : `${item.color}${item.name}`); }} onResetProduct={() => { setChosenProduct(""); setDetail(""); }} onClosePicker={() => setOperation(null)} /> :
                <GenerationExperience design={design} />}
              {view === "front" && design.front_image_url && canEdit && !point && <div className="canvas-tip"><Sparkle size={17} /> {design.layer_set?.status === "ready" ? "移到家具上直接操作；其他位置可点击选定" : "点击图中的软装位置，选好操作后在下方描述"}</div>}
              {view === "front" && design.front_image_url && canEdit && design.layer_set?.status !== "ready" && design.layer_set?.status !== "queued" && design.layer_set?.status !== "processing" && <div className="layer-entry-tip"><div><strong>这张图还没开启整件选择</strong><span>现在可点位置修改；开启后可悬停整件软装。</span></div><button type="button" onClick={() => document.getElementById("layer-prepare")?.scrollIntoView({ behavior: "smooth", block: "center" })}>开启整件交互 <ArrowRight size={15} /></button></div>}
              {generating && design.front_image_url && <div className="working-overlay"><SpinnerGap size={27} className="spin" /><span>{design.current_step}，完成后会自动更新 · 你可以先浏览其他方案</span></div>}
            </section>
            {catalogOpen && view === "iso" && <aside className="edit-side catalog-side" aria-label={tagging ? "标注商品热点" : "软装灵感库"}>
              <button className="editor-close" onClick={() => { setCatalogOpen(false); setTagging(false); setDraftPoint(null); setTagProduct(""); }} aria-label="关闭软装灵感库"><X size={18} /></button>
              <div className="side-section"><p className="eyebrow">{tagging ? "添加商品热点" : "软装灵感库"}</p><h2>{tagging ? "点位置，选单品。" : "浏览搭配参考。"}</h2><p className="muted">{tagging ? draftPoint ? "位置已选。选择一件参考单品，然后保存热点。" : "请先点击 2.5D 图片中要标注的物品。" : "这份资料尚未自动对应 2.5D 图片中的具体物品。"}</p></div>
              {products.length ? <ProductShelf products={products} selectedId={tagProduct} onChoose={tagging ? (item) => setTagProduct(item.id) : undefined} /> : <p className="muted">暂无可浏览的参考单品。</p>}
              {tagging && <button className="dark-button tag-save" onClick={saveHotspot} disabled={!draftPoint || !tagProduct || busy}>{busy ? "保存中…" : "保存这个热点"}<ArrowRight size={16} /></button>}
            </aside>}
          </div>
          {design.front_image_url && view === "front" && <section className="edit-workspace" aria-label="效果图软装编辑">
            <div className="edit-workspace-heading"><div><span>效果图编辑</span><h2>在图里选，在这里改。</h2><p>鼠标移到已识别的家具上即可替换、改色或删除；手机上点选家具。整图不满意时也可以重新生成。</p></div><button type="button" onClick={() => setView("compare")}>看原照片 <ArrowRight size={15} /></button></div>
            <div className="edit-mode-switch" role="tablist" aria-label="效果图编辑方式"><button type="button" role="tab" aria-selected={editorOpen && !feedbackOpen} className={editorOpen && !feedbackOpen ? "active" : ""} onClick={() => { setEditorOpen(true); setFeedbackOpen(false); }}>编辑软装</button><button type="button" role="tab" aria-selected={feedbackOpen} className={feedbackOpen ? "active" : ""} onClick={() => { setFeedbackOpen(true); setEditorOpen(false); setPoint(null); setOperation(null); }}>重新生成整图</button></div>
            {!feedbackOpen ? <>
              <div className="edit-target-line"><span className={point ? "is-selected" : ""}>{point ? selectedLayer !== null && design.layer_set?.status === "ready" ? `已选中整件${design.layer_set.layers[selectedLayer]?.name || "软装"}` : "已选中图中位置" : "先点效果图中的软装"}</span>{point && <button type="button" onClick={() => { setPoint(null); setSelectedLayer(null); setOperation(null); }}>取消选择 <X size={13} /></button>}</div>
              {design.layer_set?.status === "ready" ? <p className="layer-status is-ready">已准备 {design.layer_set.layers.length} 件可交互软装。鼠标移上去会显示物品轮廓；其他位置仍可点选。</p> : design.layer_set?.status === "queued" || design.layer_set?.status === "processing" ? <p className="layer-status"><SpinnerGap size={15} className="spin" /> 正在拆分本版软装，完成后这里会自动更新。通常需要一些时间。</p> : <div id="layer-prepare" className="layer-prepare"><div><strong>开启整件软装选择</strong><span>{design.layer_set?.error_message || "为当前版本拆出家具透明图层，之后悬停可看到物品轮廓；每版只需准备一次。"}</span></div><label><input type="checkbox" checked={layerCostConfirmed} onChange={(event) => setLayerCostConfirmed(event.target.checked)} /> 确认本版图层拆分费用：按实际输出计费，1.5K 最多约 ¥2.55</label><button type="button" disabled={!canEdit || busy || !layerCostConfirmed} onClick={prepareLayers}>准备整件选择 <ArrowRight size={15} /></button></div>}
              <div className="edit-operation-row" aria-label="软装修改方式">
                <button type="button" disabled={!canEdit || !point} className={operation === "replace" ? "active" : ""} onClick={() => { setOperation("replace"); setDetail(""); setChosenProduct(""); }}><Swap size={17} /> 替换</button>
                <button type="button" disabled={!canEdit || !point} className={operation === "recolor" ? "active" : ""} onClick={() => { setOperation("recolor"); setDetail(""); }}><Palette size={17} /> 改色</button>
                <button type="button" disabled={!canEdit || !point} className={operation === "delete" ? "active" : ""} onClick={() => { setOperation("delete"); setDetail(""); }}><Trash size={17} /> 删除</button>
                <button type="button" disabled={!canEdit} className={operation === "style" ? "active" : ""} onClick={() => { setOperation("style"); setDetail(""); }}><PaintBrush size={17} /> 整体风格</button>
              </div>
              <div className="structure-repair-row"><span>门窗或墙体被画错了？先点效果图中的错误位置。</span><button type="button" disabled={!canEdit || !point} className={operation === "restore_structure" ? "active" : ""} onClick={() => { setOperation("restore_structure"); setDetail(""); setChosenProduct(""); }}>参照原照片修正这一处 <ArrowRight size={14} /></button></div>
              <form className="creator-composer edit-composer" onSubmit={submitEdit}>
                <div className="edit-composer-attachments" aria-label="本次编辑参考图片"><span className="edit-current-tile">{currentFrontImage.url && <img src={currentFrontImage.url} alt="当前效果图缩略图" />}<strong>当前图</strong></span>{operation === "restore_structure" ? <><span className="edit-current-tile">{originalRoomImage.url && <img src={originalRoomImage.url} alt="原房间照片缩略图" />}<strong>原照片</strong></span><span className="edit-attachment-help">只用原照片核对结构，不带入旧家具或风格参考</span></> : operation === "style" ? <><ReferenceInput label="风格" hint="添加参考图" url={design.references?.style} preview={referencePreviews.style} onPick={(file) => pickReference("style", file)} /><span className="edit-attachment-help">整体改风格时使用这张参考图</span></> : operation === "replace" ? <>{!chosenProduct && <ReferenceInput label="家具" hint="添加参考图" url={design.references?.furniture} preview={referencePreviews.furniture} onPick={(file) => pickReference("furniture", file)} />}<span className="edit-attachment-help">{chosenProduct ? "使用已选商品主图，只替换点选的物品" : "使用家具参考图，只替换点选的物品"}</span></> : <span className="edit-attachment-help">{operation === "recolor" ? "只依据当前图改色，不带入旧参考图" : operation === "delete" ? "只依据当前图删除，不带入旧参考图" : "选择操作后显示对应参考图"}</span>}</div>
                {operation === "replace" && chosenProduct && <p className="edit-chosen-product">已选 {products.find((item) => item.id === chosenProduct)?.name || "参考商品"}，可在图片旁重新选。</p>}
                {operation === "delete" && <div className="edit-delete-note"><Trash size={18} /> 选中的软装将被移除。可写清要删除的物品，避免模型把旧家具放回原位。</div>}
                {operation === "restore_structure" && <p className="edit-structure-note">这次会同时参照原房间照片，核对点选处的墙体和门窗；当前效果图的软装应保留。原版本会保存在下方。</p>}
                {operation && <><label htmlFor="edit-instruction" className="composer-label">{operation === "delete" ? "删除目标与保留要求（建议填写）" : operation === "restore_structure" ? "这一处哪里与原照片不符？" : "本次修改要求"}</label><textarea id="edit-instruction" maxLength={200} value={detail} onChange={(event) => { setDetail(event.target.value); if (operation === "replace") setChosenProduct(""); }} disabled={!canEdit || busy} placeholder={!point && operation !== "style" ? "点选图片中要修改的位置后，在这里写下问题…" : operation === "delete" ? "例如：删除左侧整张沙发，补全墙面和地板，其他家具保持不变…" : operation === "replace" ? "例如：换成一张浅米色的低矮布艺沙发…" : operation === "recolor" ? "例如：把选中的沙发改成墨绿色，保留形状和位置…" : operation === "restore_structure" ? "例如：原照片左墙没有门，移除这扇多出的门，恢复完整墙面，保留沙发和茶几…" : "例如：整体改成温暖原木风，保留房间结构…"} /></>}
                <div className="composer-toolbar"><span>{operation ? `${actionLabels[operation]} · 每次生成计入 8 次修改上限` : "先选中软装与修改方式"}<small>{detail.length}/200</small></span><button className="primary-button" disabled={!canEdit || busy || generating || !operation || (operation !== "style" && !point) || (operation !== "delete" && !detail.trim())}>{busy ? "提交中…" : "生成修改"}<ArrowRight size={17} /></button></div>
              </form>
            </> : <form className="creator-composer edit-composer" onSubmit={submitRegenerate}>
              <div className="regenerate-view-mode" role="group" aria-label="整图生成视角"><button type="button" className={feedbackMode === "original" ? "active" : ""} onClick={() => setFeedbackMode("original")}>沿用原照片机位</button><button type="button" className={feedbackMode === "concept" ? "active" : ""} onClick={() => setFeedbackMode("concept")}>换个机位看电视墙 · 示意</button></div>
              <div className="edit-composer-attachments" aria-label="整图重做参考图片"><span className="edit-current-tile">{currentFrontImage.url && <img src={currentFrontImage.url} alt="当前效果图缩略图" />}<strong>当前图</strong></span>{feedbackMode === "original" ? <><ReferenceInput label="风格" hint="添加参考图" url={design.references?.style} preview={referencePreviews.style} onPick={(file) => pickReference("style", file)} /><ReferenceInput label="家具" hint="添加参考图" url={design.references?.furniture} preview={referencePreviews.furniture} onPick={(file) => pickReference("furniture", file)} /><span className="edit-attachment-help">从原房间重做整张图，当前版本保留在版本记录</span></> : <span className="edit-attachment-help">基于当前效果图生成另一机位的设计示意；未拍到的墙面由模型推测，不能当作精确户型图。</span>}</div>
              <label htmlFor="regenerate-feedback" className="composer-label">{feedbackMode === "concept" ? "新机位要展示什么？" : "希望重新生成的地方"}</label><textarea id="regenerate-feedback" required maxLength={200} value={feedback} onChange={(event) => setFeedback(event.target.value)} placeholder={feedbackMode === "concept" ? "例如：转向电视墙。电视悬于简洁背景墙，落地电视柜不要悬浮；保留原木风与家具比例…" : "说清哪里不对、希望怎样改。例如：保留原来的窗户和布局，换掉沙发与窗帘，整体更简洁…"} disabled={!canEdit || busy} />
              <div className="composer-toolbar"><span>{feedbackMode === "concept" ? "新机位只是设计示意" : "从原照片重做整图"} · 调用一次生图并计入 8 次修改上限<small>{feedback.length}/200</small></span><button className="primary-button" disabled={!canEdit || busy || generating || !feedback.trim()}>{busy ? "提交中…" : feedbackMode === "concept" ? "生成新机位示意" : "重新生成整图"}<ArrowRight size={17} /></button></div>
            </form>}
          </section>}
          {view === "iso" && design.status === "completed" && <div className="iso-provenance"><div><strong>这张 2.5D 来自第 {design.current_version} 版正面效果图</strong><span>{currentVersion?.operation === "initial" ? `最初的改造想法：${design.user_input}` : currentVersion ? `这一版的最后一次修改：${currentVersion.operation === "regenerate" ? "根据反馈重新生成" : currentVersion.operation === "concept_view" ? "新机位设计示意" : actionLabels[currentVersion.operation as Operation] || "调整软装"}${currentVersion.instruction ? ` · ${currentVersion.instruction}` : ""}` : "已确认的正面效果图"}</span><span>{design.hotspots?.length ? `已标注 ${design.hotspots.length} 个商品热点，点编号查看参考卡。` : "还没有商品热点；可在图上手动标注。"}</span></div><div className="iso-provenance-actions"><button disabled={(design.hotspots?.length || 0) >= 8} onClick={() => { setTagging(true); setCatalogOpen(true); setSelectedHotspot(""); }}>{(design.hotspots?.length || 0) >= 8 ? "已达 8 个热点" : "标注商品"} <ArrowRight size={16} /></button>{selectedHotspot && <button disabled={busy} onClick={removeHotspot}>删除当前热点 <Trash size={16} /></button>}<button onClick={() => { setTagging(false); setDraftPoint(null); setCatalogOpen((open) => !open); }}>{catalogOpen ? "收起" : "浏览"}软装灵感 <ArrowRight size={16} /></button><button onClick={() => { setCatalogOpen(false); setTagging(false); setView("front"); }}>查看对应效果图 <ArrowRight size={16} /></button></div></div>}
          {design.front_image_url && view === "front" && design.status === "front_ready" && <div className="confirm-inline"><span>这张效果图满意了吗？先对照原照片核对，再生成对应的 2.5D。</span><button className="dark-button" disabled={busy} onClick={() => { setReviewChecks({ doors_windows: false, walls_floor: false, camera_layout: false, concept_acknowledged: false }); setReviewImageKey(currentReviewKey); setReviewOpen(true); setView("compare"); }}>对照原图并确认 <ArrowRight size={17} /></button></div>}
          {design.front_image_url && view === "compare" && design.status === "front_ready" && reviewActive && <section className="structure-review" aria-label="效果图结构核对">
            <div><span className="eyebrow">确认第 {design.current_version} 版之前</span><h2>{design.is_concept_view ? "确认这张新机位示意" : "对照原照片，检查房间结构"}</h2><p>{design.is_concept_view ? "这张图展示原照片未完整拍到的方向，墙面和门窗由模型推测，不能当成精确户型。" : "拖动上方滑块查看原图与效果图。如果门窗或墙体变了，先回到效果图点选错误处修正。"}</p></div>
            <div className="structure-review-checks">
              {design.is_concept_view ? <label><input type="checkbox" checked={reviewChecks.concept_acknowledged} onChange={(event) => setReviewChecks((current) => ({ ...current, concept_acknowledged: event.target.checked }))} /> 我知道这是新机位设计示意，不代表房间真实结构</label> : <>
                <label><input type="checkbox" checked={reviewChecks.doors_windows} onChange={(event) => setReviewChecks((current) => ({ ...current, doors_windows: event.target.checked }))} /> 门窗的数量和位置可以接受</label>
                <label><input type="checkbox" checked={reviewChecks.walls_floor} onChange={(event) => setReviewChecks((current) => ({ ...current, walls_floor: event.target.checked }))} /> 墙体、吊顶与地面可以接受</label>
                <label><input type="checkbox" checked={reviewChecks.camera_layout} onChange={(event) => setReviewChecks((current) => ({ ...current, camera_layout: event.target.checked }))} /> 机位和主要空间布局可以接受</label>
              </>}
            </div>
            <div className="structure-review-actions"><button type="button" onClick={() => { setReviewOpen(false); setView("front"); setEditorOpen(true); setFeedbackOpen(false); }}>有问题，回到效果图修正</button><button type="button" className="dark-button" disabled={busy || !reviewImagesReady || (design.is_concept_view ? !reviewChecks.concept_acknowledged : !reviewChecks.doors_windows || !reviewChecks.walls_floor || !reviewChecks.camera_layout)} onClick={confirm}>确认本版，生成 2.5D <ArrowRight size={17} /></button></div>
          </section>}
          <section className="below-stage plan-record" aria-label="方案记录">
            <div className="plan-record-head"><div><span>方案记录</span><h2>版本记录</h2><p>对照各版图片。恢复旧版后，原有 2.5D 会失效，需再次确认效果图才能重生。</p></div><small>{design.versions.length} 个版本</small></div>
            <div className="version-gallery">{design.versions.map((version) => <VersionCard key={version.number} version={version} current={design.current_version === version.number} disabled={generating || busy} onRestore={() => restore(version.number)} />)}</div>
            <details className="design-notes-disclosure"><summary><span><strong>最初的设计说明</strong><small>展开查看生成时的完整思路</small></span><CaretDown size={18} /></summary><div className="design-notes-body">{view === "iso" && <p className="design-notes-caution">这张 2.5D 来自已确认的正面图。下方说明记录于最初生成时，不作为当前图的逐件商品说明。</p>}{design.edit_history.length > 0 && <p className="design-notes-caution">方案经过修改，以下初始说明可能与当前图片不一致，请以图片为准。</p>}{design.design_notes.length ? design.design_notes.map((note, index) => <p key={index}>{note}</p>) : <p>暂无设计说明。</p>}</div></details>
          </section>
        </>
      )}
      </div>
      </div>
    </main>
  );
}
