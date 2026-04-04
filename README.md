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

### 🔍 竞品监控
> "帮我查一下这个竞品的抖音账号，最近 30 天发了什么内容，哪条播放量最高。"

```bash
asyre-search posts "竞品抖音主页URL" --platform douyin --limit 30
```
实时拉取竞品的发布策略、爆款内容、更新频率，不再靠人工蹲点。

### 📊 市场趋势洞察
> "现在抖音上什么话题最火？小红书的热搜是什么？"

```bash
asyre-search trending --platform douyin
asyre-search trending --platform xiaohongshu
```
跨平台热搜一键聚合，快速捕捉市场风向，指导内容选题和投放策略。

### 🎯 达人筛选 & KOL 分析
> "我要找一个粉丝 50 万以上的美妆博主合作，帮我查一下她的数据。"

```bash
asyre-search user "达人主页URL" --platform xiaohongshu
asyre-search posts "达人主页URL" --platform xiaohongshu --limit 20
```
粉丝量、点赞量、互动率、内容风格——选达人不再凭感觉。

### 🕵️ 舆情监测
> "查一下这条视频底下用户都在说什么。"

```bash
asyre-search comments "视频URL" --limit 100
```
评论区是最真实的用户声音。产品口碑、用户痛点、竞品差评——全在这里。

### 📝 内容灵感采集
> "帮我搜一下小红书上关于'露营装备'的热门内容。"

```bash
asyre-search search "露营装备" --platform xiaohongshu --type note
```
一键获取平台上的爆款内容，分析标题、封面、互动数据，为你的创作提供数据支撑。

### 🌐 跨境电商选品
> "TikTok 上最近什么产品视频火了？"

```bash
asyre-search trending --platform tiktok
asyre-search search "unboxing" --platform tiktok --type video
```
追踪海外社媒爆款趋势，发现下一个跨境爆品。

### 🤖 Agent 集成
> "我的 AI Agent 需要实时查询社媒数据来辅助决策。"

Asyre Search 天然适配 AI Agent 工作流——结构化 JSON 输出，环境变量配置，CLI 调用。让你的 Agent 拥有社媒数据感知能力。

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
  <b>Asyre Search</b> — 让数据驱动每一个决策。<br>
  Powered by <a href="https://asyre.com">Asyre</a>
</p>
