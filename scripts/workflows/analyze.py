"""Account analysis workflow — full account deep dive."""

from .base import WorkflowRunner
from .metrics import (
    extract_user_metrics, extract_post_ids, extract_post_metrics,
    extract_post_metrics_from_listitem, extract_post_listitems,
    compute_account_metrics, compact_number,
)


class AnalyzeWorkflow(WorkflowRunner):
    NAME = "analyze"
    DESCRIPTION = "Full account analysis: profile + posts + engagement metrics"

    def _execute(self, target: str, limit: int = 50) -> dict:
        self._progress(f"📊 Analyzing {target} on {self.platform}...")

        # Step 1: User info
        self._progress("Getting user profile...")
        user_data = self._safe_call("get_user", self.adapter.get_user, target)
        user_metrics = extract_user_metrics(user_data, self.platform)

        # Step 2: Posts list
        self._progress("Getting posts list...")
        posts_data = self._safe_call("get_posts", self.adapter.get_posts, target, limit=limit)
        post_ids = extract_post_ids(posts_data, self.platform)
        self._progress(f"Found {len(post_ids)} posts")

        # Step 3: Extract metrics from posts list directly (cheap path).
        # Many platforms (XHS web_v2/fetch_home_notes, etc.) include full engagement fields
        # per note in the list response — no need to re-fetch each one. Saves API calls AND
        # avoids upstream rate-limiting that often kills the entire workflow.
        post_metrics_list = []
        list_items = extract_post_listitems(posts_data, self.platform)
        cap = min(len(list_items), limit if limit else len(list_items))
        list_items = list_items[:cap]

        # First pass: try cheap extraction
        need_detail_indices = []
        for i, item in enumerate(list_items):
            pm = extract_post_metrics_from_listitem(item, self.platform)
            if pm:
                post_metrics_list.append(pm)
            else:
                need_detail_indices.append(i)
                post_metrics_list.append(None)  # placeholder

        # Second pass: only get_info for items where list was insufficient
        if need_detail_indices:
            self._progress(f"Cheap path got {len(list_items) - len(need_detail_indices)}/{len(list_items)}; "
                           f"fetching detail for {len(need_detail_indices)} remaining...")
            for i in need_detail_indices:
                pid = post_ids[i] if i < len(post_ids) else None
                if not pid:
                    continue
                self._progress(f"  detail {i+1}/{len(list_items)}...")
                detail = self._safe_call(f"get_info_{i}", self.adapter.get_info, pid)
                pm = extract_post_metrics(detail, self.platform)
                if pm:
                    post_metrics_list[i] = pm

        # Drop None placeholders
        post_metrics_list = [pm for pm in post_metrics_list if pm]

        # Step 4: Compute metrics
        account_metrics = compute_account_metrics(user_metrics, post_metrics_list)

        return {
            "user": user_metrics,
            "post_count_fetched": len(post_ids),
            "post_details_count": len(post_metrics_list),
            "posts": post_metrics_list,
            "metrics": account_metrics,
        }

    def _format_markdown(self, data: dict) -> str:
        user = data.get("user", {})
        metrics = data.get("metrics", {})
        posts = data.get("posts", [])

        nickname = user.get("nickname", "Unknown")
        followers = compact_number(user.get("followers", 0))
        desc = user.get("desc", "")

        lines = [
            f"## 📊 账号分析报告: {nickname}",
            f"",
            f"### 基本信息",
            f"| 指标 | 数据 |",
            f"|------|------|",
            f"| 昵称 | {nickname} |",
            f"| 粉丝 | {followers} |",
            f"| 简介 | {desc[:80]} |",
            f"| 分析笔记数 | {metrics.get('total_posts_analyzed', 0)} |",
            f"",
            f"### 核心指标",
            f"| 指标 | 数据 |",
            f"|------|------|",
            f"| 平均点赞 | {compact_number(metrics.get('avg_likes', 0))} |",
            f"| 平均评论 | {compact_number(metrics.get('avg_comments', 0))} |",
            f"| 平均收藏 | {compact_number(metrics.get('avg_collects', 0))} |",
            f"| 互动率 | {metrics.get('engagement_rate', 0):.2%} |",
            f"| 收藏/点赞比 | {metrics.get('collect_like_ratio', 0):.0%} |",
            f"",
        ]

        # Top posts
        top_posts = metrics.get("top_posts", [])
        if top_posts:
            lines.append("### Top 5 笔记")
            lines.append("| 排名 | 标题 | 点赞 | 评论 | 收藏 |")
            lines.append("|:---:|------|-----:|-----:|-----:|")
            for i, p in enumerate(top_posts[:5], 1):
                lines.append(f"| {i} | {p.get('title', '')[:30]} | {p.get('likes', 0)} | {p.get('comments', 0)} | {p.get('collects', 0)} |")
            lines.append("")

        # Content type distribution
        dist = metrics.get("content_type_distribution", {})
        if dist:
            lines.append("### 内容类型分布")
            for t, c in sorted(dist.items(), key=lambda x: -x[1]):
                lines.append(f"- {t}: {c} 篇")
            lines.append("")

        return "\n".join(lines)

    def _build_blueprint_spec(self, data: dict) -> dict:
        user = data.get("user", {})
        metrics = data.get("metrics", {})

        sections = [
            {
                "id": "profile",
                "type": "stat-grid",
                "label": "PROFILE OVERVIEW",
                "data": {
                    "Followers": user.get("followers", 0),
                    "Avg Likes": metrics.get("avg_likes", 0),
                    "Avg Comments": metrics.get("avg_comments", 0),
                    "Engagement Rate": f"{metrics.get('engagement_rate', 0):.2%}",
                    "Collect/Like Ratio": f"{metrics.get('collect_like_ratio', 0):.0%}",
                    "Posts Analyzed": metrics.get("total_posts_analyzed", 0),
                },
            },
            {
                "id": "top_posts",
                "type": "ranked-list",
                "label": "TOP PERFORMING CONTENT",
                "data": [
                    {"rank": i + 1, "title": p.get("title", ""), "likes": p.get("likes", 0),
                     "comments": p.get("comments", 0), "collects": p.get("collects", 0)}
                    for i, p in enumerate(metrics.get("top_posts", [])[:5])
                ],
            },
            {
                "id": "engagement",
                "type": "bar-chart",
                "label": "ENGAGEMENT DISTRIBUTION",
                "data": {
                    "labels": [p.get("title", "")[:15] for p in data.get("posts", [])[:10]],
                    "values": [p.get("likes", 0) for p in data.get("posts", [])[:10]],
                },
            },
            {
                "id": "content_mix",
                "type": "pie-chart",
                "label": "CONTENT TYPE MIX",
                "data": metrics.get("content_type_distribution", {}),
            },
        ]

        return {
            "type": "account-analysis",
            "title": f"Account Analysis: {user.get('nickname', 'Unknown')} on {self.platform}",
            "sections": sections,
            "metadata": {"platform": self.platform, "workflow": self.NAME},
        }
