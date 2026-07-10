# Wallet Cluster Workflow

Use when a user asks for Renaiss wallet analysis.

```bash
python3 scripts/bsc_wallet_analyzer.py wallet-report \
  --address <wallet> \
  --out outputs/wallet_report.json \
  --out-md outputs/wallet_report.md
```

## Required behavior

1. Query recent BSC wallet history for the supplied address.
2. Decode every transaction receipt through BSC RPC.
3. If a `LegacyAssetMigrationHelper` transaction is found, infer:
   - `old_wallet`
   - `new_wallet`
   - migrated USDT
   - migrated Renaiss NFT count
   - migrated SBT IDs from ERC-1155 `TransferBatch` / `TransferSingle`
4. Add the paired wallet to `wallet_cluster` and query/decode it too.
5. Exclude cluster-internal migration transfers from net flow / PnL.
6. Resolve SBT names:
   - call ERC-1155 `uri(id)` on `RENAISS_SBT_CONTRACT`
   - fetch the returned metadata JSON
   - report `name`, not just numeric IDs
7. Classify Renaiss activity:
   - `marketplace_candidate`
   - `pack_or_buyback_candidate`
   - `sbt_activity`
   - `legacy_wallet_migration`
   - `renaiss_related`
8. Report current wallet, legacy wallets, migration txs, SBT names, NFT in/out, Marketplace buys/sells, Pack buys, pack type inference, buyback candidates, and net USDT flow excluding internal migration.

## Pack and buyback heuristics

- Marketplace proxy: `0xae3e7268ef5a062946216a44f58a8f685ffd11d0`.
- Current/legacy pack contracts include `0x94e...`, `0xfda...`, `0xb289...`, and observed legacy settlement `0xaab5f5fa75437a6e9e7004c12c9c56cda4b4885a`.
- Legacy selector `0x3233aac2` with user USDT out is treated as pack/open spend.
- Legacy selector `0xb24f1607` with user USDT in is treated as buyback/sell-back income.
- Infer pack type from `renaiss packs --json` current pack prices where possible; historical unmatched amounts must be labeled `legacy-or-unknown-*`.

## Caveat

The default command uses recent wallet history by default. For exhaustive old history and very active wallets, connect an indexer or Etherscan/BscScan V2 API key and paginate completely.


## Scan completeness

Use `--max-wallets` to control cluster breadth. If `wallet_scan_truncated = true`, treat spend/income/net spend as partial until pending wallets are scanned.
