<div align="center">

# Renaiss Collector Assistant

### A collector-first AI skill for Renaiss cards, wallets, packs, SBTs, and market opportunities.

![Version](https://img.shields.io/badge/version-v0.1.4-black?style=for-the-badge)
![Renaiss](https://img.shields.io/badge/Renaiss-Collector%20Assistant-6C5CE7?style=for-the-badge)
![Multi Agent](https://img.shields.io/badge/Multi--Agent-Ready-00B894?style=for-the-badge)
![BSC](https://img.shields.io/badge/BSC-On--Chain-F0B90B?style=for-the-badge)

**Find better cards. Understand your wallet. Track packs. Discover sequential PSA cert opportunities.**

</div>

---

## ⚡ Quick Install

把下面这句话直接发送给你的 AI Agent：

```text
阅读此文档帮我安装 Renaiss-Collector-Assistant skill：https://github.com/blueskylh/Renaiss-Collector-Assistant/blob/main/AGENT_INSTALL.md
```

Agent 安装文档：[`AGENT_INSTALL.md`](./AGENT_INSTALL.md)

---

## ✨ What is this?

**Renaiss Collector Assistant** 是一个给 Renaiss 收藏家使用的 AI skill。  
它把 Renaiss CLI、Renaiss OS Index API、BSC 链上数据和收藏策略整合到一起，让你的 AI Agent 可以像收藏研究员一样工作。

你可以用它来：

<table>
<tr>
<td width="50%">

### 🃏 Card Research

查询 Renaiss 卡牌信息、价格、FMV、top offer、last sale、PSA cert、owner 和 vault 信息。

</td>
<td width="50%">

### 🔗 Sequential Cert Finder

扫描 PSA cert 连号机会，基于 `attributes.Serial`，不是 `cardNumber`。

</td>
</tr>
<tr>
<td width="50%">

### 💹 Arbitrage Scanner

扫描所有 listed cards，计算 2% 卖方手续费后的潜在 top-offer / FMV spread。

</td>
<td width="50%">

### 👛 Wallet Intelligence

合并 Renaiss 新旧钱包，识别迁移、开包、Buyback、Marketplace 买卖和 SBT 名称。

</td>
</tr>
<tr>
<td width="50%">

### 📦 Pack Monitor

读取 `renaiss packs`，跟踪当前 pack、最近开包、tier、FMV 和 tokenId。

</td>
<td width="50%">

### 🎨 Artist Helper

辅助生成 Renaiss Artist SBT 线稿和彩色参考图，并保留 Renaiss logo 视觉元素。

</td>
</tr>
</table>

---

## 🧠 Built for Multi-Agent Workflows

这个仓库不是只给某一个 AI 产品使用的。只要你的 agent 支持读取 Markdown skill / instructions 和运行脚本，就可以接入。

| Agent / Runner 类型 | 使用方式 |
|---|---|
| 通用 AI Agent | 读取 `AGENT_INSTALL.md`，安装 skill 文件夹 |
| 自研 Agent | 把 `skills/renaiss-collector-assistant/` 加入 skills 目录 |
| CLI Runner | 直接运行 `scripts/` 下的 Python 工具 |
| Research Agent | 使用 `SKILL.md` 作为 Renaiss 收藏研究规则 |
| Automation Agent | 使用 workflows 做定时监控、扫描、报告输出 |

---

## 🧩 Core Capabilities

| Capability | Collector Value |
|---|---|
| **Card Lookup** | 快速查询卡牌价格、评级、PSA cert、owner 和交易信息 |
| **PSA Sequential Cert** | 发现可能有 SBT 价值的连号 cert 组合 |
| **Marketplace Arbitrage** | 找到低挂单价、top offer 或 FMV spread 机会 |
| **Wallet Cluster Analysis** | 自动合并迁移前后钱包，不把迁移误算成 PnL |
| **SBT Name Resolver** | 查询钱包 SBT 时显示名称，而不是只显示数字 ID |
| **Pack Intelligence** | 识别开包数量、开包花费、pack 类型和最近开包动态 |
| **Buyback / Sell-back Detection** | 识别卖回项目方或 buyback-like 收入 |
| **Artist Workflow** | 生成适合 Renaiss Artist 的线稿和彩色参考图 |

---

## 📊 Example Collector Questions

你可以让 Agent 帮你问这些问题：

> “帮我查这个 Renaiss 钱包的总花费、总收入、净支出。”

> “帮我找当前 Marketplace 上的 PSA 连号 cert 候选。”

> “帮我扫描 Renaiss 上是否有套利机会，记得扣除 2% fee。”

> “帮我监控 Eden Pack 最近开出了哪些高 FMV 卡。”

> “帮我看这个用户迁移前的钱包和迁移后的钱包是不是同一个 collector cluster。”

---

## 🗂 Repository Layout

```text
.
├── README.md
├── AGENT_INSTALL.md
├── media/
│   ├── images/
│   ├── videos/
│   └── product/
└── skills/
    └── renaiss-collector-assistant/
        ├── SKILL.md
        ├── scripts/
        ├── docs/
        ├── workflows/
        ├── examples/
        └── assets/
```

`media/` 会用于后续产品截图、演示视频和宣传视频。  
`skills/renaiss-collector-assistant/` 是 agent 需要安装的 skill 源码目录。

---

## 🖼 Coming Soon

后续这里会加入更完整的视觉材料：

<table>
<tr>
<td align="center" width="33%"><b>Product Screenshots</b><br/>钱包报告、连号扫描、套利扫描</td>
<td align="center" width="33%"><b>Demo Videos</b><br/>从安装到运行完整流程</td>
<td align="center" width="33%"><b>Collector Cases</b><br/>真实钱包、pack、SBT 分析案例</td>
</tr>
</table>

---

## 🛡 Collector Notes

- FMV 是参考，不是保证成交价。
- top offer 可能撤回、过期或有额外条件。
- 套利计算默认扣除 **2% seller fee**，gas 默认忽略。
- Sequential Cert / SBT 最终有效性以 Renaiss 官方确认为准。
- 钱包分析会合并迁移前后 wallet cluster，避免重复计算迁移交易。

---

<div align="center">

**Renaiss Collector Assistant**  
Built for collectors who want better data, faster research, and cleaner decisions.

</div>
