#!/usr/bin/env python3
"""BSC wallet analyzer for Renaiss Collector Assistant.

Decodes individual transactions and builds Renaiss wallet-cluster reports.
For full wallet history this helper needs an indexer. In `auto` mode it uses
Surf wallet-history when available; with an Etherscan/BscScan key it can be
extended to Etherscan V2 (`chainid=56`). Receipt decoding itself uses BSC RPC.
"""
import argparse, collections, datetime, json, os, shutil, subprocess, sys, urllib.request

RPCS = [
    os.getenv("BSC_RPC_URL_1", "https://bsc-dataseed.binance.org/"),
    os.getenv("BSC_RPC_URL_2", "https://bsc-dataseed1.defibit.io/"),
    os.getenv("BSC_RPC_URL_3", "https://bsc-dataseed1.ninicoin.io/"),
]

ZERO = "0x0000000000000000000000000000000000000000"
TRANSFER = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
TRANSFER_SINGLE = "0xc3d58168c5ae7397731d063d5bbf3d6578544278c03a1d1289612f2d341b0c62"
TRANSFER_BATCH = "0x4a39dc06d4c0dbc64b70af90fd698a233a518aa5d07e595d983b8c0526c8f7fb"
USDT = os.getenv("BSC_USDT_CONTRACT", "0x55d398326f99059ff775485246999027b3197955").lower()
NFT = os.getenv("RENAISS_NFT_CONTRACT", "0xf8646a3ca093e97bb404c3b25e675c0394dd5b30").lower()
SBT = os.getenv("RENAISS_SBT_CONTRACT", "0x7d1b7db704d722295fbaa284008f526634673dbf").lower()
MIGRATION = os.getenv("RENAISS_LEGACY_MIGRATION_HELPER", "0x2e737d552b3c601ada4fcd167bfbd8d4e1043b2c").lower()
PACK_CURRENT = os.getenv("RENAISS_PACK_CONTRACT_CURRENT", "0x94e7732b0b2e7c51ffd0d56580067d9c2e2b7910").lower()
PACK_LEGACY_150 = os.getenv("RENAISS_PACK_CONTRACT_LEGACY_150", "0xfda4a907d23d9f24271bc47483c5b983831e325e").lower()
PACK_LEGACY_88 = os.getenv("RENAISS_PACK_OR_BUYBACK_LEGACY_88", "0xb2891022648c5fad3721c42c05d8d283d4d53080").lower()
# Seen in legacy pack/buyback flows: selector 0x3233aac2 = user funds pack/open; selector 0xb24f1607 = payout/buyback-like receipt.
PACK_SETTLEMENT = os.getenv("RENAISS_PACK_SETTLEMENT_CONTRACT", "0xaab5f5fa75437a6e9e7004c12c9c56cda4b4885a").lower()
MARKETPLACE = os.getenv("RENAISS_MARKETPLACE_PROXY", "0xae3e7268ef5a062946216a44f58a8f685ffd11d0").lower()
ENTRYPOINT = os.getenv("BSC_ERC4337_ENTRYPOINT", "0x0000000071727de22e5e9d8baf0edac6f37da032").lower()
PACK_CONTRACTS = {PACK_CURRENT, PACK_LEGACY_150, PACK_LEGACY_88, PACK_SETTLEMENT}
KNOWN_RENAISS_CONTRACTS = {USDT, NFT, SBT, MIGRATION, PACK_CURRENT, PACK_LEGACY_150, PACK_LEGACY_88, PACK_SETTLEMENT, MARKETPLACE}


def rpc(method, params):
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode()
    last = None
    for url in RPCS:
        if not url:
            continue
        try:
            req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
            res = json.load(urllib.request.urlopen(req, timeout=30))
            if "result" in res:
                return res["result"]
            last = res.get("error")
        except Exception as e:
            last = str(e)
    raise RuntimeError(last)


def topic_addr(t):
    return "0x" + t[-40:]


def uint(data):
    return int(data, 16) if data and data != "0x" else 0


def words(data):
    h = data[2:] if data.startswith("0x") else data
    return [int(h[i:i + 64], 16) for i in range(0, len(h), 64) if h[i:i + 64]]


