<div align="center">

# Renaiss Collector Assistant

### A collector-first AI skill for Renaiss cards, wallets, packs, SBTs, monitoring, and market opportunities.

![Version](https://img.shields.io/badge/version-v0.1.10-black?style=for-the-badge)
![Renaiss](https://img.shields.io/badge/Renaiss-Collector%20Assistant-6C5CE7?style=for-the-badge)
![Multi Agent](https://img.shields.io/badge/Multi--Agent-Ready-00B894?style=for-the-badge)
![BSC](https://img.shields.io/badge/BSC-On--Chain-F0B90B?style=for-the-badge)

**Find better cards. Understand your wallet. Track packs. Discover sequential PSA cert opportunities.**

**[👉 立即注册 Renaiss (邀请链接)](https://www.renaiss.xyz/ref/blueskyone)** &nbsp;|&nbsp; **[🐦 Follow @blueskylh1](https://twitter.com/intent/user?screen_name=blueskylh1)**

</div>

---

## 🎬 Product Demo

> 这里预留给产品宣传视频 / Demo 视频。
> 后续可以把视频、GIF、截图或 YouTube / X 链接放在这里，让收藏家一打开仓库就能看到完整演示。

<!--
示例：
<p align="center">
  <a href="你的产品视频链接">
    <img src="media/product/demo-cover.png" alt="Renaiss Collector Assistant Demo" width="900" />
  </a>
</p>
-->

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
它把 Renaiss CLI、Renaiss OS Index API、BSC 链上数据、Marketplace 数据和收藏策略整合到一起，让你的 AI Agent 像收藏研究员一样工作。

---

## 🧩 Feature Overview

| 功能 | 能做什么 | 适合谁 |
|---|---|---|
| 🃏 **Card Research** | 查询 Renaiss 卡牌信息、价格、FMV、top offer、last sale、PSA cert、owner 和 vault 信息。 | 想快速了解某张卡价值和状态的收藏家 |
| 🔗 **Sequential Cert Finder** | 扫描 Renaiss 市场在售的连号卡牌，辅助用户获取 **Sequential Cert SBT**。 | 想找连号机会的收藏家 |
| 💹 **Arbitrage Scanner** | 扫描 Renaiss 市场所有正在出售的卡牌，计算扣除 **2% 卖方手续费** 后的潜在套利机会。 | 想找折价卡 / 套利机会的用户 |
| 📈 **Index Price Arbitrage** | 使用 Renaiss OS Index API 价格和 Renaiss 市场挂牌价做对比，并显示 Index 价格置信度。 | 有 Renaiss OS Index API key、想批量找价格差的用户 |
| 👛 **Wallet Intelligence** | 合并 Renaiss 新旧钱包，识别迁移、批量开包、Buyback、Marketplace 买卖、当前 SBT 持仓和 SBT 名称。 | 想看自己或其他收藏家真实成本和收入的用户 |
| 📦 **Pack Monitor** | 查询和监控 Renaiss 目前的开卡记录，跟踪 pack、最近开包、tier、FMV 和 tokenId。 | 想追踪开包动态和高价值 pull 的用户 |
| ⏰ **Card Watchlist Monitor** | 定时监控特定卡牌，跟踪价格、FMV、top offer、last sale、owner 和挂单状态变化。 | 想盯住目标卡牌价格变化的用户 |
| 🎨 **Artist Helper** | 用于生成带有 Renaiss 元素的 TCG 卡牌线稿和彩色参考图，帮助用户获取 **Renaiss Artist SBT**。 | 想画 Artist SBT，但不想从零构图的用户 |
| 🏅 **SBT Rarity Ranking** | 基于 RenaissSBT ERC-1155 转账重建每个 SBT ID 的当前 holder 数和 supply。 | 想判断 SBT 稀有程度的收藏家 |

> 后续你可以在这一段下面继续添加每个功能的截图、视频、案例和更详细说明。
> 建议素材放在 `media/images/`、`media/videos/` 或 `media/product/`。

---

## 🔎 Renaiss OS Index API Support

Renaiss OS Index API 可以作为 Renaiss Marketplace 之外的价格和卡牌索引来源。这个 skill 已经预留并接入以下能力：

| Index API 能力 | 用途 |
|---|---|
| Search | 搜索卡牌、系列、评级卡和价格信息 |
| Graded lookup | 按 PSA cert / graded cert 查询卡牌信息 |
| Indices | 查看 Index 支持的市场指数 / 数据集合 |
| Card by href | 通过 Index API 返回的 `href` 查询具体卡牌 |
| Index Price Arbitrage | 用 Index API 精确 cert 查询价格，对比 Renaiss 市场挂牌价，输出价格差和置信度 |

Index API 公共访问额度很低，适合小测试；批量套利扫描建议先申请 key：

```text
https://index.renaissos.com/partners
```

Index 套利使用 `/v1/graded/{cert}` 精确匹配 PSA cert；如果不能确认 exact cert match，候选不会进入套利榜单。扫描会写入状态 checkpoint 和 errors JSONL，方便断点续跑。

配置到 `.env` 后脚本会自动读取：

```env
RENAISS_INDEX_API_KEY=
RENAISS_INDEX_API_SECRET=
```

---

## 🔐 Alchemy API Setup for BSC Wallet Analysis

Renaiss wallet analysis uses **Alchemy BNB Mainnet** for complete wallet history and receipt decoding.

1. Open [Alchemy](https://www.alchemy.com/) and sign in.
2. Create a new app.
3. Select **BNB Chain / BNB Mainnet**.
4. Copy the API key into `.env`:

```env
ALCHEMY_API_KEY=your_alchemy_api_key_here
```

The helper scripts derive the RPC URL automatically:

```text
https://bnb-mainnet.g.alchemy.com/v2/<ALCHEMY_API_KEY>
```

Never commit `.env` or real API keys to GitHub.

---

## 🧠 Built for Multi-Agent Workflows

这个仓库不是只给某一个 AI 产品使用的。只要你的 agent 支持读取 Markdown skill / instructions 和运行脚本，就可以接入。

支持多种 agent / runner 场景，包括：**SurfAI、Codex、GPT、Claude、Claude Code、豆包 Agent 办公模式、OpenClaw、Hermes、WorkBuddy、Grok** 等。

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

## 🧰 Requirements

| Requirement | Version / Note |
|---|---|
| Node.js | **>= 22.0.0**，用于运行 Renaiss CLI |
| Python | **>= 3.11**，用于运行辅助脚本 |
| Renaiss CLI | `npx --yes renaiss` |
| Alchemy API key | 钱包历史 / BSC 链上分析建议配置；使用 BNB Mainnet 免费 key |
| Renaiss OS Index API key | 可选；批量 Index 价格套利扫描建议使用 |
| Wallet scan limit | 钱包报告默认最多扫描 20 个 cluster 地址，触顶会标记 partial |

---

## 🖼 Coming Soon

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
- Renaiss OS Index 价格是参考基准，不是可立即成交的买单。
- Marketplace snapshots are written atomically; failed refreshes should not overwrite the previous complete file.
- 套利计算默认扣除 **2% seller fee**，gas 默认忽略。
- Sequential Cert / SBT 最终有效性以 Renaiss 官方确认为准。
- 钱包分析会合并迁移前后 wallet cluster，避免重复计算迁移交易。

---

<div align="center">

**Renaiss Collector Assistant**
Built for collectors who want better data, faster research, and cleaner decisions.

</div>
