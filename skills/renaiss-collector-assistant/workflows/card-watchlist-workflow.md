# Card Watchlist Monitor Workflow

Use when the user wants to monitor specific Renaiss cards over time.

This is report-only by default: generate snapshots and Markdown/CSV reports. Do not assume Telegram, Discord, email, or push notifications unless the user explicitly connects a channel.

## 1. Create a watchlist

`data/watchlist.txt` can contain one tokenId or Renaiss card URL per line:

```text
https://www.renaiss.xyz/card/52287817309214025553881867171377810568280888389927364298190829769750135390511
52287817309214025553881867171377810568280888389927364298190829769750135390511
```

## 2. Take a snapshot

```bash
python3 scripts/renaiss_cli_tools.py watchlist-snapshot \
  --watchlist data/watchlist.txt \
  --out outputs/watchlist_snapshot_$(date -u +%Y%m%d_%H%M%S).jsonl
```

Default method is the direct card API URL because watchlists may contain more than a few cards. Use safe delay defaults and lower volume when testing.

## 3. Track changes

Compare the newest snapshot with the previous snapshot. Focus on collector-readable changes:

- Ask/listing price changed.
- FMV changed.
- Top offer changed.
- Last sale changed.
- Owner changed.
- Ask/listing expired or disappeared.
- Card moved into or out of vault/ownership state.

## 4. Output report

A report should include:

| Field | Meaning |
|---|---|
| tokenId / card URL | Card identity |
| Name / set / grade | What card it is |
| Ask price | Current listed price, converted from USDT wei to USDT |
| FMV | Current Renaiss FMV, converted from USD cents to USD |
| Top offer | Current best offer if available |
| Last sale | Most recent sale if available |
| Owner | Current owner if available |
| Change note | What changed since previous snapshot |

## 5. Suggested schedule

- High-interest cards: every 15-30 minutes.
- Normal watchlists: every 2-6 hours.
- Large watchlists: once per day, or split into batches to avoid API/WAF limits.

Always include data timestamp and remind users that FMV and top offer are references, not guaranteed executable liquidity.
