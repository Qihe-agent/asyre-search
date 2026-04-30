#!/usr/bin/env python3
"""Generate API registry and ENDPOINTS.md from upstream OpenAPI spec.

Usage:
    python3 scripts/generate_registry.py [--spec-url URL] [--output-dir DIR]

This script:
1. Fetches the OpenAPI spec from upstream
2. Parses every endpoint into a structured registry
3. Writes registry/api_registry.json
4. Generates registry/ENDPOINTS.md (human/agent-readable reference)
"""

import argparse
import json
import os
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone

import requests

SPEC_URL = os.environ.get("ASYRE_SEARCH_SPEC_URL", "https://api.tikhub.io/openapi.json")
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
DEFAULT_OUTPUT_DIR = os.path.join(PROJECT_DIR, "registry")

# ── Category classification ──────────────────────────────────────

CATEGORY_RULES = [
    # (pattern_in_endpoint_name, category)
    (r"comment|reply", "comments"),
    (r"search", "search"),
    (r"trending|hot_search|hot_list|hot_selling|popular", "trending"),
    (r"user_post|user_note|user_video|user_reel|channel_video|channel_short", "posts"),
    (r"user_profile|user_info|channel_info|channel_detail|get_user_id", "user"),
    (r"follower|following|fans_list|follow_list", "social"),
    (r"live|webcast|room", "live"),
    (r"product|shop|goods|showcase", "ecommerce"),
    (r"billboard|rank|chart", "analytics"),
    (r"danmaku|subtitle|caption", "media"),
    (r"cookie|device|register|encrypt|decrypt|sign|token|fingerprint|qrcode", "utility"),
    (r"creator|insight|milestone|health|violation", "creator"),
]

# Platforms that use app-level versioning in path (e.g. /app/v3/)
APP_VERSION_PLATFORMS = {"douyin", "tiktok"}


def classify_endpoint(endpoint_name: str) -> str:
    """Classify an endpoint into a category based on its name."""
    name_lower = endpoint_name.lower()
    for pattern, category in CATEGORY_RULES:
        if re.search(pattern, name_lower):
            return category
    # Default: if it fetches one item, it's content
    if any(w in name_lower for w in ("fetch_one", "get_video", "get_note", "fetch_post",
                                      "get_tweet", "note_detail", "video_detail",
                                      "post_detail", "post_info", "note_info")):
        return "content"
    return "other"


def extract_version(endpoint_name: str) -> str | None:
    """Extract version suffix like _v2, _v3 from endpoint name."""
    m = re.search(r"_v(\d+)$", endpoint_name)
    return f"v{m.group(1)}" if m else None


def base_name(endpoint_name: str) -> str:
    """Strip version suffix to get base endpoint name."""
    return re.sub(r"_v\d+$", "", endpoint_name)


# ── OpenAPI parsing ──────────────────────────────────────────────

def parse_parameters(params_list: list) -> dict:
    """Parse OpenAPI parameters into our schema format."""
    result = {}
    for p in params_list:
        schema = p.get("schema", {})
        param_info = {
            "type": schema.get("type", "string"),
            "required": p.get("required", False),
            "in": p.get("in", "query"),
            "description": schema.get("title", p.get("description", p.get("name", ""))),
        }
        default = schema.get("default")
        if default is not None and default != "":
            param_info["default"] = default
        # Enum values
        enum = schema.get("enum")
        if enum:
            param_info["enum"] = enum
        result[p["name"]] = param_info
    return result


def parse_request_body(body: dict, spec: dict) -> dict:
    """Parse OpenAPI requestBody into our schema format."""
    result = {}
    content = body.get("content", {})
    json_content = content.get("application/json", {})
    schema = json_content.get("schema", {})

    # Resolve $ref
    ref = schema.get("$ref", "")
    if ref:
        ref_path = ref.replace("#/", "").split("/")
        resolved = spec
        for part in ref_path:
            resolved = resolved.get(part, {})
        schema = resolved

    properties = schema.get("properties", {})
    required_fields = set(schema.get("required", []))

    for name, prop in properties.items():
        field_info = {
            "type": prop.get("type", "string"),
            "required": name in required_fields,
            "description": prop.get("title", prop.get("description", name)),
        }
        default = prop.get("default")
        if default is not None and default != "":
            field_info["default"] = default
        enum = prop.get("enum")
        if enum:
            field_info["enum"] = enum
        result[name] = field_info
    return result