def decode_transfer_batch(data):
    w = words(data)
    if len(w) < 2:
        return [], []
    off_ids, off_vals = w[0] // 32, w[1] // 32
    if off_ids >= len(w) or off_vals >= len(w):
        return [], []
    n_ids = w[off_ids]
    ids = w[off_ids + 1:off_ids + 1 + n_ids]
    n_vals = w[off_vals]
    vals = w[off_vals + 1:off_vals + 1 + n_vals]
    return ids, vals


def decode_transfer_single(data):
    w = words(data)
    if len(w) >= 2:
        return w[0], w[1]
    return None, None


def decode_abi_string(result_hex):
    if not result_hex or result_hex == "0x":
        return None
    h = result_hex[2:] if result_hex.startswith("0x") else result_hex
    try:
        offset = int(h[:64], 16)
        start = offset * 2
        length = int(h[start:start + 64], 16)
        data_start = start + 64
        return bytes.fromhex(h[data_start:data_start + length * 2]).decode("utf-8", "replace")
    except Exception:
        return None


def erc1155_uri(token_id):
    data = "0x0e89341c" + int(token_id).to_bytes(32, "big").hex()
    result = rpc("eth_call", [{"to": SBT, "data": data}, "latest"])
    return decode_abi_string(result)


def fetch_json_url(url):
    req = urllib.request.Request(url, headers={"User-Agent": "RenaissCollectorAssistant/0.1"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def resolve_sbt_metadata(ids):
    out = []
    for sid in sorted(set(ids)):
        item = {"id": sid, "name": None, "description": None, "uri": None, "image": None}
        try:
            uri = erc1155_uri(sid)
            item["uri"] = uri
            if uri:
                meta = fetch_json_url(uri)
                item["name"] = meta.get("name")
                item["description"] = meta.get("description")
                item["image"] = meta.get("image")
        except Exception as e:
            item["error"] = str(e)
        out.append(item)
    return out


def load_pack_catalog():
    defaults = [
        {"slug": "omega", "name": "OMEGA", "price_usdt": 48.0},
        {"slug": "renacrypt-pack", "name": "RenaCrypt Pack", "price_usdt": 88.0},
        {"slug": "eden-pack", "name": "Eden Pack", "price_usdt": 150.0},
    ]
    if not shutil.which("npx"):
        return defaults
    try:
        p = subprocess.run(["npx", "--yes", "renaiss", "packs", "--json"], text=True, capture_output=True, timeout=60)
        if p.returncode != 0:
            return defaults
        data = json.loads(p.stdout)
        packs = []
        for pack in data.get("cardPacks") or []:
            raw = pack.get("priceInUsdt")
            try:
                price = int(str(raw)) / 1e18
            except Exception:
                price = None
            packs.append({"slug": pack.get("slug"), "name": pack.get("name"), "price_usdt": price, "stage": pack.get("stage"), "packType": pack.get("packType")})
        return packs or defaults
    except Exception:
        return defaults


def infer_pack_type(amount_usdt, catalog):
    if amount_usdt is None:
        return "unknown"
    for p in catalog:
        price = p.get("price_usdt")
        if price is not None and abs(float(amount_usdt) - float(price)) < 0.01:
            return p.get("slug") or p.get("name") or f"{price:g} USDT pack"
    return f"legacy-or-unknown-{float(amount_usdt):g}-usdt-pack"


def block_time(block_hex):
    block = rpc("eth_getBlockByNumber", [block_hex, False])
    return datetime.datetime.fromtimestamp(int(block["timestamp"], 16), datetime.UTC).strftime("%Y-%m-%d %H:%M:%S UTC")


def decode_tx(tx_hash):
    tx = rpc("eth_getTransactionByHash", [tx_hash])
    if not tx:
        raise RuntimeError(f"transaction not found: {tx_hash}")
    rcpt = rpc("eth_getTransactionReceipt", [tx_hash])
    out = {
        "tx_hash": tx_hash,
        "time_utc": block_time(tx["blockNumber"]),
        "block_number": int(tx["blockNumber"], 16),
        "from": (tx.get("from") or "").lower(),
        "to": (tx.get("to") or "").lower(),
        "selector": tx.get("input", "")[:10],
        "status": rcpt.get("status"),
        "usdt_transfers": [],
        "renaiss_nft_transfers": [],
        "renaiss_sbt_singles": [],
        "renaiss_sbt_batches": [],
        "log_contract_counts": collections.Counter([l["address"].lower() for l in rcpt.get("logs", [])]),
    }
    for l in rcpt.get("logs", []):
        addr = l["address"].lower(); topics = l.get("topics", [])
        if not topics:
            continue
        if topics[0] == TRANSFER and len(topics) >= 3:
            if addr == USDT:
                out["usdt_transfers"].append({"from": topic_addr(topics[1]).lower(), "to": topic_addr(topics[2]).lower(), "amount_usdt": uint(l.get("data")) / 1e18})
            elif addr == NFT and len(topics) >= 4:
                out["renaiss_nft_transfers"].append({"from": topic_addr(topics[1]).lower(), "to": topic_addr(topics[2]).lower(), "tokenId": str(int(topics[3], 16))})
        elif addr == SBT and topics[0] == TRANSFER_BATCH and len(topics) >= 4:
            ids, vals = decode_transfer_batch(l.get("data", "0x"))
            out["renaiss_sbt_batches"].append({"operator": topic_addr(topics[1]).lower(), "from": topic_addr(topics[2]).lower(), "to": topic_addr(topics[3]).lower(), "ids": ids, "values": vals})
        elif addr == SBT and topics[0] == TRANSFER_SINGLE and len(topics) >= 4:
            sid, val = decode_transfer_single(l.get("data", "0x"))
            out["renaiss_sbt_singles"].append({"operator": topic_addr(topics[1]).lower(), "from": topic_addr(topics[2]).lower(), "to": topic_addr(topics[3]).lower(), "id": sid, "value": val})
    out["log_contract_counts"] = dict(out["log_contract_counts"])
    out["classification"] = classify(out)
    return out


def classify(decoded):
    to = (decoded.get("to") or "").lower()
    logs = decoded.get("log_contract_counts") or {}
    if to == MIGRATION:
        return "legacy_wallet_migration"
    if to == MARKETPLACE or MARKETPLACE in logs:
        return "marketplace_candidate"
    if to in PACK_CONTRACTS or any(c in logs for c in PACK_CONTRACTS):
        return "pack_or_buyback_candidate"
    if SBT in logs or decoded.get("renaiss_sbt_batches") or decoded.get("renaiss_sbt_singles"):
        return "sbt_activity"
    if decoded["usdt_transfers"] or decoded["renaiss_nft_transfers"]:
        return "renaiss_related"
    return "unknown"


def is_surf_available():
    return shutil.which("surf") is not None


def surf_json(args, timeout=120):
    p = subprocess.run(args, text=True, capture_output=True, timeout=timeout)
    if p.returncode != 0:
        raise RuntimeError(p.stderr.strip() or p.stdout.strip())
    return json.loads(p.stdout)


def fetch_wallet_history(address, limit=100, source="auto", max_pages=5):
    """Fetch paginated BSC wallet history.

    Surf wallet-history is cursor-paginated through `--before`. A single page is
    not enough for active Renaiss collectors, so wallet reports page by default
    and de-duplicate by tx_hash.
    """
    if source in ("auto", "surf") and is_surf_available():
        all_rows = []
        seen_hashes = set()
        metas = []
        before = None
        last_error = None
        for page in range(max(1, max_pages)):
            cmd = ["surf", "wallet-history", "--address", address, "--chain", "bsc", "--limit", str(limit), "--include", "labels", "--json"]
            if before is not None:
                cmd += ["--before", str(before)]
            j = surf_json(cmd)
            last_error = j.get("error")
            meta = j.get("meta") or {}
            meta["page"] = page + 1
            meta["before"] = before
            metas.append(meta)
            data = j.get("data") or []
            if not data:
                break
            for row in data:
                h = row.get("tx_hash")
                if h and h not in seen_hashes:
                    seen_hashes.add(h)
                    all_rows.append(row)
            if not meta.get("has_more"):
                break
            timestamps = [int(r.get("timestamp")) for r in data if r.get("timestamp") is not None]
            if not timestamps:
                break
            before = min(timestamps) + 1
        return {
            "source": "surf_wallet_history",
            "data": all_rows,
            "meta": {
                "pages_fetched": len(metas),
                "limit_per_page": limit,
                "rows": len(all_rows),
                "has_more_last": metas[-1].get("has_more") if metas else None,
                "pages": metas,
            },
            "error": last_error,
        }
    raise RuntimeError("No wallet-history source available. Install Surf CLI or add Etherscan V2/BscScan API support.")


def fetch_wallet_detail(address, source="auto"):
    if source in ("auto", "surf") and is_surf_available():
        j = surf_json(["surf", "wallet-detail", "--address", address, "--chain", "bsc", "--fields", "balance,tokens,nft,labels", "--json"])
        return {"source": "surf_wallet_detail", "data": j.get("data") or {}, "meta": j.get("meta") or {}, "error": j.get("error")}
    return {"source": None, "data": {}, "meta": {}, "error": "wallet-detail source unavailable"}


def migration_edges(decoded):
    if decoded.get("classification") != "legacy_wallet_migration":
        return []
    old_candidates, new_candidates = set(), set()
    sbt_ids = set()
    for b in decoded.get("renaiss_sbt_batches") or []:
        f, t = b.get("from"), b.get("to")
        if f and f != ZERO and t == ZERO:
            old_candidates.add(f)
            sbt_ids.update(b.get("ids") or [])
        if t and t != ZERO and f == ZERO:
            new_candidates.add(t)
            sbt_ids.update(b.get("ids") or [])
    for s in decoded.get("renaiss_sbt_singles") or []:
        f, t = s.get("from"), s.get("to")
        if f and f != ZERO and t == ZERO:
            old_candidates.add(f)
            if s.get("id") is not None: sbt_ids.add(s.get("id"))
        if t and t != ZERO and f == ZERO:
            new_candidates.add(t)
            if s.get("id") is not None: sbt_ids.add(s.get("id"))
    for u in decoded.get("usdt_transfers") or []:
        if u.get("from") and u.get("to"):
            old_candidates.add(u["from"])
            new_candidates.add(u["to"])
    edges = []
    for old in sorted(old_candidates):
        for new in sorted(new_candidates):
            if old != new and old != ZERO and new != ZERO:
                edges.append({
                    "old_wallet": old,
                    "new_wallet": new,
                    "tx_hash": decoded.get("tx_hash"),
                    "time_utc": decoded.get("time_utc"),
                    "migrated_usdt": sum(u["amount_usdt"] for u in decoded.get("usdt_transfers") or [] if u.get("from") == old and u.get("to") == new),
                    "migrated_nft_count": sum(1 for n in decoded.get("renaiss_nft_transfers") or [] if n.get("from") == old and n.get("to") == new),
                    "migrated_sbt_ids": sorted(sbt_ids),
                })
    return edges


def summarize_cluster(primary, history_by_wallet, decoded_by_hash, wallet_details):
    primary = primary.lower()
    migrations = []
    cluster = {primary}
    for d in decoded_by_hash.values():
        for e in migration_edges(d):
            migrations.append(e)
            cluster.add(e["old_wallet"]); cluster.add(e["new_wallet"])
    current_wallet = primary
    legacy_wallets = []
    for e in migrations:
        if primary == e["new_wallet"]:
            current_wallet = primary
            legacy_wallets.append(e["old_wallet"])
        elif primary == e["old_wallet"]:
            current_wallet = e["new_wallet"]
            legacy_wallets.append(primary)
        else:
            legacy_wallets.append(e["old_wallet"])
    legacy_wallets = sorted(set([w for w in legacy_wallets if w != current_wallet]))
    cluster = sorted(set(cluster))

    counters = collections.Counter()
    nft_in = []; nft_out = []
    sbt_ids = set()
    usdt_in = 0.0; usdt_out = 0.0
    marketplace_buys = 0; marketplace_sells = 0; pack_buys = 0; buyback_candidates = 0
    marketplace_buy_spend_usdt = 0.0; marketplace_sell_income_usdt = 0.0
    pack_spend_usdt = 0.0; buyback_income_usdt = 0.0
    pack_type_counts = collections.Counter(); pack_type_spend = collections.Counter()
    pack_catalog = load_pack_catalog()
    renaiss_related_txs = set()
    internal_migration_usdt = 0.0
    cluster_set = set(cluster)

    for h, d in decoded_by_hash.items():
        if d.get("error"):
            counters["decode_errors"] += 1
            continue
        cls = d.get("classification") or "unknown"
        counters[cls] += 1
        if cls != "unknown":
            renaiss_related_txs.add(h)
        is_migration = cls == "legacy_wallet_migration"
        tx_usdt_in = 0.0; tx_usdt_out = 0.0; tx_nft_in = 0; tx_nft_out = 0
        for u in d.get("usdt_transfers") or []:
            f, t, amt = u.get("from"), u.get("to"), float(u.get("amount_usdt") or 0)
            if f in cluster_set and t in cluster_set:
                if is_migration:
                    internal_migration_usdt += amt
                continue
            if f in cluster_set:
                usdt_out += amt; tx_usdt_out += amt
            if t in cluster_set:
                usdt_in += amt; tx_usdt_in += amt
        for n in d.get("renaiss_nft_transfers") or []:
            f, t = n.get("from"), n.get("to")
            if f in cluster_set and t not in cluster_set:
                nft_out.append(n.get("tokenId")); tx_nft_out += 1
            if t in cluster_set and f not in cluster_set:
                nft_in.append(n.get("tokenId")); tx_nft_in += 1
        for b in d.get("renaiss_sbt_batches") or []:
            if b.get("from") in cluster_set or b.get("to") in cluster_set:
                sbt_ids.update(b.get("ids") or [])
        for s in d.get("renaiss_sbt_singles") or []:
            if s.get("from") in cluster_set or s.get("to") in cluster_set:
                if s.get("id") is not None:
                    sbt_ids.add(s.get("id"))
        if d.get("classification") == "marketplace_candidate":
            if tx_nft_in and tx_usdt_out:
                marketplace_buys += 1
                marketplace_buy_spend_usdt += tx_usdt_out
            if tx_nft_out and tx_usdt_in:
                marketplace_sells += 1
                marketplace_sell_income_usdt += tx_usdt_in
        if d.get("classification") == "pack_or_buyback_candidate":
            selector = d.get("selector")
            # Pack opens may mint/transfer NFT directly, but some legacy perpetual pack flows only show USDT out.
            if tx_usdt_out and (tx_nft_in or selector in {"0x3233aac2", "0x644f5c2d"} or (d.get("to") or "").lower() in PACK_CONTRACTS):
                pack_buys += 1
                pack_spend_usdt += tx_usdt_out
                pack_type = infer_pack_type(tx_usdt_out, pack_catalog)
                pack_type_counts[pack_type] += 1
                pack_type_spend[pack_type] += tx_usdt_out
            # Buyback/sell-back flows can be NFT out + USDT in, or legacy payout-only selector 0xb24f1607.
            if tx_usdt_in and (tx_nft_out or selector in {"0xb24f1607"} or (d.get("from") or "").lower() in PACK_CONTRACTS):
                buyback_candidates += 1
                buyback_income_usdt += tx_usdt_in

    sbt_metadata = resolve_sbt_metadata(sbt_ids) if sbt_ids else []
    balances = {}
    for w, detail in wallet_details.items():
        data = detail.get("data") or {}
        evm_balance = data.get("evm_balance") or {}
        balances[w] = {
            "total_usd": evm_balance.get("total_usd"),
            "chain_balances": evm_balance.get("chain_balances"),
            "tokens": data.get("evm_tokens") or [],
            "nft_count": len(data.get("nft") or []),
            "source": detail.get("source"),
        }

    return {
        "primary_wallet": primary,
        "current_wallet": current_wallet,
        "legacy_wallets": legacy_wallets,
        "wallet_cluster": cluster,
        "migration_detected": bool(migrations),
        "migrations": migrations,
        "wallet_history_rows": {w: len((history_by_wallet.get(w) or {}).get("data") or []) for w in history_by_wallet},
        "decoded_tx_count": len(decoded_by_hash),
        "classification_counts": dict(counters),
        "renaiss_related_tx_count": len(renaiss_related_txs),
        "marketplace_buys": marketplace_buys,
        "marketplace_sells": marketplace_sells,
        "marketplace_buy_spend_usdt": marketplace_buy_spend_usdt,
        "marketplace_sell_income_usdt": marketplace_sell_income_usdt,
        "pack_buys": pack_buys,
        "pack_spend_usdt": pack_spend_usdt,
        "pack_type_counts": dict(pack_type_counts),
        "pack_type_spend_usdt": dict(pack_type_spend),
        "active_pack_catalog": pack_catalog,
        "buyback_candidates": buyback_candidates,
        "buyback_income_usdt": buyback_income_usdt,
        "renaiss_nft_in_count": len(nft_in),
        "renaiss_nft_out_count": len(nft_out),
        "renaiss_nft_in_token_ids": nft_in,
        "renaiss_nft_out_token_ids": nft_out,
        "sbt_ids_seen": sorted(sbt_ids),
        "sbt_metadata": sbt_metadata,
        "total_spend_usdt": pack_spend_usdt + marketplace_buy_spend_usdt,
        "total_income_usdt": buyback_income_usdt + marketplace_sell_income_usdt,
        "net_spend_usdt": (pack_spend_usdt + marketplace_buy_spend_usdt) - (buyback_income_usdt + marketplace_sell_income_usdt),
        "usdt_in_excluding_internal_migration": usdt_in,
        "usdt_out_excluding_internal_migration": usdt_out,
        "net_usdt_flow_excluding_internal_migration": usdt_in - usdt_out,
        "internal_migration_usdt": internal_migration_usdt,
        "balances": balances,
        "data_notes": [
            "Wallet cluster is inferred from LegacyAssetMigrationHelper migration transactions.",
            "Migration transfers inside the cluster are excluded from net USDT flow.",
            "Wallet history is paginated with --before; very active wallets may still need a higher --max-pages or a dedicated indexer/BscScan V2 export.",
        ],
    }


def build_wallet_report(address, limit=100, source="auto", max_pages=5):
    address = address.lower()
    history_by_wallet = {}
    wallet_details = {}
    decoded_by_hash = {}
    queue = [address]
    seen_wallets = set()
    while queue and len(seen_wallets) < 6:
        w = queue.pop(0).lower()
        if w in seen_wallets:
            continue
        seen_wallets.add(w)
        hist = fetch_wallet_history(w, limit=limit, source=source, max_pages=max_pages)
        history_by_wallet[w] = hist
        wallet_details[w] = fetch_wallet_detail(w, source=source)
        tx_hashes = []
        for item in hist.get("data") or []:
            h = item.get("tx_hash")
            if h and h not in tx_hashes:
                tx_hashes.append(h)
        for h in tx_hashes:
            if h in decoded_by_hash:
                continue
            try:
                decoded_by_hash[h] = decode_tx(h)
            except Exception as e:
                decoded_by_hash[h] = {"tx_hash": h, "error": str(e), "classification": "decode_error"}
        # Find migration-linked wallets and add them to the queue.
        for d in list(decoded_by_hash.values()):
            for e in migration_edges(d):
                for candidate in [e["old_wallet"], e["new_wallet"]]:
                    if candidate not in seen_wallets and candidate not in queue:
                        queue.append(candidate)
    summary = summarize_cluster(address, history_by_wallet, decoded_by_hash, wallet_details)
    return {
        "generated_at_utc": datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%d %H:%M:%S UTC"),
        "source": "BSC wallet-history index + BSC RPC receipts",
        "summary": summary,
        "history_meta": {w: h.get("meta") for w, h in history_by_wallet.items()},
        "decoded_transactions": list(decoded_by_hash.values()),
    }


def write_wallet_markdown(report, out_md):
    s = report["summary"]
    lines = []
    lines.append(f"# Renaiss Wallet Report - {s['primary_wallet']}")
    lines.append("")
    lines.append(f"Generated: {report['generated_at_utc']}")
    lines.append(f"Source: {report['source']}")
    lines.append("")
    lines.append("## Cluster")
    lines.append("")
    lines.append(f"- Primary wallet: `{s['primary_wallet']}`")
    lines.append(f"- Current wallet: `{s['current_wallet']}`")
    lines.append(f"- Legacy wallets: {', '.join('`'+w+'`' for w in s['legacy_wallets']) if s['legacy_wallets'] else 'none detected'}")
    lines.append(f"- Migration detected: {s['migration_detected']}")
    lines.append("")
    if s["migrations"]:
        lines.append("## Migration")
        lines.append("")
        lines.append("| Time | Old | New | USDT | NFT | SBT IDs | Tx |")
        lines.append("|---|---|---|---:|---:|---|---|")
        for m in s["migrations"]:
            ids = ', '.join(map(str, m.get('migrated_sbt_ids') or []))
            lines.append(f"| {m.get('time_utc')} | `{m.get('old_wallet')}` | `{m.get('new_wallet')}` | {m.get('migrated_usdt')} | {m.get('migrated_nft_count')} | {ids} | `{m.get('tx_hash')}` |")
        lines.append("")
    lines.append("## Activity Summary")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|---|---:|")
    for k in ["decoded_tx_count", "renaiss_related_tx_count", "marketplace_buys", "marketplace_sells", "pack_buys", "buyback_candidates", "renaiss_nft_in_count", "renaiss_nft_out_count"]:
        lines.append(f"| {k} | {s[k]} |")
    lines.append(f"| Pack spend | {s['pack_spend_usdt']:.6f} USDT |")
    lines.append(f"| Buyback income | {s['buyback_income_usdt']:.6f} USDT |")
    lines.append(f"| Marketplace buy spend | {s['marketplace_buy_spend_usdt']:.6f} USDT |")
    lines.append(f"| Marketplace sell income | {s['marketplace_sell_income_usdt']:.6f} USDT |")
    lines.append(f"| Total spend | {s['total_spend_usdt']:.6f} USDT |")
    lines.append(f"| Total income | {s['total_income_usdt']:.6f} USDT |")
    lines.append(f"| Net spend | {s['net_spend_usdt']:.6f} USDT |")
    lines.append(f"| USDT in excl. migration | {s['usdt_in_excluding_internal_migration']:.6f} |")
    lines.append(f"| USDT out excl. migration | {s['usdt_out_excluding_internal_migration']:.6f} |")
    lines.append(f"| Net USDT flow excl. migration | {s['net_usdt_flow_excluding_internal_migration']:.6f} |")
    lines.append("")
    lines.append("## Pack Types")
    lines.append("")
    if s.get('pack_type_counts'):
        lines.append("| Pack type | Count | Spend USDT |")
        lines.append("|---|---:|---:|")
        for name, count in s['pack_type_counts'].items():
            lines.append(f"| {name} | {count} | {s['pack_type_spend_usdt'].get(name, 0):.6f} |")
    else:
        lines.append("No pack type inferred.")
    lines.append("")
    lines.append("## SBT")
    lines.append("")
    if s.get('sbt_metadata'):
        lines.append("| ID | Name |")
        lines.append("|---:|---|")
        for item in s['sbt_metadata']:
            lines.append(f"| {item.get('id')} | {item.get('name') or 'unknown'} |")
    else:
        lines.append("No SBT detected.")
    lines.append("")
    lines.append("## Notes")
    lines.append("")
    for n in s["data_notes"]:
        lines.append(f"- {n}")
    with open(out_md, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def cmd_wallet_report(args):
    report = build_wallet_report(args.address, limit=args.limit, source=args.history_source, max_pages=args.max_pages)
    if args.out:
        os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
    if args.out_md:
        os.makedirs(os.path.dirname(args.out_md) or ".", exist_ok=True)
        write_wallet_markdown(report, args.out_md)
    print(json.dumps(report if args.verbose else report["summary"], ensure_ascii=False, indent=2))


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("decode-tx"); d.add_argument("--tx", required=True); d.set_defaults(func=lambda a: print(json.dumps(decode_tx(a.tx), ensure_ascii=False, indent=2)))
    m = sub.add_parser("decode-migration-tx"); m.add_argument("--tx", required=True); m.set_defaults(func=lambda a: print(json.dumps(decode_tx(a.tx), ensure_ascii=False, indent=2)))
    w = sub.add_parser("wallet-report")
    w.add_argument("--address", required=True)
    w.add_argument("--limit", type=int, default=100)
    w.add_argument("--max-pages", type=int, default=5, help="wallet-history pages to fetch per wallet via before cursor")
    w.add_argument("--history-source", choices=["auto", "surf"], default="auto")
    w.add_argument("--out")
    w.add_argument("--out-md")
    w.add_argument("--verbose", action="store_true")
    w.set_defaults(func=cmd_wallet_report)
    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
