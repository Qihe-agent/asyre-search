"""TikTok adapter for Asyre Search API."""

import re

from .base import PlatformAdapter


class TikTokAdapter(PlatformAdapter):
    """TikTok platform adapter."""

    PLATFORM_NAME = "tiktok"
    PLATFORM_LABEL = "TikTok"
    URL_PATTERNS = ["tiktok.com", "vm.tiktok.com"]

    # ── URL / ID extraction ───────────────────────────────────────

    def extract_id(self, url: str) -> str:
        """Extract aweme_id from a TikTok URL."""
        if "vm.tiktok.com" in url:
            url = self.resolve_short_url(url)
        m = re.search(r"/video/(\d+)", url)
        if m:
            return m.group(1)
        m = re.search(r"/photo/(\d+)", url)
        if m:
            return m.group(1)
        return url.strip()

    def _extract_sec_uid(self, url: str) -> str:
        """Extract secUid from a TikTok user URL."""
        if "vm.tiktok.com" in url:
            url = self.resolve_short_url(url)
        m = re.search(r"secUid=([^&]+)", url)
        if m:
            return m.group(1)
        m = re.search(r"/@([A-Za-z0-9_.]+)", url)
        if m:
            return m.group(1)
        return url.strip()

    # ── API methods ───────────────────────────────────────────────

    def get_info(self, url_or_id: str) -> dict:
        """Get video detail by aweme_id or URL."""
        aweme_id = self.extract_id(url_or_id) if url_or_id.startswith("http") else url_or_id
        return self._call("info", aweme_id=aweme_id)

    def get_user(self, url_or_id: str) -> dict:
        """Get user profile by secUid or URL."""
        sec_uid = self._extract_sec_uid(url_or_id) if url_or_id.startswith("http") else url_or_id
        return self._call("user", secUid=sec_uid)

    def get_posts(self, url_or_id: str, limit: int = 20, cursor: int = 0) -> dict:
        """Get user's posted videos."""
        sec_uid = self._extract_sec_uid(url_or_id) if url_or_id.startswith("http") else url_or_id
        # If it looks like a username (@handle), pass as unique_id
        if not sec_uid.startswith("MS4wLj"):  # secUid always starts with this
            return self._call("posts", unique_id=sec_uid, max_cursor=cursor, count=min(limit, 20))
        return self._call("posts", sec_user_id=sec_uid, max_cursor=cursor, count=min(limit, 20))

    def search(self, keyword: str, search_type: str = "video", limit: int = 20) -> dict:
        """Search TikTok content."""
        return self._call("search", keyword=keyword, offset=0)

    def get_trending(self) -> dict:
        """Get TikTok trending posts."""
        return self._call("trending")

    def get_comments(self, url_or_id: str, limit: int = 50, cursor: int = 0) -> dict:
        """Get video comments."""
        aweme_id = self.extract_id(url_or_id) if url_or_id.startswith("http") else url_or_id
        return self._call("comments", aweme_id=aweme_id, cursor=cursor, count=min(limit, 50))

    # ── Formatting ────────────────────────────────────────────────

    def format_info(self, data: dict) -> str:
        """Format TikTok video info as human-readable text."""
        aweme = self._dig_aweme(data)
        if not aweme:
            return f"⚠️ Cannot parse video data, raw response:\n{self._json_preview(data)}"

        desc = aweme.get("desc", "N/A")
        author = aweme.get("author", {})
        nickname = author.get("nickname", "N/A")
        unique_id = author.get("unique_id", "")
        duration = self._format_duration(aweme.get("duration", 0) // 1000 if aweme.get("duration", 0) > 1000 else aweme.get("duration", 0))
        create_time = self._ts_to_date(aweme.get("create_time"))

        stats = aweme.get("statistics", {})
        likes = self._compact_number(stats.get("digg_count", 0))
        comments = self._compact_number(stats.get("comment_count", 0))
        favorites = self._compact_number(stats.get("collect_count", 0))
        shares = self._compact_number(stats.get("share_count", 0))
        plays = self._compact_number(stats.get("play_count", 0))

        author_str = f"{nickname} (@{unique_id})" if unique_id else nickname

        lines = [
            f"📹 TikTok Video Detail",
            f"━━━━━━━━━━━━━━━━",
            f"Desc:     {desc}",
            f"Author:   {author_str}",
            f"Duration: {duration}",
            f"Posted:   {create_time}",
            f"",
            f"📊 Stats",
            f"Plays: {plays}  Likes: {likes}  Comments: {comments}  Favorites: {favorites}  Shares: {shares}",
        ]
        return "\n".join(lines)

    def format_user(self, data: dict) -> str:
        """Format TikTok user info."""
        user = self._dig_user(data)
        if not user:
            return f"⚠️ Cannot parse user data, raw response:\n{self._json_preview(data)}"

        nickname = user.get("nickname", "N/A")
        unique_id = user.get("unique_id", "")
        signature = user.get("signature", "")
        followers = self._compact_number(user.get("follower_count", 0))
        following = self._compact_number(user.get("following_count", 0))
        likes = self._compact_number(user.get("total_favorited", user.get("heart_count", 0)))
        videos = user.get("aweme_count", user.get("video_count", 0))

        lines = [
            f"👤 TikTok User Profile",
            f"━━━━━━━━━━━━━━━━",
            f"Name:      {nickname}",
            f"Username:  @{unique_id}",
            f"Bio:       {signature}",
            f"",
            f"📊 Stats",
            f"Followers: {followers}  Following: {following}  Likes: {likes}  Videos: {videos}",
        ]
        return "\n".join(lines)

    def format_comments(self, data: dict) -> str:
        """Format TikTok video comments."""
        comments = self._dig_comments(data)
        if not comments:
            return f"⚠️ Cannot parse comments, raw response:\n{self._json_preview(data)}"

        lines = ["💬 Comments", "━━━━━━━━━━━━━━━━"]
        for c in comments[:50]:
            user = c.get("user", {}).get("nickname", "Anonymous")
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
        return s[:max_len] + "\n..." if len(s) > max_len else s