def parse_spec(spec: dict) -> dict:
    """Parse full OpenAPI spec into our registry format."""
    platforms = defaultdict(lambda: {"label": "", "modules": defaultdict(lambda: {"label": "", "endpoints": {}})})

    paths = spec.get("paths", {})
    for path, path_item in sorted(paths.items()):
        # Parse path: /api/v1/{platform}/{module_path}/{endpoint_name}
        parts = path.strip("/").split("/")
        if len(parts) < 4 or parts[0] != "api":
            continue

        platform = parts[2]  # e.g. douyin, xiaohongshu
        # Skip demo/health/utility endpoints
        if platform in ("demo", "health", "hybrid", "ios_shortcut", "temp_mail", "sora2"):
            continue

        # Determine module and endpoint name
        remaining = parts[3:]  # e.g. ["app", "v3", "fetch_one_video"] or ["web", "get_user_info"]
        endpoint_name = remaining[-1]

        # Build module key: everything between platform and endpoint name
        module_parts = remaining[:-1]
        module_key = "_".join(module_parts) if module_parts else "default"

        for method, operation in path_item.items():
            if method in ("parameters", "summary", "description"):
                continue

            tags = operation.get("tags", [])
            summary = operation.get("summary", "")
            deprecated = operation.get("deprecated", False)

            # Set platform label from first tag
            if tags and not platforms[platform]["label"]:
                platforms[platform]["label"] = tags[0]

            # Set module label
            if tags:
                platforms[platform]["modules"][module_key]["label"] = tags[0]

            # Parse params
            params = parse_parameters(operation.get("parameters", []))

            # Parse body (for POST/PUT)
            body = None
            if operation.get("requestBody"):
                body = parse_request_body(operation["requestBody"], spec)

            version = extract_version(endpoint_name)
            category = classify_endpoint(endpoint_name)

            endpoint_data = {
                "method": method.upper(),
                "path": path,
                "summary": summary,
                "category": category,
                "params": params,
                "deprecated": deprecated,
                "version": version,
                "recommended": False,  # Set later
            }
            if body:
                endpoint_data["body"] = body

            platforms[platform]["modules"][module_key]["endpoints"][endpoint_name] = endpoint_data

    # Mark recommended versions
    _mark_recommended(platforms)

    return dict(platforms)


def _mark_recommended(platforms: dict):
    """For versioned endpoint groups, mark the highest non-deprecated as recommended."""
    for platform_data in platforms.values():
        for module_data in platform_data["modules"].values():
            endpoints = module_data["endpoints"]

            # Group by base name
            groups = defaultdict(list)
            for name, ep in endpoints.items():
                groups[base_name(name)].append((name, ep))

            for group_names in groups.values():
                # Sort: unversioned first, then by version number
                def sort_key(item):
                    v = item[1].get("version")
                    return int(v[1:]) if v else 0

                sorted_group = sorted(group_names, key=sort_key)

                # Find highest non-deprecated
                recommended = None
                for name, ep in reversed(sorted_group):
                    if not ep.get("deprecated", False):
                        recommended = name
                        break

                # If all deprecated, pick the highest anyway
                if recommended is None and sorted_group:
                    recommended = sorted_group[-1][0]

                if recommended:
                    endpoints[recommended]["recommended"] = True


# ── ENDPOINTS.md generation ──────────────────────────────────────

CATEGORY_LABELS = {
    "content": "内容详情 (Content)",
    "user": "用户信息 (User)",
    "posts": "作品列表 (Posts)",
    "search": "搜索 (Search)",
    "trending": "热搜/趋势 (Trending)",
    "comments": "评论 (Comments)",
    "social": "社交关系 (Social)",
    "live": "直播 (Live)",
    "ecommerce": "电商 (E-commerce)",
    "analytics": "数据分析 (Analytics)",
    "media": "媒体 (Media)",
    "utility": "工具 (Utility)",
    "creator": "创作者 (Creator)",
    "other": "其他 (Other)",
}

