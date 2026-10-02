# AI+软装 AIGC产品 PRD

**版本**：v1.0  
**开发周期**：4天  
**日期**：2026-09-27  
**定位**：上传房间照片，自然语言描述风格，AI生成正面效果图和2.5D互动方案

---

## 一、产品概述

**产品名**（暂定）：SnapSpace / 拍拍搭

**一句话定义**：上传一张房间照片，用自然语言描述你想要的风格，AI在十几秒内生成正面效果图和2.5D互动方案。

**产品类型**：AIGC（AI生成内容）+ 轻交互

**核心价值**：
- 让用户零门槛看到"我家能变成什么样"
- 用AI生成替代传统渲染引擎，交付速度从天级降到秒级
- 正面图负责"好看"，2.5D负责"好玩"

**本质**：用AI的生成能力替代渲染引擎，把现成API编排成产品体验。

---

## 二、目标用户

**核心受众**：25-40岁想装修/改造的业主（演示时最有感染力）  
**辅助角色**：设计师（可切换专业模式，展示B端可能性）

---

## 三、核心AI链路

```
用户照片 + 文字描述
    ↓
┌─ 国内LLM（Qwen-Flash / DeepSeek-Flash）─────────────┐
│  ① 理解意图 → 输出结构化JSON（风格/色彩/预算/成员）    │
│  ② 拼出2组SD prompt变体（正面效果 / 2.5D等距）         │
│  ③ 生成设计说明文案（为什么这么搭）                    │
└───────────────────────────────────────────────────────┘
    ↓
ControlNet Canny（提取空间结构，锁住透视）
    ↓
SD并行生成2张图（共享结构约束）：
  ① 正面效果图 → 主展示，视觉冲击，发朋友圈
  ② 2.5D等距图 → 交互玩法，热点+拖拽
    ↓
前端双Tab展示 + 对比滑块 + 热点交互 + 设计说明
```

**每一步都是真API调用，真AI在跑，真内容在生成。**

---

## 四、功能需求（MVP范围）

### FR-01：上传照片
- 支持拖拽上传 / 点击选择 / 移动端拍照
- 支持JPG/PNG/WebP，最大10MB
- 上传后前端压缩为2048px长边（后端不做处理，直接透传）

### FR-02：自然语言输入
- 单个文本输入框，placeholder："描述你想要的风格，比如：奶油风，有猫，3万预算，要温馨"
- 字数限制：200字以内
- 支持中英文

### FR-03：AI理解（LLM）
- 调用国内LLM（Qwen-Flash / DeepSeek-Flash）
- 输入：用户照片（base64或URL）+ 文字描述
- 输出：结构化JSON，包含：

```json
{
  "style": "cream",
  "colors": ["warm white", "oak", "beige"],
  "mood": "cozy, warm, minimalist",
  "budget_level": "mid",
  "members": ["couple", "cat"],
  "elements": ["soft sofa", "warm lighting", "plants", "wood texture"],
  "avoid": ["cold colors", "industrial metal"],
  "sd_prompts": {
    "front": "a cream style living room, warm lighting, cozy, eye level view, realistic photography, 24mm lens, 8k...",
    "isometric": "a cream style living room, isometric view, 45 degree angle, looking down, 3d render, blender, 8k..."
  },
  "negative_prompt": "ugly, distorted, low quality, perspective distortion...",
  "design_notes": [
    "奶油色墙面搭配原木家具营造温暖氛围",
    "暖光落地灯弥补北向采光不足",
    "低矮沙发方便猫咪跳跃"
  ],
  "layout_hints": {
    "sofa_area": { "x": 0.3, "y": 0.5 },
    "tv_area": { "x": 0.3, "y": 0.1 }
  }
}
```

### FR-04：空间结构提取（ControlNet）
- 对用户照片跑Canny边缘检测
- 输出边缘图（base64 PNG）
- 可选：同时跑Depth估计，输出深度图

### FR-05：AI生图（SDXL + ControlNet）
- 基于FR-03的prompt + FR-04的结构约束
- 并行生成2张图：
  - 正面效果图（front prompt + Canny）
  - 2.5D等距图（isometric prompt + Canny + Depth）
- 输出：图片URL + 生成耗时

