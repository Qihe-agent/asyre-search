---
name: asyre-search
description: |
  社交媒体数据查询与深度分析工具。查抖音、查小红书、查B站、查TikTok、查YouTube、查Instagram、查Twitter、查微博、查快手、查知乎——20个平台、983个API接口。
  Use this skill when the user wants to: 查博主/网红/账号数据, 看视频播放量/点赞/评论, 搜话题标签/热门内容, 找抖音热搜/trending topics, 监测品牌声量/舆情, 对比竞品社媒表现, 评估KOL/达人合作价值, or analyze any social media content or account.
  内置 5 大工作流（analyze账号分析、compare竞品对比、scout内容探查、audit达人评估、monitor跨平台监测）+ 20 个预设场景，一条命令输出完整报告 + Blueprint 可视化规格。
  Trigger whenever the user mentions 抖音/小红书/B站/TikTok/YouTube/Instagram/Twitter or any social platform combined with looking something up, checking data, searching content, finding trends, or monitoring brands.
  Examples: "抖音上什么话题最火", "帮我查小红书博主", "看看这个TikTok视频数据", "品牌在社媒上的声量", "这个达人值不值得投", "帮我分析竞品", "社媒数据", "爆款分析", "KOL评估".
---

# Asyre Search — 全平台社媒数据查询与深度分析

## 快速开始

所有命令在服务器上执行。工作目录和环境变量：

```bash
cd ~/xiu-he/Projects/moltbot/skills/asyre-search
export ASYRE_SEARCH_KEY="thp_xxx"  # 在 Asyre Portal 充值后获得

# 详见 references/key-setup.md — 包含创建 key、充值、限流、故障排查
```

平台代码：`douyin` | `xiaohongshu` | `bilibili` | `tiktok` | `youtube` | `instagram` | `twitter`

还有 13 个平台可通过 `raw` 命令访问：weibo, kuaishou, zhihu, threads, reddit, linkedin, lemon8, pipixia, toutiao, xigua, wechat_channels, wechat_mp

---

## 核心能力：3 层命令体系

### 第 1 层：原子命令（单次 API 调用）

```bash
python3 scripts/asyre_search.py info <URL>                           # 自动识别平台，查内容详情
python3 scripts/asyre_search.py -p <platform> user <ID_or_URL>       # 查用户信息
python3 scripts/asyre_search.py -p <platform> posts <ID_or_URL>      # 查用户作品列表
python3 scripts/asyre_search.py -p <platform> search <keyword>       # 搜索内容
python3 scripts/asyre_search.py -p <platform> trending               # 查热搜/趋势
python3 scripts/asyre_search.py -p <platform> comments <ID_or_URL>   # 查评论
python3 scripts/asyre_search.py raw <endpoint> [--params k=v]        # 直接调 983 个 API 中的任意一个
```

适用场景：只需要查一条具体的数据。

### 第 2 层：工作流命令（自动编排多次 API 调用）

**优先使用工作流命令。** 它们自动完成数据采集 + 指标计算 + 报告生成，比手动组合原子命令高效 10 倍。

```bash
# 账号全景分析：拉用户信息 → 全部作品 → 逐条详情 → 计算互动率/爆款/内容分布
python3 scripts/asyre_search.py -p <platform> analyze <user_id>

# 竞品对比：对 2+ 个账号各跑一次 analyze → 交叉对比
python3 scripts/asyre_search.py -p <platform> compare <user_A> <user_B> [<user_C>...]

# 内容探查：搜索关键词 → Top N 详情 → 分析爆款模式
python3 scripts/asyre_search.py -p <platform> scout <keyword>

# 达人评估：analyze + 评论质量采样 → 给出投放建议 (INVEST/NEGOTIATE/PASS)
python3 scripts/asyre_search.py -p <platform> audit <user_id>

# 跨平台监测：在多个平台搜索同一关键词 → 对比声量
python3 scripts/asyre_search.py monitor <keyword> --platforms douyin xiaohongshu bilibili
```

通用参数：
- `--limit N` — 限制分析的作品数（默认 20-50）
- `--error-policy continue|abort` — 遇到 API 错误继续还是终止（默认 continue）
- `-o output.json` — 保存完整结果（含 blueprint spec）到文件
- `--raw` — 输出原始 JSON 而非 Markdown 报告

### 第 3 层：预设场景（20 个命名工作流）

当需求能精确匹配某个场景时，直接用场景命令：

```bash
# 列出所有场景
python3 scripts/asyre_search.py scenario --list

# 运行指定场景
python3 scripts/asyre_search.py -p <platform> scenario <name> --target <user_id>
python3 scripts/asyre_search.py -p <platform> scenario <name> --keyword <keyword>
python3 scripts/asyre_search.py -p <platform> scenario <name> --targets <id1> <id2>
```

#### 场景速查表

