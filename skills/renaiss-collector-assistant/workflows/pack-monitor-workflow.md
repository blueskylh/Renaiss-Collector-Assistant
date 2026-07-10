# Pack Monitor Workflow

Use when the user wants to monitor Renaiss pack openings.

## Discover packs

```bash
npx --yes renaiss packs --json
```

Track current pack catalog dynamically. Do not hardcode the full list because new packs may appear.

Useful fields and units:

| Field | Meaning | Display conversion |
|---|---|---|
| `slug` | Pack slug, e.g. `omega`, `renacrypt-pack`, `eden-pack`. | text |
| `name` | Display name. | text |
| `packType` | Pack type, e.g. perpetual. | text |
| `stage` | active/inactive lifecycle. | text |
| `priceInUsdt` | Raw USDT base units / wei-style integer. | `price_usdt = priceInUsdt / 1e18` |
| `expectedValueInUsd` | Raw USD cents expected value. | `expected_value_usd = expectedValueInUsd / 100` |
| `featuredCardFmvInUsd` | Raw USD cents featured card FMV. | `featured_fmv_usd = featuredCardFmvInUsd / 100` |

Current examples observed through the Renaiss CLI use `priceInUsdt` as 18-decimal USDT base units, so `48000000000000000000` means `48 USDT`. If future CLI output changes unit shape, ask the user/Renaiss team for clarification before publishing pack price reports.

## Monitor one pack

```bash
npx --yes renaiss packs <slug> --json
```

Read `recentOpenedPacks` and compare against the previous snapshot.

Monitor fields:

| Field | Meaning | Display conversion |
|---|---|---|
| `collectibleTokenId` | Opened card tokenId. | text |
| `tier` | Pull tier. | text |
| `fmv` | Raw USD cents FMV. | `fmv_usd = fmv / 100` |
| `pulledAtTimestamp` | Pull timestamp. | UTC datetime |

## Suggested defaults

- Frequency: 5-10 minutes for active packs.
- Alert/report when a new `collectibleTokenId` appears.
- Track high FMV pulls above user threshold.
- Track tier distribution by slug.
- Save snapshots as JSONL and reports as Markdown.

## Output

Reports should include:

- Pack slug/name/stage/price.
- New pulls since last snapshot.
- Pull tier distribution.
- Top FMV pulls.
- Monitoring timestamp in UTC.

Monitoring is report-only by default; do not assume Telegram/Discord/Email unless the user explicitly integrates a channel.
