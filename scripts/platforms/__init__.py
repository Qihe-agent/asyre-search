"""Asyre Search platform adapters."""

from .douyin import DouyinAdapter
from .xiaohongshu import XiaohongshuAdapter
from .bilibili import BilibiliAdapter
from .tiktok import TikTokAdapter
from .youtube import YouTubeAdapter
from .instagram import InstagramAdapter
from .twitter import TwitterAdapter

# Registry: platform_name -> adapter_class
ADAPTERS = {
    "douyin": DouyinAdapter,
    "xiaohongshu": XiaohongshuAdapter,
    "bilibili": BilibiliAdapter,
    "tiktok": TikTokAdapter,
    "youtube": YouTubeAdapter,
    "instagram": InstagramAdapter,
    "twitter": TwitterAdapter,
}

# All adapter instances for URL matching
def get_all_adapters(api_key: str):
    """Return instantiated adapters for all platforms."""
    return [cls(api_key) for cls in ADAPTERS.values()]

def detect_platform(url: str, api_key: str):
    """Detect platform from URL and return matching adapter."""
    for adapter in get_all_adapters(api_key):
        if adapter.can_handle_url(url):
            return adapter
    return None
