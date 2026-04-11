"""Shared metric computation functions for all workflows."""


def safe_int(v, default=0) -> int:
    """Safely convert a value to int."""
    if v is None:
        return default
    try:
        return int(v)
    except (ValueError, TypeError):
        return default


def compact_number(n) -> str:
    """Format number for display: 12345 → '1.2万'."""
    n = safe_int(n)
    if n >= 100_000_000:
        return f"{n / 100_000_000:.1f}亿"
    if n >= 10_000:
        return f"{n / 10_000:.1f}万"
    return str(n)


def engagement_rate(likes: int, comments: int, collects: int, followers: int) -> float:
    """Compute engagement rate = (likes + comments + collects) / followers."""
    if followers <= 0:
        return 0.0
    return round((likes + comments + collects) / followers, 4)


# ── Platform-specific data extraction ────────────────────────────

def extract_user_metrics(user_data: dict, platform: str) -> dict:
    """Extract standardized user metrics from raw API response."""
    if not user_data:
        return {}

    # Navigate to the actual user data (varies by platform)
    data = user_data.get("data", user_data)
    if isinstance(data, dict) and "data" in data:
        data = data["data"]

    if platform == "xiaohongshu":
        return {
            "nickname": data.get("nickname", ""),
            "desc": data.get("desc", ""),
            "followers": safe_int(data.get("fans")),
            "following": safe_int(data.get("follows")),
            "total_likes": safe_int(data.get("interaction")),
            "note_count": safe_int(data.get("ndiscovery", data.get("note_num_stat", {}).get("posted", 0))),
            "collected": safe_int(data.get("collected", data.get("note_num_stat", {}).get("collected", 0))),
            "total_liked": safe_int(data.get("note_num_stat", {}).get("liked", 0)),
        }
    elif platform == "douyin":
        return {
            "nickname": data.get("nickname", ""),
            "desc": data.get("signature", ""),
            "followers": safe_int(data.get("follower_count")),
            "following": safe_int(data.get("following_count")),
            "total_likes": safe_int(data.get("total_favorited")),
            "note_count": safe_int(data.get("aweme_count")),
        }
    elif platform == "tiktok":
        return {
            "nickname": data.get("nickname", ""),
            "desc": data.get("signature", ""),
            "followers": safe_int(data.get("follower_count")),
            "following": safe_int(data.get("following_count")),
            "total_likes": safe_int(data.get("total_favorited", data.get("heart_count"))),
            "note_count": safe_int(data.get("aweme_count", data.get("video_count"))),
        }
    elif platform == "bilibili":
        return {
            "nickname": data.get("name", ""),
            "desc": data.get("sign", ""),
            "followers": safe_int(data.get("follower", data.get("fans"))),
            "following": safe_int(data.get("following")),
            "total_likes": safe_int(data.get("likes")),
        }
    # Generic fallback
    return {
        "nickname": data.get("nickname", data.get("name", data.get("username", ""))),
        "followers": safe_int(data.get("followers", data.get("follower_count", data.get("fans")))),
    }


def extract_post_ids(posts_data: dict, platform: str) -> list[str]:
    """Extract post/note IDs from a posts list response."""
    if not posts_data:
        return []

    data = posts_data.get("data", posts_data)
    if isinstance(data, dict) and "data" in data:
        data = data["data"]

    if platform == "xiaohongshu":
        notes = data.get("notes", [])
        return [n.get("note_id", n.get("id", "")) for n in notes if n.get("note_id") or n.get("id")]
    elif platform in ("douyin", "tiktok"):
        awemes = data.get("aweme_list", data.get("aweme_details", []))
        return [str(a.get("aweme_id", "")) for a in awemes if a.get("aweme_id")]
    elif platform == "bilibili":
        vlist = data.get("list", {}).get("vlist", data.get("vlist", []))
        return [str(v.get("bvid", "")) for v in vlist if v.get("bvid")]
    return []


