# Card Detail Rate Strategy

## Empirical test

On 2026-07-10, the Renaiss card detail endpoint was tested against PSA-listed Marketplace tokenIds using `npx --yes renaiss card <tokenId> --price --verbose --json`.

| Phase | Concurrency | Launch spacing | Requests | OK | Forbidden | Median latency |
|---|---:|---:|---:|---:|---:|---:|
| c1_spacing15_probe | 1 | 15s | 6 | 6 | 0 | 5.16s |
| c2_spacing8_probe | 2 | 8s | 8 | 8 | 0 | 3.68s |
| c3_spacing6_probe | 3 | 6s | 9 | 9 | 0 | 3.33s |
| c1_spacing10_recheck | 1 | 10s | 6 | 6 | 0 | 3.04s |

Total: 29/29 successful, 0 Forbidden.

A prior full run at burst concurrency 10 produced a 94.68% failure rate with `Forbidden`, so the stable path is not high concurrency; it is paced launches with low parallelism.

## Production defaults

```env
RENAISS_CARD_DETAIL_CONCURRENCY=2
RENAISS_CARD_DETAIL_MAX_CONCURRENCY=3
RENAISS_CARD_DETAIL_BATCH_SIZE=20
RENAISS_CARD_DETAIL_INTER_REQUEST_DELAY=8
RENAISS_CARD_DETAIL_BATCH_COOLDOWN=90
RENAISS_CARD_DETAIL_FORBIDDEN_COOLDOWN=900
RENAISS_CARD_DETAIL_MAX_FORBIDDEN_PER_BATCH=1
RENAISS_CARD_DETAIL_RETRIES=1
RENAISS_CARD_DETAIL_TIMEOUT=120
```

## Operating model

- Launch requests every 8 seconds by default.
- Allow at most 2 in flight by default, 3 maximum.
- Write every batch to JSONL immediately.
- Resume by reading the output JSONL and skipping completed tokenIds.
- Retry prior error rows by default on the next run.
- Do not immediately retry `Forbidden`; cool down first.
- After any batch with `Forbidden`, sleep 900 seconds before continuing.

## Faster but riskier mode

Only use this when you accept possible API blocking:

```bash
python3 scripts/renaiss_cli_tools.py card-details \
  --input data/psa_marketplace.jsonl \
  --out data/psa_card_details.jsonl \
  --concurrency 3 \
  --batch-size 20 \
  --inter-request-delay 6 \
  --batch-cooldown 60 \
  --forbidden-cooldown 900
```

If `Forbidden` appears, stop and resume later with the conservative defaults.
