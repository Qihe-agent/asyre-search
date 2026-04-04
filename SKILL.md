---
name: asyre-search
description: |
  Asyre Search 全平台社媒数据查询。支持抖音、小红书、B站、TikTok、YouTube、Instagram、Twitter 等 21 个平台。
  查视频详情、用户信息、作品列表、搜索、热搜、评论等。
  触发词: asyre search, 查抖音, 查小红书, 社媒数据, 平台数据, fetch video, get user info, 视频数据, 账号数据
---

# Asyre Search

全平台社媒数据查询工具，由 Asyre 提供。

## Quick Start

```bash
# 设置 API Key
export ASYRE_SEARCH_KEY="your_key_here"

# 自动识别平台，查视频详情
python3 scripts/asyre_search.py info "https://v.douyin.com/xxxxx/"

# 查用户信息
python3 scripts/asyre_search.py user "https://www.douyin.com/user/xxx" --platform douyin

# 搜索
python3 scripts/asyre_search.py search "AI" --platform douyin --type video
```

## Commands

| Command | Description | Requires `--platform` |
|---------|-------------|:---------------------:|
| `info <URL>` | 视频/帖子详情（自动识别平台） | ❌ |
| `user <URL/ID>` | 用户/频道信息 | ✅ |
| `posts <URL/ID>` | 用户作品列表 | ✅ |
| `search <keyword>` | 搜索内容 | ✅ |
| `trending` | 热搜/趋势 | ✅ |
| `comments <URL/ID>` | 评论列表 | ✅ |
| `raw <endpoint>` | 直接调用任意 API | ❌ |

## Supported Platforms

| Platform | `--platform` value | URL auto-detect |
|----------|-------------------|:---------------:|
| 抖音 | `douyin` | ✅ |
| 小红书 | `xiaohongshu` | ✅ |
| B站 | `bilibili` | ✅ |
| TikTok | `tiktok` | ✅ |
| YouTube | `youtube` | ✅ |
| Instagram | `instagram` | ✅ |
| Twitter/X | `twitter` | ✅ |

还支持 Weibo、Threads、Pinterest、Spotify、SoundCloud、Telegram 等平台，
可通过 `raw` 命令直接调用。

## Environment

| Variable | Description |
|----------|-------------|
| `ASYRE_SEARCH_KEY` | API Key（必需，由管理员提供） |
| `ASYRE_SEARCH_URL` | API 地址（可选，默认自动配置） |

## Dependencies

- Python 3.11+
- `requests`
