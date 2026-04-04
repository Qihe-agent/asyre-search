"""Twitter / X adapter for Asyre Search API."""

import re

from .base import PlatformAdapter


class TwitterAdapter(PlatformAdapter):
    """Twitter / X platform adapter."""

    PLATFORM_NAME = "twitter"
    PLATFORM_LABEL = "Twitter/X"
    URL_PATTERNS = ["twitter.com", "x.com"]

    # ── URL / ID extraction ───────────────────────────────────────

    def extract_id(self, url: str) -> str:
        """Extract tweet ID from a Twitter/X URL."""
        # /status/1234567890
        m = re.search(r"/status/(\d+)", url)
        if m:
            return m.group(1)
        return url.strip()

    def _extract_username(self, url: str) -> str:
        """Extract username from a Twitter/X URL."""
        # twitter.com/username or x.com/username (not /status/, /search, /i/, etc.)
        m = re.search(r"(?:twitter\.com|x\.com)/([A-Za-z0-9_]+)/?(?:\?|$)", url)
        if m and m.group(1).lower() not in ("search", "explore", "home", "i", "settings", "messages"):
            return m.group(1)
        return url.strip()

    # ── API methods ───────────────────────────────────────────────

    def get_info(self, url_or_id: str) -> dict:
        """Get tweet detail."""
        tweet_id = self.extract_id(url_or_id) if url_or_id.startswith("http") else url_or_id
        return self._get(
            "/api/v1/twitter/web/fetch_tweet_detail",
            params={"tweet_id": tweet_id},  # TODO: verify parameter name
        )

    def get_user(self, url_or_id: str) -> dict:
        """Get user profile by username or URL."""
        username = self._extract_username(url_or_id) if url_or_id.startswith("http") else url_or_id
        return self._get(
            "/api/v1/twitter/web/fetch_user_profile",
            params={"username": username},  # TODO: verify parameter name
        )

    def get_trending(self) -> dict:
        """Get Twitter trending topics."""
        return self._get("/api/v1/twitter/web/fetch_trending")

    # ── Formatting ────────────────────────────────────────────────

    def format_info(self, data: dict) -> str:
        """Format tweet detail as human-readable text."""
        tweet = self._dig_tweet(data)
        if not tweet:
            return f"⚠️ Cannot parse tweet data, raw response:\n{self._json_preview(data)}"

        text = tweet.get("full_text", tweet.get("text", "N/A"))
        user = tweet.get("user", tweet.get("core", {}).get("user_results", {}).get("result", {}).get("legacy", {}))
        name = user.get("name", "N/A")
        screen_name = user.get("screen_name", "")
        created = tweet.get("created_at", "N/A")

        likes = self._compact_number(tweet.get("favorite_count", 0))
        retweets = self._compact_number(tweet.get("retweet_count", 0))
        replies = self._compact_number(tweet.get("reply_count", 0))
        quotes = self._compact_number(tweet.get("quote_count", 0))
        views = self._compact_number(tweet.get("views", {}).get("count", 0) if isinstance(tweet.get("views"), dict) else tweet.get("view_count", 0))

        author_str = f"{name} (@{screen_name})" if screen_name else name

        lines = [
            f"🐦 Tweet Detail",
            f"━━━━━━━━━━━━━━━━",
            f"Author:  {author_str}",
            f"Posted:  {created}",
            f"",
            f"{text}",
            f"",
            f"📊 Stats",
            f"Views: {views}  Likes: {likes}  Retweets: {retweets}  Replies: {replies}  Quotes: {quotes}",
        ]
        return "\n".join(lines)

    def format_user(self, data: dict) -> str:
        """Format Twitter user info."""
        user = self._dig_user(data)
        if not user:
            return f"⚠️ Cannot parse user data, raw response:\n{self._json_preview(data)}"

        name = user.get("name", "N/A")
        screen_name = user.get("screen_name", "")
        bio = (user.get("description", "") or "")[:200]
        is_verified = "✅" if user.get("verified") or user.get("is_blue_verified") else ""
        followers = self._compact_number(user.get("followers_count", 0))
        following = self._compact_number(user.get("friends_count", user.get("following_count", 0)))
        tweets = self._compact_number(user.get("statuses_count", 0))
        created = user.get("created_at", "N/A")

        lines = [
            f"👤 Twitter User Profile {is_verified}",
            f"━━━━━━━━━━━━━━━━",
            f"Name:     {name}",
            f"Handle:   @{screen_name}",
            f"Bio:      {bio}",
            f"Joined:   {created}",
            f"",
            f"📊 Stats",
            f"Followers: {followers}  Following: {following}  Tweets: {tweets}",
        ]
        return "\n".join(lines)

    def format_trending(self, data: dict) -> str:
        """Format Twitter trending topics."""
        trends = self._dig_trending(data)
        if not trends:
            return f"⚠️ Cannot parse trending data, raw response:\n{self._json_preview(data)}"

        lines = ["🔥 Twitter Trending", "━━━━━━━━━━━━━━━━"]
        for i, item in enumerate(trends[:30], 1):
            name = item.get("name", item.get("trend_name", "N/A"))
            volume = item.get("tweet_volume", item.get("volume", ""))
            vol_str = f"  ({self._compact_number(volume)})" if volume else ""
            lines.append(f"{i:>2}. {name}{vol_str}")
        return "\n".join(lines)

    # ── Data navigation helpers ───────────────────────────────────

    @staticmethod
    def _dig_tweet(data: dict) -> dict:
        if not data:
            return {}
        for path in [
            lambda d: d.get("data", {}).get("tweet", {}).get("legacy", {}),
            lambda d: d.get("data", {}).get("tweetResult", {}).get("result", {}).get("legacy", {}),
            lambda d: d.get("data", {}).get("tweet", {}),
            lambda d: d.get("data", {}),
        ]:
            try:
                result = path(data)
                if result and (result.get("full_text") or result.get("text")):
                    return result
            except (KeyError, TypeError):
                continue
        return {}

    @staticmethod
    def _dig_user(data: dict) -> dict:
        if not data:
            return {}
        for path in [
            lambda d: d.get("data", {}).get("user", {}).get("legacy", {}),
            lambda d: d.get("data", {}).get("user", {}).get("result", {}).get("legacy", {}),
            lambda d: d.get("data", {}).get("user", {}),
            lambda d: d.get("user", {}),
            lambda d: d.get("data", {}),
        ]:
            try:
                result = path(data)
                if result and (result.get("screen_name") or result.get("name")):
                    return result
            except (KeyError, TypeError):
                continue
        return {}

    @staticmethod
    def _dig_trending(data: dict) -> list:
        if not data:
            return []
        for path in [
            lambda d: d.get("data", {}).get("trends", []),
            lambda d: d.get("data", []) if isinstance(d.get("data"), list) else [],
            lambda d: d.get("trends", []),
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
