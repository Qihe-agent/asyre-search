# Asyre Search

**一个 API，解锁全球 21+ 社媒平台数据。**

不用爬虫，不用逆向，不用维护。一行命令，实时获取抖音、小红书、TikTok、YouTube、Instagram、Twitter、B站等平台的视频详情、用户画像、作品列表、评论、热搜趋势。

---

## 为什么选择 Asyre Search？

| 传统方式 | Asyre Search |
|---|---|
| 每个平台写一套爬虫 | 统一 API，一套代码覆盖所有平台 |
| 反爬对抗、封号、维护成本高 | 稳定接口，无需担心封禁 |
| 数据格式不统一，清洗成本大 | 结构化 JSON，开箱即用 |
| 只能覆盖 2-3 个平台 | 21+ 平台，持续扩展中 |

---

## 支持平台

| 平台 | 国内/海外 | 视频详情 | 用户信息 | 作品列表 | 搜索 | 热搜 | 评论 |
|------|:--------:|:--------:|:--------:|:--------:|:----:|:----:|:----:|
| 抖音 | 🇨🇳 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| 小红书 | 🇨🇳 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| B站 | 🇨🇳 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| TikTok | 🌏 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| YouTube | 🌏 | ✅ | ✅ | ✅ | ✅ | — | ✅ |
| Instagram | 🌏 | ✅ | ✅ | ✅ | ✅ | — | ✅ |
| Twitter/X | 🌏 | ✅ | ✅ | ✅ | ✅ | ✅ | — |

还支持微博、Threads、Pinterest、Spotify、SoundCloud、Telegram 等 14+ 个平台，通过 `raw` 命令直接调用。

---

## 实战场景

### 🔥 场景一：爆款逆向工程 — "为什么别人的视频能爆？"

你的客户是一家美妆品牌，投了十条抖音视频，播放量���在 5000 以下。但竞品「花西子」的一条视频突然爆了 500 万播放。

**传统做法：** 打开抖音 App，手动翻，截图，记到 Excel ���。费时费力，数据还不全。

**用 Asyre Search：**

```bash
# 第一步：拉取竞品爆款视频详情 — 播放量、点赞、评论、转发、发布时间、文案、标签
asyre-search info "https://v.douyin.com/iYxxxxxx/"

# 第二步：拉取竞品最近 50 条作品，按互动量排序，找出规律
asyre-search posts "花西子抖音主页URL" --platform douyin --limit 50

# 第三步：扒评论区 — 用户到底在说什么？是被产品打动还是被创意吸引？
asyre-search comments "爆款视频URL" --limit 200
```

**你能拿到：** 发布时间规律（周几几点发）、文案结构（痛点→方案→行动号召）、标签策略、评论区高频关键词。这些是靠手动刷永远刷不出来的。

---

### 🕵️ 场景二：KOL 打假 — "这个博主的粉丝是真的吗？"

一个 MCN 找你合作推广，说旗下博主小红书 80 万粉丝，报价 5 万一条。你怎么判断值不值？

```bash
# 查博主基本信息 — 粉丝数、获赞数、关注数
asyre-search user "博主小红书主页URL" --platform xiaohongshu

# 拉最近 30 条笔记 — 看每条的点赞、收藏、评论数
asyre-search posts "博主小红书主页URL" --platform xiaohongshu --limit 30

# 重点：抽几条笔记看评论质量
asyre-search comments "某条笔记URL" --limit 100
```

**你在看什么：**
- 80 万粉丝但每条笔记只有 200 点赞？→ 大概率刷粉
- 评论全是「好好看」「求链接」这种一个字的？→ 水军
- 最近 30 条笔记互动量波动剧烈，有几条突然暴增？→ 投了 DOU+，自然流量其实很差

**一条命令省 5 万。**

---

### 📰 场景三：舆情风暴预警 — "产品翻车了，负面在扩散"

你运营的品牌突然被某个 B 站 UP 主做了一期「避雷视频」，弹幕和评论区炸了。你的老板问你：现在情况多严重？扩散到其他平台了吗？

```bash
# 查这条避雷视频到底有多少播放、转发、弹幕
asyre-search info "B站视频URL"

# 看评论区 — 用户情绪是愤怒还是吃瓜？有没有带节奏的？
asyre-search comments "B站视频URL" --platform bilibili --limit 200

# 立刻跨平台检查 — 有没有扩散到抖音、小红书？
asyre-search search "你的品牌名 避雷" --platform douyin --type video
asyre-search search "你的品牌名 踩雷" --platform xiaohongshu --type note

# Twitter/微博国际舆情
asyre-search search "你的品牌英文名" --platform twitter --type tweet
```

**你能在 5 分钟内：** 评估传播规模、判断情绪走向、确认扩散范���、锁定关键传播节点。而不是在各个 App 之间来回切换，边翻边焦虑。

