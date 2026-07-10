# Renaiss BSC Contracts

| Address | Role | Confidence | Notes |
|---|---|---:|---|
| `0x55d398326f99059ff775485246999027b3197955` | BSC USDT | High | Payment token. |
| `0xf8646a3ca093e97bb404c3b25e675c0394dd5b30` | Renaiss Card/NFT | High | ERC-721 transfers in pack, marketplace, migration. |
| `0xb95f8867ff54fd16342cb414c0f57237be7dc512` | CollectibleDiamond | High | NFT mint manager. |
| `0x7d1b7db704d722295fbaa284008f526634673dbf` | RenaissSBT (Proxy) | High | ERC-1155 TransferBatch in wallet migration. |
| `0x2e737d552b3c601ada4fcd167bfbd8d4e1043b2c` | LegacyAssetMigrationHelper (Proxy) | High | Old-to-new wallet migration. |
| `0x94e7732b0b2e7c51ffd0d56580067d9c2e2b7910` | PerpetualTokenVendingMachineV2 (Proxy) | High | Pack/vending contract. |
| `0xfda4a907d23d9f24271bc47483c5b983831e325e` | Pack/Vending proxy | Medium-High | 150 USDT pack/vending pattern. |
| `0xb2891022648c5fad3721c42c05d8d283d4d53080` | Legacy pack/buyback-like proxy | Medium-High | 88 USDT pack and sell-back flows. |
| `0xaab5f5fa75437a6e9e7004c12c9c56cda4b4885a` | Legacy pack settlement / buyback-like contract | Medium-High | Seen with `0x3233aac2` pack-funding/open flows and `0xb24f1607` payout/buyback-like flows. |
| `0xae3e7268ef5a062946216a44f58a8f685ffd11d0` | Marketplace settlement proxy | High | NFT sale settlement and fee split. |
| `0x0000000071727de22e5e9d8baf0edac6f37da032` | ERC-4337 EntryPoint | High | Infrastructure; exclude from business stats. |

Known migration examples:

| Legacy wallet | New wallet |
|---|---|
| `0x246962b7b8cd03049677c136c99de7e72a587017` | `0x3c94a801d8a2cc24c027856fccaa5f7fa6a3f1e5` |
| `0xccf7b13b58b77b963dbbdf499e12d1e8d8942557` | `0xce3a75756b2fc69b501db511b2cce2bcbac77bd5` |
| `0xb67617a7bd531ff0611536e15a54e874a4679eee` | `0x13e589367ddb2fa778f57dd6889f93a8cb6e2766` |
| `0x310de74ebfcca7cc8bac64916c9cccff39604005` | `0x2c4b91ef6de88de94ec78634baf960a8a4745a86` |
