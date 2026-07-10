<div align="center">

# Renaiss Collector Assistant

### A collector-first AI skill for Renaiss cards, wallets, packs, SBTs, monitoring, and market opportunities.

![Version](https://img.shields.io/badge/version-v0.1.4-black?style=for-the-badge)
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

## 🧩 Features

### 🃏 Card Research

查询 Renaiss 卡牌信息、价格、FMV、top offer、last sale、PSA cert、owner 和 vault 信息。

> 媒体占位：后续可在这里插入卡牌查询截图或演示视频。

<!-- Add Card Research image/video here -->

---

### 🔗 Sequential Cert Finder

扫描 Renaiss 市场在售的连号卡牌，辅助用户获取 **Sequential Cert SBT**。  
连号判断基于 `attributes.Serial` / PSA cert number，不是 `cardNumber`。

> 媒体占位：后续可在这里插入连号扫描案例图或视频。

<!-- Add Sequential Cert Finder image/video here -->

---

### 💹 Arbitrage Scanner

扫描 Renaiss 市场所有正在出售的卡牌，计算扣除 **2% 卖方手续费** 后的潜在套利机会。

> 媒体占位：后续可在这里插入套利扫描结果图或视频。

<!-- Add Arbitrage Scanner image/video here -->

---

### 👛 Wallet Intelligence

合并 Renaiss 新旧钱包，识别迁移、开包、Buyback、Marketplace 买卖和 SBT 名称。  
适合查看一个收藏家的总花费、总收入、净支出 / 净获利。

> 媒体占位：后续可在这里插入钱包报告截图或视频。

<!-- Add Wallet Intelligence image/video here -->

---

### 📦 Pack Monitor

查询和监控 Renaiss 目前的开卡记录，跟踪 pack、最近开包、tier、FMV 和 tokenId。

> 媒体占位：后续可在这里插入 pack monitor 演示。

<!-- Add Pack Monitor image/video here -->

---

### ⏰ Card Watchlist Monitor

定时监控特定卡牌，跟踪价格、FMV、top offer、last sale、owner 和挂单状态变化。  
适合盯住你想买的卡，或监控自己持仓卡牌的市场变化。

> 媒体占位：后续可在这里插入卡牌监控示例。

<!-- Add Card Watchlist Monitor image/video here -->

---

### 🎨 Artist Helper

用于生成带有 Renaiss 元素的 TCG 卡牌线稿和彩色参考图，帮助用户获取 **Renaiss Artist SBT**。  
默认偏向 **宝可梦 TCG 风格**；除非用户特别要求，否则线稿会尽量简单，方便绘画新手用少量颜料笔手动上色。

> 媒体占位：后续可在这里插入线稿、上色前后对比或 Artist SBT 案例。

<!-- Add Artist Helper image/video here -->

---

## 🧠 Built for Multi-Agent Workflows

这个仓库不是只给某一个 AI 产品使用的。只要你的 agent 支持读取 Markdown skill / instructions 和运行脚本，就可以接入。

支持多种 agent / runner 场景，包括：**SurfAI、Codex、GPT、Claude、Claude Code、豆包 Agent 办公模式、OpenClaw、Hermes、WorkBuddy、Grok** 等。

| Agent / Runner 类型 | 使用方式 |
|---|---|
| 通用 AI Agent | 读取 `AGENT_INSTALL.md`，安装 skill 文件夹 |
| SurfAI / Research Agent | 使用 `SKILL.md` 作为 Renaiss 收藏研究规则 |
| Codex / Claude Code / CLI Runner | 直接运行 `scripts/` 下的 Python 工具 |
| 自研 Agent | 把 `skills/renaiss-collector-assistant/` 加入 skills 目录 |
| Automation Agent | 使用 `workflows/` 做定时监控、扫描、报告输出 |

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