| 场景 | 命令 | 适用输入 |
|------|------|---------|
| **📊 账号分析类** | | |
| `account-deepdive` 账号深度分析 | `--target USER_ID` | 全面分析：数据+内容+分布 |
| `growth-diagnosis` 粉丝增长诊断 | `--target USER_ID` | 互动率健康度+爆款依赖度 |
| `content-matrix` 内容矩阵分析 | `--target USER_ID` | 内容类型×互动效果矩阵 |
| **⚔️ 竞品对比类** | | |
| `competitor-compare` 竞品对比 | `--targets ID1 ID2` | 2-5 个账号全方位对比 |
| `kol-comparison` 达人横评 | `--targets ID1 ID2` | 多达人性价比对比 |
| **🔍 达人评估类** | | |
| `kol-audit` 达人评估 | `--target USER_ID` | 互动真实性+粉丝质量 |
| `kol-fraud-check` KOL打假 | `--target USER_ID` | 重点检查刷量+水军 |
| **📝 内容探查类** | | |
| `viral-reverse` 爆款逆向工程 | `--keyword 关键词` | 找爆款→分析共同特征 |
| `content-ideas` 内容选题 | `--keyword 关键词` | 发现热门选题+标签策略 |
| `ad-creative-mining` 广告素材挖掘 | `--keyword 关键词` | 高互动广告创意方向 |
| `niche-scan` 赛道扫描 | `--keyword 关键词` | 品类生态：热度+竞争度 |
| **🌐 舆情监测类** | | |
| `brand-monitor` 品牌声量监测 | `--keyword 品牌名` | 跨平台声量+热搜 |
| `crisis-alert` 危机预警 | `--keyword 品牌名` | 负面舆情信号 |
| `new-product-watch` 新品上市监测 | `--keyword 产品名` | 各平台讨论热度 |
| **🔥 趋势分析类** | | |
| `trending-now` 实时热搜 | 无需参数 | 当前平台热搜榜 |
| `industry-trends` 行业趋势 | `--keyword 行业词` | 热搜+搜索交叉分析 |
| **⭐ 特殊场景** | | |
| `local-business` 本地商家获客 | `--keyword 地名+品类` | 本地内容生态 |
| `cross-platform-presence` 跨平台诊断 | `--keyword 品牌名` | 多平台声量对比 |
| `comment-insight` 评论洞察 | `--target USER_ID` | 评论质量+用户反馈 |
| `investment-dd` 投资尽调 | `--keyword 品牌名` | 社媒视角的尽调 |

---

## 执行流程

### 收到需求后的决策树

```
用户提出社媒相关需求
  │
  ├─ 需求明确（给了具体账号/链接/关键词+明确的目标）
  │   → 直接匹配工作流或场景 → 执行
  │
  └─ 需求模糊（"帮我分析竞品"、"看看数据"）
      → 进入需求澄清（下方规则）→ 锁定后执行
```

### 需求澄清规则（仅在需求模糊时使用）

1. **每次最多问 3 个问题**，给出选项而非开放提问
2. **用案例引导**：给一个类似场景的例子，让用户说"对就是这种"
3. **锁定三要素**：谁（账号/品牌）+ 哪（平台）+ 看什么（数据维度）

澄清示例：
```
用户: 帮我分析一下竞品在社媒上的情况

Agent: 好的。先确认几个信息：
1. 竞品是哪个品牌？（先告诉我最重要的 1-2 个）
2. 你最关心哪个平台？（国内：抖音/小红书/B站 | 海外：TikTok/Instagram/YouTube）
3. 分析目的？
   A. 了解竞品的内容策略
   B. 对比声量差距
   C. 找到竞品的弱点（用户吐槽什么）
```

澄清完毕后，展示执行计划并确认。

### 数据采集 + 外部情报

对于深度分析任务，采用**双视角**：

- **数据视角**：用 asyre-search 命令拉平台原生数据（硬指标）
- **情报视角**：用 Web Search 补充行业背景、趋势、政策变化（软信号）

以下情况**必须**结合 Web Search：
- 趋势分析（热搜只是快照，需要时间线）
- 品牌调研（平台数据+企业背景）
- 行业报告（白皮书、数据报告）
- 舆情追溯（事件起因可能不在社媒上）

### 输出格式

```markdown
## 📊 分析报告：[主题]

### 核心发现
- [3-5 条关键发现，直接回答用户问题]

### 数据详情
[表格、排行、对比]

### 行业/背景（如有 Web Search）
[外部情报]

### 行动建议
[具体、可执行的下一步]
```

当工作流输出包含 `blueprint_spec` 时，可以交给 blueprinter 技能生成可视化图表。使用 `-o output.json` 保存完整输出，blueprint_spec 在 JSON 的 `blueprint_spec` 字段中。

---

## 需求→命令 快速路由

| 用户说的话 | 你应该用的命令 |
|-----------|-------------|
| "分析一下这个账号" | `analyze <user_id>` |
| "帮我看看这个博主值不值得投" | `audit <user_id>` |
| "对比一下这几个竞品" | `compare <id1> <id2>` |
| "现在什么内容火/帮我找选题" | `scout <keyword>` |
| "看看品牌口碑/舆情" | `monitor <keyword> --platforms ...` |
| "查这个视频的数据" | `info <URL>` |
| "拉一下热搜" | `trending` |
| "查这个用户的评论区" | `comments <ID>` |
| 给了一个链接，没说干什么 | 先问：查数据？查作者？查评论？还是全看？ |

---

## API 注册表

本工具包含从 TikHub OpenAPI 自动生成的完整接口注册表：

- `registry/api_registry.json` — 983 个端点的完整 schema（参数、类型、必填/可选）
- `registry/ENDPOINTS.md` — 10000+ 行的人类可读接口手册
- `registry/action_map.json` — 7 个核心平台的 action→endpoint 映射

当需要调用注册表中没有被工作流覆盖的接口时，查阅 `registry/ENDPOINTS.md` 找到端点路径和参数，然后用 `raw` 命令调用。

重新生成注册表（TikHub API 更新后）：
```bash
python3 scripts/generate_registry.py
```

---

## 环境

| 变量 | 说明 |
|------|------|
| `ASYRE_SEARCH_KEY` | Asyre API Key（在 Asyre Portal 注册后获得，`thp_` 前缀） |
| `ASYRE_SEARCH_URL` | 可选，Asyre gateway 地址（默认 `http://13.228.189.206/api/social`） |

依赖：Python 3.10+, `requests`
