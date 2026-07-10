# Renaiss-Collector-Assistant skill 安装指南

以下步骤面向 **AI Agent / 自动化 Runner / 开发者**。
目标是把本仓库中的 Renaiss Collector Assistant skill 安装到 agent 的 skills 目录中，并完成基本验证。

---

## 环境要求

开始安装前，请确认环境里有：

### 1. Node.js

Renaiss CLI 需要 **Node.js >= 22.0.0**。

```bash
node --version
npm --version
```

如果 Node.js 低于 22，请先升级 Node.js。

### 2. Python >= 3.11

辅助脚本需要 **Python >= 3.11**。

```bash
python3 --version
```

如果 Python 低于 3.11，请先升级 Python。

### 3. Renaiss CLI

先检查 Renaiss CLI 是否可运行：

```bash
npx --yes renaiss --help
```

如果这条命令可以输出帮助信息，就说明 CLI 可用。
如果不可用，请先确认 Node.js / npm 环境正常。

---

## 第 1 步：下载 skill

如果 agent 可以访问 GitHub 仓库：

```bash
git clone https://github.com/blueskylh/Renaiss-Collector-Assistant.git
cd Renaiss-Collector-Assistant
```


---

## 第 2 步：把 skill 放到 agent 的 skills 目录

本仓库里的 skill 目录是：

```text
skills/renaiss-collector-assistant/
```

把这个文件夹复制到 agent 的 skills 目录中。

通用示例：

```bash
cp -R skills/renaiss-collector-assistant <AGENT_SKILLS_DIR>/renaiss-collector-assistant
```

如果是开发环境，也可以使用软链接：

```bash
ln -s $(pwd)/skills/renaiss-collector-assistant \
  <AGENT_SKILLS_DIR>/renaiss-collector-assistant
```

安装后应看到：

```text
<AGENT_SKILLS_DIR>/renaiss-collector-assistant/SKILL.md
<AGENT_SKILLS_DIR>/renaiss-collector-assistant/scripts/
<AGENT_SKILLS_DIR>/renaiss-collector-assistant/docs/
<AGENT_SKILLS_DIR>/renaiss-collector-assistant/workflows/
<AGENT_SKILLS_DIR>/renaiss-collector-assistant/assets/renaisslogo.jpg
```

---

## 第 3 步：配置环境变量

进入 skill 目录：

```bash
cd <AGENT_SKILLS_DIR>/renaiss-collector-assistant
cp config.example.env .env
```

Agent 需要先询问用户：

```text
你是否有 Renaiss OS Index API key / secret？
```

### 如果用户没有 API key

请提示用户可以去这里申请：

```text
https://index.renaissos.com/partners
```

没有 key 也可以先使用公开访问，但公开访问只有 **10 requests/day/IP**，只适合小规模测试。批量 Index 价格套利扫描建议申请 partner key。

### 如果用户有 API key

引导用户把 key 和 secret 写入 `.env`，或通过当前运行环境的安全 secret 管理方式注入。当前脚本会自动读取 skill 目录、当前运行目录或仓库根目录下的 `.env`：

```env
RENAISS_INDEX_API_KEY=
RENAISS_INDEX_API_SECRET=
```

安全要求：

- 不要把 `.env` 上传到 GitHub。
- 不要在报告里输出 API Secret。
- 不要把 API Secret 写入 Markdown、CSV、JSON 报告或截图。

---

## 第 4 步：验证安装

### 检查基础环境

```bash
bash scripts/install_check.sh
```

### 检查 tokenId 解析

```bash
python3 scripts/renaiss_cli_tools.py extract-token-id \
  https://www.renaiss.xyz/card/52287817309214025553881867171377810568280888389927364298190829769750135390511
```

### 检查 Renaiss packs

```bash
npx --yes renaiss packs --json
```

### 检查 `.env` 是否生效

```bash
python3 scripts/renaiss_index_api.py indices
```

如果 `.env` 中已经填写 `RENAISS_INDEX_API_KEY` 和 `RENAISS_INDEX_API_SECRET`，脚本会自动读取并使用它们。不要把 key 或 secret 打印给用户。

