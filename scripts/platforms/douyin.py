"""Douyin (抖音) adapter for Asyre Search API."""

import re

from .base import PlatformAdapter


class DouyinAdapter(PlatformAdapter):
    """Douyin (抖音) platform adapter — most complete reference implementation."""

    PLATFORM_NAME = "douyin"
    PLATFORM_LABEL = "抖音"
    URL_PATTERNS = ["douyin.com", "v.douyin.com"]

    # ── URL / ID extraction ───────────────────────────────────────

    def extract_id(self, url: str) -> str:
        """Extract aweme_id from a Douyin URL."""
        if "v.douyin.com" in url:
            url = self.resolve_short_url(url)
        m = re.search(r"/video/(\d+)", url)
        if m:
            return m.group(1)
        m = re.search(r"/note/(\d+)", url)
        if m:
            return m.group(1)
        return url.strip()

    def _extract_sec_uid(self, url: str) -> str:
        """Extract sec_uid from a Douyin user URL."""
        if "v.douyin.com" in url:
            url = self.resolve_short_url(url)
        m = re.search(r"sec_uid=([^&]+)", url)
        if m:
            return m.group(1)
        m = re.search(r"/user/([A-Za-z0-9_-]+)", url)
        if m:
            return m.group(1)
        return url.strip()

    # ── API methods ───────────────────────────────────────────────

    def get_info(self, url_or_id: str) -> dict:
        """Get video detail by share URL or aweme_id."""
        if url_or_id.startswith("http"):
            return self._call("info", variant="by_url", share_url=url_or_id)
        return self._call("info", variant="by_id", aweme_id=url_or_id)

    def get_user(self, url_or_id: str) -> dict:
        """Get user profile by sec_uid or URL."""
        sec_uid = self._extract_sec_uid(url_or_id) if url_or_id.startswith("http") else url_or_id
        if sec_uid.isdigit():
            return self._call("user", variant="by_uid", uid=sec_uid)
        return self._call("user", variant="by_sec_uid", sec_user_id=sec_uid)

    def get_posts(self, url_or_id: str, limit: int = 20, cursor: int = 0) -> dict:
        """Get user's post videos."""
        sec_uid = self._extract_sec_uid(url_or_id) if url_or_id.startswith("http") else url_or_id
        return self._call("posts", sec_user_id=sec_uid, max_cursor=cursor, count=min(limit, 20))

    def search(self, keyword: str, search_type: str = "video", limit: int = 20) -> dict:
        """Search Douyin content."""
        return self._call("search", keyword=keyword, count=min(limit, 20), cursor=0,
                          sort_type="0", publish_time="0", filter_duration="0", content_type="0")

    def get_trending(self) -> dict:
        """Get Douyin hot search list."""
        return self._call("trending")

    def get_comments(self, url_or_id: str, limit: int = 50, cursor: int = 0) -> dict:
        """Get video comments."""
        aweme_id = self.extract_id(url_or_id) if url_or_id.startswith("http") else url_or_id
        return self._call("comments", aweme_id=aweme_id, cursor=cursor, count=min(limit, 50))

    # ── Formatting ────────────────────────────────────────────────

    def format_info(self, data: dict) -> str:
        """Format Douyin video info as human-readable text."""
        aweme = self._dig_aweme(data)
        if not aweme:
            return f"⚠️ 无法解析视频数据，原始响应:\n{self._json_preview(data)}"

        desc = aweme.get("desc", "N/A")
        author = aweme.get("author", {})
        nickname = author.get("nickname", "N/A")
        unique_id = author.get("unique_id") or author.get("short_id", "")
        duration = self._format_duration(aweme.get("duration", 0) // 1000 if aweme.get("duration", 0) > 1000 else aweme.get("duration", 0))
        create_time = self._ts_to_date(aweme.get("create_time"))

        stats = aweme.get("statistics", {})
        likes = self._compact_number(stats.get("digg_count", 0))
        comments = self._compact_number(stats.get("comment_count", 0))
        favorites = self._compact_number(stats.get("collect_count", 0))
        shares = self._compact_number(stats.get("share_count", 0))
        plays = self._compact_number(stats.get("play_count", 0))

        tags = []
        for te in aweme.get("text_extra", []):
            ht = te.get("hashtag_name")
            if ht:
                tags.append(f"#{ht}")
        tags_str = " ".join(tags) if tags else "N/A"

        author_str = f"{nickname} (@{unique_id})" if unique_id else nickname

        lines = [
            f"📹 抖音视频详情",
            f"━━━━━━━━━━━━━━━━",
            f"标题:   {desc}",
            f"作者:   {author_str}",
            f"时长:   {duration}",
            f"发布:   {create_time}",
            f"话题:   {tags_str}",
            f"",
            f"📊 互动数据",
            f"播放: {plays}  点赞: {likes}  评论: {comments}  收藏: {favorites}  分享: {shares}",
        ]
        return "\n".join(lines)

    def format_user(self, data: dict) -> str:
        """Format Douyin user info."""
        user = self._dig_user(data)
        if not user:
            return f"⚠️ 无法解析用户数据，原始响应:\n{self._json_preview(data)}"

        nickname = user.get("nickname", "N/A")
        unique_id = user.get("unique_id") or user.get("short_id", "")
        signature = user.get("signature", "")
        followers = self._compact_number(user.get("follower_count", 0))
        following = self._compact_number(user.get("following_count", 0))
        likes = self._compact_number(user.get("total_favorited", 0))
        videos = user.get("aweme_count", 0)

        lines = [
            f"👤 抖音用户信息",
            f"━━━━━━━━━━━━━━━━",
            f"昵称:   {nickname}",
            f"抖音号: {unique_id}",
            f"简介:   {signature}",
            f"",
            f"📊 数据",
            f"粉丝: {followers}  关注: {following}  获赞: {likes}  作品: {videos}",
        ]
        return "\n".join(lines)

    def format_trending(self, data: dict) -> str:
        """Format Douyin hot search list."""
        items = self._dig_trending(data)
        if not items:
            return f"⚠️ 无法解析热搜数据，原始响应:\n{self._json_preview(data)}"

        lines = ["🔥 抖音热搜榜", "━━━━━━━━━━━━━━━━"]
        for i, item in enumerate(items[:30], 1):
            word = item.get("word", item.get("title", "N/A"))
            hot = self._compact_number(item.get("hot_value", 0))
            lines.append(f"{i:>2}. {word}  ({hot})")
        return "\n".join(lines)

    def format_comments(self, data: dict) -> str:
        """Format Douyin video comments."""
        comments = self._dig_comments(data)
        if not comments:
            return f"⚠️ 无法解析评论数据，原始响应:\n{self._json_preview(data)}"

        lines = ["💬 评论列表", "━━━━━━━━━━━━━━━━"]
        for c in comments[:50]:
            user = c.get("user", {}).get("nickname", "匿名")
            text = c.get("text", "")
            likes = c.get("digg_count", 0)
            lines.append(f"  {user}: {text}  [👍 {likes}]")
        return "\n".join(lines)

    # ── Data navigation helpers ───────────────────────────────────

    @staticmethod
    def _dig_aweme(data: dict) -> dict:
        if not data:
            return {}
        for path in [
            lambda d: d.get("data", {}).get("aweme_detail", {}),
            lambda d: d.get("data", {}).get("aweme_details", [{}])[0] if d.get("data", {}).get("aweme_details") else {},
            lambda d: d.get("aweme_detail", {}),
            lambda d: d.get("data", {}),
            lambda d: d,
        ]:
            try:
                result = path(data)
                if result and result.get("desc") is not None:
                    return result
            except (KeyError, IndexError, TypeError):
                continue
        return {}

    @staticmethod
    def _dig_user(data: dict) -> dict:
        if not data:
            return {}
        for path in [
            lambda d: d.get("data", {}).get("user", {}),
            lambda d: d.get("user", {}),
            lambda d: d.get("data", {}),
        ]:
            try:
                result = path(data)
                if result and result.get("nickname"):
                    return result
            except (KeyError, TypeError):
                continue
        return {}

    @staticmethod
    def _dig_trending(data: dict) -> list:
        if not data:
            return []
        for path in [
            lambda d: d.get("data", {}).get("word_list", []),
            lambda d: d.get("data", {}).get("trending_list", []),
            lambda d: d.get("data", []) if isinstance(d.get("data"), list) else [],
            lambda d: d.get("word_list", []),
        ]:
            try:
                result = path(data)
                if result:
                    return result
            except (KeyError, TypeError):
                continue
        return []

    @staticmethod
    def _dig_comments(data: dict) -> list:
        if not data:
            return []
        for path in [
            lambda d: d.get("data", {}).get("comments", []),
            lambda d: d.get("comments", []),
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
        if len(s) > max_len:
            return s[:max_len] + "\n..."
        return s
