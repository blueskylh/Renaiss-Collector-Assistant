# Pack Monitor Workflow

Use when the user wants to monitor Renaiss pack openings.

## Discover packs

```bash
npx --yes renaiss packs --json
```

Track current pack catalog dynamically. Do not hardcode the full list because new packs may appear.

Useful fields:

| Field | Meaning |
|---|---|
| `slug` | Pack slug, e.g. `omega`, `renacrypt-pack`, `eden-pack`. |
| `name` | Display name. |
| `packType` | Pack type, e.g. perpetual. |
| `stage` | active/inactive lifecycle. |
| `priceInUsdt` | Raw USDT wei pack price. |
| `expectedValueInUsd` | USD cents expected value. |
| `featuredCardFmvInUsd` | USD cents featured card FMV. |

## Monitor one pack

```bash
npx --yes renaiss packs <slug> --json
```

Read `recentOpenedPacks` and compare against the previous snapshot.

Monitor fields:

| Field | Meaning |
|---|---|
| `collectibleTokenId` | Opened card tokenId. |
| `tier` | Pull tier. |
| `fmv` | Raw USD cents FMV. |
| `pulledAtTimestamp` | Pull timestamp. |

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
