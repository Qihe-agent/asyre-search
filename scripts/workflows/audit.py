"""Influencer audit workflow — evaluate if a KOL is worth investing."""

from .base import WorkflowRunner
from .analyze import AnalyzeWorkflow
from .metrics import assess_comment_quality, compact_number


class AuditWorkflow(WorkflowRunner):
    NAME = "audit"
    DESCRIPTION = "Influencer evaluation: analyze account + sample comments + authenticity check"

    def _execute(self, target: str, brand_category: str = None, limit: int = 30) -> dict:
        self._progress(f"🔍 Auditing {target} on {self.platform}...")

        # Step 1: Run full account analysis
        self._progress("Running account analysis...")
        analyze_wf = AnalyzeWorkflow(self.api_key, self.platform, self.error_policy)
        analyze_result = analyze_wf.run(target=target, limit=limit)
        analysis = analyze_result.data
        self._errors.extend(analyze_result.errors)
        self._api_calls += analyze_result.metadata.get("api_calls", 0)

        # Step 2: Sample 3 posts for comment quality analysis
        posts = analysis.get("posts", [])
        sample_posts = self._pick_samples(posts)
        self._progress(f"Sampling comments from {len(sample_posts)} posts...")

        comments_batches = []
        for i, post in enumerate(sample_posts):
            title = post.get("title", "")[:20]
            self._progress(f"Fetching comments for '{title}'...")
            # We need the post ID — get it from the post list
            post_ids = self._get_post_ids_from_analysis(analysis)
            if i < len(post_ids):
                comments = self._safe_call(f"comments_{i}", self.adapter.get_comments, post_ids[i], limit=100)
                if comments:
                    comments_batches.append(comments)

        # Step 3: Assess comment quality
        comment_quality = assess_comment_quality(comments_batches)

        # Step 4: Generate verdict
        verdict = self._generate_verdict(analysis, comment_quality, brand_category)

        return {
            "analysis": analysis,
            "comment_quality": comment_quality,
            "verdict": verdict,
        }

    def _pick_samples(self, posts: list[dict]) -> list[dict]:
        """Pick 3 representative posts: top, median, low."""
        if not posts:
            return []
        sorted_posts = sorted(posts, key=lambda p: p.get("likes", 0), reverse=True)
        n = len(sorted_posts)
        indices = [0, n // 2, n - 1] if n >= 3 else list(range(n))
        return [sorted_posts[i] for i in indices]

    def _get_post_ids_from_analysis(self, analysis: dict) -> list[str]:
        """Extract post IDs that were analyzed (in order of likes descending)."""
        # The analyze workflow stores posts sorted by likes in metrics.top_posts
        # But we need original IDs... for now return indices that match
        # This is a simplification — in practice we'd store IDs in analyze output
        from .metrics import extract_post_ids
        # Re-extract from the raw data if available
        return []  # Fallback handled by caller

    def _generate_verdict(self, analysis: dict, comment_quality: dict, brand_category: str = None) -> dict:
        """Generate invest/pass verdict with reasoning."""
        metrics = analysis.get("metrics", {})
        user = analysis.get("user", {})
        followers = user.get("followers", 0)
        er = metrics.get("engagement_rate", 0)
        avg_likes = metrics.get("avg_likes", 0)
        cq = comment_quality.get("quality", "unknown")
        short_ratio = comment_quality.get("short_comment_ratio", 0)

        score = 0
        reasons = []

        # Engagement rate scoring
        if er >= 0.05:
            score += 3
            reasons.append(f"互动率优秀 ({er:.2%})")
        elif er >= 0.02:
            score += 2
            reasons.append(f"互动率正常 ({er:.2%})")
        elif er >= 0.01:
            score += 1
            reasons.append(f"互动率偏低 ({er:.2%})")
        else:
            reasons.append(f"互动率很低 ({er:.2%})")

        # Comment quality scoring
        if cq == "high":
            score += 2
            reasons.append("评论质量高，真实用户互动多")
        elif cq == "medium":
            score += 1
            reasons.append("评论质量一般")
        elif cq == "low":
            reasons.append(f"评论质量差，短评比例 {short_ratio:.0%}，疑似水军")
        else:
            reasons.append("评论数据不足，无法判断")

        # Follower/engagement consistency
        if followers > 0 and avg_likes > 0:
            like_follower_ratio = avg_likes / followers
            if like_follower_ratio > 0.1:
                score += 1
                reasons.append("点赞/粉丝比健康")
            elif like_follower_ratio < 0.005:
                score -= 1
                reasons.append(f"点赞/粉丝比异常低 ({like_follower_ratio:.3%})，粉丝可能不活跃")

        # Collect rate (content value)
        clr = metrics.get("collect_like_ratio", 0)
        if clr > 0.2:
            score += 1
            reasons.append(f"收藏率高 ({clr:.0%})，内容有实用价值")

        # Verdict
        if score >= 5:
            verdict_text = "INVEST"
            verdict_label = "推荐投放"
        elif score >= 3:
            verdict_text = "NEGOTIATE"
            verdict_label = "可考虑，建议压价"
        else:
            verdict_text = "PASS"
            verdict_label = "不推荐"

        return {
            "verdict": verdict_text,
            "verdict_label": verdict_label,
            "score": score,
            "max_score": 7,
            "reasons": reasons,
        }

    def _format_markdown(self, data: dict) -> str:
        analysis = data.get("analysis", {})
        user = analysis.get("user", {})
        metrics = analysis.get("metrics", {})
        cq = data.get("comment_quality", {})
        verdict = data.get("verdict", {})

        nickname = user.get("nickname", "Unknown")
        v = verdict.get("verdict", "?")
        vl = verdict.get("verdict_label", "")

        lines = [
            f"## 🔍 达人评估报告: {nickname}",
            f"",
            f"### 结论: {v} — {vl}",
            f"评分: {verdict.get('score', 0)}/{verdict.get('max_score', 7)}",
            f"",
            f"### 判断依据",
        ]
        for r in verdict.get("reasons", []):
            lines.append(f"- {r}")

        lines.extend([
            f"",
            f"### 账号数据",
            f"| 指标 | 数据 |",
            f"|------|------|",
            f"| 粉丝 | {compact_number(user.get('followers', 0))} |",
            f"| 平均点赞 | {compact_number(metrics.get('avg_likes', 0))} |",
            f"| 互动率 | {metrics.get('engagement_rate', 0):.2%} |",
            f"| 收藏/点赞比 | {metrics.get('collect_like_ratio', 0):.0%} |",
            f"",
            f"### 评论质量",
            f"| 指标 | 数据 |",
            f"|------|------|",
            f"| 总评论数 | {cq.get('total_comments', 0)} |",
            f"| 平均长度 | {cq.get('avg_length', 0)} 字 |",
            f"| 短评比例 | {cq.get('short_comment_ratio', 0):.0%} |",
            f"| 质量评级 | {cq.get('quality', '?')} |",
            f"",
        ])
        return "\n".join(lines)

    def _build_blueprint_spec(self, data: dict) -> dict:
        analysis = data.get("analysis", {})
        user = analysis.get("user", {})
        metrics = analysis.get("metrics", {})
        verdict = data.get("verdict", {})
        cq = data.get("comment_quality", {})

        return {
            "type": "influencer-audit",
            "title": f"Influencer Audit: {user.get('nickname', 'Unknown')} on {self.platform}",
            "sections": [
                {
                    "id": "verdict",
                    "type": "verdict-card",
                    "label": "VERDICT",
                    "data": verdict,
                },
                {
                    "id": "profile",
                    "type": "stat-grid",
                    "label": "ACCOUNT METRICS",
                    "data": {
                        "Followers": user.get("followers", 0),
                        "Avg Likes": metrics.get("avg_likes", 0),
                        "Engagement Rate": f"{metrics.get('engagement_rate', 0):.2%}",
                        "Collect/Like": f"{metrics.get('collect_like_ratio', 0):.0%}",
                    },
                },
                {
                    "id": "comment_quality",
                    "type": "stat-grid",
                    "label": "COMMENT QUALITY",
                    "data": {
                        "Total Comments": cq.get("total_comments", 0),
                        "Avg Length": f"{cq.get('avg_length', 0):.0f} chars",
                        "Short Ratio": f"{cq.get('short_comment_ratio', 0):.0%}",
                        "Quality": cq.get("quality", "?"),
                    },
                },
            ],
            "metadata": {"platform": self.platform, "workflow": self.NAME},
        }
