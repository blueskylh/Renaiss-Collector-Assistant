# Sequential Cert Workflow

Sequential Cert is PSA-only and must use `attributes.Serial` / PSA cert number, not `cardNumber`.

1. Fetch all listed PSA cards:

```bash
python3 scripts/renaiss_cli_tools.py marketplace-snapshot --listed --grading PSA --out data/psa_marketplace.jsonl
```

2. Scan directly from marketplace snapshot. Renaiss Marketplace rows include `attributes.Serial`, so per-card detail calls are usually unnecessary:

```bash
python3 scripts/renaiss_cli_tools.py sequential-scan --cards data/psa_marketplace.jsonl --out outputs/sequential_candidates.csv
```

3. Only call `card-details` as a fallback if serial fields are missing or the user wants richer evidence.
4. Add special tags.
5. Save raw data and final report.
6. Remind: final SBT validity is verified by Renaiss team.
7. If the user wants to buy a candidate card, tell them to search the PSA cert / `attributes.Serial` on `https://www.renaiss.xyz/`.
