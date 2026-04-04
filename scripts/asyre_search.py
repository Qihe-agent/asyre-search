#!/usr/bin/env python3
"""Asyre Search — 全平台社媒数据查询工具。

Usage:
    python3 scripts/asyre_search.py info <URL>
    python3 scripts/asyre_search.py user <URL_or_ID> --platform douyin
    python3 scripts/asyre_search.py posts <URL_or_ID> --platform douyin [--limit 20]
    python3 scripts/asyre_search.py search <keyword> --platform douyin [--type video]
    python3 scripts/asyre_search.py trending --platform douyin
    python3 scripts/asyre_search.py comments <URL_or_ID> --platform douyin [--limit 50]
    python3 scripts/asyre_search.py raw /api/v1/douyin/app/v3/fetch_hot_search_list [--params key=value]
"""

import argparse
import json
import os
import sys

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_DIR = os.path.dirname(_SCRIPT_DIR)
if _PROJECT_DIR not in sys.path:
    sys.path.insert(0, _PROJECT_DIR)

from scripts.platforms import ADAPTERS, detect_platform, get_all_adapters
from scripts.platforms.base import PlatformAdapter


# ── API key resolution ────────────────────────────────────────────

def _load_api_key() -> str:
    """Load API key from environment."""
    key = os.environ.get("ASYRE_SEARCH_KEY")
    if key:
        return key
    # Fallback to legacy env var
    key = os.environ.get("TIKHUB_API_KEY")
    if key:
        return key

    print("❌ ASYRE_SEARCH_KEY not found. Set it via environment variable.", file=sys.stderr)
    sys.exit(1)


# ── URL platform auto-detection ───────────────────────────────────

def _resolve_url(url: str) -> str:
    """Resolve short URLs via HEAD request if needed."""
    import requests

    short_domains = ["v.douyin.com", "vm.tiktok.com", "b23.tv", "xhslink.com", "t.co"]
    if any(d in url for d in short_domains):
        try:
            resp = requests.head(url, allow_redirects=True, timeout=10,
                                 headers={"User-Agent": "Mozilla/5.0"})
            return resp.url
        except Exception:
            pass
    return url


# ── Output helpers ────────────────────────────────────────────────

def _output(data, fmt: str, adapter=None, format_fn: str = None, output_file: str = None):
    """Output data in the requested format."""
    if fmt == "json" or fmt == "raw":
        text = json.dumps(data, ensure_ascii=False, indent=2)
    elif adapter and format_fn:
        fn = getattr(adapter, format_fn, None)
        text = fn(data) if fn else json.dumps(data, ensure_ascii=False, indent=2)
    else:
        text = json.dumps(data, ensure_ascii=False, indent=2)

    if output_file:
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"✅ Output saved to {output_file}")
    else:
        print(text)


# ── Subcommand handlers ──────────────────────────────────────────

def cmd_info(args):
    api_key = _load_api_key()
    url = args.target
    resolved = _resolve_url(url)

    adapter = detect_platform(resolved, api_key)
    if not adapter and resolved != url:
        adapter = detect_platform(url, api_key)
    if not adapter:
        print(f"❌ Cannot detect platform from URL: {url}", file=sys.stderr)
        print(f"   Supported: douyin, xiaohongshu, bilibili, tiktok, youtube, instagram, twitter", file=sys.stderr)
        sys.exit(1)

    print(f"🔍 Detected platform: {adapter.PLATFORM_LABEL} ({adapter.PLATFORM_NAME})", file=sys.stderr)
    data = adapter.get_info(resolved)
    _output(data, "json" if args.raw else args.format, adapter, "format_info", args.output)


def cmd_user(args):
    api_key = _load_api_key()
    adapter = _get_adapter(args.platform, api_key)
    data = adapter.get_user(args.target)
    _output(data, "json" if args.raw else args.format, adapter, "format_user", args.output)


