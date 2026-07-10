# Arbitrage Workflow

Arbitrage must scan all listed cards. Do not restrict to PSA unless the user explicitly asks for PSA-only arbitrage.

1. Fetch all listed marketplace rows:

```bash
python3 scripts/renaiss_cli_tools.py marketplace-snapshot --listed --out data/marketplace_all_listed.jsonl
```

2. Enrich card detail only when needed for top offer / verbose price data. In auto mode, <=10 cards use CLI; >10 cards use the direct API URL with rate-safe batching:

```bash
python3 scripts/renaiss_cli_tools.py card-details --input data/marketplace_all_listed.jsonl --out data/card_details.jsonl
```

3. Convert USDT wei and USD cents.
4. Deduct 2% seller fee.
5. Rank direct top-offer opportunities and FMV discount opportunities.
6. Save raw data, CSV candidates, and Markdown report.
7. Include risk notes in every report.
8. If the user wants to buy a candidate, tell them to search the PSA cert / `attributes.Serial` or card details on `https://www.renaiss.xyz/`.
