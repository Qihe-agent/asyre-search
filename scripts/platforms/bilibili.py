"""Bilibili (B站) adapter for Asyre Search API."""

import re

from .base import PlatformAdapter


class BilibiliAdapter(PlatformAdapter):
    """Bilibili (B站) platform adapter."""

    PLATFORM_NAME = "bilibili"
    PLATFORM_LABEL = "B站"
    URL_PATTERNS = ["bilibili.com", "b23.tv"]

    # ── URL / ID extraction ───────────────────────────────────────

    def extract_id(self, url: str) -> str:
        """Extract BV id from a Bilibili URL."""
        if "b23.tv" in url:
            url = self.resolve_short_url(url)
        m = re.search(r"/(BV[A-Za-z0-9]+)", url)
        if m:
            return m.group(1)
        m = re.search(r"/av(\d+)", url)
        if m:
            return m.group(1)
        return url.strip()

    def _extract_mid(self, url: str) -> str:
        """Extract user mid from URL."""
        if "b23.tv" in url:
            url = self.resolve_short_url(url)
        m = re.search(r"/space/(\d+)", url)
        if m:
            return m.group(1)
        return url.strip()

    # ── API methods ───────────────────────────────────────────────

    def get_info(self, url_or_id: str) -> dict:
        """Get video detail."""
        bvid = self.extract_id(url_or_id) if url_or_id.startswith("http") else url_or_id
        return self._get(
            "/api/v1/bilibili/web/fetch_one_video",
            params={"bv_id": bvid},  # TODO: verify parameter name
        )

    def get_user(self, url_or_id: str) -> dict:
        """Get user profile."""
        mid = self._extract_mid(url_or_id) if url_or_id.startswith("http") else url_or_id
        return self._get(
            "/api/v1/bilibili/web/fetch_user_profile",
            params={"mid": mid},  # TODO: verify parameter name
        )

    def get_posts(self, url_or_id: str, limit: int = 20, cursor: int = 0) -> dict:
        """Get user's videos."""
        mid = self._extract_mid(url_or_id) if url_or_id.startswith("http") else url_or_id
        return self._get(
            "/api/v1/bilibili/web/fetch_user_post_videos",
            params={
                "mid": mid,  # TODO: verify parameter name
                "pn": (cursor // limit) + 1 if limit else 1,
                "ps": min(limit, 30),
            },
        )

    def get_comments(self, url_or_id: str, limit: int = 50, cursor: int = 0) -> dict:
        """Get video comments."""
        bvid = self.extract_id(url_or_id) if url_or_id.startswith("http") else url_or_id
        return self._get(
            "/api/v1/bilibili/web/fetch_video_comments",
            params={
                "bv_id": bvid,  # TODO: verify parameter name
                "pn": (cursor // limit) + 1 if limit else 1,
            },
        )

    def get_trending(self) -> dict:
        """Get Bilibili hot search."""
        return self._get("/api/v1/bilibili/web/fetch_hot_search")

    def search(self, keyword: str, search_type: str = "video", limit: int = 20) -> dict:
        """Search Bilibili content."""
        return self._get(
            "/api/v1/bilibili/web/fetch_search_result",
            params={
                "keyword": keyword,
                "search_type": search_type,  # TODO: verify parameter name
                "page": 1,
                "page_size": min(limit, 20),
            },
        )

    # ── Formatting ────────────────────────────────────────────────

    def format_info(self, data: dict) -> str:
        """Format Bilibili video info."""
        video = self._dig_video(data)
        if not video:
            return f"⚠️ 无法解析视频数据，原始响应:\n{self._json_preview(data)}"

        title = video.get("title", "N/A")
        owner = video.get("owner", {})
        name = owner.get("name", "N/A")
        duration = self._format_duration(video.get("duration", 0))
        pubdate = self._ts_to_date(video.get("pubdate"))
        bvid = video.get("bvid", "")

        stat = video.get("stat", {})
        views = self._compact_number(stat.get("view", 0))
        likes = self._compact_number(stat.get("like", 0))
        coins = self._compact_number(stat.get("coin", 0))
        favorites = self._compact_number(stat.get("favorite", 0))
        danmaku = self._compact_number(stat.get("danmaku", 0))
        comments = self._compact_number(stat.get("reply", 0))
        shares = self._compact_number(stat.get("share", 0))

        lines = [
            f"📺 B站视频详情",
            f"━━━━━━━━━━━━━━━━",
            f"标题:   {title}",
            f"UP主:   {name}",
            f"BV号:   {bvid}",
            f"时长:   {duration}",
            f"发布:   {pubdate}",
            f"",
            f"📊 互动数据",
            f"播放: {views}  点赞: {likes}  投币: {coins}  收藏: {favorites}",
            f"弹幕: {danmaku}  评论: {comments}  分享: {shares}",
        ]
        return "\n".join(lines)

    def format_user(self, data: dict) -> str:
        """Format Bilibili user info."""
        user = self._dig_user(data)
        if not user:
            return f"⚠️ 无法解析用户数据，原始响应:\n{self._json_preview(data)}"

        name = user.get("name", "N/A")
        sign = user.get("sign", "")
        mid = user.get("mid", "")
        fans = self._compact_number(user.get("follower", user.get("fans", 0)))
        following = self._compact_number(user.get("following", 0))
        likes = self._compact_number(user.get("likes", 0))

        lines = [
            f"👤 B站用户信息",
            f"━━━━━━━━━━━━━━━━",
            f"昵称:   {name}",
            f"UID:    {mid}",
            f"简介:   {sign}",
            f"",
            f"📊 数据",
            f"粉丝: {fans}  关注: {following}  获赞: {likes}",
        ]
        return "\n".join(lines)

    def format_trending(self, data: dict) -> str:
        """Format Bilibili hot search."""
        items = self._dig_trending(data)
        if not items:
            return f"⚠️ 无法解析热搜数据，原始响应:\n{self._json_preview(data)}"

        lines = ["🔥 B站热搜榜", "━━━━━━━━━━━━━━━━"]
        for i, item in enumerate(items[:30], 1):
            word = item.get("keyword", item.get("show_name", "N/A"))
            lines.append(f"{i:>2}. {word}")
        return "\n".join(lines)

    # ── Data navigation ───────────────────────────────────────────

    @staticmethod
    def _dig_video(data: dict) -> dict:
        if not data:
            return {}
        for path in [
            lambda d: d.get("data", {}).get("video_data", {}),
            lambda d: d.get("data", {}),
        ]:
            try:
                result = path(data)
                if result and result.get("title"):
                    return result
            except (KeyError, TypeError):
                continue
        return {}

    @staticmethod
    def _dig_user(data: dict) -> dict:
        if not data:
            return {}
        for path in [
            lambda d: d.get("data", {}).get("card", {}),
            lambda d: d.get("data", {}),
        ]:
            try:
                result = path(data)
                if result and result.get("name"):
                    return result
            except (KeyError, TypeError):
                continue
        return {}

    @staticmethod
    def _dig_trending(data: dict) -> list:
        if not data:
            return []
        for path in [
            lambda d: d.get("data", {}).get("trending", {}).get("list", []),
            lambda d: d.get("data", {}).get("list", []),
            lambda d: d.get("data", []) if isinstance(d.get("data"), list) else [],
        ]:
            try:
                result = path(data)
                if result:
                    return result
            except (KeyError, TypeError):
                continue
        return []

    @staticmethod
    def _json_preview(data, max_len=300):
        import json
        s = json.dumps(data, ensure_ascii=False, indent=2)
        return s[:max_len] + "\n..." if len(s) > max_len else s
