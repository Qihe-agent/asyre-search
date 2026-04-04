---
name: asyre-search
description: |
  Asyre Search 全平台社媒数据查询与深度分析。支持抖音、小红书、B站、TikTok、YouTube、Instagram、Twitter 等 21+ 平台。
  采用双 Agent 协作模式：数据猎手负责平台数据采集，趋势分析师负责外部情报补充，主 Agent 整合输出。
  触发词: asyre search, 查抖音, 查小红书, 社媒数据, 平台数据, 社媒分析, 竞品分析, 舆情监测, 达人分析, 内容选题, 跨境选品, fetch video, get user info
---

# Asyre Search — 全平台社媒数据查询与深度分析

## 执行流程

当用户提出社媒相关需求时，严格按照以下流程执行：

### Phase 1: 需求理解与计划制定

收到用户请求后，先分析需求本质，判断属于以下哪类（可以是多类组合）：

| 类型 | 典型需求 | 核心动作 |
|------|---------|---------|
| 数据查询 | "帮我查这个视频的数据" | 直接调用 API |
| 竞品分析 | "分析我和竞品的差距" | 多账号对比 + 评论分析 |
| 趋势洞察 | "现在什么内容火？" | 热搜 + 搜索 + Web Search |
| 达人评估 | "这个博主值不值得投？" | 用户信息 + 作品列表 + 评论质量 |
| 舆情监测 | "看看品牌口碑" | 跨平台搜索 + 评论情感 |
| 选题策划 | "帮我找内容灵感" | 搜索 + 热搜 + 对标账号 |
| 市场调研 | "这个品类在社媒上怎么样？" | 搜索 + Web Search + 数据交叉 |

制定明确的执行计划，列出：
1. 需要查询的平台（哪些平台最相关）
2. 需要使用的命令组合
3. 需要补充的外部信息（Web Search）

将计划展示给用户确认后再执行。

### Phase 2: 双 Agent 协作

将任务拆分给两个角色，各自独立思考后汇总：

#### 🔍 Agent A — 数据猎手 (Data Hunter)

**职责：** 平台原生数据采集与结构化分析

- 使用 `asyre-search` 命令获取平台数据
- 关注硬指标：播放量、点赞量、评论量、粉丝数、发布频率
- 做数据对比、排序、异常检测
- 输出结构化数据表格

**思考框架：**
```
1. 用户的核心问题是什么？需要哪些数据来回答？
2. 应该查哪些平台？优先级如何？
3. 需要哪些维度的数据？（用户/作品/评论/趋势）
4. 数据之间有什么关联可以挖掘？
5. 有没有反常数据需要深挖？
```

#### 🌐 Agent B — 趋势研究员 (Trend Analyst)

**职责：** 外部情报收集与趋势判断

- 使用 Web Search 获取行业报告、新闻、分析文章
- 关注软信号：行业趋势、政策变化、消费者情绪转向、平台算法变化
- 提供背景上下文，解释"为什么"数据是这样的
- 补充 Agent A 无法从平台数据中获取的信息

**思考框架：**
```
1. 这个话题/品牌/品类最近有什么大事发生？
2. 行业趋势是什么？有没有相关的研究报告？
3. 平台最近有没有算法调整或政策变化影响数据？
4. 竞争格局是什么？有没有新玩家入场？
5. 消费者偏好有没有变化？
```

### Phase 3: 整合与执行

主 Agent 综合两个角色的分析：

1. **交叉验证**：Agent A 的数据 + Agent B 的情报是否一致？如果矛盾，深挖原因
2. **补充查询**：根据初步分析结果，决定是否需要追加查询
3. **生成洞察**：不只是罗列数据，而是得出可执行的结论
4. **输出报告**：结构化的分析报告，包含数据、洞察、建议

### Phase 4: 输出格式

最终输出应包含：

```markdown
## 📊 分析报告：[用户的问题]

### 核心发现
- [3-5 条关键发现，直接回答用户的问题]

### 平台数据
[Agent A 的数据表格和分析]

### 行业背景
[Agent B 的趋势和情报]

### 交叉分析
[两个 Agent 的信息交叉验证后的深度洞察]

### 行动建议
[基于以上分析，用户应该怎么做？]
```

