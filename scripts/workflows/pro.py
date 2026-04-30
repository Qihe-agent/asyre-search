"""Account Pro analysis — orchestrates advanced metrics into a rich report.

Adds on top of basic 'analyze':
- Time-series trend (rising/stable/declining) with segment comparisons
- Posting cadence (frequency, gaps, monthly distribution)
- Title pattern mining (TF-IDF style: top 25% vs bottom 25%)
- Comment intent classification (price/discuss/praise/complaint)
- Health score (0-100, 6 dimensions)
- Rule-based diagnosis (P0/P1 prioritized recommendations)
"""

from __future__ import annotations

from .base import WorkflowRunner
from .metrics import (
    extract_user_metrics, extract_post_ids, extract_post_metrics,
    compute_account_metrics, compact_number,
)
from . import metrics_pro as mp


class ProAnalyzeWorkflow(WorkflowRunner):
    NAME = "analyze-pro"
    DESCRIPTION = "Account Pro analysis: trend + cadence + title patterns + comment intent + health score + diagnosis"

    def _execute(self, target: str, limit: int = 30, comment_sample: int = 5) -> dict:
        self._progress(f"📊 Pro analysis on {target} ({self.platform})...")

        # Step 1: User
        self._progress("Getting user profile...")
        user_data = self._safe_call("get_user", self.adapter.get_user, target)
        user_metrics = extract_user_metrics(user_data, self.platform)

        # Step 2: Posts list
        self._progress("Getting posts list...")
        posts_data = self._safe_call("get_posts", self.adapter.get_posts, target, limit=limit)
        post_ids = extract_post_ids(posts_data, self.platform)
        self._progress(f"Found {len(post_ids)} posts")

        # Step 3: Post details
        post_metrics_list: list[dict] = []
        batch_size = min(len(post_ids), limit)
        for i, pid in enumerate(post_ids[:batch_size]):
            self._progress(f"Fetching post detail {i+1}/{batch_size}...")
            detail = self._safe_call(f"get_info_{i}", self.adapter.get_info, pid)
            pm = extract_post_metrics(detail, self.platform)
            if pm:
                # Carry the platform id through (needed for timestamp decoding on XHS)
                pm.setdefault("note_id", pid)
                post_metrics_list.append(pm)

        # Step 4: Comments sample (for top N posts)
        self._progress(f"Sampling comments on top {comment_sample} posts...")
        sorted_by_likes = sorted(post_metrics_list, key=lambda p: -p.get("likes", 0))
        comment_lists: list[list[dict]] = []
        for i, p in enumerate(sorted_by_likes[:comment_sample]):
            pid = p.get("note_id") or p.get("id")
            self._progress(f"Comments {i+1}/{comment_sample} ({pid[:10]}...)")
            cdata = self._safe_call(f"get_comments_{i}", self.adapter.get_comments, pid)
            if cdata:
                inner = cdata.get("data", {})
                if isinstance(inner, dict) and "data" in inner:
                    inner = inner["data"]
                comments = inner.get("comments") if isinstance(inner, dict) else []
                comment_lists.append(comments or [])

        # Step 5: Compute everything
        account_metrics = compute_account_metrics(user_metrics, post_metrics_list)
        trend = mp.trend_metrics(post_metrics_list, self.platform)
        cadence = mp.cadence_metrics(post_metrics_list, self.platform)
        distribution = mp.distribution_metrics(post_metrics_list)
        title_patterns = mp.title_pattern_metrics(post_metrics_list)
        comment_quality = mp.comment_quality_metrics(comment_lists) if comment_lists else None
        score = mp.health_score(
            user_metrics, account_metrics, trend, cadence, distribution, comment_quality
        )
        diagnosis = mp.diagnose(
            user_metrics, account_metrics, trend, cadence, distribution,
            title_patterns, comment_quality, score,
        )

        return {
            "user": user_metrics,
            "post_count_fetched": len(post_ids),
            "posts_analyzed": len(post_metrics_list),
            "comments_sampled": sum(len(c) for c in comment_lists),
            "metrics": account_metrics,
            "trend": trend,
            "cadence": cadence,
            "distribution": distribution,
            "title_patterns": title_patterns,
            "comment_quality": comment_quality,
            "score": score,
            "diagnosis": diagnosis,
            "posts": post_metrics_list,
        }

    def _format_markdown(self, data: dict) -> str:
        user = data["user"]
        m = data["metrics"]
        trend = data["trend"]
        cadence = data["cadence"]
        dist = data["distribution"]
        tp = data["title_patterns"]
        cq = data.get("comment_quality") or {}
        score = data["score"]
        diag = data["diagnosis"]

        nickname = user.get("nickname", "Unknown")
        followers = compact_number(user.get("followers", 0))

        lines = [
            f"# 📊 Pro 账号分析: {nickname}",
            "",
            f"**平台**: {self.platform} ｜ **粉丝**: {followers} ｜ **分析笔记数**: {data['posts_analyzed']} ｜ **采样评论**: {data['comments_sampled']}",
            "",
            "---",
            "",
            f"## 🎯 综合健康度: **{score['overall']}/100 ({score['grade']})**",
            "",
            "| 维度 | 分数 | 权重 |",
            "|------|-----:|-----:|",
        ]
        for dim, s in score["by_dimension"].items():
            w = score["weights"].get(dim, 0)
            lines.append(f"| {self._dim_label(dim)} | {s} | {w:.0%} |")
        lines.append("")

        # Diagnosis / Findings
        lines += ["## 🚨 诊断结论", ""]
        if not diag:
            lines.append("_当前未发现需要立即处理的问题。_")
        else:
            for f in diag:
                lines.append(f"### [{f['priority']}] {f['title']} `{f['code']}`")
                lines.append(f"- **证据**: {f['evidence']}")
                lines.append(f"- **建议**: {f['action']}")
                lines.append("")

        # Trend
        lines += ["## 📈 互动趋势", ""]
        if trend.get("insufficient_data"):
            lines.append(f"_数据不足 (需 ≥ 4 篇带时间戳的笔记，当前 {trend.get('sample_size')})_")
        else:
            arrow = {"rising": "↗ 上升", "stable": "→ 平稳", "declining": "↘ 下滑", "unknown": "?"}[trend["direction"]]
            lines += [
                f"**方向**: {arrow}　**最近 5 篇 vs 早期半数 Δ**: {trend.get('delta_recent_vs_first_pct')}%",
                "",
                "| 时段 | 平均赞 |",
                "|------|------:|",
                f"| 前半段 ({trend['sample_size'] // 2} 篇) | {trend['avg_likes_first_half']} |",
                f"| 后半段 | {trend['avg_likes_second_half']} |",
                f"| 最近 5 篇 | **{trend['avg_likes_recent_5']}** |",
                f"| 整体 | {trend['avg_likes_overall']} |",
                f"| 斜率 (赞/天) | {trend['slope_likes_per_day']} |",
                "",
            ]

        # Cadence
        lines += ["## ⏱️ 发布节奏", ""]
        if cadence.get("insufficient_data"):
            lines.append("_数据不足_")
        else:
            lines += [
                f"- 跨度: {cadence['first_post_date']} → {cadence['last_post_date']} ({cadence['span_days']} 天)",
                f"- 频率: 平均每 **{cadence['avg_interval_days']} 天 1 篇** ({cadence['posts_per_week']}/周)",
                f"- 标准差: {cadence['stdev_interval_days']} 天　最长断更: {cadence['longest_gap_days']} 天",
                "",
                "**月度分布**:",
                "",
                "| 月份 | 篇数 |",
                "|------|----:|",
            ]
            for month, n in sorted(cadence["monthly_distribution"].items()):
                lines.append(f"| {month} | {n} |")
            lines.append("")

        # Distribution
        lines += [
            "## 📊 互动分布",
            "",
            f"- 最高: {dist.get('max')}　Top 25% 门槛: {dist.get('viral_threshold')}",
            f"- 中位数: {dist.get('median')}　最低: {dist.get('min')}",
            f"- 标准差: {dist.get('stdev')}",
            f"- **Top 10% 笔记贡献了 {dist.get('top_decile_share_pct')}% 的总互动**",
            "",
        ]

        # Title patterns
        lines += ["## 🔑 爆款标题关键词 (TF-IDF Lift)", ""]
        if tp.get("insufficient_data"):
            lines.append(f"_数据不足 (需 ≥ 8 篇笔记)_")
        else:
            lines += [
                f"取 Top {tp['top_n']} 篇 vs 末尾 {tp['bottom_n']} 篇做对比，找出爆款关键词:",
                "",
                "| 关键词 | Top 频次 | 末位频次 | Lift |",
                "|--------|--------:|--------:|-----:|",
            ]
            for kw in tp["viral_keywords"][:12]:
                lines.append(f"| `{kw['token']}` | {kw['top_freq']} | {kw['bottom_freq']} | {kw['lift']} |")
            lines.append("")

        # Comment quality
        lines += ["## 💬 评论质量", ""]
        if not cq or cq.get("insufficient_data"):
            lines.append("_无评论数据或采样为零_")
        else:
            lines += [
                f"采样 {cq['posts_sampled']} 篇笔记共 **{cq['total_comments_sampled']} 条评论**",
                f"- 平均字数: {cq['avg_chars']}　短句灌水占比: {cq['short_filler_pct']}%",
                f"- 是否纯销售漏斗: **{'是 ⚠️' if cq['is_pure_sales_funnel'] else '否'}**",
                f"- 是否高质量讨论: **{'是 ✅' if cq['is_high_engagement'] else '否'}**",
                "",
                "**评论意图分布**:",
                "",
                "| 意图 | 数量 | 占比 |",
                "|------|----:|----:|",
            ]
            label_map = {
                "price_inquiry": "💰 问价/咨询",
                "discussion": "💬 讨论/对比",
                "praise": "❤️ 称赞",
                "complaint": "😡 吐槽",
                "consult": "🙋 求推荐",
                "question_other": "❓ 其他疑问",
                "filler": "💨 灌水",
                "other": "🌫️ 其他",
            }
            for k, v in cq["intent_distribution"].items():
                lines.append(f"| {label_map.get(k, k)} | {v['count']} | {v['pct']}% |")
            lines.append("")

        # Top posts
        lines += ["## 🏆 Top 笔记", "", "| # | 标题 | 赞 | 评 | 藏 |", "|:-:|------|---:|---:|---:|"]
        for i, p in enumerate(m.get("top_posts", [])[:10], 1):
            lines.append(f"| {i} | {p.get('title', '')[:38]} | {p.get('likes', 0)} | {p.get('comments', 0)} | {p.get('collects', 0)} |")
        lines.append("")

        return "\n".join(lines)

    def _dim_label(self, key: str) -> str:
        return {
            "engagement": "互动率",
            "trend": "趋势方向",
            "cadence": "发布节奏",
            "content_diversity": "内容多样性",
            "title_hook": "标题钩子",
            "comment_quality": "评论质量",
        }.get(key, key)

    def _build_blueprint_spec(self, data: dict) -> dict:
        score = data["score"]
        sections = [
            {
                "id": "score-radar",
                "type": "radar-chart",
                "label": "HEALTH SCORE BY DIMENSION",
                "data": {
                    "axes": [self._dim_label(k) for k in score["by_dimension"]],
                    "values": list(score["by_dimension"].values()),
                    "max": 100,
                    "overall": score["overall"],
                    "grade": score["grade"],
                },
            },
            {
                "id": "trend-line",
                "type": "line-chart",
                "label": "ENGAGEMENT TREND",
                "data": {
                    "first_half": data["trend"].get("avg_likes_first_half"),
                    "second_half": data["trend"].get("avg_likes_second_half"),
                    "recent_5": data["trend"].get("avg_likes_recent_5"),
                    "direction": data["trend"].get("direction"),
                },
            },
            {
                "id": "viral-keywords",
                "type": "tag-cloud",
                "label": "VIRAL KEYWORDS (TF-IDF LIFT)",
                "data": [
                    {"token": kw["token"], "weight": kw["lift"]}
                    for kw in data["title_patterns"].get("viral_keywords", [])[:15]
                ],
            },
            {
                "id": "comment-intent",
                "type": "pie-chart",
                "label": "COMMENT INTENT MIX",
                "data": (data.get("comment_quality") or {}).get("intent_distribution", {}),
            },
            {
                "id": "diagnosis",
                "type": "checklist",
                "label": "PRIORITIZED FINDINGS",
                "data": [
                    {"priority": d["priority"], "title": d["title"], "action": d["action"]}
                    for d in data["diagnosis"]
                ],
            },
        ]
        return {
            "type": "account-pro-analysis",
            "title": f"Pro Analysis: {data['user'].get('nickname', '?')} on {self.platform}",
            "sections": sections,
            "metadata": {
                "platform": self.platform,
                "workflow": self.NAME,
                "overall_score": score["overall"],
                "grade": score["grade"],
            },
        }
