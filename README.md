<div align="center">

# Asyre Search

**Social media intelligence across 20 platforms. One tool, 983 APIs.**

**全平台社媒数据查询与深度分析。一个工具，983 个接口。**

![Python](https://img.shields.io/badge/Python-3.10%2B-green)
![Platforms](https://img.shields.io/badge/Platforms-20-orange)
![APIs](https://img.shields.io/badge/APIs-983-blue)
![Workflows](https://img.shields.io/badge/Workflows-5-blueviolet)
![Scenarios](https://img.shields.io/badge/Scenarios-20-yellow)
![License](https://img.shields.io/badge/License-Asyre%20Source%20Available-lightgrey)

[English](#english) · [中文](#中文)

</div>

---

<a id="english"></a>

## Overview

Asyre Search is an AI-agent-native social media data tool. It wraps 983 TikHub API endpoints across 20 platforms into a 3-layer command system — from single API calls to full analysis workflows — designed to be used by both humans and AI agents.

### What it does

- **Atomic commands**: Query any post, user, search, trending, or comments on any platform
- **Workflows**: One command runs a complete analysis pipeline (account deep-dive, competitor comparison, content discovery, KOL audit, cross-platform monitoring)
- **20 named scenarios**: Pre-configured analysis templates for common business use cases
- **Auto-generated registry**: 983 endpoints stay in sync with TikHub's API via OpenAPI spec

### Supported Platforms

| Domestic (CN) | International |
|:---:|:---:|
| 抖音 Douyin (246) | TikTok (206) |
| 小红书 Xiaohongshu (79) | YouTube (44) |
| B站 Bilibili (41) | Instagram (88) |
| 微博 Weibo (64) | Twitter/X (13) |
| 快手 Kuaishou (33) | Reddit (24) |
| 知乎 Zhihu (34) | LinkedIn (25) |
| 微信视频号 (10) | Threads (11) |
| 微信公众号 (10) | Lemon8 (16) |
| 西瓜/头条/皮皮虾 (31) | |

Numbers in parentheses = available API endpoints per platform.

---

## Quick Start

```bash
# Set your API key
export TIKHUB_API_KEY="your_key_here"

# Atomic: get a video's data
python3 scripts/asyre_search.py info "https://v.douyin.com/iYxxxxxx/"

# Atomic: search a keyword
python3 scripts/asyre_search.py -p xiaohongshu search "AI创业"

# Workflow: full account analysis
python3 scripts/asyre_search.py -p xiaohongshu analyze USER_ID

# Workflow: compare competitors
python3 scripts/asyre_search.py -p douyin compare USER_A USER_B

# Workflow: discover viral content patterns
python3 scripts/asyre_search.py -p xiaohongshu scout "护肤品推荐"

# Workflow: evaluate a KOL for partnership
python3 scripts/asyre_search.py -p xiaohongshu audit USER_ID

# Workflow: monitor a brand across platforms
python3 scripts/asyre_search.py monitor "品牌名" --platforms douyin xiaohongshu bilibili

# Scenario: run a named analysis template
python3 scripts/asyre_search.py scenario --list
python3 scripts/asyre_search.py -p xiaohongshu scenario viral-reverse --keyword "AI"

# Raw: call any of the 983 endpoints directly
python3 scripts/asyre_search.py raw /api/v1/douyin/app/v3/fetch_hot_search_list
```

---

## Architecture

```
asyre-search/
├── SKILL.md                      # Agent instructions (Claude Code skill)
├── scripts/
│   ├── asyre_search.py           # CLI entry point
│   ├── generate_registry.py      # Auto-generate registry from OpenAPI spec
│   ├── platforms/
│   │   ├── base.py               # PlatformAdapter base + _call() method
│   │   ├── registry.py           # EndpointRegistry resolver
│   │   ├── douyin.py             # Platform adapters (7 total)
│   │   ├── xiaohongshu.py
│   │   ├── bilibili.py
│   │   ├── tiktok.py
│   │   ├── youtube.py
│   │   ├── instagram.py
│   │   └── twitter.py
│   └── workflows/
│       ├── base.py               # WorkflowRunner + WorkflowResult
│       ├── metrics.py            # Shared metric computation
│       ├── analyze.py            # Account analysis
│       ├── compare.py            # Competitive comparison
│       ├── scout.py              # Content discovery
│       ├── audit.py              # KOL evaluation
│       ├── monitor.py            # Cross-platform monitoring
│       └── scenarios.py          # 20 named scenarios
└── registry/
    ├── api_registry.json         # Auto-generated (983 endpoints)
    ├── action_map.json           # Hand-curated action→endpoint mapping
    └── ENDPOINTS.md              # Auto-generated human-readable docs (10K+ lines)
```

### Registry-Driven Design

Endpoint paths are never hardcoded. A generator script pulls from TikHub's OpenAPI spec and produces a structured registry. Adapters resolve endpoints at runtime via `action_map.json`. When TikHub updates their API:

```bash
python3 scripts/generate_registry.py  # Re-sync all 983 endpoints
```

### Workflow Output

Every workflow returns a `WorkflowResult` with three outputs:
- **JSON data** — structured metrics for programmatic use
- **Markdown report** — human-readable analysis
- **Blueprint spec** — visualization spec for the blueprinter skill

---

## 20 Scenarios

| Category | Scenario | Input |
|----------|----------|-------|
| **Account** | `account-deepdive` Full analysis | `--target USER_ID` |
| | `growth-diagnosis` Growth health check | `--target USER_ID` |
| | `content-matrix` Content type analysis | `--target USER_ID` |
| **Competition** | `competitor-compare` Side-by-side | `--targets ID1 ID2` |
| | `kol-comparison` KOL benchmarking | `--targets ID1 ID2` |
| **KOL** | `kol-audit` Partnership evaluation | `--target USER_ID` |
| | `kol-fraud-check` Fake follower detection | `--target USER_ID` |
| **Content** | `viral-reverse` Viral pattern analysis | `--keyword KEYWORD` |
| | `content-ideas` Topic discovery | `--keyword KEYWORD` |
| | `ad-creative-mining` Ad creative research | `--keyword KEYWORD` |
| | `niche-scan` Category landscape | `--keyword KEYWORD` |
| **Monitoring** | `brand-monitor` Brand voice tracking | `--keyword BRAND` |
| | `crisis-alert` Crisis early warning | `--keyword BRAND` |
| | `new-product-watch` Launch tracking | `--keyword PRODUCT` |
| **Trending** | `trending-now` Real-time hot topics | (none) |
| | `industry-trends` Industry analysis | `--keyword INDUSTRY` |
| **Special** | `local-business` Local market research | `--keyword "CITY+CATEGORY"` |
| | `cross-platform-presence` Multi-platform audit | `--keyword BRAND` |
| | `comment-insight` Comment quality analysis | `--target USER_ID` |
| | `investment-dd` Investment due diligence | `--keyword BRAND` |

---

## License

Asyre Source Available License v1.0 — free for personal, educational, and non-commercial use. Commercial use requires a separate license from [Qihe-agent](https://github.com/Qihe-agent).

---

<a id="中文"></a>

## 概述

Asyre Search 是一个为 AI Agent 原生设计的社媒数据工具。它将 TikHub 的 983 个 API 端点封装成 3 层命令体系——从单次 API 调用到完整分析工作流——人类和 AI Agent 都能高效使用。

### 核心能力

- **原子命令**：查任意平台的帖子、用户、搜索、热搜、评论
- **工作流**：一条命令跑完完整分析流程（账号深度分析、竞品对比、内容探查、达人评估、跨平台监测）
- **20 个预设场景**：覆盖常见业务场景的分析模板
- **自动生成的注册表**：983 个端点通过 OpenAPI 规范自动同步

### 支持平台

| 国内平台 | 海外平台 |
|:---:|:---:|
| 抖音 (246 接口) | TikTok (206) |
| 小红书 (79) | YouTube (44) |
| B站 (41) | Instagram (88) |
| 微博 (64) | Twitter/X (13) |
| 快手 (33) | Reddit (24) |
| 知乎 (34) | LinkedIn (25) |
| 微信视频号 (10) | Threads (11) |
| 微信公众号 (10) | Lemon8 (16) |
| 西瓜/头条/皮皮虾 (31) | |

括号内数字 = 该平台可用的 API 端点数。

---

## 快速开始

```bash
# 设置 API Key
export TIKHUB_API_KEY="your_key_here"

# 原子命令：查视频数据
python3 scripts/asyre_search.py info "https://v.douyin.com/iYxxxxxx/"

# 原子命令：搜索关键词
python3 scripts/asyre_search.py -p xiaohongshu search "AI创业"

# 工作流：账号全景分析
python3 scripts/asyre_search.py -p xiaohongshu analyze USER_ID

# 工作流：竞品对比
python3 scripts/asyre_search.py -p douyin compare 用户A 用户B

# 工作流：爆款内容探查
python3 scripts/asyre_search.py -p xiaohongshu scout "护肤品推荐"

# 工作流：达人评估（给出 INVEST/NEGOTIATE/PASS 建议）
python3 scripts/asyre_search.py -p xiaohongshu audit USER_ID

# 工作流：跨平台品牌监测
python3 scripts/asyre_search.py monitor "品牌名" --platforms douyin xiaohongshu bilibili

# 场景：运行预设分析模板
python3 scripts/asyre_search.py scenario --list                    # 查看所有场景
python3 scripts/asyre_search.py -p xiaohongshu scenario viral-reverse --keyword "AI"

# 直接调用：983 个端点任意调
python3 scripts/asyre_search.py raw /api/v1/douyin/app/v3/fetch_hot_search_list
```

---

## 架构

```
asyre-search/
├── SKILL.md                      # Agent 指令（Claude Code 技能）
├── scripts/
│   ├── asyre_search.py           # CLI 入口
│   ├── generate_registry.py      # 从 OpenAPI 自动生成注册表
│   ├── platforms/                # 平台适配器（7 个）+ 注册表解析器
│   └── workflows/                # 5 个工作流 + 20 个场景
└── registry/
    ├── api_registry.json         # 自动生成（983 个端点完整 schema）
    ├── action_map.json           # 手动维护的 action→endpoint 映射
    └── ENDPOINTS.md              # 自动生成的接口手册（10000+ 行）
```

### 注册表驱动设计

端点路径不再硬编码。生成器脚本从 TikHub 的 OpenAPI 规范拉取并生成结构化注册表。适配器在运行时通过 `action_map.json` 解析端点。TikHub API 更新时：

```bash
python3 scripts/generate_registry.py  # 一条命令重新同步全部 983 个端点
```

### 工作流输出

每个工作流返回 `WorkflowResult`，包含三种输出：
- **JSON 数据** — 结构化指标，供程序使用
- **Markdown 报告** — 人类可读的分析报告
- **Blueprint 规格** — 可交给 blueprinter 技能生成可视化图表

---

## 20 个场景

| 分类 | 场景 | 输入 |
|------|------|------|
| **📊 账号分析** | `account-deepdive` 账号深度分析 | `--target 用户ID` |
| | `growth-diagnosis` 粉丝增长诊断 | `--target 用户ID` |
| | `content-matrix` 内容矩阵分析 | `--target 用户ID` |
| **⚔️ 竞品对比** | `competitor-compare` 竞品对比 | `--targets ID1 ID2` |
| | `kol-comparison` 达人横评 | `--targets ID1 ID2` |
| **🔍 达人评估** | `kol-audit` 达人评估 | `--target 用户ID` |
| | `kol-fraud-check` KOL打假 | `--target 用户ID` |
| **📝 内容探查** | `viral-reverse` 爆款逆向工程 | `--keyword 关键词` |
| | `content-ideas` 内容选题 | `--keyword 关键词` |
| | `ad-creative-mining` 广告素材挖掘 | `--keyword 关键词` |
| | `niche-scan` 赛道扫描 | `--keyword 关键词` |
| **🌐 舆情监测** | `brand-monitor` 品牌声量监测 | `--keyword 品牌名` |
| | `crisis-alert` 危机预警 | `--keyword 品牌名` |
| | `new-product-watch` 新品上市监测 | `--keyword 产品名` |
| **🔥 趋势分析** | `trending-now` 实时热搜 | （无参数） |
| | `industry-trends` 行业趋势 | `--keyword 行业词` |
| **⭐ 特殊场景** | `local-business` 本地商家获客 | `--keyword "地名+品类"` |
| | `cross-platform-presence` 跨平台诊断 | `--keyword 品牌名` |
| | `comment-insight` 评论洞察 | `--target 用户ID` |
| | `investment-dd` 投资尽调 | `--keyword 品牌名` |

---

## 许可证

Asyre Source Available License v1.0 — 个人、教育和非商业用途免费。商业使用需要联系 [Qihe-agent](https://github.com/Qihe-agent) 获取商业许可。