def extract_post_metrics(detail_data: dict, platform: str) -> dict | None:
    """Extract standardized metrics from a single post detail response."""
    if not detail_data:
        return None

    data = detail_data.get("data", detail_data)

    if platform == "xiaohongshu":
        # app/get_note_info returns data as list
        if isinstance(data, dict) and "data" in data:
            inner = data["data"]
            if isinstance(inner, list) and inner:
                note_list = inner[0].get("note_list", [])
                note = note_list[0] if note_list else {}
            else:
                note = inner
        elif isinstance(data, list) and data:
            note_list = data[0].get("note_list", [])
            note = note_list[0] if note_list else {}
        else:
            note = data

        return {
            "title": note.get("title", note.get("display_title", ""))[:60],
            "likes": safe_int(note.get("liked_count")),
            "comments": safe_int(note.get("comments_count")),
            "collects": safe_int(note.get("collected_count")),
            "shares": safe_int(note.get("share_count")),
            "type": "video" if note.get("type") == "video" else "image",
        }

    elif platform in ("douyin", "tiktok"):
        aweme = data.get("aweme_detail", data)
        if isinstance(aweme, dict) and "aweme_details" in aweme:
            aweme = aweme["aweme_details"][0] if aweme["aweme_details"] else {}
        stats = aweme.get("statistics", {})
        return {
            "title": (aweme.get("desc", "") or "")[:60],
            "likes": safe_int(stats.get("digg_count")),
            "comments": safe_int(stats.get("comment_count")),
            "collects": safe_int(stats.get("collect_count")),
            "shares": safe_int(stats.get("share_count")),
            "plays": safe_int(stats.get("play_count")),
        }

    elif platform == "bilibili":
        video = data.get("video_data", data)
        stat = video.get("stat", {})
        return {
            "title": (video.get("title", "") or "")[:60],
            "likes": safe_int(stat.get("like")),
            "comments": safe_int(stat.get("reply")),
            "collects": safe_int(stat.get("favorite")),
            "shares": safe_int(stat.get("share")),
            "plays": safe_int(stat.get("view")),
        }

    return None


def compute_account_metrics(user_metrics: dict, post_metrics_list: list[dict]) -> dict:
    """Compute aggregate account metrics from user profile + post details."""
    if not post_metrics_list:
        return {"total_posts_analyzed": 0}

    total_likes = sum(p.get("likes", 0) for p in post_metrics_list)
    total_comments = sum(p.get("comments", 0) for p in post_metrics_list)
    total_collects = sum(p.get("collects", 0) for p in post_metrics_list)
    n = len(post_metrics_list)
    followers = user_metrics.get("followers", 0)

    avg_likes = round(total_likes / n)
    avg_comments = round(total_comments / n)
    avg_collects = round(total_collects / n)

    er = engagement_rate(avg_likes, avg_comments, avg_collects, followers) if followers > 0 else 0

    # Sort by likes to find top posts
    sorted_posts = sorted(post_metrics_list, key=lambda p: p.get("likes", 0), reverse=True)

    # Content type distribution
    type_counts = {}
    for p in post_metrics_list:
        t = p.get("type", "unknown")
        type_counts[t] = type_counts.get(t, 0) + 1

    # Collect/like ratio (indicates utility value)
    collect_rate = round(total_collects / total_likes, 2) if total_likes > 0 else 0

    return {
        "total_posts_analyzed": n,
        "total_likes": total_likes,
        "total_comments": total_comments,
        "total_collects": total_collects,
        "avg_likes": avg_likes,
        "avg_comments": avg_comments,
        "avg_collects": avg_collects,
        "engagement_rate": er,
        "collect_like_ratio": collect_rate,
        "top_posts": sorted_posts[:5],
        "content_type_distribution": type_counts,
    }


def assess_comment_quality(comments_batches: list[list[dict]]) -> dict:
    """Assess comment quality from multiple batches of comments."""
    all_comments = []
    for batch in comments_batches:
        if not batch:
            continue
        data = batch.get("data", batch) if isinstance(batch, dict) else batch
        if isinstance(data, dict):
            data = data.get("data", data)
            comments = data.get("comments", [])
        elif isinstance(data, list):
            comments = data
        else:
            comments = []
        all_comments.extend(comments)

    if not all_comments:
        return {"total_comments": 0, "quality": "insufficient_data"}

    total = len(all_comments)
    # Simple heuristics for quality
    lengths = [len(c.get("text", c.get("content", ""))) for c in all_comments]
    avg_length = sum(lengths) / total if total > 0 else 0
    short_comments = sum(1 for l in lengths if l <= 2)
    short_ratio = round(short_comments / total, 2) if total > 0 else 0

    # Quality assessment
    if short_ratio > 0.6:
        quality = "low"
    elif short_ratio > 0.3:
        quality = "medium"
    else:
        quality = "high"

    return {
        "total_comments": total,
        "avg_length": round(avg_length, 1),
        "short_comment_ratio": short_ratio,
        "quality": quality,
    }
