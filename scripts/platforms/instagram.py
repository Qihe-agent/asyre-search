"""Instagram adapter for Asyre Search API."""

import re

from .base import PlatformAdapter


class InstagramAdapter(PlatformAdapter):
    """Instagram platform adapter."""

    PLATFORM_NAME = "instagram"
    PLATFORM_LABEL = "Instagram"
    URL_PATTERNS = ["instagram.com"]

    # ── URL / ID extraction ───────────────────────────────────────

    def extract_id(self, url: str) -> str:
        """Extract shortcode from an Instagram URL."""
        # /p/SHORTCODE/ or /reel/SHORTCODE/ or /tv/SHORTCODE/
        m = re.search(r"/(?:p|reel|tv)/([A-Za-z0-9_-]+)", url)
        if m:
            return m.group(1)
        return url.strip()

    def _extract_username(self, url: str) -> str:
        """Extract username from an Instagram URL."""
        # instagram.com/username (not /p/, /reel/, /explore/, etc.)
        m = re.search(r"instagram\.com/([A-Za-z0-9_.]+)/?(?:\?|$)", url)
        if m:
            return m.group(1)
        return url.strip()

    # ── API methods ───────────────────────────────────────────────

    def get_info(self, url_or_id: str) -> dict:
        """Get post detail by shortcode or URL."""
        shortcode = self.extract_id(url_or_id) if url_or_id.startswith("http") else url_or_id
        return self._get(
            "/api/v1/instagram/v2/fetch_post_detail",
            params={"shortcode": shortcode},  # TODO: verify parameter name
        )

    def get_user(self, url_or_id: str) -> dict:
        """Get user info by username or URL."""
        username = self._extract_username(url_or_id) if url_or_id.startswith("http") else url_or_id
        return self._get(
            "/api/v1/instagram/v2/fetch_user_info",
            params={"username": username},  # TODO: verify parameter name
        )

    # ── Formatting ────────────────────────────────────────────────

    def format_info(self, data: dict) -> str:
        """Format Instagram post info as human-readable text."""
        post = self._dig_post(data)
        if not post:
            return f"⚠️ Cannot parse post data, raw response:\n{self._json_preview(data)}"

        caption_obj = post.get("caption", {}) or {}
        caption = caption_obj.get("text", "") if isinstance(caption_obj, dict) else str(caption_obj)
        caption = caption[:200]

        owner = post.get("owner", post.get("user", {}))
        username = owner.get("username", "N/A") if isinstance(owner, dict) else "N/A"
        media_type = post.get("media_type", post.get("__typename", "N/A"))
        taken_at = self._ts_to_date(post.get("taken_at"))

        likes = self._compact_number(post.get("like_count", post.get("edge_media_preview_like", {}).get("count", 0)))
        comments = self._compact_number(post.get("comment_count", post.get("edge_media_to_comment", {}).get("count", 0)))

        lines = [
            f"📷 Instagram Post Detail",
            f"━━━━━━━━━━━━━━━━",
            f"Caption:  {caption}{'...' if len(str(caption_obj.get('text', '') if isinstance(caption_obj, dict) else '')) > 200 else ''}",
            f"Author:   @{username}",
            f"Type:     {media_type}",
            f"Posted:   {taken_at}",
            f"",
            f"📊 Stats",
            f"Likes: {likes}  Comments: {comments}",
        ]
        return "\n".join(lines)

    def format_user(self, data: dict) -> str:
        """Format Instagram user info."""
        user = self._dig_user(data)
        if not user:
            return f"⚠️ Cannot parse user data, raw response:\n{self._json_preview(data)}"

        username = user.get("username", "N/A")
        full_name = user.get("full_name", "")
        bio = (user.get("biography", "") or "")[:200]
        is_verified = "✅" if user.get("is_verified") else ""
        followers = self._compact_number(user.get("follower_count", user.get("edge_followed_by", {}).get("count", 0)))
        following = self._compact_number(user.get("following_count", user.get("edge_follow", {}).get("count", 0)))
        posts = user.get("media_count", user.get("edge_owner_to_timeline_media", {}).get("count", "N/A"))

        lines = [
            f"👤 Instagram User Profile {is_verified}",
            f"━━━━━━━━━━━━━━━━",
            f"Username:  @{username}",
            f"Name:      {full_name}",
            f"Bio:       {bio}",
            f"",
            f"📊 Stats",
            f"Followers: {followers}  Following: {following}  Posts: {posts}",
        ]
        return "\n".join(lines)

    # ── Data navigation helpers ───────────────────────────────────

    @staticmethod
    def _dig_post(data: dict) -> dict:
        if not data:
            return {}
        for path in [
            lambda d: d.get("data", {}).get("items", [{}])[0] if d.get("data", {}).get("items") else {},
            lambda d: d.get("data", {}).get("media", {}),
            lambda d: d.get("data", {}).get("shortcode_media", {}),
            lambda d: d.get("data", {}),
        ]:
            try:
                result = path(data)
                if result and (result.get("caption") is not None or result.get("owner") or result.get("user")):
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
                if result and result.get("username"):
                    return result
            except (KeyError, TypeError):
                continue
        return {}

    @staticmethod
    def _json_preview(data, max_len=300):
        import json
        s = json.dumps(data, ensure_ascii=False, indent=2)
        return s[:max_len] + "\n..." if len(s) > max_len else s
