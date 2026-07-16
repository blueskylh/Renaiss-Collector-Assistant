# Renaiss Collector Assistant

Version: `0.1.11`

这是一个面向主流 agent 的 Renaiss 能力包，覆盖：

- Renaiss CLI 安装与使用；
- Renaiss Marketplace 全量采集；
- Renaiss 卡牌查询；
- PSA cert 连号候选扫描；
- 套利与 FMV 折价扫描；
- 卡牌价格监控；
- Renaiss BSC 钱包与老钱包迁移分析；
- Renaiss OS Index API 查询；

## 快速安装

```bash
cd renaiss-collector-assistant-skill
cp config.example.env .env
# 钱包历史 / BSC 链上分析请在 .env 中填写：ALCHEMY_API_KEY=your_alchemy_api_key_here
bash scripts/install_check.sh
```

## 基础命令

检查环境：

```bash
python3 scripts/renaiss_cli_tools.py check
```

抓取已挂单 marketplace 快照（写入采用临时文件 + 原子替换，避免失败刷新覆盖上一份完整数据）：

```bash
python3 scripts/renaiss_cli_tools.py marketplace-snapshot --listed --limit 100 --out data/marketplace.jsonl
```

抓取 PSA 已挂单卡并扫描连号。Marketplace 返回的 `attributes.Serial` 已满足 Sequential Cert 的核心需求，所以连号扫描优先直接用 marketplace snapshot，不必每张都跑 `renaiss card`：

```bash
python3 scripts/renaiss_cli_tools.py marketplace-snapshot --listed --grading PSA --out data/psa_marketplace.jsonl
python3 scripts/renaiss_cli_tools.py sequential-scan --cards data/psa_marketplace.jsonl --out outputs/sequential_candidates.csv
```

套利扫描不要限制评级公司；先抓全部 listed，再按需要补充 card detail。`card-details` 默认 auto：10 张以内用 CLI，超过 10 张用 API URL `https://api.renaiss.xyz/v0/cards/{tokenId}?verbosePrice=true`，并启用分批、限速、冷却和断点续跑：

```bash
python3 scripts/renaiss_cli_tools.py marketplace-snapshot --listed --out data/marketplace_all_listed.jsonl
python3 scripts/renaiss_cli_tools.py card-details --input data/marketplace_all_listed.jsonl --out data/card_details.jsonl
python3 scripts/renaiss_cli_tools.py arbitrage-scan --cards data/card_details.jsonl --out outputs/arbitrage_candidates.csv
```

显式指定 API 安全批量参数：

```bash
python3 scripts/renaiss_cli_tools.py card-details \
  --input data/marketplace_all_listed.jsonl \
  --out data/card_details.jsonl \
  --method api \
  --batch-size 10 \
  --inter-request-delay 1 \
  --batch-cooldown 5 \
  --forbidden-cooldown 300
```

如需断点续跑，直接重复同一条命令即可；脚本会跳过已成功 tokenId，并默认重试上次失败的 tokenId。

扫描连号候选：

```bash
python3 scripts/renaiss_cli_tools.py sequential-scan --cards data/psa_card_details.jsonl --out outputs/sequential_candidates.csv
```

扫描套利机会：

```bash
python3 scripts/renaiss_cli_tools.py arbitrage-scan --cards data/psa_card_details.jsonl --out outputs/arbitrage_candidates.csv
```


Renaiss OS Index 价格套利扫描（需要 `.env` 中配置 Renaiss OS Index API key，公共额度只适合小测试）：

```bash
python3 scripts/renaiss_cli_tools.py index-arbitrage-scan \
  --cards data/marketplace_all_listed.jsonl \
  --out outputs/index_arbitrage_candidates.csv
```

输出会包含 `index_price_usd`、`index_confidence`、`exact_cert_match`、`index_spread_usdt` 和 `risk_notes`。脚本会先用 `/v1/graded/{cert}` 做精确 cert 查询；如果 cert 命中但价格为空，会按返回的 `href` 回退查询 card overview 价格。不能 exact cert match 或仍没有 Index 价格的行会写入 `outputs/index_arbitrage_candidates.csv.errors.jsonl`；每张卡的处理状态会写入 `outputs/index_arbitrage_candidates.csv.state.jsonl`。`--resume` 只跳过同一输入快照内尚未过期的 terminal 状态，默认 TTL 为 6 小时，避免动态价格状态长期跳过。

卡牌 watchlist 快照：

```bash
python3 scripts/renaiss_cli_tools.py watchlist-snapshot \
  --watchlist data/watchlist.txt \
  --out outputs/watchlist_snapshot.jsonl
```

Renaiss Index API 查询：

```bash
python3 scripts/renaiss_index_api.py search --q charizard --limit 5
python3 scripts/renaiss_index_api.py indices
python3 scripts/renaiss_index_api.py graded --cert PSA149595098
```

BSC 迁移交易解析：

```bash
python3 scripts/bsc_wallet_analyzer.py decode-migration-tx --tx 0x2d6a672c59b67dac82ac4c01e04e1e95bea8f107595239e35a0d84bc2f8c0f67
```

Renaiss 钱包报告，自动识别并合并迁移前 / 迁移后钱包。钱包历史使用 Alchemy BNB Mainnet，需在 `.env` 中配置 `ALCHEMY_API_KEY`：

```bash
python3 scripts/bsc_wallet_analyzer.py wallet-report \
  --address 0x032e4a8eb38843a65ce5e65131d1f99c10b03201 \
  --history-source alchemy \
  --out outputs/wallet_report.json \
  --out-md outputs/wallet_report.md \
  --max-wallets 20
```

`wallet-report` 会先通过 Alchemy 查询输入地址的钱包历史，发现 `LegacyAssetMigrationHelper` 迁移交易后，把旧钱包和新钱包合并成 `wallet_cluster`，并排除迁移内部转账后统计 Renaiss NFT、当前 SBT 持仓、Marketplace、Pack 和 USDT 流向。批量开包会按 pack 单价推断 1/5/10 或未来其他整数倍的 pack 数量。

查询每个 RenaissSBT 当前 holder 数排名，用来判断 SBT 稀有程度：

```bash
python3 scripts/bsc_wallet_analyzer.py sbt-holder-ranking \
  --max-pages 500 \
  --out outputs/sbt_holder_ranking.json \
  --out-csv outputs/sbt_holder_ranking.csv
```

如果输出里的 `complete=false`，说明 Alchemy 仍有后续分页，需要提高 `--max-pages` 后重跑。

## 重要规则

- Sequential Cert 看 `attributes.Serial`，不是 `cardNumber`。
- 连号不要求同一张卡，也不要求 PSA 10。
- 套利卖出端扣除 2% 手续费；gas 默认忽略。
- 钱包分析必须合并旧钱包与新钱包；迁移交易不计入 PnL。
- RenaissSBT 是 ERC-1155 风格，必须解析 `TransferBatch`。