---

## 可用命令

```bash
# 视频/帖子详情（自动识别平台）
python3 scripts/asyre_search.py info <URL>

# 用户信息
python3 scripts/asyre_search.py user <URL_or_ID> --platform <platform>

# 用户作品列表
python3 scripts/asyre_search.py posts <URL_or_ID> --platform <platform> [--limit N]

# 搜索内容
python3 scripts/asyre_search.py search <keyword> --platform <platform> [--type video|note] [--limit N]

# 热搜趋势
python3 scripts/asyre_search.py -p <platform> trending

# 评论列表
python3 scripts/asyre_search.py comments <URL_or_ID> --platform <platform> [--limit N]

# 直接调用 API
python3 scripts/asyre_search.py raw <endpoint> [--params key=value]
```

### 支持平台

`douyin` | `xiaohongshu` | `bilibili` | `tiktok` | `youtube` | `instagram` | `twitter`

还支持微博、Threads、Pinterest、Spotify、SoundCloud、Telegram 等 14+ 平台（通过 `raw` 命令）。

### 输出控制

| 参数 | 说明 |
|------|------|
| `--format json/table/text` | 输出格式 |
| `--raw` | 原始 JSON |
| `-o filename` | 保存到文件 |

---

## Web Search 配合策略

在以下情况下，**必须**结合 Web Search 使用：

1. **趋势分析** — 平台热搜只是当前快照，Web Search 补充趋势的时间线和原因
2. **品牌调研** — 平台数据看声量，Web Search 看企业背景、融资、团队
3. **行业报告** — 搜索相关的行业白皮书、数据报告作为分析框架
4. **政策影响** — 平台政策、监管变化会直接影响数据表现
5. **事件追溯** — 舆情事件的起因、经过，可能不在社媒平台上

**搜索建议关键词模板：**
```
"{品牌名} 行业分析 2026"
"{品类} 市场规模 报告"
"{平台名} 算法更新 最新"
"{品牌名} 融资 估值"
"{话题} 趋势 预测"
```

---

## 场景速查表

在理解用户需求后，快速匹配适用场景：

| 场景 | 关键命令 | 是否需要 Web Search |
|------|---------|:------------------:|
| 爆款逆向工程 | info + posts + comments | 可选 |
| KOL 打假/达人评估 | user + posts + comments | ✅ 查背景 |
| 舆情风暴预警 | search(跨平台) + comments | ✅ 查事件 |
| 跨境电商选品 | trending + search + info | ✅ 查趋势 |
| MCN 批量选题 | search(多赛道) + posts(对标) | 可选 |
| 投资尽调 | search + user + posts | ✅ 查企业 |
| 音乐/影视推广 | search(跨平台) + trending | ✅ 查行业 |
| 本地商家获客 | search + comments | 可选 |
| Agent 自动化调研 | 全部命令 | ✅ |
| 学术研究 | search + comments + raw | ✅ 查文献 |
| 品牌声量对比 | search(A vs B) + user + posts | ✅ |
| 新品上市监测 | search + trending + comments | ✅ |
| 广告素材挖掘 | search + info + posts | 可选 |
| 用户画像分析 | comments + search | ✅ 查人群 |
| 危机公关复盘 | search(时间线) + comments | ✅ |
| 时尚趋势预测 | trending + search(跨平台) | ✅ |
| 供应链情报 | search + comments | ✅ |
| 招聘背调 | user + posts(多平台) | ✅ |
| 政策舆情分析 | search + trending + comments | ✅ |
| 跨平台内容迁移 | posts + info(对比格式) | 可选 |

---

## 环境变量

| 变量 | 说明 |
|------|------|
| `ASYRE_SEARCH_KEY` | API Key（必需，由管理员提供） |
| `ASYRE_SEARCH_URL` | API 地址（可选，默认自动配置） |

## 依赖

- Python 3.10+
- `requests`
