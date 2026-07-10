# Renaiss Collector Assistant

Version: `0.1.3`

这是一个面向主流 agent 的 Renaiss 能力包，覆盖：

- Renaiss CLI 安装与使用；
- Renaiss Marketplace 全量采集；
- Renaiss 卡牌查询；
- PSA cert 连号候选扫描；
- 套利与 FMV 折价扫描；
- 卡牌价格监控；
- Renaiss BSC 钱包与老钱包迁移分析；
- Renaiss OS Index API 查询；
- Renaiss Artist SBT 辅助创作。

## 快速安装

```bash
cd renaiss-collector-assistant-skill
cp config.example.env .env
bash scripts/install_check.sh
```

## 基础命令

检查环境：

```bash
python3 scripts/renaiss_cli_tools.py check
```

抓取已挂单 marketplace 快照：

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

Renaiss 钱包报告，自动识别并合并迁移前 / 迁移后钱包：

```bash
python3 scripts/bsc_wallet_analyzer.py wallet-report \
  --address 0x032e4a8eb38843a65ce5e65131d1f99c10b03201 \
  --out outputs/wallet_report.json \
  --out-md outputs/wallet_report.md
```

`wallet-report` 会先查询输入地址的钱包历史，发现 `LegacyAssetMigrationHelper` 迁移交易后，把旧钱包和新钱包合并成 `wallet_cluster`，并排除迁移内部转账后统计 Renaiss NFT、SBT、Marketplace、Pack 和 USDT 流向。

## 重要规则

- Sequential Cert 看 `attributes.Serial`，不是 `cardNumber`。
- 连号不要求同一张卡，也不要求 PSA 10。
- 套利卖出端扣除 2% 手续费；gas 默认忽略。
- 钱包分析必须合并旧钱包与新钱包；迁移交易不计入 PnL。
- RenaissSBT 是 ERC-1155 风格，必须解析 `TransferBatch`。
- Renaiss Artist 输出必须包含黑白线稿和彩色参考图，并把 Renaiss logo 明确放入画面。
