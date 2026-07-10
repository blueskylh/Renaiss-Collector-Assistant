# Agent Install Guide - Renaiss Collector Assistant

This file is for AI agents, automation runners, and developers who need to install or load the Renaiss Collector Assistant skill.

## Skill location

The skill lives under:

```text
skills/renaiss-collector-assistant/
```

The skill entry file is:

```text
skills/renaiss-collector-assistant/SKILL.md
```

Do not treat the repository root as the skill root. The repository root is for collector-facing documentation and future media assets.

---

## Install into an agent runtime

### Option A: Copy the skill folder

Copy this folder into the agent's skill directory:

```text
skills/renaiss-collector-assistant/
```

The final installed structure should look like:

```text
<agent-skills-dir>/renaiss-collector-assistant/SKILL.md
<agent-skills-dir>/renaiss-collector-assistant/scripts/
<agent-skills-dir>/renaiss-collector-assistant/docs/
<agent-skills-dir>/renaiss-collector-assistant/workflows/
<agent-skills-dir>/renaiss-collector-assistant/assets/renaisslogo.jpg
```

### Option B: Symlink during development

```bash
ln -s /path/to/Renaiss-Collector-Assistant/skills/renaiss-collector-assistant \
  <agent-skills-dir>/renaiss-collector-assistant
```

---

## Runtime prerequisites

### Node.js

Renaiss CLI requires Node.js `>=22.0.0`.

```bash
node --version
npm --version
npx --yes renaiss --help
```

### Python

The helper scripts use Python 3 and standard-library modules.

```bash
python3 --version
```

### Renaiss CLI

Use:

```bash
npx --yes renaiss --help
```

Do not point Renaiss CLI at the Index API host. Renaiss CLI uses `https://api.renaiss.xyz` and `/v0/...` routes by default.

---

## Environment configuration

Copy the example config if running scripts directly:

```bash
cd skills/renaiss-collector-assistant
cp config.example.env .env
```

Important variables:

```env
RENAISS_INDEX_API_BASE=https://api.renaissos.com
RENAISS_INDEX_API_KEY=
RENAISS_INDEX_API_SECRET=
BSC_RPC_URL_1=https://bsc-dataseed.binance.org/
```

Security rules:

- Never commit `.env`.
- Never print or store `RENAISS_INDEX_API_SECRET` in reports.
- Use `config.example.env` only as a template.

---

## Smoke tests

Run from the skill folder:

```bash
cd skills/renaiss-collector-assistant
bash scripts/install_check.sh
```

Check tokenId parsing:

```bash
python3 scripts/renaiss_cli_tools.py extract-token-id \
  https://www.renaiss.xyz/card/52287817309214025553881867171377810568280888389927364298190829769750135390511
```

Check packs:

```bash
npx --yes renaiss packs --json
```

Check wallet report:

```bash
python3 scripts/bsc_wallet_analyzer.py wallet-report \
  --address 0x032e4a8eb38843a65ce5e65131d1f99c10b03201 \
  --out outputs/wallet_report.json \
  --out-md outputs/wallet_report.md
```

---

## Agent behavior rules

When this skill is active, the agent should follow these rules:

1. **Wallets:** always analyze Renaiss wallets as a `wallet_cluster`, not a single address, because users may have legacy and current wallets after migration.
2. **Migration:** exclude `LegacyAssetMigrationHelper` internal transfers from PnL / net spend.
3. **SBT:** show SBT names, not IDs only. Resolve ERC-1155 `uri(id)` and fetch metadata JSON.
4. **Sequential Cert:** use `attributes.Serial` / PSA cert number, not `cardNumber`.
5. **Sequential scan:** PSA-only by default.
6. **Arbitrage scan:** do not restrict to PSA unless the user explicitly asks. Scan all listed cards.
7. **Card details:** for <=10 cards, CLI is fine; for >10 cards, prefer direct API URL with safe batching.
8. **Rate limits:** if card API returns 429/403, cool down; do not immediately switch to CLI because both share the same backend/WAF.
9. **Buying candidates:** tell users to search `attributes.Serial` / PSA cert or card detail on `https://www.renaiss.xyz/`.
10. **Reports:** include timestamps, source labels, field meanings, and risk notes.

---

## Useful commands

### Marketplace snapshot

```bash
python3 scripts/renaiss_cli_tools.py marketplace-snapshot \
  --listed \
  --out data/marketplace_all_listed.jsonl
```

### PSA Sequential Cert scan

```bash
python3 scripts/renaiss_cli_tools.py marketplace-snapshot \
  --listed \
  --grading PSA \
  --out data/psa_marketplace.jsonl

python3 scripts/renaiss_cli_tools.py sequential-scan \
  --cards data/psa_marketplace.jsonl \
  --out outputs/sequential_candidates.csv
```

### Arbitrage scan

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

### Pack monitor source

```bash
npx --yes renaiss packs --json
npx --yes renaiss packs omega --json
npx --yes renaiss packs renacrypt-pack --json
npx --yes renaiss packs eden-pack --json
```

---

## Expected output files

Runtime output should go under local ignored folders, not into git:

```text
data/
outputs/
```

These folders are ignored by the root `.gitignore`.