---

### 🛒 场景四��跨境选品 — "TikTok 上什么东西正在爆？"

你做跨境电商，需要每周找到下一个潜在爆品。以前靠人工刷 TikTok For You 页面碰运气。

```bash
# 查 TikTok 当前热搜 — 什么话题正在起势
asyre-search trending --platform tiktok

# 搜索特定品类的爆款视频
asyre-search search "kitchen gadgets" --platform tiktok --type video --limit 30
asyre-search search "cleaning hack" --platform tiktok --type video --limit 30

# 发现一个爆款视频？立刻拉详情 — 播放量、点赞、评论
asyre-search info "https://www.tiktok.com/@user/video/xxxxx"

# 再查这个博主 — 是不是经常带货？其他视频表现如何？
asyre-search posts "博主TikTok主��" --platform tiktok --limit 20
```

**选品逻辑：** 找到播放量 > 100 万但商品链接还没有被大量跟卖的视频 → 这就是窗口期。你从发现到上架如果能在 48 小时内完成，就能吃到第一波流量红利。

---

### 🎬 场景五：内容工厂 — "我管 30 个账号，怎么批量找选题？"

你是一家 MCN 的内容总监，手下 30 个账��覆盖美食、旅���、母婴、科技四个赛道。每周一要给每个账号出 3 条选题方向。

```bash
# 四个赛道的热搜，一次拉完
asyre-search search "美食探店" --platform douyin --type video --limit 20
asyre-search search "旅行攻略" --platform xiaohongshu --type note --limit 20
asyre-search search "母婴好物" --platform xiaohongshu --type note --limit 20
asyre-search search "数码测评" --platform bilibili --type video --limit 20

# 对标账号追踪 — 每个赛道盯 3 个头部账号
asyre-search posts "对标账号1" --platform douyin --limit 10
asyre-search posts "对标账号2" --platform douyin --limit 10
asyre-search posts "对标账号3" --platform douyin --limit 10
```

**你得到的：** 一份覆盖 4 个赛道、12 个对标账号、80+ 条最新内容的数据表。哪些话题在起势、哪些在衰退、哪些账号在变风格——全是结构化数���，直接喂给你的 AI 生成选题报告。

---

### 💼 场景六：投资尽调 — "这个网红品牌真有这么火吗？"

一个新消费品牌来融资，BP 里写着「小红书 10 万篇笔记、抖音话题播放 5 亿」。你是投资经理，需要验证。

```bash
# 搜品牌关键词 — 看真实的内容量和互动质量
asyre-search search "品牌名" --platform xiaohongshu --type note --limit 50
asyre-search search "品牌名" --platform douyin --type video --limit 50

# 查品牌官方账号 — 真实粉丝和互动数据
asyre-search user "品牌官方抖音" --platform douyin
asyre-search posts "品牌官方抖音" --platform douyin --limit 30

# 看用户真实评价 — 而不是品牌方给你筛选过的
asyre-search search "品牌名 踩雷" --platform xiaohongshu --type note
asyre-search search "品牌名 真实测评" --platform xiaohongshu --type note
```

**真相藏在数据里：** 10 万篇笔记里有多少是素人自发的、多少是水军铺的？官方账号互动率是 5% 还是 0.5%？搜「踩雷」出来多少条？这些数据决定的不是一条广告的好坏，而是一笔几百万投资的成败。

---

### 🎵 场景七：音乐推广 — "我的歌能不能火？先看数据"

你是一个独立音乐人，刚发了一首新歌。你想知道类似风格的歌曲在各个平台的传播情况，找到最合适的推广渠道。

```bash
# 看类似风格的歌在抖音��的热度
asyre-search search "独立民谣" --platform douyin --type video --limit 30

# 查 B 站音乐区 — 哪些翻唱/二创播放量高
asyre-search search "民谣吉他" --platform bilibili --type video --limit 30

# Instagram 上音乐 Reels 的趋势
asyre-search search "indie folk" --platform instagram --type reel --limit 20

# 如果发现某个视频用了类似的 BGM 并且火了 — 立刻扒详情
asyre-search info "视频URL"
asyre-search comments "视频URL" --limit 100
```

**策略产出：** 抖音上 15 秒副歌片段 + 情感画面的模板播放量最高；B 站适合 3 分钟以上的完整版 + 制作过程；Instagram Reels 要卡节奏点。不同平台不同策略，数据告诉你答案。

---

### 🏠 场景八：本地生意获客 — "隔壁奶茶店天天排队，他做了什么？"

你在某个城市开了一家咖啡店，隔壁新开的奶茶店每天排长队。你想知道他们的线上推广策略。

