# Card Detail API Strategy

For small jobs, `npx --yes renaiss card <tokenId> --price --verbose --json` is fine. For bulk jobs, prefer the direct API endpoint and fall back to CLI only when the API URL changes or non-rate-limit errors occur.

## Endpoint

```text
GET https://api.renaiss.xyz/v0/cards/{tokenId}?verbosePrice=true
```

This endpoint returns the same high-level shape used by the CLI: `collectible`, `pricing`, and `activities`.

## Safety rules

The endpoint is protected by Vercel WAF. CLI and direct API share the same backend; when the API returns 429/403, immediately switching to CLI usually does not help.

Recommended defaults:

```env
RENAISS_CARD_DETAIL_METHOD=auto
RENAISS_CARD_DETAIL_API_THRESHOLD=10
RENAISS_CARD_DETAIL_API_CONCURRENCY=1
RENAISS_CARD_DETAIL_API_BATCH_SIZE=10
RENAISS_CARD_DETAIL_API_INTER_REQUEST_DELAY=1
RENAISS_CARD_DETAIL_API_BATCH_COOLDOWN=5
RENAISS_CARD_DETAIL_FORBIDDEN_COOLDOWN=300
```

## Performance estimate

Approximate runtime with API mode:

| Cards | Batches | Request spacing | Batch cooldown | Estimate |
|---:|---:|---:|---:|---:|
| 10 | 1 | 10s | 0s | ~10-30s depending API latency |
| 50 | 5 | 50s | 20s | ~70-120s |
| 100 | 10 | 100s | 45s | ~145-220s |
| 500 | 50 | 500s | 245s | ~12-18min |

Always tell the user when a bulk job may take minutes and ensure the agent/runtime can continue long enough.

## Fallback

- `200` → parse and save.
- `429` → cool down, retry once; reduce batch size if repeated.
- `403` → cool down at least 300s, retry once; do not immediately fallback to CLI.
- Other API errors → fallback to CLI for that tokenId.

## Smoke test

A 2026-07-10 smoke test using 10 requests at 1s spacing returned 10/10 HTTP 200. A separate 2-card API detail test returned 2/2 success with parsed PSA serials.
