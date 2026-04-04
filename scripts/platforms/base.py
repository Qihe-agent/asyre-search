"""Base adapter for Asyre Search platform APIs."""

import json
import os
import re
import sys
from datetime import datetime
from urllib.parse import urljoin

import requests


class PlatformAdapter:
    """Asyre Search platform adapter base class."""

    PLATFORM_NAME = ""
    PLATFORM_LABEL = ""  # Human-readable name (e.g. "抖音", "TikTok")
    BASE_URL = os.environ.get("ASYRE_SEARCH_URL", "https://api.tikhub.io")
    URL_PATTERNS = []  # List of domain patterns this adapter handles

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {api_key}",
            "Accept": "application/json",
            "User-Agent": "Asyre-Search/1.0",
        })

    # ── HTTP helpers ──────────────────────────────────────────────

    def _get(self, endpoint: str, params: dict = None) -> dict:
        """Send GET request to API."""
        url = urljoin(self.BASE_URL + "/", endpoint.lstrip("/"))
        try:
            resp = self.session.get(url, params=params, timeout=30)
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.HTTPError as e:
            self._handle_error(e, resp)
        except requests.exceptions.RequestException as e:
            print(f"❌ Request failed: {e}", file=sys.stderr)
            sys.exit(1)

    def _post(self, endpoint: str, data: dict = None, params: dict = None) -> dict:
        """Send POST request to API."""
        url = urljoin(self.BASE_URL + "/", endpoint.lstrip("/"))
        try:
            resp = self.session.post(url, json=data, params=params, timeout=30)
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.HTTPError as e:
            self._handle_error(e, resp)
        except requests.exceptions.RequestException as e:
            print(f"❌ Request failed: {e}", file=sys.stderr)
            sys.exit(1)

    def _handle_error(self, error, resp):
        """Print clear error info and exit."""
        try:
            body = resp.json()
        except Exception:
            body = resp.text[:500]
        print(f"❌ API error ({resp.status_code}): {body}", file=sys.stderr)
        sys.exit(1)

    # ── URL detection ─────────────────────────────────────────────

    def can_handle_url(self, url: str) -> bool:
        """Check if this adapter can handle the given URL."""
        url_lower = url.lower()
        return any(pattern in url_lower for pattern in self.URL_PATTERNS)

    def resolve_short_url(self, url: str) -> str:
        """Follow redirects on short URLs to get the final URL."""
        try:
            resp = requests.head(url, allow_redirects=True, timeout=10,
                                 headers={"User-Agent": "Mozilla/5.0"})
            return resp.url
        except Exception:
            return url

    def extract_id(self, url: str) -> str:
        """Extract content ID from URL. Override in subclasses."""
        raise NotImplementedError

    # ── Core methods (override in subclasses) ─────────────────────

    def get_info(self, url_or_id: str) -> dict:
        raise NotImplementedError(f"{self.PLATFORM_NAME}: get_info not implemented")

    def get_user(self, url_or_id: str) -> dict:
        raise NotImplementedError(f"{self.PLATFORM_NAME}: get_user not implemented")

    def get_posts(self, url_or_id: str, limit: int = 20, cursor: int = 0) -> dict:
        raise NotImplementedError(f"{self.PLATFORM_NAME}: get_posts not implemented")

    def search(self, keyword: str, search_type: str = "video", limit: int = 20) -> dict:
        raise NotImplementedError(f"{self.PLATFORM_NAME}: search not implemented")

    def get_trending(self) -> dict:
        raise NotImplementedError(f"{self.PLATFORM_NAME}: get_trending not implemented")

    def get_comments(self, url_or_id: str, limit: int = 50, cursor: int = 0) -> dict:
        raise NotImplementedError(f"{self.PLATFORM_NAME}: get_comments not implemented")

    # ── Formatting helpers ────────────────────────────────────────

    def format_info(self, data: dict) -> str:
        return json.dumps(data, ensure_ascii=False, indent=2)

    def format_user(self, data: dict) -> str:
        return json.dumps(data, ensure_ascii=False, indent=2)

    def format_posts(self, data: dict) -> str:
        return json.dumps(data, ensure_ascii=False, indent=2)

    def format_trending(self, data: dict) -> str:
        return json.dumps(data, ensure_ascii=False, indent=2)

    def format_comments(self, data: dict) -> str:
        return json.dumps(data, ensure_ascii=False, indent=2)

    def format_search(self, data: dict) -> str:
        return json.dumps(data, ensure_ascii=False, indent=2)

    # ── Utility ───────────────────────────────────────────────────

    @staticmethod
    def _ts_to_date(ts) -> str:
        if not ts:
            return "N/A"
        try:
            return datetime.fromtimestamp(int(ts)).strftime("%Y-%m-%d")
        except (ValueError, TypeError, OSError):
            return str(ts)

    @staticmethod
    def _format_duration(seconds) -> str:
        if not seconds:
            return "N/A"
        try:
            seconds = int(seconds)
            m, s = divmod(seconds, 60)
            return f"{m}:{s:02d}"
        except (ValueError, TypeError):
            return str(seconds)

    @staticmethod
    def _compact_number(n) -> str:
        if n is None:
            return "0"
        try:
            n = int(n)
        except (ValueError, TypeError):
            return str(n)
        if n >= 100_000_000:
            return f"{n / 100_000_000:.1f}亿"
        if n >= 10_000:
            return f"{n / 10_000:.1f}万"
        return str(n)
