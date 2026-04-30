"""Pro-level analytics: trend, cadence, content patterns, comment intent, scoring.

These functions only need post lists and comment lists already shaped by metrics.py.
They produce richer dimensions that the basic 'analyze' workflow doesn't.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from datetime import datetime, timezone
from statistics import mean, median, stdev


# ── Time / cadence ─────────────────────────────────────────────────

def decode_xhs_timestamp(note_id: str) -> int | None:
    """XHS note IDs encode unix timestamp in the leading 8 hex chars."""
    if not note_id or len(note_id) < 8:
        return None
    try:
        return int(note_id[:8], 16)
    except ValueError:
        return None


def post_timestamp(post: dict, platform: str) -> int | None:
    """Return unix timestamp for a post across platforms, or None if unknown."""
    for k in ("create_time", "timestamp", "time", "publish_time"):
        v = post.get(k)
        if v:
            try:
                t = int(v)
                if t > 1e12:
                    t //= 1000
                return t
            except (ValueError, TypeError):
                pass
    if platform == "xiaohongshu":
        return decode_xhs_timestamp(post.get("note_id") or post.get("id") or "")
    return None


def cadence_metrics(posts: list[dict], platform: str) -> dict:
    """Posting frequency stats: span, avg interval, std, longest gap, monthly hist."""
    timestamps = sorted(t for t in (post_timestamp(p, platform) for p in posts) if t)
    if len(timestamps) < 2:
        return {"sample_size": len(timestamps), "insufficient_data": True}

    span_days = (timestamps[-1] - timestamps[0]) / 86400.0
    intervals_days = [
        (timestamps[i + 1] - timestamps[i]) / 86400.0
        for i in range(len(timestamps) - 1)
    ]
    monthly = Counter()
    for t in timestamps:
        d = datetime.fromtimestamp(t, tz=timezone.utc)
        monthly[d.strftime("%Y-%m")] += 1

    return {
        "sample_size": len(timestamps),
        "first_post_date": datetime.fromtimestamp(timestamps[0], tz=timezone.utc).strftime("%Y-%m-%d"),
        "last_post_date": datetime.fromtimestamp(timestamps[-1], tz=timezone.utc).strftime("%Y-%m-%d"),
        "span_days": round(span_days, 1),
        "avg_interval_days": round(mean(intervals_days), 1),
        "median_interval_days": round(median(intervals_days), 1),
        "stdev_interval_days": round(stdev(intervals_days), 1) if len(intervals_days) > 1 else 0.0,
        "longest_gap_days": round(max(intervals_days), 1),
        "posts_per_week": round(len(timestamps) / max(span_days, 1) * 7, 2),
        "monthly_distribution": dict(monthly),
    }


# ── Trend (engagement over time) ───────────────────────────────────

def linear_slope(xs: list[float], ys: list[float]) -> float:
    """Simple OLS slope of y vs x. Returns 0 if degenerate."""
    n = len(xs)
    if n < 2:
        return 0.0
    mx = mean(xs)
    my = mean(ys)
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    den = sum((x - mx) ** 2 for x in xs)
    return num / den if den else 0.0


def trend_metrics(posts: list[dict], platform: str) -> dict:
    """Time-ordered engagement trend with slope + segment comparisons.

    Splits posts into halves and 'recent 5'. Computes likes-vs-time slope.
    Returns direction label: rising / stable / declining.
    """
    indexed = []
    for p in posts:
        t = post_timestamp(p, platform)
        if t is None:
            continue
        indexed.append((t, p.get("likes", 0)))
    indexed.sort()
    if len(indexed) < 4:
        return {"sample_size": len(indexed), "insufficient_data": True}

    n = len(indexed)
    first_half = [l for _, l in indexed[: n // 2]]
    second_half = [l for _, l in indexed[n // 2 :]]
    recent_5 = [l for _, l in indexed[-5:]]
    overall = [l for _, l in indexed]

    # Slope normalized to days
    xs_days = [(t - indexed[0][0]) / 86400.0 for t, _ in indexed]
    ys = [l for _, l in indexed]
    slope_per_day = linear_slope(xs_days, ys)

    avg_first = round(mean(first_half), 2) if first_half else 0
    avg_second = round(mean(second_half), 2) if second_half else 0
    avg_recent = round(mean(recent_5), 2) if recent_5 else 0
    avg_all = round(mean(overall), 2) if overall else 0

    # Direction heuristic: compare recent 5 vs first half
    if avg_first > 0:
        delta_pct = (avg_recent - avg_first) / avg_first
        if delta_pct >= 0.20:
            direction = "rising"
        elif delta_pct <= -0.20:
            direction = "declining"
        else:
            direction = "stable"
    else:
        direction = "unknown"

    return {
        "sample_size": n,
        "avg_likes_first_half": avg_first,
        "avg_likes_second_half": avg_second,
        "avg_likes_recent_5": avg_recent,
        "avg_likes_overall": avg_all,
        "slope_likes_per_day": round(slope_per_day, 4),
        "direction": direction,
        "delta_recent_vs_first_pct": round((avg_recent - avg_first) / avg_first * 100, 1) if avg_first else None,
    }


# ── Distribution diagnostics ───────────────────────────────────────

def distribution_metrics(posts: list[dict]) -> dict:
    """Engagement distribution: pareto, std, top-decile share."""
    likes = sorted([p.get("likes", 0) for p in posts], reverse=True)
    if not likes:
        return {"sample_size": 0}
    n = len(likes)
    total = sum(likes) or 1
    top10pct_count = max(1, n // 10)
    top10pct_share = sum(likes[:top10pct_count]) / total
    median_likes = median(likes)
    p25, p75 = (likes[3 * n // 4] if n >= 4 else likes[-1], likes[n // 4] if n >= 4 else likes[0])

    return {
        "sample_size": n,
        "max": likes[0],
        "p75": p75,
        "median": median_likes,
        "p25": p25,
        "min": likes[-1],
        "stdev": round(stdev(likes), 2) if n > 1 else 0,
        "top_decile_share_pct": round(top10pct_share * 100, 1),
        "viral_threshold": likes[max(0, n // 4 - 1)] if n >= 4 else likes[0],  # top 25% bar
    }


# ── Title pattern mining ───────────────────────────────────────────

# Conservative CN tokenizer: split on punctuation + whitespace, then
# slide bigrams/trigrams over CJK runs. No external deps.
_PUNCT = re.compile(r"[\s，。！？、,\.\!\?\|｜·…—–\-/／【】\[\]\(\)（）「」『』《》「」“”\":：\#＃@➕+]+")
_CJK_RUN = re.compile(r"[\u4e00-\u9fff]+")
_LATIN_WORD = re.compile(r"[A-Za-z][A-Za-z0-9]+")


def tokenize_cn(text: str, ngram_min: int = 2, ngram_max: int = 4) -> list[str]:
    """Tokenize a CN+EN mixed title into meaningful tokens."""
    if not text:
        return []
    tokens: list[str] = []
    chunks = [c for c in _PUNCT.split(text) if c]
    for chunk in chunks:
        # Latin word as-is (lowered)
        for w in _LATIN_WORD.findall(chunk):
            if len(w) >= 3:
                tokens.append(w.lower())
        # CJK bigrams/trigrams within each CJK run
        for run in _CJK_RUN.findall(chunk):
            for n in range(ngram_min, ngram_max + 1):
                for i in range(len(run) - n + 1):
                    ng = run[i : i + n]
                    if not _is_stopword(ng):
                        tokens.append(ng)
    return tokens


_STOPWORDS = {
    "悉尼", "上海", "北京", "我们", "你们", "他们", "什么", "怎么", "这个", "那个",
    "今天", "明天", "昨天", "如果", "因为", "所以", "但是", "可以", "应该", "不过",
}


def _is_stopword(s: str) -> bool:
    return s in _STOPWORDS or len(s) < 2


def title_pattern_metrics(posts: list[dict], top_pct: float = 0.25, bottom_pct: float = 0.25) -> dict:
    """Compare titles of top X% posts vs bottom Y% posts.

    Returns lift dict: keyword -> (top_freq, bottom_freq, lift_score).
    Lift = top_freq / max(bottom_freq, 0.5). Higher = more associated with virality.
    """
    if len(posts) < 8:
        return {"insufficient_data": True, "sample_size": len(posts)}

    sorted_posts = sorted(posts, key=lambda p: -p.get("likes", 0))
    n = len(sorted_posts)
    top_n = max(2, int(n * top_pct))
    bot_n = max(2, int(n * bottom_pct))
    top_titles = [p.get("title", "") for p in sorted_posts[:top_n]]
    bot_titles = [p.get("title", "") for p in sorted_posts[-bot_n:]]

    top_tokens = Counter()
    for t in top_titles:
        for tok in tokenize_cn(t):
            top_tokens[tok] += 1
    bot_tokens = Counter()
    for t in bot_titles:
        for tok in tokenize_cn(t):
            bot_tokens[tok] += 1

    # Lift score: appears in top, rare in bottom
    candidates = []
    for tok, top_freq in top_tokens.items():
        if top_freq < 2:  # require ≥2 occurrences to avoid noise
            continue
        bot_freq = bot_tokens.get(tok, 0)
        lift = top_freq / max(bot_freq, 0.5)
        candidates.append({"token": tok, "top_freq": top_freq, "bottom_freq": bot_freq, "lift": round(lift, 2)})

    candidates.sort(key=lambda x: (-x["lift"], -x["top_freq"]))

    return {
        "sample_size": n,
        "top_n": top_n,
        "bottom_n": bot_n,
        "viral_keywords": candidates[:15],
        "top_titles": [{"title": p.get("title", ""), "likes": p.get("likes", 0)} for p in sorted_posts[:top_n]],
    }


# ── Comment intent classification ──────────────────────────────────

INTENT_PATTERNS = {
    "price_inquiry": [
        r"价格", r"多少钱", r"价钱", r"几钱", r"几多", r"礼貌问价", r"strata", r"管理费", r"周供", r"周租", r"\bpw\b",
    ],
    "discussion": [
        r"我觉得", r"我认为", r"个人觉得", r"我看", r"对比", r"vs", r"比较", r"是不是", r"为什么", r"怎么看",
    ],
    "praise": [
        r"好看", r"漂亮", r"喜欢", r"爱", r"超棒", r"绝", r"yyds", r"赞", r"美", r"心动", r"\bnice\b", r"\bcool\b", r"\bgood\b",
    ],
    "complaint": [
        r"垃圾", r"差", r"难看", r"骗", r"虚假", r"忽悠", r"避雷", r"踩坑", r"难用",
    ],
    "consult": [
        r"求推荐", r"推荐一下", r"求助", r"想咨询", r"私信", r"加微信", r"求联系", r"DM",
    ],
    "question_other": [
        r"\?$", r"？$", r"\?[\s\S]*$", r"？[\s\S]*$",
    ],
}


def classify_comment_intent(text: str) -> str:
    """Rule-based intent: price_inquiry > consult > complaint > discussion > praise > question_other > other."""
    if not text:
        return "other"
    t = text.lower()
    # ordered priority
    for intent in ("price_inquiry", "consult", "complaint", "discussion", "praise"):
        for pat in INTENT_PATTERNS[intent]:
            if re.search(pat, t):
                return intent
    if "?" in t or "？" in t:
        return "question_other"
    if len(t) < 4:
        return "filler"
    return "other"


def comment_quality_metrics(comment_lists_by_post: list[list[dict]]) -> dict:
    """Aggregate comment intent distribution and stats across posts.

    comment_lists_by_post: [[{content, like_count, user, ...}, ...], ...]
    """
    flat = [c for lst in comment_lists_by_post for c in (lst or [])]
    total = len(flat)
    if total == 0:
        return {"total_comments": 0, "insufficient_data": True}

    intent_counts: Counter = Counter()
    char_lengths: list[int] = []
    for c in flat:
        text = c.get("content", "")
        intent_counts[classify_comment_intent(text)] += 1
        char_lengths.append(len(text or ""))

    return {
        "total_comments_sampled": total,
        "posts_sampled": len(comment_lists_by_post),
        "avg_chars": round(mean(char_lengths), 1) if char_lengths else 0,
        "median_chars": median(char_lengths) if char_lengths else 0,
        "short_filler_pct": round(
            sum(1 for l in char_lengths if l < 4) / total * 100, 1
        ),
        "intent_distribution": {
            k: {"count": v, "pct": round(v / total * 100, 1)}
            for k, v in intent_counts.most_common()
        },
        "is_pure_sales_funnel": intent_counts.get("price_inquiry", 0) / total >= 0.5,
        "is_high_engagement": intent_counts.get("discussion", 0) / total >= 0.20,
    }


# ── Health score (composite) ───────────────────────────────────────

def health_score(
    user_metrics: dict,
    account_metrics: dict,
    trend: dict,
    cadence: dict,
    distribution: dict,
    comment_quality: dict | None,
) -> dict:
    """Score 6 dimensions 0-100 each, plus weighted overall."""
    scores: dict = {}

    # 1. Engagement quality (互动率 vs benchmark)
    er = account_metrics.get("engagement_rate", 0)
    if er <= 0:
        scores["engagement"] = 0
    else:
        # Benchmark: 1% baseline, 5% great, 10%+ excellent (capped at 100)
        scores["engagement"] = min(100, round(er * 1000))

    # 2. Growth trend
    if trend.get("insufficient_data"):
        scores["trend"] = 50
    else:
        d = trend.get("direction", "unknown")
        scores["trend"] = {"rising": 90, "stable": 60, "declining": 25, "unknown": 50}[d]

    # 3. Cadence consistency
    if cadence.get("insufficient_data"):
        scores["cadence"] = 30
    else:
        per_week = cadence.get("posts_per_week", 0)
        std = cadence.get("stdev_interval_days", 0)
        # Reward 2-5 posts/week with low variance
        freq_score = 0
        if per_week >= 0.5:
            freq_score = min(80, 40 + (per_week - 0.5) * 20)
        # Penalty for high variance
        var_penalty = min(40, std)
        scores["cadence"] = max(0, round(freq_score + 20 - var_penalty))

    # 4. Content concentration (top 10% share — too high = over-reliance on outliers)
    if distribution.get("sample_size", 0) < 5:
        scores["content_diversity"] = 50
    else:
        share = distribution.get("top_decile_share_pct", 100) / 100
        # Sweet spot: 30-60% from top decile = healthy long tail
        if 0.30 <= share <= 0.60:
            scores["content_diversity"] = 90
        elif share < 0.30:
            scores["content_diversity"] = 70
        else:
            scores["content_diversity"] = max(20, round(100 - (share - 0.60) * 200))

    # 5. Title hook strength (presence of viral keywords + variance)
    titles = [p.get("title", "") for p in account_metrics.get("top_posts", [])]
    if titles:
        avg_len = mean(len(t) for t in titles)
        scores["title_hook"] = min(100, round(50 + (avg_len - 10) * 2))
    else:
        scores["title_hook"] = 50

    # 6. Comment quality
    if comment_quality and not comment_quality.get("insufficient_data"):
        intent = comment_quality.get("intent_distribution", {})
        discuss_pct = intent.get("discussion", {}).get("pct", 0)
        praise_pct = intent.get("praise", {}).get("pct", 0)
        sales_pct = intent.get("price_inquiry", {}).get("pct", 0)
        # Reward discussion + praise, penalize over-saturation of price asks
        scores["comment_quality"] = max(
            0, min(100, round(discuss_pct * 2 + praise_pct * 1.2 + (50 - sales_pct)))
        )
    else:
        scores["comment_quality"] = 50

    weights = {
        "engagement": 0.25,
        "trend": 0.20,
        "cadence": 0.15,
        "content_diversity": 0.15,
        "title_hook": 0.10,
        "comment_quality": 0.15,
    }
    overall = round(sum(scores[k] * w for k, w in weights.items()))

    return {
        "overall": overall,
        "grade": _grade_letter(overall),
        "by_dimension": scores,
        "weights": weights,
    }


def _grade_letter(score: int) -> str:
    if score >= 85:
        return "A"
    if score >= 70:
        return "B"
    if score >= 55:
        return "C"
    if score >= 40:
        return "D"
    return "F"


# ── Diagnosis (rule-based recommendations) ─────────────────────────

def diagnose(
    user_metrics: dict,
    account_metrics: dict,
    trend: dict,
    cadence: dict,
    distribution: dict,
    title_patterns: dict,
    comment_quality: dict | None,
    score: dict,
) -> list[dict]:
    """Generate up to ~6 prioritized recommendations from data."""
    findings: list[dict] = []

    # Trend declining
    if trend.get("direction") == "declining":
        delta = trend.get("delta_recent_vs_first_pct")
        findings.append({
            "priority": "P0",
            "code": "TREND_DECLINING",
            "title": "互动量持续下滑",
            "evidence": f"最近 5 篇平均赞 {trend.get('avg_likes_recent_5')} vs 早期 {trend.get('avg_likes_first_half')} (Δ {delta}%)",
            "action": "切换内容形态：当前模式可能被算法识别为同质化降权。下一篇尝试新角度（个人故事 / 对比类 / 数据型）。",
        })

    # Cadence problems
    if not cadence.get("insufficient_data"):
        per_week = cadence.get("posts_per_week", 0)
        std = cadence.get("stdev_interval_days", 0)
        gap = cadence.get("longest_gap_days", 0)
        if per_week < 1:
            findings.append({
                "priority": "P1",
                "code": "CADENCE_TOO_SLOW",
                "title": "发布频率过低",
                "evidence": f"平均每 {cadence.get('avg_interval_days')} 天 1 篇 (~{per_week} 次/周)",
                "action": "目标提升至每周 2-3 篇。算法对低频账号推送量保护极少。",
            })
        if std > 14:
            findings.append({
                "priority": "P1",
                "code": "CADENCE_INCONSISTENT",
                "title": "发布节奏不稳定",
                "evidence": f"间隔标准差 {std} 天，最长断更 {gap} 天",
                "action": "建立固定节奏（如每周一/三/六），算法识别『稳定输出』后会给基础流量保护。",
            })

    # Comment quality skew
    if comment_quality and not comment_quality.get("insufficient_data"):
        if comment_quality.get("is_pure_sales_funnel"):
            sales_pct = comment_quality["intent_distribution"].get("price_inquiry", {}).get("pct", 0)
            findings.append({
                "priority": "P0",
                "code": "COMMENT_PURE_SALES",
                "title": "评论 100% 是问价/咨询",
                "evidence": f"问价类评论占 {sales_pct}%，几乎无讨论/共鸣",
                "action": "在文案末尾加『讨论钩子』（开放问题/对比征集），算法对无讨论评论权重低。",
            })
        if comment_quality.get("avg_chars", 0) < 6:
            findings.append({
                "priority": "P1",
                "code": "COMMENT_TOO_SHORT",
                "title": "评论过短，互动深度不足",
                "evidence": f"评论平均 {comment_quality.get('avg_chars')} 字",
                "action": "加引导性开放式问题，鼓励长评论（算法把『字数 ≥ 10 字 + 含表情/数字』的评论权重判更高）。",
            })

    # Distribution: over-reliance on a few posts
    if distribution.get("top_decile_share_pct", 0) > 65:
        findings.append({
            "priority": "P1",
            "code": "DIST_TOP_HEAVY",
            "title": "互动严重集中在头部少数笔记",
            "evidence": f"Top 10% 笔记贡献了 {distribution.get('top_decile_share_pct')}% 总互动",
            "action": "拆解爆款共同因子，复用到下一批内容。建议参考 viral_keywords 字段。",
        })

    # Engagement rate too low
    er = account_metrics.get("engagement_rate", 0)
    if 0 < er < 0.02:
        findings.append({
            "priority": "P1",
            "code": "ENG_LOW",
            "title": "互动率偏低",
            "evidence": f"互动率 {er:.2%}（行业基线 ~1%，健康账号 5%+）",
            "action": "重新看互动钩子设计：标题、封面、文案末尾问句的转化能力。",
        })

    # Followers too low for note count
    notes = user_metrics.get("note_count", 0)
    fans = user_metrics.get("followers", 0)
    if notes >= 30 and fans < 1000:
        findings.append({
            "priority": "P0",
            "code": "FANS_LOW_VS_POSTS",
            "title": "粉丝转化效率低",
            "evidence": f"已发 {notes} 篇笔记仅获 {fans} 粉",
            "action": "内容形态可能纯获客漏斗，未沉淀『可持续关注价值』。增加专业洞察 / 系列化栏目 / 个人 IP 内容。",
        })

    # Score below threshold
    if score.get("overall", 100) < 50:
        findings.append({
            "priority": "P0",
            "code": "OVERALL_LOW",
            "title": f"综合健康度 {score.get('overall')}/100 ({score.get('grade')})",
            "evidence": f"维度评分: {score.get('by_dimension')}",
            "action": "优先解决得分最低的两个维度，30 天后复测。",
        })

    return findings[:8]


# ── Niche benchmark stubs (network-call-free helpers) ──────────────

def percentile_rank(value: int, peer_values: list[int]) -> float:
    """Return 0..1 percentile of value among peer_values."""
    if not peer_values:
        return 0.0
    below = sum(1 for v in peer_values if v < value)
    return round(below / len(peer_values), 2)
