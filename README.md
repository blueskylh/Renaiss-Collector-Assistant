# Renaiss Collector Assistant

**Renaiss Collector Assistant** 是一个面向 Renaiss 收藏家的工具包。它可以帮助你查询卡牌、发现 PSA 连号机会、扫描潜在套利、分析 Renaiss 钱包迁移、统计开包/卖回/交易平台买卖，并辅助制作 Renaiss Artist 作品。

> 简单理解：这是一个给 Renaiss 收藏家用的研究助手，不是只给开发者看的代码库。

---

## 它能帮你做什么？

### 1. 查卡牌

输入 Renaiss 卡牌链接或 tokenId，查询：

- 卡牌名称、年份、系列、编号；
- 评级公司和分数；
- PSA cert / `attributes.Serial`；
- 当前挂单价、FMV、top offer、last sale；
- owner、vault、图片和交易记录。

### 2. 找 PSA 连号

它会从 Renaiss Marketplace 已挂单的 PSA 卡里找：

- `PSA123456789` 和 `PSA123456790` 这种 cert 连号；
- 是否同系列、同角色、同语言、同等级、同 owner；
- 是否有 FMV 折价或低成本组合。

连号判断用的是 **`attributes.Serial` / PSA cert number**，不是卡牌编号 `cardNumber`。

### 3. 扫描潜在套利

它可以扫描 Renaiss Marketplace 的已挂单卡，计算：

- 买入价；
- top offer 扣除 2% 卖方手续费后的净收入；
- FMV 扣除 2% 后的参考价差；
- 潜在 profit / spread。

套利扫描默认不只看 PSA，而是看所有 listed cards。

### 4. 分析 Renaiss 钱包

它会把 Renaiss 平台迁移前后的钱包合并成一个 wallet cluster，例如：

- 当前钱包；
- 旧钱包；
- 迁移交易；
- SBT 名称；
- 开包数量和花费；
- Buyback / 卖回项目方收入；
- Marketplace 买入/卖出；
- 总花费、总收入、净支出/净获利。

重点：迁移交易只算内部转移，不会被错误算成收入或支出。

### 5. 监控开包和市场变化

可以用来监控：

- 当前有哪些 pack；
- 每个 pack 最近开出了什么卡；
- tier / FMV / tokenId；
- 新开包事件；
- 价格、owner、top offer、last sale 变化。

默认只输出报告，不接 Telegram、Discord 或 Email。

### 6. Renaiss Artist 辅助创作

可以生成：

- 黑白线稿；
- 彩色参考图；
- 带 Renaiss logo 的卡牌风格画面。

适合打印后手动上色，再发到 X 并 tag `@renaissxyz`。

---

## 仓库结构

```text
.
├── README.md                         # 给收藏家看的介绍
├── AGENT_INSTALL.md                  # 给 agent / AI 助手看的安装指南
├── media/                            # 后续放图片、视频、宣传素材
│   ├── images/
│   ├── videos/
│   └── product/
└── skills/
    └── renaiss-collector-assistant/  # 真正的 skill 文件和脚本
```

真正的 skill 在这里：

```text
skills/renaiss-collector-assistant/
```

---

## 快速开始

如果你只是收藏家，不需要理解所有代码。你可以让支持 skill 的 agent 安装这个目录：

```text
skills/renaiss-collector-assistant/
```

如果你是 agent 或开发者，请看：

```text
AGENT_INSTALL.md
```

---

## 常见使用例子

### 查询钱包

```bash
python3 scripts/bsc_wallet_analyzer.py wallet-report \
  --address 0x032e4a8eb38843a65ce5e65131d1f99c10b03201 \
  --out outputs/wallet_report.json \
  --out-md outputs/wallet_report.md
```

### 扫描 PSA 连号

```bash
python3 scripts/renaiss_cli_tools.py marketplace-snapshot \
  --listed \
  --grading PSA \
  --out data/psa_marketplace.jsonl

python3 scripts/renaiss_cli_tools.py sequential-scan \
  --cards data/psa_marketplace.jsonl \
  --out outputs/sequential_candidates.csv
```

### 扫描套利

```bash
python3 scripts/renaiss_cli_tools.py marketplace-snapshot \
  --listed \
  --out data/marketplace_all_listed.jsonl

python3 scripts/renaiss_cli_tools.py card-details \
  --input data/marketplace_all_listed.jsonl \
  --out data/card_details.jsonl

python3 scripts/renaiss_cli_tools.py arbitrage-scan \
  --cards data/card_details.jsonl \
  --out outputs/arbitrage_candidates.csv
```

> 注意：批量查询很多卡牌会花时间。100 张卡大约几分钟，500 张卡可能十几分钟以上，取决于 Renaiss API 限流和网络情况。

---

## 风险提示

- FMV 只是参考价，不代表一定能成交。
- top offer 可能撤回、过期或有未知限制。
- 套利计算默认扣除 2% 卖方手续费，但不包含 gas。
- Renaiss SBT 和 Sequential Cert 的最终有效性以 Renaiss 官方/团队确认为准。
- 钱包历史统计依赖链上数据和索引器，极活跃钱包可能需要完整分页或专用 indexer。

---

## 后续计划

这个仓库后续会加入：

- 产品截图；
- 使用演示视频；
- 钱包分析案例；
- 连号案例；
- 套利扫描案例；
- Renaiss Artist 作品示例。

这些素材会放在：

```text
media/
```

---

## 当前版本

当前 skill 版本：**v0.1.3**

主要能力已经包括：

- Renaiss CLI；
- Renaiss OS Index API；
- Renaiss Marketplace；
- BSC 钱包迁移识别；
- SBT 名称解析；
- PSA 连号扫描；
- 套利扫描；
- Pack 监控工作流；
- Artist 生图工作流。