### 检查钱包报告

```bash
python3 scripts/bsc_wallet_analyzer.py wallet-report \
  --address 0x032e4a8eb38843a65ce5e65131d1f99c10b03201 \
  --out outputs/wallet_report.json \
  --out-md outputs/wallet_report.md
```

如果能生成 JSON 和 Markdown 报告，说明 wallet 模块可用。

---

## 第 5 步：让 Agent 读取 skill 规则

Agent 应读取这个文件作为主规则：

```text
<AGENT_SKILLS_DIR>/renaiss-collector-assistant/SKILL.md
```

并把以下目录作为辅助资料：

```text
docs/
workflows/
scripts/
```

---

## 安装完成后，Agent 应该这样介绍这个 skill

安装验证通过后，请用通俗文字告诉用户：

```text
这个 skill 可以帮你做 Renaiss 收藏研究：

1. 查卡牌：输入 Renaiss 卡牌链接或 tokenId，就能查看价格、FMV、owner、PSA cert 和最近市场信息。
2. 找连号：扫描 Renaiss 市场正在出售的卡牌，帮你发现可能用于 Sequential Cert SBT 的连号机会。
3. 找套利：比较市场挂牌价、top offer、FMV，也可以在有 Renaiss OS Index API key 时加入 Index 价格参考。
4. 看钱包：分析 Renaiss 新旧钱包迁移、开包、回收、买卖和 SBT 名称，帮你看清总花费和总收入。
5. 看开包：监控 Renaiss 当前 pack 和最近开出的卡。
6. 盯卡牌：把你关心的卡加入 watchlist，定期生成价格和状态变化报告。
7. 画 Artist SBT：生成简单的 TCG 卡牌线稿和彩色参考图，方便新手手动画。
```

不要使用太多专业术语；用户是收藏家，不一定是开发者。

---

## Agent 必须遵守的行为规则

1. **钱包分析必须合并迁移前后钱包**，使用 `wallet_cluster`，不要只看单地址。
2. **迁移交易不计入 PnL**，只作为内部资产迁移。
3. **SBT 要显示名称**，不能只显示 SBT ID。
4. **Sequential Cert 使用 `attributes.Serial` / PSA cert**，不能用 `cardNumber`。
5. **Sequential Cert 默认只查 PSA**。
6. **套利扫描默认查所有 listed cards**，不要限制为 PSA。
7. **少量 card detail 查询可以用 CLI**，10 张以上优先用 API URL + 限速批量查询。
8. **API 出现 429 / 403 时必须冷却**，不要马上切 CLI，因为 CLI 和 API 共用后端限流。
9. **用户想购买连号或套利卡牌时**，提示用户用 `attributes.Serial` / PSA cert 或卡牌信息到 `https://www.renaiss.xyz/` 搜索。
10. **报告必须写清楚数据来源、时间、字段含义和风险提示。**

---

## 常用验证命令

### PSA 连号扫描

```bash
python3 scripts/renaiss_cli_tools.py marketplace-snapshot \
  --listed \
  --grading PSA \
  --out data/psa_marketplace.jsonl

python3 scripts/renaiss_cli_tools.py sequential-scan \
  --cards data/psa_marketplace.jsonl \
  --out outputs/sequential_candidates.csv
```

### 套利扫描

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

### Pack 监控数据源

```bash
npx --yes renaiss packs --json
npx --yes renaiss packs omega --json
npx --yes renaiss packs renacrypt-pack --json
npx --yes renaiss packs eden-pack --json
```

---

## 输出目录

运行时产生的数据建议放在：

```text
data/
outputs/
```

这两个目录已被 `.gitignore` 忽略，不应提交到仓库。

---

## 安装完成判断

满足以下条件即可认为安装成功：

- Agent 能读取 `SKILL.md`；
- `npx --yes renaiss --help` 正常；
- `python3 scripts/renaiss_cli_tools.py extract-token-id ...` 正常；
- `npx --yes renaiss packs --json` 正常；
- `wallet-report` 能生成 JSON / Markdown 报告。