### FR-06：生成过程状态推送
- 后端维护任务状态机：`pending → understanding → analyzing → rendering → completed / failed`
- 前端轮询或SSE推送状态变更
- 每个状态附带可展示的元数据（如LLM输出JSON、边缘图URL）

### FR-07：结果获取
- 获取生成的2张图URL
- 获取LLM输出的设计说明
- 获取热点数据（基于layout_hints + 预设家具库映射）

### FR-08：微调（可选，Day 4 if时间允许）
- 用户输入："把沙发换皮质的"
- 后端：LLM解析微调意图 → 修改对应prompt → 重新调SD inpainting
- 输出：局部重绘后的新图

### FR-09：历史记录
- 保存每次生成的任务记录（照片、描述、结果图、时间戳）
- 列表查询

---

## 五、非功能需求

| 项目 | 要求 |
|------|------|
| 响应时间 | LLM理解 ≤3秒，SD生图 ≤20秒，总流程 ≤30秒 |
| 并发 | 演示场景，单用户串行即可 |
| 可用性 | 生成失败有友好提示 + 重试按钮 |
| 安全 | 用户照片不上链、不持久化（可选加密存储） |
| 成本 | 单次完整生成 ≤¥0.5 |

---

## 六、不做的事（Out of Scope）

| ❌ 不做 | 原因 |
|---------|------|
| 不训模型 | 四天训不出有用的，用现成API+prompt调优 |
| 不做真3D | SD直接生成2.5D视角，替代渲染引擎 |
| 不用GPT | 换国内LLM，成本降几十倍 |
| 不建真实商品库 | 热点商品数据mock |
| 不做平面图 | 偏离软装美学初心，那是硬装/CAD的事 |
| 不考虑商业化 | 路径清楚但不执行 |
| 不做用户系统 | 演示用session即可 |

---

## 七、系统架构

```
┌──────────┐
│  前端     │  Next.js + Tailwind + Framer Motion
│  (Day3-4) │
└────┬─────┘
     │  REST API / SSE
┌────▼─────────────────────────────────────────────┐
│  后端 API（FastAPI / Node.js）                    │
│                                                  │
│  ┌─────────┐  ┌──────────┐  ┌─────────────────┐  │
│  │ /upload  │  │ /generate│  │ /status/:taskId │  │
│  └────┬────┘  └────┬─────┘  └───────┬─────────┘  │
│       │             │                 │            │
│  ┌────▼─────────────▼─────────────────▼─────────┐  │
│  │         任务编排层（Task Orchestrator）         │  │
│  │  pending → understanding → analyzing → render  │  │
│  └────┬─────────────┬───────────────┬────────────┘  │
│       │             │               │               │
│  ┌────▼───┐   ┌────▼────┐   ┌─────▼─────┐         │
│  │ LLM    │   │ ControlNet│   │ SDXL      │         │
│  │ Qwen   │   │ Canny+   │   │ Replicate  │         │
│  │ Flash  │   │ Depth    │   │ API        │         │
│  └────────┘   └─────────┘   └───────────┘         │
│                                                  │
│  ┌──────────────────────────────────────────────┐  │
│  │  存储层                                      │  │
│  │  - 任务状态：Redis / 内存Map                   │  │
│  │  - 图片：Vercel Blob / 本地tmp                 │  │
│  │  - 预设数据：JSON文件（户型模板、家具库）        │  │
│  └──────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────┘
```

---

## 八、后端API定义

> **全部API完成后才允许进入前端交互层开发。**

### API-01：上传照片

```
POST /api/upload
Content-Type: multipart/form-data

Request:
  file: binary (image)

Response 200:
{
  "photo_id": "uuid",
  "url": "https://blob.url/photo_uuid.jpg",
  "width": 1920,
  "height": 1080
}
```

### API-02：提交生成任务

```
POST /api/generate
Content-Type: application/json

Request:
{
  "photo_id": "uuid",
  "user_input": "奶油风，有猫，3万预算，要温馨"
}

Response 200:
{
  "task_id": "uuid",
  "status": "pending",
  "created_at": "2026-09-27T10:00:00Z"
}
```

### API-03：查询任务状态（轮询）

