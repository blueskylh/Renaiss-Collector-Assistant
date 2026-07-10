# Arbitrage Workflow

Arbitrage must scan all listed cards. Do not restrict to PSA unless the user explicitly asks for PSA-only arbitrage.

## Mode A: Renaiss marketplace / top offer / FMV scan

1. Fetch all listed marketplace rows:

```bash
python3 scripts/renaiss_cli_tools.py marketplace-snapshot --listed --out data/marketplace_all_listed.jsonl
```

2. Enrich card detail only when needed for top offer / verbose price data. In auto mode, <=10 cards use CLI; >10 cards use the direct API URL with rate-safe batching:

```bash
python3 scripts/renaiss_cli_tools.py card-details --input data/marketplace_all_listed.jsonl --out data/card_details.jsonl
```

3. Scan candidates:

```bash
python3 scripts/renaiss_cli_tools.py arbitrage-scan --cards data/card_details.jsonl --out outputs/arbitrage_candidates.csv
```

Rules:

- Convert USDT wei and USD cents.
- Deduct 2% seller fee from the sell side.
- Rank by `ranking_value`, not by a negative direct-profit field.
- Include `opportunity_type` so direct top-offer opportunities and FMV-discount opportunities are not confused.
- Include risk notes in every report.

## Mode B: Renaiss OS Index price arbitrage

Use this only when the user has Renaiss OS Index API key/secret. Public Index access is limited to 10 requests/day/IP and is not enough for scanning many marketplace cards.

Input is the Renaiss marketplace snapshot. The scanner uses each card's marketplace `attributes.Serial` value as the Index API search query, then compares Index benchmark price with Renaiss market ask:

```bash
python3 scripts/renaiss_cli_tools.py index-arbitrage-scan \
  --cards data/marketplace_all_listed.jsonl \
  --out outputs/index_arbitrage_candidates.csv
```

For a tiny public-quota smoke test only:

```bash
python3 scripts/renaiss_cli_tools.py index-arbitrage-scan \
  --cards data/marketplace_all_listed.jsonl \
  --out outputs/index_arbitrage_candidates.csv \
  --max-cards 2 \
  --allow-public-index
```

Output must include:

- `index_price_usd`
- `index_price_net_usd`
- `index_spread_usdt`
- `index_spread_pct`
- `index_confidence`
- `index_href`
- risk notes

Risk language:

- Renaiss OS Index price is a benchmark, not executable liquidity.
- Renaiss market ask may change or expire.
- Top offer may expire, withdraw, or have conditions.
- Seller fee is included; gas is ignored by default.

If the user wants to buy a candidate, tell them to search the PSA cert / serial or card details on `https://www.renaiss.xyz/`.
