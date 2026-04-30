# Asyre Search — Key Setup & Troubleshooting

How to get an API key, where keys are stored, how to top up, and what to do when things break.

---

## 1. Architecture (One-Minute Overview)

```
┌──────────┐      ┌─────────────────┐      ┌─────────────┐
│  Client  │ ───→ │  Asyre Gateway  │ ───→ │   TikHub    │
│ (skill)  │      │ (PM2 #19)       │      │  upstream   │
└──────────┘      └─────────────────┘      └─────────────┘
                  ↓ verifies thp_* key
                  ↓ debits credits
                  ↓ rate-limits 60-120/min
                  ↓ caches 24h
```

- **Gateway public endpoint**: `http://13.228.189.206/api/social`
- **Gateway internal**: `127.0.0.1:18795` on `xiuhe-cloud`
- **Auth**: `Authorization: Bearer thp_<48-hex-chars>`
- **Pricing**: per-endpoint, debited from prepaid USD balance

---

## 2. Where Keys Live

| Location | Path | Scope |
|----------|------|-------|
| **Server vault (master)** | `xiuhe-cloud:~/xiu-he/vault/.env.master` | `ASYRE_SEARCH_KEY` + `ASYRE_SEARCH_URL` |
| **Vault index** | `xiuhe-cloud:~/xiu-he/vault/README.md` | Looked up by humans |
| **Gateway DB** | `xiuhe-cloud:~/xiu-he/services/tikhub-proxy/proxy.db` | Source of truth for all keys + balances |
| **Local Mac (optional)** | `~/.config/asyre/search.env` | Sourced by `~/.zshrc` |

---

## 3. Creating a New Key

```bash
ssh xiuhe-cloud
cd ~/xiu-he/services/tikhub-proxy
python3 cli.py create-key 'My-Client-Name' --rate-limit 120 --notes 'description'
# → outputs: thp_xxxx... (save it, only shown once)
```

Then top it up:

```bash
# List keys to find the new key id
python3 cli.py list-keys

# Grant credits (USD)
python3 cli.py credit <key_id> 100.00 --note 'initial allocation'
```

---

## 4. Using the Key

### From the skill (server side)

```bash
ssh xiuhe-cloud
SK=$(grep ^ASYRE_SEARCH_KEY ~/xiu-he/vault/.env.master | cut -d= -f2)
ASYRE_SEARCH_KEY=$SK python3 ~/xiu-he/Projects/moltbot/skills/asyre-search/scripts/asyre_search.py \
  --platform xiaohongshu user <user_id>
```

### From local Mac (direct curl)

```bash
source ~/.config/asyre/search.env  # auto-loaded by zsh if present
curl -H "Authorization: Bearer $ASYRE_SEARCH_KEY" \
  "$ASYRE_SEARCH_URL/api/v1/xiaohongshu/web/get_user_info?user_id=XXX"
```

---

## 5. Operational Commands

```bash
# Balance + recent calls
ssh xiuhe-cloud "cd ~/xiu-he/services/tikhub-proxy && python3 cli.py list-keys"

# Top up by $50
ssh xiuhe-cloud "cd ~/xiu-he/services/tikhub-proxy && python3 cli.py credit <key_id> 50.00"

# Last 7 days usage stats for a key
ssh xiuhe-cloud "cd ~/xiu-he/services/tikhub-proxy && python3 cli.py stats --key <key_id> --days 7"

# Per-endpoint breakdown
ssh xiuhe-cloud "cd ~/xiu-he/services/tikhub-proxy && python3 cli.py stats-detail <key_id>"

# Revoke / restore a key
ssh xiuhe-cloud "cd ~/xiu-he/services/tikhub-proxy && python3 cli.py revoke-key <key_id>"
ssh xiuhe-cloud "cd ~/xiu-he/services/tikhub-proxy && python3 cli.py restore-key <key_id>"
```

---

## 6. Troubleshooting

### `❌ ASYRE_SEARCH_KEY not found`
Skill can't find the env var. Either:
- Forgot to `source ~/.config/asyre/search.env` (locally)
- Or didn't prepend `ASYRE_SEARCH_KEY=...` (server side)

### `401 Unauthorized: invalid or missing API key`
- Key revoked → run `python3 cli.py list-keys`, look for `❌ revoked`
- Wrong prefix → key must start with `thp_`

### `402 Insufficient credits`
- Top up: `python3 cli.py credit <key_id> 50.00`

### `429 Rate limit exceeded`
- Default 60 req/min. Bump with `--rate-limit 120` at create time, or wait 60s.

### `404 Endpoint not available on this gateway`
- Path not in gateway's allowlist. Either it's not whitelisted yet, or you're calling a TikHub endpoint that the upstream key doesn't have permission for (typically `web_v3/*`).

### `502 / 504 Gateway Time-out`
- Transient TikHub upstream issue or nginx timeout. Just retry.

### `400 from upstream` for `get_user_notes_v2`
- Some brand official accounts (e.g. 完美日记) reject this endpoint. Try `app_v2/get_user_posted_notes` instead via `raw` command, or skip those users.

### Pagination stuck at 21 notes
- TikHub upstream limit on `web/get_user_notes_v2`. The `has_more=true` but `cursor=null` bug is upstream-side. Workaround: try `app/get_user_notes` via `raw` (may need different params).

---

## 7. Test Suite (Last Verified: 2026-04-30)

Verified on `Asher-Internal` key against 4 KOL types:

| Test | Target | Result |
|------|--------|--------|
| search_users | 李佳琦 / 完美日记 / 张大奕 / Tim 罗翔 | ✅ all returned valid user_ids |
| user info | 完美日记 (186.1万粉) / 张大奕eve (30.6万) | ✅ |
| posts | 张大奕eve | ✅ (5 notes returned) |
| posts | 完美日记 (品牌官号) | ⚠️ 400 — known upstream limit |
| comments | 张大奕「小棉袄退房啦」(933评) | ✅ 10 comments |
| trending | XHS hot list | ✅ 20 items |
| search notes | "美妆" | ✅ 22 results |
| trending | TikTok | ✅ |
| trending | Douyin | ⚠️ skill formatter bug (data returned OK, parser fails) |
| trending | Bilibili | ⚠️ 422 — skill missing `limit` param |

**Conclusion**: XHS pipeline is production-ready. Douyin/Bilibili have skill-side bugs unrelated to gateway/key.
