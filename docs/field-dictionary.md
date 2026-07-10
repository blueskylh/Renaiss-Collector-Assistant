# Field Dictionary

## Marketplace snapshot fields

| Field | Meaning |
|---|---|
| `collected_at_utc` | UTC collection time. |
| `source` | Usually `Renaiss CLI`. |
| `tokenId` | Renaiss collectible token ID. |
| `card_url` | `https://www.renaiss.xyz/card/<tokenId>`. |
| `name` | Full card/collectible name. |
| `type` | POKEMON / ONE_PIECE / SPORTS. |
| `setName` | Card set name. |
| `cardNumber` | Card number; **not** PSA cert number. |
| `ownerAddress` | Current owner address. |
| `askPriceInUSDT_raw` | Raw USDT wei. |
| `ask_usdt` | Human-readable ask price. |
| `fmvPriceInUSD_raw` | Raw USD cents. |
| `fmv_usd` | Human-readable FMV. |
| `gradingCompany` | PSA/BGS/CGC/SGC. |
| `grade` | Grade label from Renaiss CLI. |

## Card detail fields

| Field | Meaning |
|---|---|
| `serial_raw` | Raw value from `attributes.Serial`, e.g. `PSA127320817`. |
| `serial_number` | Numeric PSA cert extracted from `serial_raw`. |
| `language` | Value from `attributes.Language`. |
| `top_offer_usdt` | Highest offer in USDT after unit conversion. |
| `last_sale_usdt` | Last sale in USDT after unit conversion. |
| `price_history_json` | Verbose price history. |
| `offers_json` | Verbose offer list. |
| `activities_json` | On-chain / marketplace activity history. |

## Sequential scan fields

| Field | Meaning |
|---|---|
| `serial_gap` | Difference between two PSA cert numbers; should be 1. |
| `special_tags` | Relationship tags such as same_set, same_grade, fmv_discount. |
| `candidate_strength` | strong / medium / weak. |
| `risk_note` | Renaiss team still needs final verification. |

## Arbitrage fields

| Field | Meaning |
|---|---|
| `ask_usdt` | Buy cost. |
| `top_offer_usdt` | Gross offer. |
| `top_offer_net_usdt` | `top_offer_usdt * 0.98`. |
| `direct_arbitrage_profit` | `top_offer_net_usdt - ask_usdt`. |
| `fmv_net_usd` | `fmv_usd * 0.98`. |
| `fmv_spread_net` | `fmv_net_usd - ask_usdt`. |
| `fee_rate` | 0.02 by default. |
| `risk_notes` | Required risk disclosure. |

## Wallet cluster fields

| Field | Meaning |
|---|---|
| `primary_wallet` | Address supplied by user. |
| `current_wallet` | New wallet after migration. |
| `legacy_wallets` | Old wallet(s). |
| `migration_tx_hash` | Migration transaction. |
| `migrated_nft_count` | Renaiss NFT count transferred. |
| `migrated_sbt_ids` | SBT IDs migrated. |
| `sbt_metadata` | ERC-1155 metadata resolved from `uri(id)`, including SBT `name`, description, image, and URI. |
| `migrated_usdt` | USDT balance migrated. |
| `pack_spend_usdt` | USDT spent on pack/open transactions. |
| `pack_type_counts` | Pack counts by inferred type, based on `renaiss packs --json` current prices or legacy/unknown fallback. |
| `buyback_income_usdt` | USDT received from buyback/sell-back candidate transactions. |
| `marketplace_buy_spend_usdt` | USDT spent on Marketplace buys through the Marketplace proxy. |
| `marketplace_sell_income_usdt` | Net USDT received from Marketplace sells through the Marketplace proxy. |
| `total_spend_usdt` | `pack_spend_usdt + marketplace_buy_spend_usdt`. |
| `total_income_usdt` | `buyback_income_usdt + marketplace_sell_income_usdt`. |
| `net_spend_usdt` | `total_spend_usdt - total_income_usdt`. |
| `migration_is_internal` | Always true; exclude from PnL. |