```
GET /api/task/:task_id

Response 200 (进行中):
{
  "task_id": "uuid",
  "status": "rendering",
  "progress": 65,
  "current_step": "SD正在渲染方案...",
  "step_details": {
    "understanding": {
      "completed": true,
      "result": { "style": "cream", "colors": ["warm white"], ... }
    },
    "analyzing": {
      "completed": true,
      "canny_url": "https://blob.url/canny.png",
      "depth_url": "https://blob.url/depth.png"
    },
    "rendering": {
      "completed": false,
      "progress": 60
    }
  },
  "result": null,
  "error": null
}

Response 200 (完成):
{
  "task_id": "uuid",
  "status": "completed",
  "progress": 100,
  "result": {
    "front_image_url": "https://blob.url/front.png",
    "isometric_image_url": "https://blob.url/iso.png",
    "design_notes": [
      "奶油色墙面搭配原木家具营造温暖氛围",
      "暖光落地灯弥补北向采光不足",
      "低矮沙发方便猫咪跳跃"
    ],
    "hotspots": [
      {
        "id": "h1",
        "label": "奶油色布艺沙发",
        "x": 0.35,
        "y": 0.55,
        "product": {
          "name": "云朵沙发",
          "brand": "造作",
          "price": 4999,
          "image_url": "https://mock.url/sofa.png"
        }
      }
    ],
    "layout_hints": {
      "sofa_area": { "x": 0.3, "y": 0.5 },
      "tv_area": { "x": 0.3, "y": 0.1 }
    }
  }
}

Response 200 (失败):
{
  "task_id": "uuid",
  "status": "failed",
  "error": {
    "code": "SD_GENERATION_TIMEOUT",
    "message": "图片生成超时，请重试"
  }
}
```

### API-04：微调（可选）

```
POST /api/regenerate/:task_id
Content-Type: application/json

Request:
{
  "modification": "把沙发换成皮质的"
}

Response 200:
{
  "task_id": "new_uuid",
  "status": "pending"
}
```

### API-05：历史列表

```
GET /api/history?session_id=xxx

Response 200:
{
  "tasks": [
    {
      "task_id": "uuid",
      "photo_url": "...",
      "user_input": "...",
      "front_image_url": "...",
      "created_at": "..."
    }
  ]
}
```

---

## 九、后端任务编排逻辑

```python
# 伪代码

async def generate_task(task_id, photo_url, user_input):
    # Step 1: LLM理解
    update_status(task_id, "understanding", progress=10)
    llm_result = await call_qwen_flash(photo_url, user_input)
    # llm_result = { style, colors, mood, sd_prompts, design_notes, layout_hints }
    
    update_status(task_id, "understanding", completed=True, result=llm_result)
    
    # Step 2: 空间结构提取
    update_status(task_id, "analyzing", progress=30)
    canny_img = await call_replicate_canny(photo_url)
    depth_img = await call_replicate_depth(photo_url)
    
    update_status(task_id, "analyzing", completed=True, canny_url=canny_img, depth_url=depth_img)
    
    # Step 3: SD生图（并行）
    update_status(task_id, "rendering", progress=50)
    
    front_task = call_replicate_sdxl(
        prompt=llm_result["sd_prompts"]["front"],
        negative_prompt=llm_result["negative_prompt"],
        controlnet=canny_img,
        controlnet_type="canny"
    )
    
    iso_task = call_replicate_sdxl(
        prompt=llm_result["sd_prompts"]["isometric"],
        negative_prompt=llm_result["negative_prompt"],
        controlnet=canny_img,
        controlnet_type="canny",
        depth_map=depth_img
    )
    
    front_url, iso_url = await asyncio.gather(front_task, iso_task)
    
    # Step 4: 组装热点数据
    hotspots = build_hotspots(llm_result["layout_hints"], llm_result["style"])
    
    update_status(task_id, "completed", progress=100, result={
        "front_image_url": front_url,
        "isometric_image_url": iso_url,
        "design_notes": llm_result["design_notes"],
        "hotspots": hotspots,
        "layout_hints": llm_result["layout_hints"]
    })
```

---

## 十、后端完成标准（Gate）

**以下全部通过，才允许开始前端开发：**

