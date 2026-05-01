"""Xiaohongshu (小红书) adapter for Asyre Search API."""

import re

from .base import PlatformAdapter


class XiaohongshuAdapter(PlatformAdapter):
    """Xiaohongshu (小红书) platform adapter."""

    PLATFORM_NAME = "xiaohongshu"
    PLATFORM_LABEL = "小红书"
    URL_PATTERNS = ["xiaohongshu.com", "xhslink.com"]

    # ── URL / ID extraction ───────────────────────────────────────

    def extract_id(self, url: str) -> str:
        """Extract note_id from a Xiaohongshu URL."""
        if "xhslink.com" in url:
            url = self.resolve_short_url(url)
        m = re.search(r"/(?:explore|discovery/item)/([a-f0-9]+)", url)
        if m:
            return m.group(1)
        return url.strip()

    def _extract_user_id(self, url: str) -> str:
        """Extract user_id from URL."""
        if "xhslink.com" in url:
            url = self.resolve_short_url(url)
        m = re.search(r"/user/profile/([a-f0-9]+)", url)
        if m:
            return m.group(1)
        return url.strip()

    # ── API methods ───────────────────────────────────────────────

    def get_info(self, url_or_id: str) -> dict:
        """Get note detail."""
        note_id = self.extract_id(url_or_id) if url_or_id.startswith("http") else url_or_id
        return self._call("info", note_id=note_id)

    def get_user(self, url_or_id: str) -> dict:
        """Get user info."""
        user_id = self._extract_user_id(url_or_id) if url_or_id.startswith("http") else url_or_id
        return self._call("user", user_id=user_id)

    def get_posts(self, url_or_id: str, limit: int = 20, cursor: int = 0) -> dict:
        """Get user's posted notes."""
        user_id = self._extract_user_id(url_or_id) if url_or_id.startswith("http") else url_or_id
        params = {"user_id": user_id}
        if cursor:
            params["lastCursor"] = str(cursor)
        return self._call("posts", **params)

    def search(self, keyword: str, search_type: str = "note", limit: int = 20) -> dict:
        """Search notes/users with keyword variant fallback.

        XHS upstream has counter-intuitive risk control: SHORT keywords are blocked
        (400) more aggressively than full names (which hit "exact match" path).
        We try the original keyword first, then progressively shorter variants
        only if 0 items returned. Endpoint-level fallback is handled by base._call.
        """
        action = "search_users" if search_type == "user" else "search"

        variants = [keyword]
        # Variant 1: drop noise particles (的/之/了) — sometimes matches better
        for ch in ["的", "之"]:
            if ch in keyword:
                stripped = keyword.replace(ch, "")
                if stripped and stripped not in variants:
                    variants.append(stripped)
        # Variant 2: trim long names to 6 chars — last-ditch broad search
        if len(keyword) > 6:
            short = keyword[:6]
            if short not in variants:
                variants.append(short)

        last_result = None
        for kw in variants:
            try:
                last_result = self._call(action, keyword=kw, page=1)
            except Exception:
                continue
            if self._has_search_results(last_result):
                if isinstance(last_result, dict):
                    last_result.setdefault("_asyre_meta", {})["keyword_used"] = kw
                    if kw != keyword:
                        last_result["_asyre_meta"]["keyword_variants_tried"] = variants[:variants.index(kw)+1]
                return last_result
        return last_result or {}

    @staticmethod
    def _has_search_results(data: dict) -> bool:
        """Detect if a search response actually has items (handles XHS double-nesting)."""
        if not isinstance(data, dict):
            return False
        # Try common paths where XHS items show up
        for path in [
            lambda d: d.get("data", {}).get("items"),
            lambda d: d.get("data", {}).get("data", {}).get("items"),
            lambda d: d.get("data", {}).get("notes"),
            lambda d: d.get("data", {}).get("users"),
        ]:
            try:
                items = path(data)
                if items:
                    return True
            except (AttributeError, TypeError):
                continue
        return False

    def get_trending(self) -> dict:
        """Get Xiaohongshu hot list."""
        return self._call("trending")

    def get_comments(self, url_or_id: str, limit: int = 50, cursor: int = 0) -> dict:
        """Get note comments."""
        note_id = self.extract_id(url_or_id) if url_or_id.startswith("http") else url_or_id
        params = {"note_id": note_id}
        if cursor:
            params["start"] = str(cursor)
        return self._call("comments", **params)

    # ── Formatting ────────────────────────────────────────────────

    def format_info(self, data: dict) -> str:
        """Format Xiaohongshu note info."""
        note = self._dig_note(data)
        if not note:
            return f"⚠️ 无法解析笔记数据，原始响应:\n{self._json_preview(data)}"

        title = note.get("title", "")
        desc = note.get("desc", "")
        display_text = title or desc or "N/A"
        user = note.get("user", {})
        nickname = user.get("nickname", "N/A")
        note_type = "视频笔记" if note.get("type") == "video" else "图文笔记"

        interact = note.get("interact_info", {})
        likes = self._compact_number(interact.get("liked_count", 0))
        comments = self._compact_number(interact.get("comment_count", 0))
        collects = self._compact_number(interact.get("collected_count", 0))
        shares = self._compact_number(interact.get("share_count", 0))

        tags = []
        for tag in note.get("tag_list", []):
            tag_name = tag.get("name", "")
            if tag_name:
                tags.append(f"#{tag_name}")
        tags_str = " ".join(tags) if tags else "N/A"

        lines = [
            f"📕 小红书{note_type}详情",
            f"━━━━━━━━━━━━━━━━",
            f"标题:   {display_text}",
            f"作者:   {nickname}",
            f"话题:   {tags_str}",
            f"",
            f"📊 互动数据",
            f"点赞: {likes}  评论: {comments}  收藏: {collects}  分享: {shares}",
        ]
        return "\n".join(lines)

    def format_user(self, data: dict) -> str:
        """Format Xiaohongshu user info."""
        user = self._dig_user(data)
        if not user:
            return f"⚠️ 无法解析用户数据，原始响应:\n{self._json_preview(data)}"

        nickname = user.get("nickname", "N/A")
        desc = user.get("desc", "")
        fans = self._compact_number(user.get("fans", 0))
        follows = self._compact_number(user.get("follows", 0))
        interaction = self._compact_number(user.get("interaction", 0))

        lines = [
            f"👤 小红书用户信息",
            f"━━━━━━━━━━━━━━━━",
            f"昵称:   {nickname}",
            f"简介:   {desc}",
            f"",
            f"📊 数据",
            f"粉丝: {fans}  关注: {follows}  获赞与收藏: {interaction}",
        ]
        return "\n".join(lines)

    # ── Data navigation ───────────────────────────────────────────

    @staticmethod
    def _dig_note(data: dict) -> dict:
        if not data:
            return {}
        for path in [
            lambda d: d.get("data", {}).get("note_detail", {}),
            lambda d: d.get("data", {}).get("items", [{}])[0].get("note_card", {}) if d.get("data", {}).get("items") else {},
            # app/get_note_info returns data as list
            lambda d: d.get("data", [{}])[0].get("note_list", [{}])[0] if isinstance(d.get("data"), list) and d.get("data") else {},
            lambda d: d.get("data", {}),
        ]:
            try:
                result = path(data)
                if result and (result.get("title") or result.get("desc") or result.get("liked_count") is not None):
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
            lambda d: d.get("data", {}).get("data", {}),
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
    def _json_preview(data, max_len=300):
        import json
        s = json.dumps(data, ensure_ascii=False, indent=2)
        return s[:max_len] + "\n..." if len(s) > max_len else s
