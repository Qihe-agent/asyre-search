# 同赛道深度对比 Playbook (Niche Deep-Dive)

> 这是 Asyre Search 内部沉淀的专业 MCN 竞品分析完整方法论。LLM 在遇到类似请求时按本文档执行。

## 何时触发本 playbook

**必须**走本 playbook 的请求关键词：

- 同赛道深度分析 / 同行业对标 / 竞品深度对比
- 5 个账号横评 / 赛道矩阵分析 / 护城河打分
- MCN 全面诊断 / 我是 MCN 想了解 X 在赛道里的位置
- X 是不是赛道头部 / X 真正的对手是谁

**不要**用本 playbook 的（用其他场景）：

- 单账号分析 → 用 `account-pro` 或 `account-deepdive`
- 2-3 账号简单对比 → 用 `competitor-compare`
- 仅找选题 → 用 `content-ideas`
- 跨平台同名搜索 → 用 `cross-platform-presence`

## 历史成功案例

- 2026-05-01 · 悉尼姜博士同赛道分析（4 个对标 + 1 个主体 = 5 账号 × 792 笔记 × 4 家 Top 1 评论 = 30+ 页 Word + 10 页 SVG deck）

---

## 完整 4 阶段流水线

### Phase 1 · 定位主体账号 + 识别同赛道竞品

**输入**：用户给的主体账号（昵称或 user_id）+ 赛道描述

**步骤**：

1. **如果用户没给 user_id**，先用 `search` 命令搜主体账号
   ```bash
   python3 scripts/asyre_search.py --format json -p xiaohongshu search '<完整账号名>'
   ```
   - 关键：用**完整全名**搜，短词会被风控（参见 SKILL.md 故障处理铁律）
   - 取第一条 note 的 user.userid 作为主体 user_id

2. **识别同赛道竞品**（核心判断）：
   - 先用赛道关键词搜笔记（如 悉尼地产 / 澳洲留学 / 上海房产）
   - 从结果里抽取 user_id 做频次统计
   - 取 top 4 不重复 user_id 作为竞品候选
   - 排除规则：粉丝差距超过 10 倍的（不在同段位）、最近 6 个月发文量 < 5 的（停更账号），主体账号本身

3. **可选：用户提供候选名单**
   - 如果用户给了候选名单（如 对比 X / Y / Z），直接用，跳过自动识别

**输出**：5 个 user_id（1 主体 + 4 竞品），命名清晰（中文名 + uid 前 12 位）

### Phase 2 · 全量数据采集（5 账号并行）

对每个账号执行：

1. **profile**：`app/get_user_info` 拿 fans / follows / interactions / desc / verify_content
2. **全量笔记翻页**：`web_v2/fetch_home_notes` 用 cursor 翻到底
   - 期望量级：每个账号 50-500 篇
   - 注意：tikhub 有时翻到第 5-8 页会 400，是上游限频，重试 1 次然后停
3. **Top 1-3 笔记的评论抽样**：`app/get_note_comments`
   - 路径是双层嵌套：`data.data.comments`（不是 `data.comments`）
   - 每个账号至少抽 30 条 L1 评论

**避坑**：
- 不要 per-post 调 `get_info` —— posts list 已含完整互动字段，重复调用会触发 400 限流
- 5 个账号并行用 Python 协程或 shell &，单账号串行翻页
- 总耗时目标：< 5 分钟（5 账号 × ~1 分钟）

### Phase 3 · 计算 11 维矩阵 + 10 维护城河打分

#### 11 维数据矩阵（横向对比表）

| # | 维度 | 计算方式 |
|---|---|---|
| 1 | 粉丝数 | profile.interactions.fans |
| 2 | 笔记总数 + 视频比例 | len(notes) + count(type=video)/total |
| 3 | 累计总互动 | Σ(likes + comments + collected) |
| 4 | 单笔记均互动 | total / count |
| 5 | 单笔记中位互动 | median(eng) |
| 6 | P90 / 最高 | sorted[int(n*0.9)] / max |
| 7 | 单粉互动率 | total / (count * fans) × 100% |
| 8 | 近 60 天均互动 vs 前 60 天 | 时间分桶 + 变化幅度 |
| 9 | 揭秘类笔记数 | 标题正则匹配 揭秘/内幕/不会说/避雷/吐槽 |
| 10 | 真实购房咨询占比 | Top 1 笔记评论手工分类（≥30 条抽样）|
| 11 | 平台认证 | profile.red_official_verify_content |

#### 10 维护城河打分（雷达图核心）

每个维度对每个账号给 1-5 分（赛道末位=1，赛道第一=5），按以下顺序：

1. 粉丝量级
2. 单粉互动率
3. 单条最高互动
4. 近 60 天活跃度
5. 内容效率（单笔记均互动）
6. 视频化程度
7. 题材差异化（揭秘 / 故事 / 工具类占比）
8. 评论商业价值（真实购房咨询占比）
9. 平台认证（蓝V=5，无=1）
10. 增长动能（近 60 天 vs 前 60 天变化幅度）

**总分**：5 × 10 = 50。一般来说赛道头部 ≥ 38，腰部 25-35，尾部 < 25。

#### 评论商业价值分级（关键定性指标）

抽样每家账号 Top 1 笔记前 30 条 L1 评论，按以下分类计数：

- **真实购买咨询**：问价格、户型、政策、加 V、申请 / 购房决策类
- **同行八卦 / 价值观争议**：行业讨论、社会观察、调侃
- **路人吃瓜**：感叹、点赞、与产品决策无关的回复

