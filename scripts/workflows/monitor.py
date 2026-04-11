"""Cross-platform monitoring workflow — search keyword across multiple platforms."""

from .base import WorkflowRunner, WorkflowResult
from .metrics import compact_number


class MonitorWorkflow(WorkflowRunner):
    NAME = "monitor"
    DESCRIPTION = "Cross-platform sentiment/presence snapshot for a keyword or brand"

    def _execute(self, keyword: str, platforms: list[str] = None) -> dict:
        if not platforms:
            platforms = ["douyin", "xiaohongshu", "bilibili"]

        self._progress(f"🌐 Monitoring '{keyword}' across {', '.join(platforms)}...")

        platform_results = {}
        for plat in platforms:
            self._progress(f"── {plat} ──")
            try:
                adapter = self._get_adapter(plat, self.api_key)
            except ValueError as e:
                self._errors.append({"step": f"init_{plat}", "error": str(e)})
                continue

            # Search
            self._progress(f"  Searching on {plat}...")
            search_data = self._safe_call(f"search_{plat}", adapter.search, keyword)
            result_count = self._count_results(search_data, plat)

            # Trending (if available)
            trending_data = None
            try:
                self._progress(f"  Checking trending on {plat}...")
                trending_data = self._safe_call(f"trending_{plat}", adapter.get_trending)
            except Exception:
                pass

            # Check if keyword appears in trending
            trending_match = self._check_trending_match(trending_data, keyword, plat)

            platform_results[plat] = {
                "search_results": result_count,
                "trending_match": trending_match,
            }

        # Aggregate
        total_results = sum(r.get("search_results", 0) for r in platform_results.values())
        trending_platforms = [p for p, r in platform_results.items() if r.get("trending_match")]

        return {
            "keyword": keyword,
            "platforms": platform_results,
            "summary": {
                "total_platforms": len(platforms),
                "total_search_results": total_results,
                "trending_on": trending_platforms,
            },
        }

    def _count_results(self, search_data: dict, platform: str) -> int:
        """Count how many results were returned."""
        if not search_data:
            return 0
        data = search_data.get("data", search_data)
        if isinstance(data, dict) and "data" in data:
            data = data["data"]
        if isinstance(data, dict):
            items = data.get("items", data.get("result", data.get("aweme_list", [])))
            return len(items) if isinstance(items, list) else 0
        return 0

    def _check_trending_match(self, trending_data: dict, keyword: str, platform: str) -> bool:
        """Check if keyword appears in trending data."""
        if not trending_data:
            return False
        kw_lower = keyword.lower()
        # Flatten trending to text and search
        import json
        text = json.dumps(trending_data, ensure_ascii=False).lower()
        return kw_lower in text

    def _format_markdown(self, data: dict) -> str:
        keyword = data.get("keyword", "")
        platforms = data.get("platforms", {})
        summary = data.get("summary", {})

        lines = [
            f"## 🌐 跨平台监测报告: \"{keyword}\"",
            f"",
            f"### 概览",
            f"- 监测平台数: {summary.get('total_platforms', 0)}",
            f"- 搜索结果总数: {summary.get('total_search_results', 0)}",
        ]

        trending_on = summary.get("trending_on", [])
        if trending_on:
            lines.append(f"- 上热搜平台: {', '.join(trending_on)}")
        else:
            lines.append("- 热搜: 未上榜")

        lines.extend(["", "### 各平台详情", ""])
        lines.append("| 平台 | 搜索结果 | 热搜命中 |")
        lines.append("|------|--------:|:--------:|")
        for plat, result in platforms.items():
            trending = "✓" if result.get("trending_match") else "-"
            lines.append(f"| {plat} | {result.get('search_results', 0)} | {trending} |")

        lines.append("")
        return "\n".join(lines)

    def _build_blueprint_spec(self, data: dict) -> dict:
        platforms = data.get("platforms", {})
        summary = data.get("summary", {})

        return {
            "type": "cross-platform-monitor",
            "title": f"Cross-Platform Monitor: \"{data.get('keyword', '')}\"",
            "sections": [
                {
                    "id": "overview",
                    "type": "stat-grid",
                    "label": "MONITORING OVERVIEW",
                    "data": {
                        "Platforms": summary.get("total_platforms", 0),
                        "Total Results": summary.get("total_search_results", 0),
                        "Trending On": len(summary.get("trending_on", [])),
                    },
                },
                {
                    "id": "platform_comparison",
                    "type": "comparison-table",
                    "label": "PLATFORM BREAKDOWN",
                    "data": {
                        "platforms": [
                            {"name": plat, **result}
                            for plat, result in platforms.items()
                        ]
                    },
                },
            ],
            "metadata": {"workflow": self.NAME},
        }
