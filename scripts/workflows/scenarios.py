"""20 pre-built analysis scenarios — named workflow combinations for common use cases.

Usage:
    asyre-search scenario <scenario_name> --target <target> --platform <platform>
    asyre-search scenario --list  # show all available scenarios
"""

import json
import sys
import time

from .base import WorkflowRunner, WorkflowResult, RateLimiter
from .metrics import (
    extract_user_metrics, extract_post_ids, extract_post_metrics,
    compute_account_metrics, assess_comment_quality, compact_number, safe_int,
)


# ── Scenario Registry ────────────────────────────────────────────

SCENARIOS = {
    # ── 账号分析类 ──
    "account-deepdive": {
        "name": "账号深度分析",
        "name_en": "Account Deep Dive",
        "description": "全面分析一个账号：基本信息 + 全部笔记互动 + 内容分布 + 增长诊断",
        "required": ["target", "platform"],
        "category": "account",
    },
    "account-pro": {
        "name": "账号 Pro 分析",
        "name_en": "Account Pro Analysis",
        "description": "Pro 级账号分析：趋势 + 节奏 + 标题挖掘 + 评论意图 + 健康度评分 + 优先级诊断（替代 account-deepdive 的轻量版）",
        "required": ["target", "platform"],
        "category": "account",
    },
    "growth-diagnosis": {
        "name": "粉丝增长诊断",
        "name_en": "Growth Diagnosis",
        "description": "分析账号增长健康度：互动率趋势、爆款占比、内容一致性",
        "required": ["target", "platform"],
        "category": "account",
    },
    "content-matrix": {
        "name": "内容矩阵分析",
        "name_en": "Content Matrix",
        "description": "分析账号内容结构：类型分布、爆款特征、最佳发布策略",
        "required": ["target", "platform"],
        "category": "account",
    },

    # ── 竞品分析类 ──
    "competitor-compare": {
        "name": "竞品对比",
        "name_en": "Competitor Compare",
        "description": "2-5 个竞品账号全方位数据对比",
        "required": ["targets", "platform"],
        "category": "competition",
    },
    "kol-comparison": {
        "name": "达人横评",
        "name_en": "KOL Comparison",
        "description": "多个达人数据横向对比，找出性价比最高的投放对象",
        "required": ["targets", "platform"],
        "category": "competition",
    },
    "niche-deepdive": {
        "name": "同赛道深度对比",
        "name_en": "Niche Deep-Dive",
        "description": "完整 4 阶段流水线：定位主体 + 识别 4 个同赛道竞品 + 全量笔记爬取 + Top 评论质量审计 + 11 维矩阵 + 10 维护城河打分。下游交给 docforge (Word 报告) + next-slide-impeccable (SVG deck)。详见 references/niche-deepdive-playbook.md",
        "required": ["target", "platform"],
        "optional": ["competitors", "niche_keyword"],
        "category": "competition",
    },


    # ── 达人评估类 ──
    "kol-audit": {
        "name": "达人评估",
        "name_en": "KOL Audit",
        "description": "评估达人是否值得投放：互动真实性 + 粉丝质量 + 内容匹配度",
        "required": ["target", "platform"],
        "category": "kol",
    },
    "kol-fraud-check": {
        "name": "KOL打假",
        "name_en": "KOL Fraud Check",
        "description": "重点检查粉丝/互动是否刷量：评论质量分析 + 互动率异常检测",
        "required": ["target", "platform"],
        "category": "kol",
    },

    # ── 内容探查类 ──
    "viral-reverse": {
        "name": "爆款逆向工程",
        "name_en": "Viral Reverse Engineering",
        "description": "搜索关键词 → 找到爆款内容 → 分析爆款共同特征",
        "required": ["keyword", "platform"],
        "category": "content",
    },
    "content-ideas": {
        "name": "内容选题",
        "name_en": "Content Ideas",
        "description": "围绕关键词发现热门内容，提取选题灵感和标签策略",
        "required": ["keyword", "platform"],
        "category": "content",
    },
    "ad-creative-mining": {
        "name": "广告素材挖掘",
        "name_en": "Ad Creative Mining",
        "description": "搜索品类关键词，找到高互动广告内容，分析创意方向",
        "required": ["keyword", "platform"],
        "category": "content",
    },
    "niche-scan": {
        "name": "赛道扫描",
        "name_en": "Niche Scan",
        "description": "扫描某个赛道/品类的整体内容生态：热度、竞争度、内容缺口",
        "required": ["keyword", "platform"],
        "category": "content",
    },

    # ── 舆情/监测类 ──
    "brand-monitor": {
        "name": "品牌声量监测",
        "name_en": "Brand Voice Monitor",
        "description": "跨平台监测品牌关键词的声量和热度",
        "required": ["keyword"],
        "category": "monitor",
    },
    "crisis-alert": {
        "name": "危机预警",
        "name_en": "Crisis Alert",
        "description": "监测品牌/产品的负面舆情信号",
        "required": ["keyword"],
        "category": "monitor",
    },
    "new-product-watch": {
        "name": "新品上市监测",
        "name_en": "New Product Watch",
        "description": "监测新品相关关键词在各平台的讨论热度",
        "required": ["keyword"],
        "category": "monitor",
    },

    # ── 趋势/行业类 ──
    "trending-now": {
        "name": "实时热搜",
        "name_en": "Trending Now",
        "description": "拉取指定平台当前热搜/趋势榜单",
        "required": ["platform"],
        "category": "trending",
    },
    "industry-trends": {
        "name": "行业趋势",
        "name_en": "Industry Trends",
        "description": "搜索行业关键词 + 拉热搜，交叉分析行业趋势",
        "required": ["keyword", "platform"],
        "category": "trending",
    },

    # ── 特殊场景 ──
    "local-business": {
        "name": "本地商家获客",
        "name_en": "Local Business Lead Gen",
        "description": "搜索本地化关键词（地名+品类），分析本地内容生态",
        "required": ["keyword", "platform"],
        "category": "special",
    },
    "cross-platform-presence": {
        "name": "跨平台账号诊断",
        "name_en": "Cross-Platform Presence",
        "description": "在多个平台搜索同一品牌/关键词，对比各平台声量",
        "required": ["keyword"],
        "category": "special",
    },
    "comment-insight": {
        "name": "评论洞察",
        "name_en": "Comment Insight",
        "description": "深度分析某个账号/内容的评论质量和用户反馈",
        "required": ["target", "platform"],
        "category": "special",
    },
    "investment-dd": {
        "name": "投资尽调",
        "name_en": "Investment Due Diligence",
        "description": "从社媒角度做投资尽调：品牌声量 + 用户口碑 + 增长趋势",
        "required": ["keyword"],
        "category": "special",
    },
}


