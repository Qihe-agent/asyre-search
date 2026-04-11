"""Content discovery workflow — analyze keyword/topic performance."""

from .base import WorkflowRunner
from .metrics import extract_post_metrics, compact_number, safe_int


class ScoutWorkflow(WorkflowRunner):
    NAME = "scout"
    DESCRIPTION = "Content/keyword discovery: search → analyze top posts → find patterns"

    def _execute(self, keyword: str, limit: int = 20) -> dict:
        self._progress(f"🔍 Scouting '{keyword}' on {self.platform}...")

        # Step 1: Search
        self._progress("Searching...")
        search_data = self._safe_call("search", self.adapter.search, keyword, limit=limit)

        # Step 2: Extract top post IDs from search results
        top_ids = self._extract_search_ids(search_data)
        self._progress(f"Found {len(top_ids)} results")

        # Step 3: Get details for top N
        detail_limit = min(len(top_ids), 10)
        post_details = []
        for i, pid in enumerate(top_ids[:detail_limit]):
            self._progress(f"Fetching detail {i+1}/{detail_limit}...")
            detail = self._safe_call(f"detail_{i}", self.adapter.get_info, pid)
            pm = extract_post_metrics(detail, self.platform)
            if pm:
                post_details.append(pm)

        # Step 4: Analyze patterns
        patterns = self._analyze_patterns(post_details)

        return {
            "keyword": keyword,
            "total_results": len(top_ids),
            "details_fetched": len(post_details),
            "posts": post_details,
            "patterns": patterns,
        }

    def _extract_search_ids(self, search_data: dict) -> list[str]:
        """Extract post IDs from search results (platform-specific)."""
        if not search_data:
            return []

        data = search_data.get("data", search_data)
        if isinstance(data, dict) and "data" in data:
            data = data["data"]

        if self.platform == "xiaohongshu":
            items = data.get("items", [])
            return [i.get("note", {}).get("id", "") for i in items if i.get("note", {}).get("id")]
        elif self.platform in ("douyin", "tiktok"):
            items = data.get("data", data.get("aweme_list", []))
            if isinstance(items, list):
                return [str(i.get("aweme_id", i.get("aweme_info", {}).get("aweme_id", ""))) for i in items if i.get("aweme_id") or i.get("aweme_info")]
        elif self.platform == "bilibili":
            results = data.get("result", [])
            return [str(r.get("bvid", "")) for r in results if r.get("bvid")]

        return []

    def _analyze_patterns(self, posts: list[dict]) -> dict:
        if not posts:
            return {}

        likes_list = [p.get("likes", 0) for p in posts]
        avg_likes = sum(likes_list) / len(likes_list) if likes_list else 0
        max_likes = max(likes_list) if likes_list else 0
        median_likes = sorted(likes_list)[len(likes_list) // 2] if likes_list else 0

        # Content type distribution
        types = {}
        for p in posts:
            t = p.get("type", "unknown")
            types[t] = types.get(t, 0) + 1

        return {
            "avg_likes": round(avg_likes),
            "max_likes": max_likes,
            "median_likes": median_likes,
            "content_type_distribution": types,
            "total_analyzed": len(posts),
        }

    def _format_markdown(self, data: dict) -> str:
        keyword = data.get("keyword", "")
        patterns = data.get("patterns", {})
        posts = data.get("posts", [])

        lines = [
            f"## 🔍 内容探查报告: \"{keyword}\"",
            f"",
            f"### 概览",
            f"- 搜索结果: {data.get('total_results', 0)} 条",
            f"- 详细分析: {data.get('details_fetched', 0)} 条",
            f"- 平均点赞: {compact_number(patterns.get('avg_likes', 0))}",
            f"- 最高点赞: {compact_number(patterns.get('max_likes', 0))}",
            f"- 中位点赞: {compact_number(patterns.get('median_likes', 0))}",
            f"",
        ]

        # Top posts
        sorted_posts = sorted(posts, key=lambda p: p.get("likes", 0), reverse=True)
        if sorted_posts:
            lines.append("### Top 内容")
            lines.append("| 排名 | 标题 | 点赞 | 评论 | 收藏 |")
            lines.append("|:---:|------|-----:|-----:|-----:|")
            for i, p in enumerate(sorted_posts[:10], 1):
                lines.append(f"| {i} | {p.get('title', '')[:30]} | {p.get('likes', 0)} | {p.get('comments', 0)} | {p.get('collects', 0)} |")
            lines.append("")

        # Content type
        dist = patterns.get("content_type_distribution", {})
        if dist:
            lines.append("### 内容类型分布")
            for t, c in sorted(dist.items(), key=lambda x: -x[1]):
                lines.append(f"- {t}: {c} 篇")
            lines.append("")

        return "\n".join(lines)

    def _build_blueprint_spec(self, data: dict) -> dict:
        patterns = data.get("patterns", {})
        posts = sorted(data.get("posts", []), key=lambda p: p.get("likes", 0), reverse=True)

        return {
            "type": "content-scout",
            "title": f"Content Scout: \"{data.get('keyword', '')}\" on {self.platform}",
            "sections": [
                {
                    "id": "overview",
                    "type": "stat-grid",
                    "label": "SEARCH OVERVIEW",
                    "data": {
                        "Results": data.get("total_results", 0),
                        "Avg Likes": patterns.get("avg_likes", 0),
                        "Max Likes": patterns.get("max_likes", 0),
                        "Median Likes": patterns.get("median_likes", 0),
                    },
                },
                {
                    "id": "top_content",
                    "type": "ranked-list",
                    "label": "TOP CONTENT",
                    "data": [
                        {"rank": i + 1, "title": p.get("title", ""), "likes": p.get("likes", 0)}
                        for i, p in enumerate(posts[:10])
                    ],
                },
                {
                    "id": "content_types",
                    "type": "pie-chart",
                    "label": "CONTENT TYPE DISTRIBUTION",
                    "data": patterns.get("content_type_distribution", {}),
                },
            ],
            "metadata": {"platform": self.platform, "workflow": self.NAME},
        }
