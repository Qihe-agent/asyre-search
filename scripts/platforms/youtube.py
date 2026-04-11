"""YouTube adapter for Asyre Search API."""

import re

from .base import PlatformAdapter


class YouTubeAdapter(PlatformAdapter):
    """YouTube platform adapter."""

    PLATFORM_NAME = "youtube"
    PLATFORM_LABEL = "YouTube"
    URL_PATTERNS = ["youtube.com", "youtu.be"]

    # ── URL / ID extraction ───────────────────────────────────────

    def extract_id(self, url: str) -> str:
        """Extract video ID from a YouTube URL."""
        m = re.search(r"youtu\.be/([A-Za-z0-9_-]{11})", url)
        if m:
            return m.group(1)
        m = re.search(r"[?&]v=([A-Za-z0-9_-]{11})", url)
        if m:
            return m.group(1)
        m = re.search(r"/shorts/([A-Za-z0-9_-]{11})", url)
        if m:
            return m.group(1)
        m = re.search(r"/embed/([A-Za-z0-9_-]{11})", url)
        if m:
            return m.group(1)
        return url.strip()

    def _extract_channel_id(self, url: str) -> str:
        """Extract channel ID or handle from URL."""
        m = re.search(r"/channel/(UC[A-Za-z0-9_-]+)", url)
        if m:
            return m.group(1)
        m = re.search(r"/@([A-Za-z0-9_.-]+)", url)
        if m:
            return m.group(1)
        m = re.search(r"/c/([A-Za-z0-9_.-]+)", url)
        if m:
            return m.group(1)
        return url.strip()

    # ── API methods ───────────────────────────────────────────────

    def get_info(self, url_or_id: str) -> dict:
        """Get video detail."""
        video_id = self.extract_id(url_or_id) if url_or_id.startswith("http") else url_or_id
        return self._call("info", video_id=video_id)

    def get_user(self, url_or_id: str) -> dict:
        """Get channel detail."""
        channel_id = self._extract_channel_id(url_or_id) if url_or_id.startswith("http") else url_or_id
        return self._call("user", channel_id=channel_id)

    def get_posts(self, url_or_id: str, limit: int = 20, cursor: int = 0) -> dict:
        """Get channel videos."""
        channel_id = self._extract_channel_id(url_or_id) if url_or_id.startswith("http") else url_or_id
        return self._call("posts", channel_id=channel_id)

    def search(self, keyword: str, search_type: str = "video", limit: int = 20) -> dict:
        """Search YouTube content."""
        return self._call("search", search_query=keyword)

    def get_trending(self) -> dict:
        """Get YouTube trending videos."""
        return self._call("trending")

    def get_comments(self, url_or_id: str, limit: int = 50, cursor: int = 0) -> dict:
        """Get video comments."""
        video_id = self.extract_id(url_or_id) if url_or_id.startswith("http") else url_or_id
        return self._call("comments", video_id=video_id)

    # ── Formatting ────────────────────────────────────────────────

    def format_info(self, data: dict) -> str:
        """Format YouTube video info as human-readable text."""
        video = self._dig_video(data)
        if not video:
            return f"⚠️ Cannot parse video data, raw response:\n{self._json_preview(data)}"

        title = video.get("title", "N/A")
        author = video.get("author", video.get("channel", {}))
        if isinstance(author, str):
            channel_name = author
        else:
            channel_name = author.get("name", author.get("title", "N/A"))

        duration = video.get("lengthText", video.get("duration", "N/A"))
        published = video.get("publishedTimeText", video.get("publish_date", "N/A"))
        description = (video.get("description", "") or "")[:200]

        views = self._compact_number(video.get("viewCount", video.get("view_count", 0)))
        likes = self._compact_number(video.get("likeCount", video.get("like_count", 0)))

        lines = [
            f"📹 YouTube Video Detail",
            f"━━━━━━━━━━━━━━━━",
            f"Title:    {title}",
            f"Channel:  {channel_name}",
            f"Duration: {duration}",
            f"Posted:   {published}",
            f"Desc:     {description}{'...' if len(video.get('description', '') or '') > 200 else ''}",
            f"",
            f"📊 Stats",
            f"Views: {views}  Likes: {likes}",
        ]
        return "\n".join(lines)

    def format_user(self, data: dict) -> str:
        """Format YouTube channel info."""
        channel = self._dig_channel(data)
        if not channel:
            return f"⚠️ Cannot parse channel data, raw response:\n{self._json_preview(data)}"

        name = channel.get("title", channel.get("name", "N/A"))
        handle = channel.get("vanityChannelUrl", channel.get("handle", ""))
        description = (channel.get("description", "") or "")[:200]
        subscribers = channel.get("subscriberCountText", self._compact_number(channel.get("subscriber_count", 0)))
        videos = channel.get("videoCountText", channel.get("video_count", "N/A"))

        lines = [
            f"📺 YouTube Channel",
            f"━━━━━━━━━━━━━━━━",
            f"Name:        {name}",
            f"Handle:      {handle}",
            f"Description: {description}",
            f"",
            f"📊 Stats",
            f"Subscribers: {subscribers}  Videos: {videos}",
        ]
        return "\n".join(lines)

    # ── Data navigation helpers ───────────────────────────────────

    @staticmethod
    def _dig_video(data: dict) -> dict:
        if not data:
            return {}
        for path in [
            lambda d: d.get("data", {}).get("videoDetails", {}),
            lambda d: d.get("data", {}).get("video", {}),
            lambda d: d.get("videoDetails", {}),
            lambda d: d.get("data", {}),
        ]:
            try:
                result = path(data)
                if result and (result.get("title") or result.get("videoId")):
                    return result
            except (KeyError, TypeError):
                continue
        return {}

    @staticmethod
    def _dig_channel(data: dict) -> dict:
        if not data:
            return {}
        for path in [
            lambda d: d.get("data", {}).get("channel", {}),
            lambda d: d.get("data", {}).get("header", {}),
            lambda d: d.get("channel", {}),
            lambda d: d.get("data", {}),
        ]:
            try:
                result = path(data)
                if result and (result.get("title") or result.get("name")):
                    return result
            except (KeyError, TypeError):
                continue
        return {}

    @staticmethod
    def _json_preview(data, max_len=300):
        import json
        s = json.dumps(data, ensure_ascii=False, indent=2)
        return s[:max_len] + "\n..." if len(s) > max_len else s
