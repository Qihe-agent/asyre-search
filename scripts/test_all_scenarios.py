#!/usr/bin/env python3
"""Test all 20 scenarios — lightweight run with minimal API calls."""

import os
import sys
import time
import json

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_DIR = os.path.dirname(_SCRIPT_DIR)
if _PROJECT_DIR not in sys.path:
    sys.path.insert(0, _PROJECT_DIR)

from scripts.workflows.scenarios import SCENARIOS, ScenarioRunner

API_KEY = os.environ.get("TIKHUB_API_KEY", os.environ.get("ASYRE_SEARCH_KEY", ""))
if not API_KEY:
    print("❌ Set TIKHUB_API_KEY env var")
    sys.exit(1)

# Test parameters for each scenario
TEST_PARAMS = {
    # Account scenarios (xiaohongshu - Asher's account)
    "account-deepdive":     {"platform": "xiaohongshu", "target": "5bfe5c9c44363b526a02e527", "limit": 5},
    "growth-diagnosis":     {"platform": "xiaohongshu", "target": "5bfe5c9c44363b526a02e527", "limit": 5},
    "content-matrix":       {"platform": "xiaohongshu", "target": "5bfe5c9c44363b526a02e527", "limit": 5},

    # Compare scenarios (xiaohongshu - 2 accounts)
    "competitor-compare":   {"platform": "xiaohongshu", "targets": ["5bfe5c9c44363b526a02e527", "5e0c63090000000001007717"], "limit": 5},
    "kol-comparison":       {"platform": "xiaohongshu", "targets": ["5bfe5c9c44363b526a02e527", "5e0c63090000000001007717"], "limit": 5},

    # KOL scenarios (xiaohongshu)
    "kol-audit":            {"platform": "xiaohongshu", "target": "5e0c63090000000001007717", "limit": 5},
    "kol-fraud-check":      {"platform": "xiaohongshu", "target": "5e0c63090000000001007717", "limit": 5},

    # Scout scenarios (xiaohongshu)
    "viral-reverse":        {"platform": "xiaohongshu", "keyword": "AI创业", "limit": 5},
    "content-ideas":        {"platform": "xiaohongshu", "keyword": "澳洲留学", "limit": 5},
    "ad-creative-mining":   {"platform": "xiaohongshu", "keyword": "护肤品推荐", "limit": 5},
    "niche-scan":           {"platform": "xiaohongshu", "keyword": "宠物用品", "limit": 5},

    # Monitor scenarios (cross-platform, limit to 2 platforms for speed)
    "brand-monitor":        {"platform": "xiaohongshu", "keyword": "花西子", "platforms": ["xiaohongshu", "bilibili"]},
    "crisis-alert":         {"platform": "xiaohongshu", "keyword": "食品安全", "platforms": ["xiaohongshu", "bilibili"]},
    "new-product-watch":    {"platform": "xiaohongshu", "keyword": "iPhone 17", "platforms": ["xiaohongshu", "bilibili"]},

    # Trending scenarios
    "trending-now":         {"platform": "xiaohongshu"},
    "industry-trends":      {"platform": "xiaohongshu", "keyword": "AI", "limit": 5},

    # Special scenarios
    "local-business":       {"platform": "xiaohongshu", "keyword": "墨尔本奶茶", "limit": 5},
    "cross-platform-presence": {"platform": "xiaohongshu", "keyword": "OpenAI", "platforms": ["xiaohongshu", "bilibili"]},
    "comment-insight":      {"platform": "xiaohongshu", "target": "5e0c63090000000001007717", "limit": 5},
    "investment-dd":        {"platform": "xiaohongshu", "keyword": "完美日记", "platforms": ["xiaohongshu", "bilibili"]},
}


def run_test(scenario_name: str, params: dict) -> dict:
    """Run a single scenario test and return result summary."""
    platform = params.pop("platform", "xiaohongshu")
    try:
        runner = ScenarioRunner(API_KEY, platform, "continue", scenario_name=scenario_name)
        result = runner.run(**params)
        return {
            "status": result.status,
            "api_calls": result.metadata.get("api_calls", 0),
            "elapsed": result.metadata.get("elapsed_seconds", 0),
            "errors": len(result.errors),
            "has_markdown": len(result.markdown) > 50,
            "has_blueprint": bool(result.blueprint_spec),
            "error_details": [e["step"] + ": " + e["error"][:60] for e in result.errors[:3]],
        }
    except Exception as e:
        return {"status": "exception", "error": str(e)[:100]}


def main():
    print(f"🧪 Testing all {len(SCENARIOS)} scenarios")
    print(f"{'='*70}")

    results = {}
    total_api_calls = 0
    total_time = 0
    passed = 0
    failed = 0

    for i, (name, config) in enumerate(SCENARIOS.items(), 1):
        label = config["name"]
        params = TEST_PARAMS.get(name, {}).copy()
        print(f"\n[{i:2d}/20] {name} — {label}")
        print(f"        params: {json.dumps(params, ensure_ascii=False)[:80]}")

        start = time.time()
        result = run_test(name, params)
        elapsed = time.time() - start

        status = result.get("status", "?")
        api_calls = result.get("api_calls", 0)
        errors = result.get("errors", 0)
        total_api_calls += api_calls
        total_time += elapsed

        if status in ("complete", "partial"):
            passed += 1
            icon = "✅" if status == "complete" else "⚠️"
        else:
            failed += 1
            icon = "❌"

        print(f"        {icon} {status} | {api_calls} calls | {elapsed:.1f}s | {errors} errors")
        if result.get("error_details"):
            for ed in result["error_details"]:
                print(f"           └─ {ed}")
        if result.get("error"):
            print(f"           └─ {result['error']}")

        results[name] = result

    print(f"\n{'='*70}")
    print(f"📊 Results: {passed} passed, {failed} failed out of {len(SCENARIOS)}")
    print(f"   Total: {total_api_calls} API calls in {total_time:.0f}s")

    # Summary table
    print(f"\n{'Name':<28} {'Status':<10} {'Calls':>5} {'Time':>6} {'Errs':>4}")
    print(f"{'-'*28} {'-'*10} {'-'*5} {'-'*6} {'-'*4}")
    for name, r in results.items():
        s = r.get("status", "?")
        print(f"{name:<28} {s:<10} {r.get('api_calls',0):>5} {r.get('elapsed',0):>5.0f}s {r.get('errors',0):>4}")


if __name__ == "__main__":
    main()