```bash
# 搜这家店在小红书上的笔记 — 是投了达人还是自然传播？
asyre-search search "奶茶店名 城市名" --platform xiaohongshu --type note --limit 30

# 看抖音上有没有探店视频
asyre-search search "奶茶店名" --platform douyin --type video --limit 20

# 找到探店达人的视频 �� 分析哪种内容形式带来的互动最高
asyre-search info "探店视频URL"
asyre-search comments "探店视频URL" --limit 50
```

**你发现了什么：** 他们和 8 个本地达人合作了探店视频，每条成本大概 500-2000 元。其中效果最好的是「隐藏菜单」类内容，评论区全在问「怎么点」。你不需要抄他们的内容，但你知道了有效的获客路径——然后用更少的预算、更好的创意去超越。

---

### 🧠 场景九：AI Agent 自主调研 — "让 Agent 自己去查"

你给客户部署了一个 AI 业务助手。客户说：「帮我分析一下我们品牌和竞品在社交媒体��的声量对比。」

Agent 不需要人工操作，直接调用 Asyre Search：

```python
# Agent 内部工作流
own_brand = asyre_search("search", "自家品牌", platform="xiaohongshu", limit=50)
competitor = asyre_search("search", "竞品品牌", platform="xiaohongshu", limit=50)
own_posts = asyre_search("posts", "自家品牌小红书主页", platform="xiaohongshu", limit=30)
comp_posts = asyre_search("posts", "竞品小红书主页", platform="xiaohongshu", limit=30)

# Agent 自动分析：
# - 内容量对比
# - 平均互动率对比
# - 用户评价情感分析
# - 内容策略差异
# → 输出一份结构化的竞品分析报告
```

**Asyre Search 是给 Agent 装上的「社媒之眼」。** 结构化 JSON 输出、CLI 调用、环境变���配置——天然适配自动化工作流。你的 Agent 从此拥有实时感知社交媒体的能力。

---

### 📐 场景十：��术研究 — "我需要大规模社媒数据做分析"

你是一名研究社交媒体传播学的博士生，课题是「短视频平台上健康信息的传播特征」。你需要收集数据但不会写爬虫。

```bash
# 收集抖音上「健康科普」相关视频
asyre-search search "健康科普" --platform douyin --type video --limit 50 --raw -o health_douyin.json

# 收集 B 站上的「医学科普」视频
asyre-search search "医学科普" --platform bilibili --type video --limit 50 --raw -o health_bilibili.json

# 收集 YouTube 上英文健康内容做对比
asyre-search search "health education" --platform youtube --type video --limit 50 --raw -o health_youtube.json

# 对高播放量视频抓取评论做情感分析
asyre-search comments "视频URL" --limit 200 --raw -o comments.json
```

**输出：** 结构化 JSON 文件，可以直接导入 Python/R 做统计分析。播放量、点赞量、评论量、发布时间、作者信息——论文需要的变量全齐了。不用写一行爬虫代码，不用担心 IP 被封。

---

## 快速开始

```bash
# 1. 配置 API Key（由管理员提供）
export ASYRE_SEARCH_KEY="your_key_here"

# 2. 查询一条抖音视频
python3 scripts/asyre_search.py info "https://v.douyin.com/xxxxx/"

# 3. 搜索小红书内容
python3 scripts/asyre_search.py search "AI" --platform xiaohongshu

# 4. 查看抖音热搜
python3 scripts/asyre_search.py -p douyin trending
```

## 命令一览

| 命令 | 用途 | 示例 |
|------|------|------|
| `info <URL>` | 视频/帖子详情，自动识别平台 | `info "https://v.douyin.com/xxx/"` |
| `user <URL/ID>` | 用户/频道信息 | `user "主页URL" -p douyin` |
| `posts <URL/ID>` | 用户作品列表 | `posts "主页URL" -p douyin --limit 50` |
| `search <keyword>` | 搜索内容 | `search "关键词" -p xiaohongshu` |
| `trending` | 热搜/趋势 | `trending -p douyin` |
| `comments <URL/ID>` | 评论列表 | `comments "视频URL" --limit 100` |
| `raw <endpoint>` | 直接调用任意 API | `raw /api/v1/...` |

## 输出格式

| 参数 | 说明 |
|------|------|
| `--format table` | 默认，人类可读表格 |
| `--format json` | 结构化 JSON |
| `--raw` | 原��� API 响应 |
| `-o filename` | 输出到文件 |

## 环境变量

| 变量 | 说明 |
|------|------|
| `ASYRE_SEARCH_KEY` | API Key（必需，由管理员提供） |
| `ASYRE_SEARCH_URL` | API 地址（可选，默认自动配置） |

## 依赖

- Python 3.10+
- `requests`（`pip install requests`）

---

<p align="center">
  <b>Asyre Search</b> — 让数据驱动每一���决策。<br>
  Powered by <a href="https://asyre.com">Asyre</a>
</p>
