"""Base adapter for Asyre Search platform APIs."""

import json
import os
import re
import sys
from datetime import datetime
from urllib.parse import urljoin

import requests

# Per-endpoint hard timeout. Was 60s — that caused LLM "sleep+retry" loops on
# upstream 504s. 15s gives upstream enough time but fails fast so fallback can kick in.
DEFAULT_TIMEOUT = int(os.environ.get("ASYRE_SEARCH_TIMEOUT", "15"))


class UpstreamUnavailable(RuntimeError):
    """5xx / connection error / timeout from upstream. Try next endpoint in chain."""

    def __init__(self, status_code, body, path):
        self.status_code = status_code
        self.body = body
        self.path = path
        super().__init__(f"upstream {status_code} on {path}")


class RiskControlBlocked(RuntimeError):
    """4xx from upstream — params malformed OR upstream rejected (rate-limit / risk control).
    Try next endpoint, but if all fail it is likely a real param/keyword issue."""

    def __init__(self, status_code, body, path):
        self.status_code = status_code
        self.body = body
        self.path = path
        super().__init__(f"blocked {status_code} on {path}")


# Lazy-loaded singleton registry
_registry = None


def get_registry():
    """Get or create the shared EndpointRegistry instance."""
    global _registry
    if _registry is None:
        from .registry import EndpointRegistry
        _registry = EndpointRegistry()
    return _registry


class PlatformAdapter:
    """Asyre Search platform adapter base class."""

    PLATFORM_NAME = ""
    PLATFORM_LABEL = ""  # Human-readable name (e.g. "抖音", "TikTok")
    BASE_URL = os.environ.get("ASYRE_SEARCH_URL", "http://13.228.189.206/api/social")
    URL_PATTERNS = []  # List of domain patterns this adapter handles

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.registry = get_registry()
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
            resp = self.session.get(url, params=params, timeout=DEFAULT_TIMEOUT)
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.HTTPError as e:
            self._handle_error(e, resp)
        except requests.exceptions.RequestException as e:
            # Connection error / timeout / DNS failure - treat as upstream unavailable
            raise UpstreamUnavailable(0, str(e), getattr(resp if 'resp' in dir() else None, 'url', endpoint)) from e

    def _post(self, endpoint: str, data: dict = None, params: dict = None) -> dict:
        """Send POST request to API."""
        url = urljoin(self.BASE_URL + "/", endpoint.lstrip("/"))
        try:
            resp = self.session.post(url, json=data, params=params, timeout=DEFAULT_TIMEOUT)
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.HTTPError as e:
            self._handle_error(e, resp)
        except requests.exceptions.RequestException as e:
            raise UpstreamUnavailable(0, str(e), getattr(resp if 'resp' in dir() else None, 'url', endpoint)) from e

    def _call(self, action: str, variant: str = None, **kwargs) -> dict:
        """Resolve endpoint chain and call with automatic fallback on failure.

        Walks the action's fallback chain (configured in action_map.json) trying
        each endpoint in priority order. First endpoint that returns 2xx wins.
        On 5xx / timeout / connection error, immediately tries next endpoint.
        On 4xx, also tries next (might be endpoint-specific param mismatch).

        Args:
            action: CLI action name (info, user, posts, search, trending, comments)
            variant: optional sub-variant (e.g. "by_url", "by_id")
            **kwargs: parameters to pass to the endpoint

        Returns:
            API response dict from the first successful endpoint.

        Raises:
            UpstreamUnavailable if all endpoints in chain fail with 5xx/timeout.
            RiskControlBlocked  if all endpoints fail with 4xx (likely real param issue).
        """
        chain = self.registry.resolve_chain(self.PLATFORM_NAME, action, variant)
        last_exc = None
        attempts = []

        for spec in chain:
            try:
                if spec.method == "POST":
                    query_params = {}
                    body = {}
                    param_keys = set(spec.params.keys()) if spec.params else set()
                    for k, v in kwargs.items():
                        if k in param_keys:
                            query_params[k] = v
                        else:
                            body[k] = v
                    result = self._post(spec.path, data=body or None, params=query_params or None)
                else:
                    result = self._get(spec.path, params=kwargs or None)

                # Tag which endpoint succeeded (for debugging/observability)
                if isinstance(result, dict):
                    result.setdefault("_asyre_meta", {})["endpoint_used"] = spec.path
                    if attempts:
                        result["_asyre_meta"]["fallback_attempts"] = attempts
                return result
            except (UpstreamUnavailable, RiskControlBlocked) as e:
                attempts.append({"path": spec.path, "status": e.status_code,
                                 "reason": type(e).__name__})
                last_exc = e
                continue

        # All endpoints failed
        if last_exc:
            raise last_exc
        raise RuntimeError(f"No endpoints available for {self.PLATFORM_NAME}/{action}")

    def _handle_error(self, error, resp):
        """Raise typed exception with API error details.

        5xx -> UpstreamUnavailable (retry on next endpoint)
        4xx -> RiskControlBlocked  (retry on next endpoint, but likely param/keyword issue)
        """
        try:
            body = resp.json()
        except Exception:
            body = resp.text[:500]
        sc = resp.status_code
        if 500 <= sc < 600:
            raise UpstreamUnavailable(sc, body, resp.url)
        if 400 <= sc < 500:
            raise RiskControlBlocked(sc, body, resp.url)
        raise RuntimeError(f"API error ({sc}): {body}")

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