def cmd_posts(args):
    api_key = _load_api_key()
    adapter = _get_adapter(args.platform, api_key)
    data = adapter.get_posts(args.target, limit=args.limit)
    _output(data, "json" if args.raw else args.format, adapter, "format_posts", args.output)


def cmd_search(args):
    api_key = _load_api_key()
    adapter = _get_adapter(args.platform, api_key)
    data = adapter.search(args.keyword, search_type=args.type, limit=args.limit)
    _output(data, "json" if args.raw else args.format, adapter, "format_search", args.output)


def cmd_trending(args):
    api_key = _load_api_key()
    adapter = _get_adapter(args.platform, api_key)
    data = adapter.get_trending()
    _output(data, "json" if args.raw else args.format, adapter, "format_trending", args.output)


def cmd_comments(args):
    api_key = _load_api_key()
    adapter = _get_adapter(args.platform, api_key)
    data = adapter.get_comments(args.target, limit=args.limit)
    _output(data, "json" if args.raw else args.format, adapter, "format_comments", args.output)


def cmd_raw(args):
    api_key = _load_api_key()
    adapter = PlatformAdapter(api_key)
    params = {}
    if args.params:
        for pair in args.params:
            if "=" in pair:
                k, v = pair.split("=", 1)
                params[k] = v
    data = adapter._get(args.endpoint, params=params or None)
    _output(data, "json", output_file=args.output)


# ── Helpers ───────────────────────────────────────────────────────

def _get_adapter(platform: str, api_key: str) -> PlatformAdapter:
    if not platform:
        print("❌ --platform is required for this command.", file=sys.stderr)
        print(f"   Available: {', '.join(ADAPTERS.keys())}", file=sys.stderr)
        sys.exit(1)
    cls = ADAPTERS.get(platform.lower())
    if not cls:
        print(f"❌ Unknown platform: {platform}", file=sys.stderr)
        print(f"   Available: {', '.join(ADAPTERS.keys())}", file=sys.stderr)
        sys.exit(1)
    return cls(api_key)


# ── CLI entry point ───────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        prog="asyre-search",
        description="Asyre Search — 全平台社媒数据查询工具",
        epilog="Supported platforms: douyin, xiaohongshu, bilibili, tiktok, youtube, instagram, twitter",
    )
    parser.add_argument("--format", "-f", choices=["json", "table", "text"], default="table")
    parser.add_argument("--raw", action="store_true", help="Output raw JSON")
    parser.add_argument("--platform", "-p", help="Target platform")
    parser.add_argument("-o", "--output", help="Save output to file")

    sub = parser.add_subparsers(dest="command", help="Available commands")

    p = sub.add_parser("info", help="视频/帖子详情（自动识别平台）")
    p.add_argument("target", help="URL")
    p.set_defaults(func=cmd_info)

    p = sub.add_parser("user", help="用户信息")
    p.add_argument("target", help="User URL or ID")
    p.set_defaults(func=cmd_user)

    p = sub.add_parser("posts", help="用户作品列表")
    p.add_argument("target", help="User URL or ID")
    p.add_argument("--limit", type=int, default=20)
    p.set_defaults(func=cmd_posts)

    p = sub.add_parser("search", help="搜索内容")
    p.add_argument("keyword")
    p.add_argument("--type", default="video")
    p.add_argument("--limit", type=int, default=20)
    p.set_defaults(func=cmd_search)

    p = sub.add_parser("trending", help="热搜/趋势")
    p.set_defaults(func=cmd_trending)

    p = sub.add_parser("comments", help="评论列表")
    p.add_argument("target")
    p.add_argument("--limit", type=int, default=50)
    p.set_defaults(func=cmd_comments)

    p = sub.add_parser("raw", help="直接调用 API endpoint")
    p.add_argument("endpoint")
    p.add_argument("--params", nargs="*")
    p.set_defaults(func=cmd_raw)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(0)
    args.func(args)


if __name__ == "__main__":
    main()