CATEGORY_ORDER = list(CATEGORY_LABELS.keys())

PLATFORM_LABELS = {
    "douyin": "抖音 Douyin",
    "tiktok": "TikTok",
    "xiaohongshu": "小红书 Xiaohongshu",
    "bilibili": "B站 Bilibili",
    "youtube": "YouTube",
    "instagram": "Instagram",
    "twitter": "Twitter/X",
    "weibo": "微博 Weibo",
    "kuaishou": "快手 Kuaishou",
    "zhihu": "知乎 Zhihu",
    "threads": "Threads",
    "reddit": "Reddit",
    "linkedin": "LinkedIn",
    "lemon8": "Lemon8",
    "pipixia": "皮皮虾 Pipixia",
    "toutiao": "今日头条 Toutiao",
    "xigua": "西瓜视频 Xigua",
    "wechat_channels": "微信视频号",
    "wechat_mp": "微信公众号",
}


def generate_endpoints_md(platforms: dict) -> str:
    """Generate ENDPOINTS.md from registry data."""
    lines = []
    lines.append("# Asyre Search API 完整接口手册")
    lines.append("")
    lines.append(f"> 自动生成于 {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")

    # Count totals
    total_endpoints = sum(
        len(mod["endpoints"])
        for p in platforms.values()
        for mod in p["modules"].values()
    )
    lines.append(f"> 共 **{total_endpoints}** 个接口，覆盖 **{len(platforms)}** 个平台")
    lines.append(f"> Base URL: gateway-managed (upstream proxied via Asyre Gateway)")
    lines.append("")

    # Quick lookup table
    lines.append("## 快速查找 (Quick Lookup)")
    lines.append("")
    core_actions = ["content", "user", "posts", "search", "trending", "comments"]
    header = "| 平台 | " + " | ".join(CATEGORY_LABELS.get(a, a) for a in core_actions) + " |"
    sep = "|------|" + "|".join(["---:" for _ in core_actions]) + "|"
    lines.append(header)
    lines.append(sep)

    # Sort platforms: core 7 first, then alphabetical
    core_platforms = ["douyin", "xiaohongshu", "bilibili", "tiktok", "youtube", "instagram", "twitter"]
    sorted_platforms = core_platforms + sorted(p for p in platforms if p not in core_platforms)

    for plat in sorted_platforms:
        if plat not in platforms:
            continue
        plat_data = platforms[plat]
        label = PLATFORM_LABELS.get(plat, plat)
        cells = []
        for action in core_actions:
            count = sum(
                1 for mod in plat_data["modules"].values()
                for ep in mod["endpoints"].values()
                if ep["category"] == action
            )
            if count > 0:
                cells.append(f"[{count}](#{plat}-{action})")
            else:
                cells.append("-")
        lines.append(f"| {label} | " + " | ".join(cells) + " |")

    lines.append("")
    lines.append("---")
    lines.append("")

    # Per-platform sections
    for plat in sorted_platforms:
        if plat not in platforms:
            continue
        plat_data = platforms[plat]
        label = PLATFORM_LABELS.get(plat, plat)
        lines.append(f"## {label}")
        lines.append("")

        # Group endpoints by category
        by_category = defaultdict(list)
        for mod_key, mod_data in plat_data["modules"].items():
            for ep_name, ep in mod_data["endpoints"].items():
                by_category[ep["category"]].append((mod_key, ep_name, ep))

        for cat in CATEGORY_ORDER:
            if cat not in by_category:
                continue
            eps = by_category[cat]
            cat_label = CATEGORY_LABELS.get(cat, cat)
            anchor = f"{plat}-{cat}"
            lines.append(f"### <a id=\"{anchor}\"></a>{cat_label}")
            lines.append("")

            # Sort: recommended first, then alphabetically
            eps.sort(key=lambda x: (not x[2].get("recommended", False), x[1]))

            for mod_key, ep_name, ep in eps:
                method = ep["method"]
                path = ep["path"]
                summary = ep["summary"]
                rec = " ★" if ep.get("recommended") else ""
                dep = " ⚠️DEPRECATED" if ep.get("deprecated") else ""

                lines.append(f"#### `{method} {path}`{rec}{dep}")
                lines.append(f"> {summary}")
                lines.append("")

                # Params table
                params = ep.get("params", {})
                body = ep.get("body", {})

                if params:
                    lines.append("**Query 参数:**")
                    lines.append("")
                    lines.append("| 参数 | 类型 | 必填 | 说明 |")
                    lines.append("|------|------|:----:|------|")
                    for pname, pinfo in params.items():
                        req = "✓" if pinfo.get("required") else ""
                        ptype = pinfo.get("type", "string")
                        desc = pinfo.get("description", "")
                        default = pinfo.get("default")
                        if default is not None:
                            desc += f" (默认: `{default}`)"
                        enum = pinfo.get("enum")
                        if enum:
                            desc += f" 可选值: {', '.join(f'`{e}`' for e in enum)}"
                        lines.append(f"| `{pname}` | {ptype} | {req} | {desc} |")
                    lines.append("")

                if body:
                    lines.append("**请求体 (JSON Body):**")
                    lines.append("")
                    lines.append("| 字段 | 类型 | 必填 | 说明 |")
                    lines.append("|------|------|:----:|------|")
                    for fname, finfo in body.items():
                        req = "✓" if finfo.get("required") else ""
                        ftype = finfo.get("type", "string")
                        desc = finfo.get("description", "")
                        default = finfo.get("default")
                        if default is not None:
                            desc += f" (默认: `{default}`)"
                        enum = finfo.get("enum")
                        if enum:
                            desc += f" 可选值: {', '.join(f'`{e}`' for e in enum)}"
                        lines.append(f"| `{fname}` | {ftype} | {req} | {desc} |")
                    lines.append("")

                if not params and not body:
                    lines.append("*无参数*")
                    lines.append("")

        lines.append("---")
        lines.append("")

    return "\n".join(lines)