# ── Scenario Runner ──────────────────────────────────────────────

class ScenarioRunner(WorkflowRunner):
    """Execute a named scenario by composing base workflow steps."""

    NAME = "scenario"

    def __init__(self, api_key: str, platform: str = "xiaohongshu",
                 error_policy: str = "continue", scenario_name: str = ""):
        self.scenario_name = scenario_name
        self.scenario_config = SCENARIOS.get(scenario_name, {})
        # For monitor/cross-platform scenarios, platform might not be needed
        super().__init__(api_key, platform, error_policy)

    def run(self, **kwargs) -> WorkflowResult:
        """Override to set NAME dynamically."""
        self.NAME = self.scenario_name
        return super().run(**kwargs)

    def _execute(self, **kwargs) -> dict:
        cat = self.scenario_config.get("category", "")
        scenario = self.scenario_name
        target = kwargs.get("target", "")
        targets = kwargs.get("targets", [])
        keyword = kwargs.get("keyword", "")
        platforms = kwargs.get("platforms", ["douyin", "xiaohongshu", "bilibili"])
        limit = kwargs.get("limit", 20)

        label = self.scenario_config.get("name", scenario)
        self._progress(f"🎯 场景: {label}")

        # Route to appropriate handler
        if scenario == "account-pro":
            return self._run_pro_scenario(target, limit)
        elif scenario in ("account-deepdive", "growth-diagnosis", "content-matrix"):
            return self._run_account_scenario(scenario, target, limit)
        elif scenario in ("competitor-compare", "kol-comparison"):
            return self._run_compare_scenario(scenario, targets, limit)
        elif scenario == "niche-deepdive":
            return self._run_niche_deepdive(target, kwargs.get("competitors", []),
                                            kwargs.get("niche_keyword", ""), limit)
        elif scenario in ("kol-audit", "kol-fraud-check"):
            return self._run_audit_scenario(scenario, target, limit)
        elif scenario in ("viral-reverse", "content-ideas", "ad-creative-mining", "niche-scan"):
            return self._run_scout_scenario(scenario, keyword, limit)
        elif scenario in ("brand-monitor", "crisis-alert", "new-product-watch",
                          "cross-platform-presence", "investment-dd"):
            return self._run_monitor_scenario(scenario, keyword, platforms)
        elif scenario == "trending-now":
            return self._run_trending_scenario()
        elif scenario == "industry-trends":
            return self._run_industry_trends(keyword, limit)
        elif scenario == "local-business":
            return self._run_scout_scenario(scenario, keyword, limit)
        elif scenario == "comment-insight":
            return self._run_comment_insight(target, limit)
        else:
            return {"error": f"Unknown scenario: {scenario}"}

    # ── Account scenarios ────────────────────────────────────────

    def _run_pro_scenario(self, target: str, limit: int) -> dict:
        """Run Pro account analysis using ProAnalyzeWorkflow."""
        from .pro import ProAnalyzeWorkflow
        runner = ProAnalyzeWorkflow(api_key=self.api_key, platform=self.platform)
        runner.adapter = self.adapter
        runner._safe_call = self._safe_call
        runner._progress = self._progress
        return runner._execute(target=target, limit=limit)

    def _run_account_scenario(self, scenario: str, target: str, limit: int) -> dict:
        # Get user info
        self._progress("Getting user profile...")
        user_data = self._safe_call("get_user", self.adapter.get_user, target)
        user_metrics = extract_user_metrics(user_data, self.platform)

        # Get posts
        self._progress("Getting posts...")
        posts_data = self._safe_call("get_posts", self.adapter.get_posts, target, limit=limit)
        post_ids = extract_post_ids(posts_data, self.platform)
        self._progress(f"Found {len(post_ids)} posts")

        # Get details
        post_metrics_list = []
        batch = min(len(post_ids), 20)
        for i, pid in enumerate(post_ids[:batch]):
            self._progress(f"Fetching post {i+1}/{batch}...")
            detail = self._safe_call(f"info_{i}", self.adapter.get_info, pid)
            pm = extract_post_metrics(detail, self.platform)
            if pm:
                post_metrics_list.append(pm)

        metrics = compute_account_metrics(user_metrics, post_metrics_list)

        # Scenario-specific analysis
        analysis = {"scenario": scenario, "user": user_metrics, "posts": post_metrics_list, "metrics": metrics}

        if scenario == "growth-diagnosis":
            analysis["diagnosis"] = self._diagnose_growth(user_metrics, metrics)
        elif scenario == "content-matrix":
            analysis["matrix"] = self._analyze_content_matrix(post_metrics_list)

        return analysis

    def _diagnose_growth(self, user: dict, metrics: dict) -> dict:
        followers = user.get("followers", 0)
        er = metrics.get("engagement_rate", 0)
        top_posts = metrics.get("top_posts", [])
        avg_likes = metrics.get("avg_likes", 0)

        issues = []
        strengths = []

        # Check engagement rate
        if er >= 0.05:
            strengths.append(f"互动率优秀 ({er:.2%})，粉丝粘性高")
        elif er >= 0.02:
            strengths.append(f"互动率正常 ({er:.2%})")
        else:
            issues.append(f"互动率偏低 ({er:.2%})，可能粉丝不活跃或内容不够吸引")

        # Check top-heavy distribution
        if top_posts and avg_likes > 0:
            top_ratio = top_posts[0].get("likes", 0) / (avg_likes * len(metrics.get("top_posts", [1])))
            if top_ratio > 5:
                issues.append("流量过度依赖单条爆款，稳定性差")
            else:
                strengths.append("内容互动分布均匀，不依赖爆款")

        # Collect rate
        clr = metrics.get("collect_like_ratio", 0)
        if clr > 0.2:
            strengths.append(f"收藏率高 ({clr:.0%})，内容有长期价值")
        elif clr < 0.05:
            issues.append(f"收藏率低 ({clr:.0%})，内容缺乏保存价值")

        return {"issues": issues, "strengths": strengths}

    def _analyze_content_matrix(self, posts: list[dict]) -> dict:
        if not posts:
            return {}

        types = {}
        for p in posts:
            t = p.get("type", "unknown")
            if t not in types:
                types[t] = {"count": 0, "total_likes": 0, "total_collects": 0}
            types[t]["count"] += 1
            types[t]["total_likes"] += p.get("likes", 0)
            types[t]["total_collects"] += p.get("collects", 0)

        for t, d in types.items():
            d["avg_likes"] = round(d["total_likes"] / d["count"]) if d["count"] > 0 else 0
            d["avg_collects"] = round(d["total_collects"] / d["count"]) if d["count"] > 0 else 0

        return {"content_types": types}

    # ── Compare scenarios ────────────────────────────────────────

    def _run_compare_scenario(self, scenario: str, targets: list[str], limit: int) -> dict:
        accounts = []
        for t in targets:
            self._progress(f"── Analyzing {t} ──")
            data = self._run_account_scenario("account-deepdive", t, limit)
            accounts.append(data)

        # Cross compare
        rows = []
        for a in accounts:
            u = a.get("user", {})
            m = a.get("metrics", {})
            rows.append({
                "nickname": u.get("nickname", "?"),
                "followers": u.get("followers", 0),
                "avg_likes": m.get("avg_likes", 0),
                "avg_comments": m.get("avg_comments", 0),
                "engagement_rate": m.get("engagement_rate", 0),
                "collect_like_ratio": m.get("collect_like_ratio", 0),
            })

        ranked = sorted(rows, key=lambda r: r["engagement_rate"], reverse=True)

        return {
            "scenario": scenario,
            "accounts": accounts,
            "comparison": {"rows": rows, "ranking": [r["nickname"] for r in ranked]},
        }

    # ── Niche deep-dive (5 acct × full notes × moat scoring) ──

    def _run_niche_deepdive(self, target: str, competitors: list,
                             niche_keyword: str, limit: int = 100) -> dict:
        """Full 4-phase pipeline. See references/niche-deepdive-playbook.md.

        Phase 1: locate main + identify 4 same-niche competitors (auto if not given)
        Phase 2: pull full notes for all 5 accounts
        Phase 3: compute 11-dim matrix + 10-dim moat scores (5 accts)
        Phase 4: sample Top 1 note comments per account for buy-intent audit

        Web Search (Phase 4 industry context) is NOT executed here — it requires the
        host LLM environment. The output JSON includes a "web_search_queries" hint
        the host can run, then write a final report.
        """
        self._progress(f"📊 Niche Deep-Dive: target={target}, competitors={len(competitors)}")
        results = {"main": None, "competitors": [], "web_search_queries": [],
                    "slide_recommendations": [], "meta": {}}

        # ── Phase 1: identify competitors if not provided ──
        if not competitors:
            if not niche_keyword:
                return {"error": "Provide either 'competitors' list or 'niche_keyword' for auto-discovery"}
            self._progress(f"Discovering competitors for niche: {niche_keyword}")
            search_data = self._safe_call("search", self.adapter.search, niche_keyword)
            uid_freq = {}
            items = (search_data.get("data", {}).get("data", {}).get("items", []) or
                     search_data.get("data", {}).get("items", []) or [])
            for it in items[:50]:
                note = it.get("note") or it.get("note_card") or it
                if not isinstance(note, dict): continue
                u = note.get("user", {}) or {}
                uid = u.get("userid") or u.get("user_id")
                if uid and uid != target:
                    uid_freq[uid] = uid_freq.get(uid, 0) + 1
            top_uids = sorted(uid_freq, key=lambda k: -uid_freq[k])[:4]
            competitors = top_uids
            self._progress(f"Auto-discovered: {len(competitors)} competitors")

        all_targets = [target] + competitors[:4]

        # ── Phase 2: pull full data for each ──
        for idx, uid in enumerate(all_targets):
            label = "main" if idx == 0 else f"comp_{idx}"
            self._progress(f"[{idx+1}/{len(all_targets)}] Pulling {label} ({uid})...")
            user_data = self._safe_call(f"get_user_{idx}", self.adapter.get_user, uid)
            user_metrics = extract_user_metrics(user_data, self.platform)

            posts_data = self._safe_call(f"get_posts_{idx}", self.adapter.get_posts, uid, limit=limit)
            from .metrics import extract_post_metrics_from_listitem, extract_post_listitems
            list_items = extract_post_listitems(posts_data, self.platform)[:limit]
            post_metrics_list = []
            for item in list_items:
                pm = extract_post_metrics_from_listitem(item, self.platform)
                if pm:
                    post_metrics_list.append(pm)

            account_metrics = compute_account_metrics(user_metrics, post_metrics_list)

            # Top 1 comments (for buy-intent audit)
            top_comments = []
            if post_metrics_list:
                top_post = max(post_metrics_list,
                               key=lambda p: p.get("likes", 0) + p.get("comments", 0) + p.get("collects", 0))
                top_id = top_post.get("id", "")
                if top_id:
                    c_data = self._safe_call(f"comments_{idx}", self.adapter.get_comments, top_id)
                    inner = c_data.get("data", {}).get("data", c_data.get("data", {}))
                    cs = inner.get("comments", [])[:30] if isinstance(inner, dict) else []
                    top_comments = [{"author": c.get("user", {}).get("nickname", ""),
                                     "content": (c.get("content") or "")[:200],
                                     "likes": c.get("like_count", 0),
                                     "sub_count": c.get("sub_comment_count", 0)}
                                     for c in cs]
                    quality = assess_comment_quality(c_data)
                else:
                    quality = {}
            else:
                quality = {}

            entry = {
                "uid": uid,
                "label": label,
                "user": user_metrics,
                "post_count": len(post_metrics_list),
                "posts": post_metrics_list,
                "metrics": account_metrics,
                "top_comments_sample": top_comments,
                "comment_quality": quality,
            }
            if idx == 0:
                results["main"] = entry
            else:
                results["competitors"].append(entry)
            time.sleep(0.4)  # gentle pacing

        # ── Phase 3: 11-dim matrix + 10-dim moat scores ──
        all_entries = [results["main"]] + results["competitors"]
        results["matrix_11dim"] = self._build_matrix_11dim(all_entries)
        results["moat_scores"] = self._compute_moat_scores(all_entries)

        # Hint Web Search queries for the host LLM (Phase 4)
        nk = niche_keyword or "该赛道"
        results["web_search_queries"] = [
            f"{self.platform} {nk} 限流 严打 政策 2025 2026",
            f"{nk} 头部账号 {self.platform} 2026",
            f"{self.platform} 算法更新 2026",
        ]

        # Slide recommendations (mapping to canonical structures)
        results["slide_recommendations"] = [
            {"page": 1, "template": "custom-cover", "role": "hero"},
            {"page": 2, "template": "bento-grid-dense", "role": "5-findings"},
            {"page": 3, "template": "08-comparison-matrix-dense", "role": "11-dim-matrix"},
            {"page": 4, "template": "02-hub-spoke", "role": "blue-oceans"},
            {"page": 5, "template": "16-story-mountain", "role": "twist-narrative"},
            {"page": 6, "template": "21-binary-comparison", "role": "hero-vs-threat"},
            {"page": 7, "template": "05-radar-chart-decagon", "role": "moat-scoring"},
            {"page": 8, "template": "20-comparison-table", "role": "comment-quality"},
            {"page": 9, "template": "bento-2x2", "role": "30day-actions"},
            {"page": 10, "template": "06-dashboard", "role": "kpi-projection"},
            {"page": 11, "template": "custom-closing", "role": "call-to-action"},
        ]

        results["meta"] = {
            "playbook": "niche-deepdive",
            "playbook_doc": "references/niche-deepdive-playbook.md",
            "phase": "data-collected",
            "next_steps": [
                "1. Run web_search_queries via host environment",
                "2. Write Markdown report (use playbook templates)",
                "3. Convert to Word: docforge -p proposal --eisvogel --font 'PingFang SC' --titlepage --toc <md>",
                "4. Build 10-page SVG deck via next-slide-impeccable using slide_recommendations",
            ]
        }

        return results

    def _build_matrix_11dim(self, entries: list) -> list:
        """Build 11-dimension comparative matrix."""
        return [
            {"dim": "粉丝数", "values": [e["user"].get("followers", 0) for e in entries]},
            {"dim": "笔记数", "values": [e["post_count"] for e in entries]},
            {"dim": "累计互动",
             "values": [int(e["metrics"].get("avg_likes", 0) * e["post_count"] +
                            e["metrics"].get("avg_comments", 0) * e["post_count"] +
                            e["metrics"].get("avg_collects", 0) * e["post_count"]) for e in entries]},
            {"dim": "单笔记均互动",
             "values": [round(e["metrics"].get("avg_likes", 0) +
                              e["metrics"].get("avg_comments", 0) +
                              e["metrics"].get("avg_collects", 0), 1) for e in entries]},
            {"dim": "互动率",
             "values": [round(e["metrics"].get("engagement_rate", 0) * 100, 2) for e in entries]},
            {"dim": "视频比例",
             "values": [round(e["metrics"].get("content_type_distribution", {}).get("video", 0) /
                              max(e["post_count"], 1) * 100, 1) for e in entries]},
            {"dim": "Top3 占比",
             "values": [self._top3_pct(e) for e in entries]},
            {"dim": "评论商业价值",
             "values": [e.get("comment_quality", {}).get("buy_intent_score", "-") for e in entries]},
            {"dim": "平台认证",
             "values": [e["user"].get("verify_content", "") or "无" for e in entries]},
        ]

    @staticmethod
    def _top3_pct(entry: dict) -> float:
        posts = entry.get("posts", [])
        if not posts:
            return 0.0
        engs = sorted([p.get("likes", 0) + p.get("comments", 0) + p.get("collects", 0) for p in posts], reverse=True)
        total = sum(engs)
        if total == 0:
            return 0.0
        return round(sum(engs[:3]) / total * 100, 1)

    def _compute_moat_scores(self, entries: list) -> dict:
        """Score each account 1-5 across 10 dimensions, then sum."""
        # For each dim, rank accounts and assign scores
        # Higher rank = higher score
        dims = ["fans", "engagement_rate", "max_eng", "recent_60d_count",
                "avg_eng", "video_pct", "diff_topics_count", "buy_intent",
                "verified", "recent_60d_growth"]
        scores = {e["label"]: {d: 0 for d in dims} for e in entries}

        # Extract raw values per dim
        def raw(e, d):
            if d == "fans": return e["user"].get("followers", 0)
            if d == "engagement_rate": return e["metrics"].get("engagement_rate", 0)
            if d == "max_eng":
                p = e.get("posts", [])
                if not p: return 0
                return max((x.get("likes", 0) + x.get("comments", 0) + x.get("collects", 0)) for x in p)
            if d == "recent_60d_count": return e.get("metrics", {}).get("recent_60d_count", e["post_count"])
            if d == "avg_eng":
                m = e.get("metrics", {})
                return m.get("avg_likes", 0) + m.get("avg_comments", 0) + m.get("avg_collects", 0)
            if d == "video_pct":
                p = e.get("posts", [])
                if not p: return 0
                return sum(1 for x in p if x.get("type") == "video") / len(p)
            if d == "diff_topics_count": return 0  # heuristic — would need topic classifier
            if d == "buy_intent": return e.get("comment_quality", {}).get("buy_intent_score", 0)
            if d == "verified": return 1 if e["user"].get("verify_content") else 0
            if d == "recent_60d_growth": return e.get("metrics", {}).get("recent_growth_pct", 0)
            return 0

        # For each dimension, rank and assign 1-5
        for d in dims:
            vals = [(e["label"], raw(e, d)) for e in entries]
            sorted_vals = sorted(vals, key=lambda x: -x[1])
            n = len(sorted_vals)
            for rank, (label, _) in enumerate(sorted_vals):
                # Top: 5, Bottom: 1, linear scale
                score = max(1, min(5, round(5 - rank * 4 / max(n - 1, 1))))
                scores[label][d] = score

        # Total
        for label in scores:
            scores[label]["total"] = sum(v for k, v in scores[label].items() if k != "total")

        return scores

    # ── Audit scenarios ──────────────────────────────────────────

    def _run_audit_scenario(self, scenario: str, target: str, limit: int) -> dict:
        # Base analysis
        analysis = self._run_account_scenario("account-deepdive", target, limit)

        # Sample comments
        post_ids = extract_post_ids(
            self._safe_call("get_posts_for_comments", self.adapter.get_posts, target, limit=10),
            self.platform)

        comment_batches = []
        sample_count = 3 if scenario == "kol-audit" else 5  # fraud check samples more
        for i, pid in enumerate(post_ids[:sample_count]):
            self._progress(f"Sampling comments {i+1}/{sample_count}...")
            c = self._safe_call(f"comments_{i}", self.adapter.get_comments, pid, limit=100)
            if c:
                comment_batches.append(c)

        cq = assess_comment_quality(comment_batches)

        # Verdict
        metrics = analysis.get("metrics", {})
        user = analysis.get("user", {})
        verdict = self._generate_verdict(user, metrics, cq, scenario)

        return {"scenario": scenario, "analysis": analysis, "comment_quality": cq, "verdict": verdict}

    def _generate_verdict(self, user, metrics, cq, scenario):
        er = metrics.get("engagement_rate", 0)
        quality = cq.get("quality", "unknown")
        short_ratio = cq.get("short_comment_ratio", 0)
        score = 0
        reasons = []

        if er >= 0.05:
            score += 3; reasons.append(f"互动率优秀 ({er:.2%})")
        elif er >= 0.02:
            score += 2; reasons.append(f"互动率正常 ({er:.2%})")
        elif er >= 0.01:
            score += 1; reasons.append(f"互动率偏低 ({er:.2%})")
        else:
            reasons.append(f"互动率很低 ({er:.2%})")

        if quality == "high":
            score += 2; reasons.append("评论质量高")
        elif quality == "medium":
            score += 1; reasons.append("评论质量一般")
        elif quality == "low":
            reasons.append(f"评论质量差，短评占比 {short_ratio:.0%}")
            if scenario == "kol-fraud-check":
                reasons.append("⚠️ 疑似刷量")

        clr = metrics.get("collect_like_ratio", 0)
        if clr > 0.2:
            score += 1; reasons.append(f"收藏率高 ({clr:.0%})")

        if score >= 5:
            verdict, label = "INVEST", "推荐投放"
        elif score >= 3:
            verdict, label = "NEGOTIATE", "可考虑，建议压价"
        else:
            verdict, label = "PASS", "不推荐"

        return {"verdict": verdict, "label": label, "score": score, "max_score": 6, "reasons": reasons}

    # ── Scout scenarios ──────────────────────────────────────────

    def _run_scout_scenario(self, scenario: str, keyword: str, limit: int) -> dict:
        self._progress(f"Searching '{keyword}'...")
        search_data = self._safe_call("search", self.adapter.search, keyword, limit=limit)

        # Extract IDs
        top_ids = self._extract_search_ids(search_data)
        self._progress(f"Found {len(top_ids)} results")

        # Details
        detail_limit = min(len(top_ids), 10)
        posts = []
        for i, pid in enumerate(top_ids[:detail_limit]):
            self._progress(f"Detail {i+1}/{detail_limit}...")
            d = self._safe_call(f"detail_{i}", self.adapter.get_info, pid)
            pm = extract_post_metrics(d, self.platform)
            if pm:
                posts.append(pm)

        # Pattern analysis
        sorted_posts = sorted(posts, key=lambda p: p.get("likes", 0), reverse=True)
        likes = [p.get("likes", 0) for p in posts]
        avg_likes = sum(likes) / len(likes) if likes else 0
        max_likes = max(likes) if likes else 0

        types = {}
        for p in posts:
            t = p.get("type", "unknown")
            types[t] = types.get(t, 0) + 1

        return {
            "scenario": scenario,
            "keyword": keyword,
            "total_results": len(top_ids),
            "posts": sorted_posts,
            "patterns": {
                "avg_likes": round(avg_likes),
                "max_likes": max_likes,
                "content_types": types,
                "analyzed": len(posts),
            },
        }

    def _extract_search_ids(self, search_data: dict) -> list[str]:
        if not search_data:
            return []
        data = search_data.get("data", search_data)
        if isinstance(data, dict) and "data" in data:
            data = data["data"]
        if self.platform == "xiaohongshu":
            return [i.get("note", {}).get("id", "") for i in data.get("items", []) if i.get("note", {}).get("id")]
        elif self.platform in ("douyin", "tiktok"):
            items = data.get("data", data.get("aweme_list", []))
            if isinstance(items, list):
                return [str(i.get("aweme_id", "")) for i in items if i.get("aweme_id")]
        elif self.platform == "bilibili":
            return [str(r.get("bvid", "")) for r in data.get("result", []) if r.get("bvid")]
        return []

    # ── Monitor scenarios ────────────────────────────────────────

    def _run_monitor_scenario(self, scenario: str, keyword: str, platforms: list[str]) -> dict:
        self._progress(f"Monitoring '{keyword}' across {len(platforms)} platforms...")

        results = {}
        for plat in platforms:
            self._progress(f"── {plat} ──")
            try:
                adapter = self._get_adapter(plat, self.api_key)
            except ValueError:
                self._errors.append({"step": f"init_{plat}", "error": f"Platform {plat} not available"})
                continue

            search = self._safe_call(f"search_{plat}", adapter.search, keyword)
            count = 0
            if search:
                d = search.get("data", search)
                if isinstance(d, dict) and "data" in d:
                    d = d["data"]
                items = d.get("items", d.get("result", d.get("aweme_list", [])))
                count = len(items) if isinstance(items, list) else 0

            trending_match = False
            try:
                trending = self._safe_call(f"trending_{plat}", adapter.get_trending)
                if trending:
                    import json as _json
                    trending_match = keyword.lower() in _json.dumps(trending, ensure_ascii=False).lower()
            except Exception:
                pass

            results[plat] = {"search_results": count, "trending_match": trending_match}

        total = sum(r["search_results"] for r in results.values())
        trending_on = [p for p, r in results.items() if r["trending_match"]]

        return {
            "scenario": scenario,
            "keyword": keyword,
            "platforms": results,
            "summary": {"total_results": total, "trending_on": trending_on},
        }

    # ── Trending scenario ────────────────────────────────────────

    def _run_trending_scenario(self) -> dict:
        self._progress(f"Fetching trending on {self.platform}...")
        data = self._safe_call("trending", self.adapter.get_trending)
        return {"scenario": "trending-now", "platform": self.platform, "raw": data}

    # ── Industry trends ──────────────────────────────────────────

    def _run_industry_trends(self, keyword: str, limit: int) -> dict:
        # Trending + scout
        self._progress("Fetching trending...")
        trending = self._safe_call("trending", self.adapter.get_trending)

        self._progress(f"Searching '{keyword}'...")
        scout = self._run_scout_scenario("industry-trends", keyword, limit)

        return {"scenario": "industry-trends", "trending": trending, "scout": scout}

    # ── Comment insight ──────────────────────────────────────────

    def _run_comment_insight(self, target: str, limit: int) -> dict:
        # Get posts
        self._progress("Getting posts...")
        posts_data = self._safe_call("get_posts", self.adapter.get_posts, target, limit=limit)
        post_ids = extract_post_ids(posts_data, self.platform)

        # Sample comments from up to 5 posts
        batches = []
        sample = min(len(post_ids), 5)
        for i, pid in enumerate(post_ids[:sample]):
            self._progress(f"Fetching comments {i+1}/{sample}...")
            c = self._safe_call(f"comments_{i}", self.adapter.get_comments, pid, limit=100)
            if c:
                batches.append(c)

        cq = assess_comment_quality(batches)
        return {"scenario": "comment-insight", "post_count": len(post_ids), "sampled": sample, "quality": cq}

    # ── Formatting ───────────────────────────────────────────────

    def _format_markdown(self, data: dict) -> str:
        scenario = data.get("scenario", self.scenario_name)
        config = SCENARIOS.get(scenario, {})
        name = config.get("name", scenario)
        name_en = config.get("name_en", "")

        lines = [f"## 🎯 {name} ({name_en})", ""]

        # Route to appropriate formatter
        cat = config.get("category", "")

        if scenario == "account-pro":
            from .pro import ProAnalyzeWorkflow
            pro = ProAnalyzeWorkflow(api_key=self.api_key, platform=self.platform)
            return pro._format_markdown(data)
        if cat == "account":
            lines.extend(self._fmt_account(data))
        elif cat == "competition":
            lines.extend(self._fmt_compare(data))
        elif cat == "kol":
            lines.extend(self._fmt_audit(data))
        elif cat == "content" or scenario in ("local-business", "industry-trends"):
            lines.extend(self._fmt_scout(data))
        elif cat == "monitor" or scenario in ("cross-platform-presence", "investment-dd"):
            lines.extend(self._fmt_monitor(data))
        elif cat == "trending":
            lines.append("*Raw trending data returned as JSON*")
        elif scenario == "comment-insight":
            lines.extend(self._fmt_comment_insight(data))
        else:
            lines.append(json.dumps(data, ensure_ascii=False, indent=2)[:500])

        return "\n".join(lines)

    def _fmt_account(self, data: dict) -> list[str]:
        user = data.get("user", {})
        m = data.get("metrics", {})
        lines = [
            "### 账号概览",
            f"- 昵称: {user.get('nickname', '?')}",
            f"- 粉丝: {compact_number(user.get('followers', 0))}",
            f"- 平均点赞: {compact_number(m.get('avg_likes', 0))}",
            f"- 互动率: {m.get('engagement_rate', 0):.2%}",
            f"- 收藏/点赞比: {m.get('collect_like_ratio', 0):.0%}",
            "",
        ]
        # Top posts
        top = m.get("top_posts", [])
        if top:
            lines.append("### Top 内容")
            lines.append("| # | 标题 | 赞 | 评 | 藏 |")
            lines.append("|---|------|---:|---:|---:|")
            for i, p in enumerate(top[:5], 1):
                lines.append(f"| {i} | {p.get('title','')[:25]} | {p.get('likes',0)} | {p.get('comments',0)} | {p.get('collects',0)} |")
            lines.append("")

        # Diagnosis
        diag = data.get("diagnosis", {})
        if diag:
            if diag.get("strengths"):
                lines.append("### 优势")
                for s in diag["strengths"]:
                    lines.append(f"- ✓ {s}")
            if diag.get("issues"):
                lines.append("### 问题")
                for s in diag["issues"]:
                    lines.append(f"- ✗ {s}")
            lines.append("")

        # Matrix
        matrix = data.get("matrix", {})
        if matrix.get("content_types"):
            lines.append("### 内容矩阵")
            lines.append("| 类型 | 数量 | 均赞 | 均藏 |")
            lines.append("|------|-----:|-----:|-----:|")
            for t, d in matrix["content_types"].items():
                lines.append(f"| {t} | {d['count']} | {d['avg_likes']} | {d['avg_collects']} |")
            lines.append("")

        return lines

    def _fmt_compare(self, data: dict) -> list[str]:
        comp = data.get("comparison", {})
        rows = comp.get("rows", [])
        if not rows:
            return ["*No comparison data*"]

        lines = ["### 对比表"]
        header = "| 指标 | " + " | ".join(r["nickname"] for r in rows) + " |"
        sep = "|------|" + "|".join(["------:" for _ in rows]) + "|"
        lines.extend([header, sep])

        fields = [
            ("粉丝", "followers", lambda v: compact_number(v)),
            ("均赞", "avg_likes", lambda v: compact_number(v)),
            ("互动率", "engagement_rate", lambda v: f"{v:.2%}"),
            ("藏赞比", "collect_like_ratio", lambda v: f"{v:.0%}"),
        ]
        for label, key, fmt in fields:
            vals = " | ".join(fmt(r.get(key, 0)) for r in rows)
            lines.append(f"| {label} | {vals} |")

        ranking = comp.get("ranking", [])
        if ranking:
            lines.extend(["", f"### 互动率排名: {' > '.join(ranking)}"])
        return lines

    def _fmt_audit(self, data: dict) -> list[str]:
        verdict = data.get("verdict", {})
        cq = data.get("comment_quality", {})
        lines = [
            f"### 结论: {verdict.get('verdict', '?')} — {verdict.get('label', '')}",
            f"评分: {verdict.get('score', 0)}/{verdict.get('max_score', 6)}",
            "",
            "### 判断依据",
        ]
        for r in verdict.get("reasons", []):
            lines.append(f"- {r}")
        lines.extend([
            "",
            f"### 评论质量: {cq.get('quality', '?')}",
            f"- 总评论: {cq.get('total_comments', 0)}",
            f"- 均长度: {cq.get('avg_length', 0):.0f} 字",
            f"- 短评占比: {cq.get('short_comment_ratio', 0):.0%}",
        ])
        return lines

    def _fmt_scout(self, data: dict) -> list[str]:
        # Handle nested scout data from industry-trends
        scout = data.get("scout", data)
        patterns = scout.get("patterns", {})
        posts = scout.get("posts", [])

        lines = [
            f"- 关键词: {scout.get('keyword', data.get('keyword', '?'))}",
            f"- 搜索结果: {scout.get('total_results', '?')}",
            f"- 均赞: {compact_number(patterns.get('avg_likes', 0))}",
            f"- 最高赞: {compact_number(patterns.get('max_likes', 0))}",
            "",
        ]
        if posts:
            lines.append("### Top 内容")
            lines.append("| # | 标题 | 赞 | 评 | 藏 |")
            lines.append("|---|------|---:|---:|---:|")
            for i, p in enumerate(posts[:10], 1):
                lines.append(f"| {i} | {p.get('title','')[:25]} | {p.get('likes',0)} | {p.get('comments',0)} | {p.get('collects',0)} |")
        return lines

    def _fmt_monitor(self, data: dict) -> list[str]:
        platforms = data.get("platforms", {})
        summary = data.get("summary", {})
        lines = [
            f"- 关键词: {data.get('keyword', '?')}",
            f"- 总结果: {summary.get('total_results', 0)}",
            f"- 上热搜: {', '.join(summary.get('trending_on', [])) or '无'}",
            "",
            "### 平台详情",
            "| 平台 | 结果数 | 热搜 |",
            "|------|------:|:----:|",
        ]
        for p, r in platforms.items():
            tr = "✓" if r.get("trending_match") else "-"
            lines.append(f"| {p} | {r.get('search_results', 0)} | {tr} |")
        return lines

    def _fmt_comment_insight(self, data: dict) -> list[str]:
        cq = data.get("quality", {})
        return [
            f"- 笔记总数: {data.get('post_count', 0)}",
            f"- 采样数: {data.get('sampled', 0)}",
            f"- 总评论: {cq.get('total_comments', 0)}",
            f"- 均长度: {cq.get('avg_length', 0):.0f} 字",
            f"- 短评占比: {cq.get('short_comment_ratio', 0):.0%}",
            f"- 质量评级: {cq.get('quality', '?')}",
        ]

    def _build_blueprint_spec(self, data: dict) -> dict:
        scenario = data.get("scenario", self.scenario_name)
        config = SCENARIOS.get(scenario, {})
        return {
            "type": f"scenario-{scenario}",
            "title": f"{config.get('name', scenario)} — {config.get('name_en', '')}",
            "data": data,
            "metadata": {"platform": self.platform, "workflow": "scenario", "scenario": scenario},
        }


def list_scenarios() -> str:
    """Format all scenarios as a readable list."""
    lines = ["📋 可用场景 (20 个)", ""]
    cats = {}
    for key, s in SCENARIOS.items():
        cat = s.get("category", "other")
        if cat not in cats:
            cats[cat] = []
        cats[cat].append((key, s))

    cat_labels = {
        "account": "📊 账号分析", "competition": "⚔️ 竞品对比", "kol": "🔍 达人评估",
        "content": "📝 内容探查", "monitor": "🌐 舆情监测", "trending": "🔥 趋势分析",
        "special": "⭐ 特殊场景",
    }

    for cat, items in cats.items():
        lines.append(f"### {cat_labels.get(cat, cat)}")
        for key, s in items:
            req = ", ".join(s.get("required", []))
            lines.append(f"  `{key}` — {s['name']} ({s['name_en']})")
            lines.append(f"    {s['description']}")
            lines.append(f"    需要: {req}")
            lines.append("")

    return "\n".join(lines)