商业转化潜力 = 真实购买咨询占比。≥ 80% = ⭐⭐⭐⭐⭐，60-80% = ⭐⭐⭐⭐，40-60% = ⭐⭐⭐，20-40% = ⭐⭐，< 20% = ⭐

### Phase 4 · 行业背景 Web Search（增加报告深度）

用 Web Search 工具查 3 个角度（每个 1 个 query）：

1. **平台政策风险**：`<平台名> <类目> 限流 严打 政策 2025 2026`
2. **赛道趋势**：`<赛道名> 头部账号 <平台名> 2026`
3. **算法更新**：`<平台名> 算法更新 2026`

提取要点放到报告外部背景章节。这一步不能跳——会显著提升报告权威性。

---

## 输出与下游 Skill 链

本 skill 产出**结构化数据 + Markdown 报告骨架**。下游交给：

| 交付物 | 下游 Skill | 命令 |
|---|---|---|
| Word 报告（可发客户）| asyre-docforge | `docforge -p proposal --eisvogel --font 'PingFang SC' --titlepage --toc <md>` |
| 16:9 SVG Deck（投影演讲）| next-slide-impeccable | 多页 Mode A 创建，建议 10 页见下表 |

### 推荐 deck 结构（10 页 × canonical 模板映射）

| # | Slide | Canonical 模板 | 关键可视化 |
|---|---|---|---|
| 01 | Cover | 自定 + Asyre 招牌 | bigGlow 标题 + 5 个 anchor counter |
| 02 | 5 个核心结论 | bento-grid 2+3 | 5 张 finding 卡 + 大数字 |
| 03 | 5 账号 11 维矩阵 | `08-comparison-matrix-dense` | 11 行 × 5 列数据表 |
| 04 | 三蓝海中心辐射 | `02-hub-spoke` 或 `17-structural-breakdown` | 中心账号 + 3 蓝海 spoke |
| 05 | 反转叙事（如有）| `16-story-mountain` | 5 幕弧线 + climax/twist |
| 06 | 双账号 vs | `21-binary-comparison` | VS bounce.out + 6 行 |
| **07** | **十维护城河打分** ⭐ | `05-radar-chart` 改 decagon | **10 轴 × 5 多边形 · sweep beam · 5 卡 counter · 10 行 breakdown** |
| 08 | 评论质量分级 | `20-comparison-table` | 5 列 × 3 行评论分类 |
| 09 | 30 天紧急动作 | bento 2x2 | 2 红 urgent + 2 金 high |
| 11 | 12 周 KPI 看板 | `06-dashboard` | 5 KPI counter + 趋势曲线 |
| 12 | Closing | 自定 + Asyre | 双层 hero + 浮动粒子 |

详细每页结构见 `~/Desktop/客户交付/悉尼姜博士MCN诊断/deck-v2/`（reference 实例）。

---

## 决议节奏（4 阶段总耗时 < 30 分钟）

| 阶段 | 子任务 | 预计耗时 |
|---|---|---|
| Phase 1 | 定位 + 识别竞品 | 3-5 分钟 |
| Phase 2 | 5 账号全量数据 | 5-8 分钟 |
| Phase 3 | 11 维矩阵 + 10 维打分 | 3-5 分钟 |
| Phase 4 | Web Search × 3 | 3-5 分钟 |
| 报告写作 | Markdown 报告 | 8-12 分钟 |
| docforge | Word 转换 | < 1 分钟 |
| next-slide | 10 页 SVG deck | 12-20 分钟 |

---

## 输出 schema（JSON，传给下游 LLM）

```json
{
  "main": {
    "name": "", "uid": "", "platform": "xiaohongshu",
    "profile": {...}, "notes_count": 0, "metrics": {...},
    "moat_scores": {"粉丝量级": 5, ...}, "moat_total": 0
  },
  "competitors": [
    {"name": "", "uid": "", "profile": {...}, "metrics": {...},
     "moat_scores": {...}, "moat_total": 0}
  ],
  "matrix_11dim": [...],
  "top_comments_audit": [
    {"account": "", "top_note_id": "", "buy_intent_pct": 0.20,
     "trade_value_stars": 3, "sample_quotes": [...]}
  ],
  "web_context": {
    "policy_risk": "...", "niche_trend": "...", "algo_update": "..."
  },
  "slide_recommendations": [
    {"page": 7, "template": "05-radar-chart", "data": {...}}
  ]
}
```

---

## 故障处理

参见 SKILL.md "故障处理铁律" 章节。本 playbook 特有的额外规则：

- **找不到主体账号** → 让用户给 user_id / 主页 URL，不要硬扛
- **某个竞品停更/数据稀疏** → 标记为 参考标的而非竞争对手，不强求满足相同采样量
- **Web Search 失败** → 跳过 Phase 4，在报告中明确标注 "行业背景部分本次未补充"
- **总耗时超 30 分钟** → 减少竞品数量到 3 家或减少抽样深度，不要在死路上等

---

## 历史复盘要点

1. **悉尼姜博士项目** (2026-05-01)：
   - 初版 deck 用了 CSS 卡片而非 SVG canonical → 用户判定 "非常次" → 后重做为 10 页 SVG canonical 模板
   - 关键学习：deck 类报告必须用 `structures/` 下的 canonical 模板，不要走 CSS 偷懒
   - radar 模板的 hex (6 维) 改 decagon (10 维) 需要重算所有顶点坐标，用 Python 一次性算清楚再写 SVG