| # | 验收项 | 验证方式 |
|---|--------|---------|
| 1 | `/api/upload` 能接收图片并返回URL | curl测试 |
| 2 | `/api/generate` 能创建任务并返回task_id | curl测试 |
| 3 | LLM调用返回结构化JSON，字段完整 | 日志检查 |
| 4 | Canny边缘图生成成功，URL可访问 | 浏览器打开 |
| 5 | SD生成正面图成功，URL可访问，质量可接受 | 人工检查 |
| 6 | SD生成2.5D图成功，URL可访问，视角正确 | 人工检查 |
| 7 | `/api/task/:id` 状态流转完整（pending→completed） | 轮询测试 |
| 8 | 热点数据正确生成（坐标+商品mock） | JSON校验 |
| 9 | 全流程端到端跑通（上传→生成→查询结果） | 完整流程测试 |
| 10 | 失败场景有错误处理（API超时、参数错误） | 注入故障测试 |

**验收通过后，输出《后端完成报告》，包含：**
- 所有API的curl示例和响应示例
- 生成图片的样例（至少3组不同风格）
- 平均响应时间
- 已知限制和边界情况

---

## 十一、前端交互层（后端Gate通过后开始）

### 页面结构

```
/                    首页（上传+输入）
/generating/:taskId  加载页（状态轮询）
/result/:taskId      结果页（双Tab+交互）
/history             历史列表（可选）
```

### 组件清单

| 组件 | 功能 | 交互细节 |
|------|------|---------|
| UploadZone | 拖拽上传+拍照 | 拖入放大发光、格式校验 |
| TextInput | 自然语言输入 | placeholder动画、字数计数 |
| ProgressSteps | 加载页分阶段展示 | 4阶段动画，每阶段配图标+文字 |
| StepUnderstanding | 展示LLM JSON | 打字机效果逐字段显示 |
| StepAnalyzing | 展示边缘图 | 边缘图绘制动画 |
| StepRendering | 渲染进度 | 进度条+粒子效果 |
| ResultTabs | 效果/互动切换 | 平滑切换动画 |
| FrontView | 正面图+对比滑块 | clip-path拖动，阻尼感 |
| IsometricView | 2.5D图+热点 | 脉冲动画，点击弹窗 |
| HotspotMarker | 热点标注 | 呼吸光晕，hover放大 |
| ProductCard | 商品信息弹窗 | spring动画弹出 |
| DesignNotes | 设计说明面板 | 可折叠，逐条显示 |
| SchemeSwitcher | 底部方案切换 | 3卡片横向滑动 |
| ActionBar | 操作栏 | 重新生成/微调/分享 |

### 状态管理（Zustand）

```typescript
interface AppState {
  // 上传
  photoFile: File | null
  photoUrl: string | null
  
  // 输入
  userInput: string
  
  // 任务
  taskId: string | null
  taskStatus: 'idle' | 'pending' | 'understanding' | 'analyzing' | 'rendering' | 'completed' | 'failed'
  taskProgress: number
  stepDetails: Record<string, any>
  
  // 结果
  frontImageUrl: string | null
  isometricImageUrl: string | null
  designNotes: string[]
  hotspots: Hotspot[]
  
  // Actions
  uploadPhoto: (file: File) => Promise<void>
  startGenerate: () => Promise<void>
  pollTask: () => Promise<void>
  selectScheme: (index: number) => void
}
```

### 关键交互时序

```
用户上传照片 + 输入文字
    ↓
点击"生成" → POST /api/generate → 拿到task_id
    ↓
跳转 /generating/:taskId
    ↓
前端每2秒轮询 GET /api/task/:taskId
    ↓
status=understanding → 展示LLM JSON打字机
status=analyzing → 展示Canny边缘图动画
status=rendering → 展示进度条
status=completed → 跳转 /result/:taskId
status=failed → 展示错误+重试
    ↓
结果页加载
    ↓
默认显示「效果」Tab → 正面图+对比滑块
    ↓
用户点「互动」Tab → 2.5D图+热点
    ↓
点击热点 → 商品卡弹窗
    ↓
拖拽热点 → 更新位置+LLM说明
```

---

## 十二、技术栈

