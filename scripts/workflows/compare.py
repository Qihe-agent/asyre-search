"""Competitive comparison workflow — compare 2+ accounts side by side."""

from .base import WorkflowRunner
from .analyze import AnalyzeWorkflow
from .metrics import compact_number


class CompareWorkflow(WorkflowRunner):
    NAME = "compare"
    DESCRIPTION = "Compare 2+ accounts: run analyze on each, then cross-compare"

    def _execute(self, targets: list[str], limit: int = 30) -> dict:
        analyses = []
        for target in targets:
            self._progress(f"── Analyzing {target} ──")
            wf = AnalyzeWorkflow(self.api_key, self.platform, self.error_policy)
            result = wf.run(target=target, limit=limit)
            analyses.append(result.data)
            self._errors.extend(result.errors)
            self._api_calls += result.metadata.get("api_calls", 0)

        comparison = self._cross_compare(analyses)
        return {"analyses": analyses, "comparison": comparison}

    def _cross_compare(self, analyses: list[dict]) -> dict:
        """Generate comparison table and ranking."""
        rows = []
        for a in analyses:
            user = a.get("user", {})
            m = a.get("metrics", {})
            rows.append({
                "nickname": user.get("nickname", "?"),
                "followers": user.get("followers", 0),
                "avg_likes": m.get("avg_likes", 0),
                "avg_comments": m.get("avg_comments", 0),
                "engagement_rate": m.get("engagement_rate", 0),
                "collect_like_ratio": m.get("collect_like_ratio", 0),
                "total_posts_analyzed": m.get("total_posts_analyzed", 0),
            })

        # Rank by engagement rate
        ranked = sorted(rows, key=lambda r: r.get("engagement_rate", 0), reverse=True)
        return {"accounts": rows, "ranking_by_engagement": [r["nickname"] for r in ranked]}

    def _format_markdown(self, data: dict) -> str:
        comparison = data.get("comparison", {})
        accounts = comparison.get("accounts", [])

        lines = [
            f"## 📊 竞品对比报告",
            f"",
            f"### 核心指标对比",
            f"",
        ]

        if accounts:
            header = "| 指标 | " + " | ".join(a["nickname"] for a in accounts) + " |"
            sep = "|------|" + "|".join(["------:" for _ in accounts]) + "|"
            lines.append(header)
            lines.append(sep)

            fields = [
                ("粉丝", "followers", lambda v: compact_number(v)),
                ("平均点赞", "avg_likes", lambda v: compact_number(v)),
                ("平均评论", "avg_comments", lambda v: compact_number(v)),
                ("互动率", "engagement_rate", lambda v: f"{v:.2%}"),
                ("收藏/点赞比", "collect_like_ratio", lambda v: f"{v:.0%}"),
                ("分析笔记数", "total_posts_analyzed", lambda v: str(v)),
            ]
            for label, key, fmt in fields:
                vals = " | ".join(fmt(a.get(key, 0)) for a in accounts)
                lines.append(f"| {label} | {vals} |")

            lines.append("")
            ranking = comparison.get("ranking_by_engagement", [])
            if ranking:
                lines.append(f"### 互动率排名: {' > '.join(ranking)}")
                lines.append("")

        return "\n".join(lines)

    def _build_blueprint_spec(self, data: dict) -> dict:
        comparison = data.get("comparison", {})
        accounts = comparison.get("accounts", [])
        return {
            "type": "competitive-comparison",
            "title": f"Competitive Comparison on {self.platform}",
            "sections": [
                {
                    "id": "comparison_table",
                    "type": "comparison-table",
                    "label": "ACCOUNT COMPARISON",
                    "data": {"accounts": accounts},
                },
                {
                    "id": "engagement_ranking",
                    "type": "ranked-list",
                    "label": "ENGAGEMENT RANKING",
                    "data": [
                        {"rank": i + 1, "name": name}
                        for i, name in enumerate(comparison.get("ranking_by_engagement", []))
                    ],
                },
            ],
            "metadata": {"platform": self.platform, "workflow": self.NAME},
        }
