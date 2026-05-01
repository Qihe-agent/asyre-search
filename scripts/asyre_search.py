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


# ── Workflow command handlers ────────────────────────────────────

def _output_workflow(result, args):
    """Output a WorkflowResult based on format flags."""
    if args.raw or args.format == "json":
        print(json.dumps(result.data, ensure_ascii=False, indent=2))
    else:
        print(result.markdown)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump({
                "data": result.data,
                "blueprint_spec": result.blueprint_spec,
                "metadata": result.metadata,
            }, f, ensure_ascii=False, indent=2)
        print(f"\n✅ Full output saved to {args.output}", file=sys.stderr)

    if result.errors:
        print(f"\n⚠️ {len(result.errors)} step(s) had errors:", file=sys.stderr)
        for e in result.errors:
            print(f"  - {e['step']}: {e['error']}", file=sys.stderr)

    print(f"\n📊 {result.metadata.get('api_calls', 0)} API calls in {result.metadata.get('elapsed_seconds', 0)}s [{result.status}]", file=sys.stderr)


def cmd_workflow_analyze(args):
    api_key = _load_api_key()
    from scripts.workflows.analyze import AnalyzeWorkflow
    wf = AnalyzeWorkflow(api_key, args.platform, args.error_policy)
    result = wf.run(target=args.target, limit=args.limit)
    _output_workflow(result, args)


def cmd_workflow_compare(args):
    api_key = _load_api_key()
    from scripts.workflows.compare import CompareWorkflow
    wf = CompareWorkflow(api_key, args.platform, args.error_policy)
    result = wf.run(targets=args.targets, limit=args.limit)
    _output_workflow(result, args)


def cmd_workflow_scout(args):
    api_key = _load_api_key()
    from scripts.workflows.scout import ScoutWorkflow
    wf = ScoutWorkflow(api_key, args.platform, args.error_policy)
    result = wf.run(keyword=args.keyword, limit=args.limit)
    _output_workflow(result, args)


def cmd_workflow_audit(args):
    api_key = _load_api_key()
    from scripts.workflows.audit import AuditWorkflow
    wf = AuditWorkflow(api_key, args.platform, args.error_policy)
    result = wf.run(target=args.target, brand_category=args.brand_category, limit=args.limit)
    _output_workflow(result, args)


def cmd_scenario(args):
    if args.list or not args.name:
        from scripts.workflows.scenarios import list_scenarios
        print(list_scenarios())
        return

    from scripts.workflows.scenarios import SCENARIOS, ScenarioRunner
    if args.name not in SCENARIOS:
        print(f"❌ Unknown scenario: {args.name}", file=sys.stderr)
        print(f"   Use --list to see available scenarios", file=sys.stderr)
        sys.exit(1)

    api_key = _load_api_key()
    platform = args.platform or "xiaohongshu"
    runner = ScenarioRunner(api_key, platform, args.error_policy, scenario_name=args.name)
    result = runner.run(
        target=args.target or "",
        targets=args.targets or [],
        competitors=([c.strip() for c in args.competitors.split(",") if c.strip()] if args.competitors else []),
        niche_keyword=args.niche_keyword or "",
        keyword=args.keyword or "",
        platforms=args.platforms,
        limit=args.limit,
    )
    _output_workflow(result, args)


def cmd_workflow_monitor(args):
    api_key = _load_api_key()
    from scripts.workflows.monitor import MonitorWorkflow
    wf = MonitorWorkflow(api_key, args.platforms[0] if args.platforms else "douyin", args.error_policy)
    result = wf.run(keyword=args.keyword, platforms=args.platforms)
    _output_workflow(result, args)


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

    # ── Workflow commands ──────────────────────────────────────────

    p = sub.add_parser("analyze", help="📊 账号全景分析")
    p.add_argument("target", help="User ID or URL")
    p.add_argument("--limit", type=int, default=50, help="Max posts to analyze")
    p.add_argument("--error-policy", choices=["continue", "abort"], default="continue")
    p.set_defaults(func=cmd_workflow_analyze)

    p = sub.add_parser("compare", help="📊 竞品对比分析")
    p.add_argument("targets", nargs="+", help="2+ user IDs or URLs")
    p.add_argument("--limit", type=int, default=30)
    p.add_argument("--error-policy", choices=["continue", "abort"], default="continue")
    p.set_defaults(func=cmd_workflow_compare)

    p = sub.add_parser("scout", help="🔍 内容探查/选题分析")
    p.add_argument("keyword")
    p.add_argument("--limit", type=int, default=20)
    p.add_argument("--error-policy", choices=["continue", "abort"], default="continue")
    p.set_defaults(func=cmd_workflow_scout)

    p = sub.add_parser("audit", help="🔍 达人评估")
    p.add_argument("target", help="User ID or URL")
    p.add_argument("--brand-category", help="Brand category for relevance scoring")
    p.add_argument("--limit", type=int, default=30)
    p.add_argument("--error-policy", choices=["continue", "abort"], default="continue")
    p.set_defaults(func=cmd_workflow_audit)

    p = sub.add_parser("monitor", help="🌐 跨平台舆情监测")
    p.add_argument("keyword")
    p.add_argument("--platforms", nargs="+", default=["douyin", "xiaohongshu", "bilibili"])
    p.add_argument("--error-policy", choices=["continue", "abort"], default="continue")
    p.set_defaults(func=cmd_workflow_monitor)

    p = sub.add_parser("scenario", help="🎯 运行预设场景 (20 个)")
    p.add_argument("name", nargs="?", help="Scenario name (use --list to see all)")
    p.add_argument("--list", action="store_true", help="List all available scenarios")
    p.add_argument("--target", help="User ID or URL (for account/kol scenarios)")
    p.add_argument("--targets", nargs="+", help="Multiple user IDs (for compare scenarios)")
    p.add_argument("--keyword", help="Search keyword (for content/monitor scenarios)")
    p.add_argument("--competitors", help="Comma-separated competitor user IDs (for niche-deepdive)")
    p.add_argument("--niche-keyword", dest="niche_keyword", help="Niche keyword for auto-discovering competitors (for niche-deepdive)")
    p.add_argument("--platforms", nargs="+", default=["douyin", "xiaohongshu", "bilibili"])
    p.add_argument("--limit", type=int, default=20)
    p.add_argument("--error-policy", choices=["continue", "abort"], default="continue")
    p.set_defaults(func=cmd_scenario)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(0)
    try:
        args.func(args)
    except RuntimeError as e:
        print(f"❌ {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