| 层 | 选型 | 理由 |
|---|------|------|
| 前端 | Next.js + Tailwind + Framer Motion | 快、好看、动效强 |
| LLM | 通义Qwen-Flash（默认）/ DeepSeek-Flash（备用） | 中文好、JSON输出稳、成本极低 |
| 生图 | Replicate SD API（SDXL + ControlNet Canny） | 不用部署，ControlNet现成 |
| 热点交互 | 绝对定位div + Zustand | 轻量 |
| 对比滑块 | CSS clip-path | 丝滑 |
| 拖拽 | react-draggable / framer-motion drag | 内置 |
| 部署 | Vercel | 一键部署，全球加速 |
| 存储 | Vercel Blob / Cloudinary | 用户上传+生成结果 |

**成本**：单次完整生成（LLM+2张SD图）约¥0.1-0.3，演示一天不到几块钱。

---

## 十三、四天开发排期（严格Gate）

| 天 | 阶段 | 做什么 | 产出 |
|---|------|--------|------|
| **Day 1** | 后端Day 1 | API-01上传、API-02创建任务、LLM调用、结构化输出 | 能接收照片+文字→返回JSON |
| **Day 2** | 后端Day 2 | ControlNet Canny/Depth、SD生图（正面+2.5D）、任务状态机、API-03查询 | 全流程跑通，生成图片URL可访问 |
| **Day 2.5** | **Gate检查** | 后端10项验收全部通过，输出《后端完成报告》 | ✅ Gate通过，才允许进前端 |
| **Day 3** | 前端Day 1 | 首页上传+输入、加载页分阶段动画、状态轮询 | 能走完"上传→加载→看到结果"流程 |
| **Day 4** | 前端Day 2 | 结果页双Tab、对比滑块、热点交互、动效打磨、预生成保底 | 完整可演示产品 |

**如果Day 2.5 Gate没过**：Day 3上午继续修后端，下午才开始前端。宁可前端少做一天，也要保证后端能跑。

---

## 十四、预生成保底（Day 4执行）

```
backend/pregen/
  ├── scheme_01_cream_cat.json    # 完整API响应格式
  ├── scheme_01_front.png
  ├── scheme_01_iso.png
  ├── scheme_02_japandi_dog.json
  ├── scheme_02_front.png
  ├── scheme_02_iso.png
  ├── ...
```

前端检测：如果 `task_id` 以 `demo_` 开头，直接从本地JSON加载，不走API。

演示时：默认用 `demo_scheme_01`，现场生成作为"额外展示"。

---

## 十五、演示脚本

1. 打开首页 → 精美留白 + 上传区
2. 上传一张"丑客厅"照片
3. 输入："奶油风，有猫，3万预算，要温馨"
4. 点击生成 → 跳转加载页
5. 看LLM理解阶段 → JSON逐字段打字机显示
6. 看结构分析 → Canny边缘图动画
7. 看渲染进度 → 进度条走完
8. 跳转结果页 → 默认「效果」Tab → 正面图全屏
9. 拖动对比滑块 → 原图 vs AI方案
10. 点「互动」Tab → 2.5D图 → 点击热点 → 商品卡弹出
11. 拖拽沙发 → LLM说"移到窗边采光更好"
12. 展示设计说明
13. （可选）点重新生成 → 新方案出来

---

## 十六、AIGC符合性自检

| AIGC核心特征 | 是否符合 | 说明 |
|-------------|---------|------|
| AI生成内容 | ✅ | SD生成正面效果图+2.5D图 |
| 用户引导生成 | ✅ | 照片+自然语言描述引导 |
| 生成过程可视化 | ✅ | 加载页展示AI思考、结构分析、渲染进度 |
| 多模态输入 | ✅ | 图像（照片）+ 文本（描述） |
| 多模态输出 | ✅ | 图像（2张图）+ 文本（设计说明） |
| 内容可迭代 | ✅ | 微调、重新生成、多方案切换 |
| 生成结果具个性 | ✅ | 基于用户照片和个性化需求，每张图都不同 |
| AIGC典型交互 | ✅ | 输入→等待生成→查看结果→反馈迭代 |

**结论**：本产品为标准AIGC产品——用AI生成视觉内容（软装效果图），用户通过自然语言引导生成，生成过程可视化，结果可交互可迭代可分享。

---

## 十七、一句话总结

> **四天交付一个"真AI+多视角+精美交互"的软装产品。正面图负责"好看"，2.5D负责"好玩"，LLM负责"听懂你"，SD负责"画出来"。不训模型、不做3D、不花大钱，用编排能力把别人的AI变成你的产品。后端先全部跑通，才允许前端介入。**