# ── Main ─────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Generate API registry from upstream OpenAPI spec")
    parser.add_argument("--spec-url", default=SPEC_URL, help="OpenAPI spec URL")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR, help="Output directory")
    args = parser.parse_args()

    output_dir = args.output_dir
    os.makedirs(output_dir, exist_ok=True)

    # Fetch spec
    print(f"📥 Fetching OpenAPI spec from {args.spec_url}...")
    resp = requests.get(args.spec_url, timeout=60)
    resp.raise_for_status()
    spec = resp.json()
    print(f"   Spec version: {spec.get('info', {}).get('version', 'unknown')}")
    print(f"   Total paths: {len(spec.get('paths', {}))}")

    # Parse
    print("🔧 Parsing endpoints...")
    platforms = parse_spec(spec)

    total_endpoints = sum(
        len(mod["endpoints"])
        for p in platforms.values()
        for mod in p["modules"].values()
    )
    print(f"   Parsed {total_endpoints} endpoints across {len(platforms)} platforms")

    # Build registry
    registry = {
        "meta": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "source": args.spec_url,
            "total_endpoints": total_endpoints,
            "total_platforms": len(platforms),
        },
        "platforms": platforms,
    }

    # Write api_registry.json
    registry_path = os.path.join(output_dir, "api_registry.json")
    with open(registry_path, "w", encoding="utf-8") as f:
        json.dump(registry, f, ensure_ascii=False, indent=2)
    size_kb = os.path.getsize(registry_path) / 1024
    print(f"✅ {registry_path} ({size_kb:.0f} KB)")

    # Generate ENDPOINTS.md
    print("📝 Generating ENDPOINTS.md...")
    md_content = generate_endpoints_md(platforms)
    md_path = os.path.join(output_dir, "ENDPOINTS.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_content)
    line_count = md_content.count("\n")
    print(f"✅ {md_path} ({line_count} lines)")

    # Summary
    print("\n📊 Platform summary:")
    for plat in sorted(platforms.keys()):
        plat_data = platforms[plat]
        ep_count = sum(len(m["endpoints"]) for m in plat_data["modules"].values())
        mod_count = len(plat_data["modules"])
        print(f"   {plat}: {ep_count} endpoints in {mod_count} modules")


if __name__ == "__main__":
    main()
