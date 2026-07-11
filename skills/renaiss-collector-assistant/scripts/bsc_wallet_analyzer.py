#!/usr/bin/env python3
"""BSC wallet analyzer for Renaiss Collector Assistant.

Decodes individual transactions and builds Renaiss wallet-cluster reports.
For full wallet history this helper uses Alchemy's BNB Mainnet Transfers API
when an Alchemy key/RPC URL is configured. Receipt decoding uses the Alchemy
BNB RPC first, with public BSC RPC endpoints kept only as read-only fallbacks.
"""
import argparse, base64, collections, csv, datetime, ipaddress, json, os, re, shutil, socket, subprocess, sys, urllib.parse, urllib.request

try:
    from common_env import load_dotenv_files
    load_dotenv_files()
except Exception:
    pass

def _env(name):
    value = os.getenv(name)
    return value.strip() if value and value.strip() else None


def alchemy_bnb_rpc_url():
    """Return the configured Alchemy BNB Mainnet JSON-RPC URL.

    Prefer an explicit URL for advanced users, otherwise derive the endpoint
    from the API key. Never hard-code real keys in this repository.
    """
    explicit = _env("ALCHEMY_BNB_RPC_URL") or _env("BNB_RPC_URL")
    if explicit:
        return explicit
    key = _env("ALCHEMY_API_KEY") or _env("ALCHEMY_BNB_API_KEY")
    if key:
        return f"https://bnb-mainnet.g.alchemy.com/v2/{key}"
    return None


ALCHEMY_BNB_RPC_URL = alchemy_bnb_rpc_url()


def _dedupe_urls(urls):
    out = []
    seen = set()
    for url in urls:
        if not url:
            continue
        url = str(url).strip()
        if not url or url in seen:
            continue
        seen.add(url)
        out.append(url)
    return out


def _rpc_urls():
    # Alchemy is primary. Public BSC endpoints remain as receipt-decoding
    # fallbacks so decode-tx can still work before the user configures a key.
    return _dedupe_urls([
        ALCHEMY_BNB_RPC_URL,
        _env("BSC_RPC_URL"),
        os.getenv("BSC_RPC_URL_1", "https://bsc-dataseed.binance.org/"),
        os.getenv("BSC_RPC_URL_2", "https://bsc-dataseed1.defibit.io/"),
        os.getenv("BSC_RPC_URL_3", "https://bsc-dataseed1.ninicoin.io/"),
    ])


RPCS = _rpc_urls()

ZERO = "0x0000000000000000000000000000000000000000"
TRANSFER = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
TRANSFER_SINGLE = "0xc3d58168c5ae7397731d063d5bbf3d6578544278c03a1d1289612f2d341b0c62"
# RenaissSBT currently emits an ERC-1155-like single transfer event whose
# topic starts with the standard TransferSingle selector prefix but differs in
# the full topic hash. Decode it with the same indexed/data layout.
RENAISS_TRANSFER_SINGLE_PREFIX = "0xc3d58168"
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


def redact_secret_url(message):
    if message is None:
        return message
    return re.sub(r"(https://bnb-mainnet\.g\.alchemy\.com/v2/)[A-Za-z0-9_-]+", r"\1<redacted>", str(message))


def is_alchemy_configured():
    return bool(ALCHEMY_BNB_RPC_URL)


def _json_rpc_request(url, method, params, timeout=30):
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode()
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
    res = json.load(urllib.request.urlopen(req, timeout=timeout))
    if "result" in res:
        return res["result"]
    raise RuntimeError(res.get("error") or res)


def rpc(method, params):
    last = None
    for url in RPCS:
        if not url:
            continue
        try:
            return _json_rpc_request(url, method, params)
        except Exception as e:
            last = redact_secret_url(e)
    raise RuntimeError(last)


def alchemy_rpc(method, params):
    if not ALCHEMY_BNB_RPC_URL:
        raise RuntimeError("Missing ALCHEMY_API_KEY or ALCHEMY_BNB_RPC_URL for Alchemy BNB Mainnet.")
    try:
        return _json_rpc_request(ALCHEMY_BNB_RPC_URL, method, params)
    except Exception as e:
        raise RuntimeError(redact_secret_url(e))


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


def is_sbt_transfer_single_topic(topic):
    return topic == TRANSFER_SINGLE or str(topic or "").startswith(RENAISS_TRANSFER_SINGLE_PREFIX)


def int_auto(value, default=0):
    if value is None:
        return default
    if isinstance(value, int):
        return value
    text = str(value).strip()
    if not text:
        return default
    try:
        return int(text, 16) if text.startswith("0x") else int(text)
    except Exception:
        return default


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


def normalize_metadata_uri(uri, token_id):
    if not uri:
        return uri
    token_hex = format(int(token_id), "064x")
    uri = str(uri).replace("{id}", token_hex)
    if uri.startswith("ipfs://"):
        return "https://ipfs.io/ipfs/" + uri[len("ipfs://"):].lstrip("/")
    if uri.startswith("ar://"):
        return "https://arweave.net/" + uri[len("ar://"):].lstrip("/")
    return uri


def _host_resolves_private(host):
    try:
        infos = socket.getaddrinfo(host, None)
    except Exception as exc:
        raise RuntimeError(f"metadata host resolution failed: {host}") from exc
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_reserved:
            return True
    return False


def validate_metadata_url(url):
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https":
        raise RuntimeError(f"metadata URL scheme not allowed: {parsed.scheme or 'missing'}")
    if not parsed.hostname:
        raise RuntimeError("metadata URL host missing")
    if _host_resolves_private(parsed.hostname):
        raise RuntimeError(f"metadata URL resolves to private/loopback address: {parsed.hostname}")


def fetch_json_url(url):
    if url.startswith("data:application/json"):
        meta, data = url.split(",", 1)
        if ";base64" in meta:
            return json.loads(base64.b64decode(data).decode("utf-8"))
        return json.loads(urllib.parse.unquote(data))
    validate_metadata_url(url)
    req = urllib.request.Request(url, headers={"User-Agent": "RenaissCollectorAssistant/0.1"})
    with urllib.request.urlopen(req, timeout=30) as r:
        final_url = r.geturl()
        if final_url and final_url != url:
            validate_metadata_url(final_url)
        return json.load(r)


def resolve_sbt_metadata(ids):
    out = []
    for sid in sorted(set(ids)):
        item = {"id": sid, "name": None, "description": None, "uri": None, "resolved_uri": None, "image": None}
        try:
            uri = erc1155_uri(sid)
            item["uri"] = uri
            resolved_uri = normalize_metadata_uri(uri, sid) if uri else None
            item["resolved_uri"] = resolved_uri
            if resolved_uri:
                meta = fetch_json_url(resolved_uri)
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


def infer_pack_purchase(amount_usdt, catalog):
    """Infer pack slug and pack count from a USDT spend.

    Renaiss supports batch opens (currently 1/5/10 packs, with future multiples
    possible). Match total spend to unit pack prices by integer multiples.
    """
    if amount_usdt is None:
        return {"pack_type": "unknown", "pack_count": None, "unit_price_usdt": None, "batch_multiple": None}
    amount = float(amount_usdt)
    best = None
    for p in catalog:
        price = p.get("price_usdt")
        if price is None or float(price) <= 0:
            continue
        multiple = amount / float(price)
        nearest = round(multiple)
        if nearest >= 1 and abs(amount - nearest * float(price)) < 0.01:
            candidate = {
                "pack_type": p.get("slug") or p.get("name") or f"{float(price):g} USDT pack",
                "pack_count": int(nearest),
                "unit_price_usdt": float(price),
                "batch_multiple": int(nearest),
            }
            if best is None or candidate["pack_count"] < best["pack_count"]:
                best = candidate
    if best:
        return best
    return {"pack_type": f"legacy-or-unknown-{amount:g}-usdt-pack", "pack_count": None, "unit_price_usdt": None, "batch_multiple": None}


def infer_pack_type(amount_usdt, catalog):
    return infer_pack_purchase(amount_usdt, catalog)["pack_type"]


def block_time(block_hex):
    block = rpc("eth_getBlockByNumber", [block_hex, False])
    return datetime.datetime.fromtimestamp(int(block["timestamp"], 16), datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


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
        elif addr == SBT and is_sbt_transfer_single_topic(topics[0]) and len(topics) >= 4:
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


ALCHEMY_TRANSFER_CATEGORIES = ["external", "internal", "erc20", "erc721", "erc1155", "specialnft"]


def _parse_alchemy_block_timestamp(value):
    if not value:
        return None, None
    try:
        dt = datetime.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=datetime.timezone.utc)
        dt = dt.astimezone(datetime.timezone.utc)
        return int(dt.timestamp()), dt.strftime("%Y-%m-%d %H:%M:%S UTC")
    except Exception:
        return None, None


def _merge_history_row(rows_by_hash, transfer):
    tx_hash = transfer.get("hash")
    if not tx_hash:
        return
    metadata = transfer.get("metadata") or {}
    timestamp, time_utc = _parse_alchemy_block_timestamp(metadata.get("blockTimestamp"))
    block_num = transfer.get("blockNum")
    try:
        block_number = int(block_num, 16) if isinstance(block_num, str) and block_num.startswith("0x") else int(block_num)
    except Exception:
        block_number = None
    category = transfer.get("category")
    asset = transfer.get("asset")
    row = rows_by_hash.get(tx_hash)
    if row is None:
        rows_by_hash[tx_hash] = {
            "tx_hash": tx_hash,
            "block_number": block_number,
            "timestamp": timestamp,
            "time_utc": time_utc,
            "from": (transfer.get("from") or "").lower(),
            "to": (transfer.get("to") or "").lower(),
            "alchemy_categories": [category] if category else [],
            "alchemy_assets": [asset] if asset else [],
        }
        return
    if block_number is not None and row.get("block_number") is None:
        row["block_number"] = block_number
    if timestamp is not None and row.get("timestamp") is None:
        row["timestamp"] = timestamp
        row["time_utc"] = time_utc
    if category and category not in row["alchemy_categories"]:
        row["alchemy_categories"].append(category)
    if asset and asset not in row["alchemy_assets"]:
        row["alchemy_assets"].append(asset)


def fetch_wallet_history_alchemy(address, limit=100, max_pages=5):
    """Fetch BSC wallet transaction hashes with Alchemy Transfers API.

    The Transfers API is queried twice, once for outbound and once for inbound
    transfers, then de-duplicated by transaction hash before receipt decoding.
    """
    if not is_alchemy_configured():
        raise RuntimeError("Missing ALCHEMY_API_KEY or ALCHEMY_BNB_RPC_URL for Alchemy wallet history.")
    address = address.lower()
    max_count = max(1, min(int(limit), 1000))
    page_limit = max(1, int(max_pages))
    rows_by_hash = {}
    direction_metas = []
    errors = []
    has_more_last = False
    for direction, address_key in (("from", "fromAddress"), ("to", "toAddress")):
        page_key = None
        pages = 0
        transfers_seen = 0
        direction_error = None
        for page in range(page_limit):
            query = {
                "fromBlock": "0x0",
                "toBlock": "latest",
                "order": "desc",
                "withMetadata": True,
                "excludeZeroValue": False,
                "maxCount": hex(max_count),
                "category": ALCHEMY_TRANSFER_CATEGORIES,
                address_key: address,
            }
            if page_key:
                query["pageKey"] = page_key
            try:
                result = alchemy_rpc("alchemy_getAssetTransfers", [query])
            except Exception as e:
                direction_error = redact_secret_url(e)
                errors.append(f"{direction}: {direction_error}")
                break
            pages += 1
            transfers = result.get("transfers") or []
            transfers_seen += len(transfers)
            for transfer in transfers:
                _merge_history_row(rows_by_hash, transfer)
            page_key = result.get("pageKey")
            if not page_key:
                break
        if page_key:
            has_more_last = True
        direction_metas.append({
            "direction": direction,
            "pages_fetched": pages,
            "transfers_seen": transfers_seen,
            "has_more": bool(page_key),
            "error": direction_error,
        })
    if errors and not rows_by_hash:
        raise RuntimeError("Alchemy wallet history failed: " + "; ".join(errors))
    rows = sorted(
        rows_by_hash.values(),
        key=lambda r: (r.get("block_number") if r.get("block_number") is not None else -1, r.get("tx_hash") or ""),
        reverse=True,
    )
    return {
        "source": "alchemy_getAssetTransfers",
        "data": rows,
        "meta": {
            "pages_fetched": sum(m["pages_fetched"] for m in direction_metas),
            "limit_per_page": max_count,
            "rows": len(rows),
            "has_more_last": has_more_last,
            "directions": direction_metas,
        },
        "error": "; ".join(errors) if errors else None,
    }


def fetch_wallet_history(address, limit=100, source="auto", max_pages=5):
    """Fetch paginated BSC wallet history.

    `auto` prefers Alchemy when `ALCHEMY_API_KEY` / `ALCHEMY_BNB_RPC_URL` is
    configured. Surf remains a fallback for environments that already provide a
    wallet-history index.
    """
    alchemy_error = None
    if source in ("auto", "alchemy"):
        if is_alchemy_configured():
            try:
                return fetch_wallet_history_alchemy(address, limit=limit, max_pages=max_pages)
            except Exception as e:
                alchemy_error = redact_secret_url(e)
                if source == "alchemy":
                    raise RuntimeError(alchemy_error)
        elif source == "alchemy":
            raise RuntimeError("Missing ALCHEMY_API_KEY or ALCHEMY_BNB_RPC_URL for Alchemy wallet history.")

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
    if alchemy_error:
        raise RuntimeError(f"Alchemy wallet history failed and no fallback source is available: {alchemy_error}")
    raise RuntimeError("No wallet-history source available. Set ALCHEMY_API_KEY or ALCHEMY_BNB_RPC_URL for Alchemy BNB Mainnet wallet history.")


def _erc20_balance(token, owner):
    data = "0x70a08231" + owner.lower().replace("0x", "").rjust(64, "0")
    return int(alchemy_rpc("eth_call", [{"to": token, "data": data}, "latest"]), 16)


def fetch_wallet_detail_alchemy(address):
    address = address.lower()
    data = {"evm_balance": {"total_usd": None, "chain_balances": []}, "evm_tokens": [], "nft": []}
    errors = []
    try:
        native_wei = int(alchemy_rpc("eth_getBalance", [address, "latest"]), 16)
        data["evm_balance"]["chain_balances"].append({
            "chain": "bsc",
            "native_symbol": "BNB",
            "native_balance_wei": str(native_wei),
            "native_balance": native_wei / 1e18,
        })
    except Exception as e:
        errors.append("native_balance: " + str(redact_secret_url(e)))
    try:
        usdt_raw = _erc20_balance(USDT, address)
        data["evm_tokens"].append({
            "chain": "bsc",
            "contract": USDT,
            "symbol": "USDT",
            "balance_raw": str(usdt_raw),
            "balance": usdt_raw / 1e18,
        })
    except Exception as e:
        errors.append("usdt_balance: " + str(redact_secret_url(e)))
    return {"source": "alchemy_bnb_rpc", "data": data, "meta": {}, "error": "; ".join(errors) if errors else None}


def fetch_wallet_detail(address, source="auto"):
    if source in ("auto", "alchemy") and is_alchemy_configured():
        return fetch_wallet_detail_alchemy(address)
    if source in ("auto", "surf") and is_surf_available():
        j = surf_json(["surf", "wallet-detail", "--address", address, "--chain", "bsc", "--fields", "balance,tokens,nft,labels", "--json"])
        return {"source": "surf_wallet_detail", "data": j.get("data") or {}, "meta": j.get("meta") or {}, "error": j.get("error")}
    if source == "alchemy":
        return {"source": None, "data": {}, "meta": {}, "error": "Missing ALCHEMY_API_KEY or ALCHEMY_BNB_RPC_URL for Alchemy wallet detail."}
    return {"source": None, "data": {}, "meta": {}, "error": "wallet-detail source unavailable"}


def alchemy_erc1155_transfers(*, address=None, direction=None, contract=SBT, max_pages=50, limit=1000, order="asc"):
    if not is_alchemy_configured():
        raise RuntimeError("Missing ALCHEMY_API_KEY or ALCHEMY_BNB_RPC_URL for Alchemy ERC-1155 transfers.")
    rows = []
    page_key = None
    pages = 0
    while pages < max(1, int(max_pages)):
        query = {
            "fromBlock": "0x0",
            "toBlock": "latest",
            "order": order,
            "withMetadata": True,
            "excludeZeroValue": False,
            "maxCount": hex(max(1, min(int(limit), 1000))),
            "category": ["erc1155"],
            "contractAddresses": [contract],
        }
        if address and direction == "from":
            query["fromAddress"] = address.lower()
        elif address and direction == "to":
            query["toAddress"] = address.lower()
        elif address:
            raise ValueError("direction must be 'from' or 'to' when address is supplied")
        if page_key:
            query["pageKey"] = page_key
        result = alchemy_rpc("alchemy_getAssetTransfers", [query])
        rows.extend(result.get("transfers") or [])
        pages += 1
        page_key = result.get("pageKey")
        if not page_key:
            break
    return {"transfers": rows, "pages_fetched": pages, "has_more": bool(page_key)}


def transfer_sort_key(t):
    return (int_auto(t.get("blockNum")), int_auto(str(t.get("uniqueId") or "").split(":log:")[-1], 0), t.get("hash") or "")


def erc1155_items_from_transfer(t):
    items = []
    for item in t.get("erc1155Metadata") or []:
        token_id = int_auto(item.get("tokenId"), None)
        value = int_auto(item.get("value"), 0)
        if token_id is not None and value:
            items.append((token_id, value))
    return items


def sbt_transfer_balance_delta_for_owner(owner, transfer):
    owner = owner.lower()
    delta = collections.Counter()
    f = (transfer.get("from") or "").lower()
    t = (transfer.get("to") or "").lower()
    for token_id, value in erc1155_items_from_transfer(transfer):
        if f == owner:
            delta[token_id] -= value
        if t == owner:
            delta[token_id] += value
    return delta


def fetch_sbt_balances_for_owner(owner, max_pages=50):
    owner = owner.lower()
    by_uid = {}
    metas = []
    for direction in ("from", "to"):
        result = alchemy_erc1155_transfers(address=owner, direction=direction, max_pages=max_pages, order="asc")
        metas.append({"direction": direction, "pages_fetched": result["pages_fetched"], "rows": len(result["transfers"]), "has_more": result["has_more"]})
        for t in result["transfers"]:
            by_uid[t.get("uniqueId") or f"{t.get('hash')}:{len(by_uid)}"] = t
    balances = collections.Counter()
    for t in sorted(by_uid.values(), key=transfer_sort_key):
        balances.update(sbt_transfer_balance_delta_for_owner(owner, t))
    holdings = [{"id": token_id, "balance": bal} for token_id, bal in sorted(balances.items()) if bal > 0]
    meta_by_id = {m.get("id"): m for m in resolve_sbt_metadata([h["id"] for h in holdings])} if holdings else {}
    for h in holdings:
        meta = meta_by_id.get(h["id"]) or {}
        h["name"] = meta.get("name")
        h["description"] = meta.get("description")
        h["uri"] = meta.get("uri")
    return {"owner": owner, "holdings": holdings, "sbt_count": sum(h["balance"] for h in holdings), "unique_sbt_types": len(holdings), "meta": {"sources": metas, "has_more": any(m["has_more"] for m in metas)}}


def build_sbt_holder_ranking(max_pages=500, limit=1000):
    result = alchemy_erc1155_transfers(max_pages=max_pages, limit=limit, order="asc")
    balances = collections.defaultdict(collections.Counter)
    for t in sorted(result["transfers"], key=transfer_sort_key):
        f = (t.get("from") or "").lower()
        to = (t.get("to") or "").lower()
        for token_id, value in erc1155_items_from_transfer(t):
            if f and f != ZERO:
                balances[token_id][f] -= value
            if to and to != ZERO:
                balances[token_id][to] += value
    ids = sorted(balances)
    meta_by_id = {m.get("id"): m for m in resolve_sbt_metadata(ids)} if ids else {}
    rows = []
    for token_id in ids:
        holder_count = sum(1 for bal in balances[token_id].values() if bal > 0)
        supply = sum(bal for bal in balances[token_id].values() if bal > 0)
        meta = meta_by_id.get(token_id) or {}
        rows.append({"id": token_id, "name": meta.get("name"), "holder_count": holder_count, "current_supply": supply})
    rows.sort(key=lambda r: (r["holder_count"], r["id"]))
    return {"generated_at_utc": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"), "source": "Alchemy ERC-1155 transfers + RenaissSBT metadata", "complete": not result["has_more"], "pages_fetched": result["pages_fetched"], "transfers_scanned": len(result["transfers"]), "ranking": rows}


def migration_edges(decoded):
    """Infer strict old_wallet -> new_wallet migration edges from one transaction.

    Avoids candidate cartesian products: SBT burn/mint evidence is paired by
    overlapping IDs, and USDT/NFT evidence only strengthens direct from->to
    pairs already present in transaction logs.
    """
    if decoded.get("classification") != "legacy_wallet_migration":
        return []

    burned_by_old = collections.defaultdict(set)
    minted_by_new = collections.defaultdict(set)
    direct_pairs = collections.defaultdict(lambda: {"usdt": 0.0, "nft": 0})

    for b in decoded.get("renaiss_sbt_batches") or []:
        f, t = b.get("from"), b.get("to")
        ids = set(b.get("ids") or [])
        if f and f != ZERO and t == ZERO:
            burned_by_old[f].update(ids)
        if t and t != ZERO and f == ZERO:
            minted_by_new[t].update(ids)
    for s in decoded.get("renaiss_sbt_singles") or []:
        f, t = s.get("from"), s.get("to")
        ids = {s.get("id")} if s.get("id") is not None else set()
        if f and f != ZERO and t == ZERO:
            burned_by_old[f].update(ids)
        if t and t != ZERO and f == ZERO:
            minted_by_new[t].update(ids)

    def valid_wallet(addr):
        return bool(addr and addr != ZERO and addr.lower() not in KNOWN_RENAISS_CONTRACTS)

    for u in decoded.get("usdt_transfers") or []:
        f, t = u.get("from"), u.get("to")
        if valid_wallet(f) and valid_wallet(t) and f != t:
            direct_pairs[(f, t)]["usdt"] += float(u.get("amount_usdt") or 0)
    for n in decoded.get("renaiss_nft_transfers") or []:
        f, t = n.get("from"), n.get("to")
        if valid_wallet(f) and valid_wallet(t) and f != t:
            direct_pairs[(f, t)]["nft"] += 1

    edge_map = {}
    single_pair_context = len([a for a in burned_by_old if valid_wallet(a)]) == 1 and len([a for a in minted_by_new if valid_wallet(a)]) == 1
    for old, burned_ids in burned_by_old.items():
        if not valid_wallet(old):
            continue
        for new, minted_ids in minted_by_new.items():
            if not valid_wallet(new) or old == new:
                continue
            overlap = burned_ids & minted_ids
            # SBT IDs are ERC-1155 badge types, not user-unique IDs. In multi-user
            # migration transactions, overlapping badge IDs alone can create false
            # A->C/A->D/B->C/B->D edges. Only accept SBT-only evidence when the tx
            # has exactly one old and one new wallet; otherwise require direct
            # old->new USDT/NFT evidence before creating an edge.
            if not overlap:
                continue
            direct = direct_pairs.get((old, new), {})
            if not single_pair_context and not (direct.get("usdt") or direct.get("nft")):
                continue
            edge_map[(old, new)] = {
                "old_wallet": old,
                "new_wallet": new,
                "tx_hash": decoded.get("tx_hash"),
                "time_utc": decoded.get("time_utc"),
                "block_number": decoded.get("block_number"),
                "migrated_usdt": 0.0,
                "migrated_nft_count": 0,
                "migrated_sbt_ids": sorted(overlap),
                "ambiguous_migration_guard": not single_pair_context,
                "evidence": ["sbt_burn_mint_same_tx"],
            }

    # Direct old->new USDT/NFT transfers strengthen existing SBT edges, or can
    # create an edge when the transaction is explicitly sent to the migration helper.
    for (old, new), info in direct_pairs.items():
        if old == new:
            continue
        edge = edge_map.get((old, new))
        if edge is None:
            # When SBT burn/mint evidence exists, do not invent additional migration
            # edges from unrelated USDT transfers in the same transaction.
            if edge_map or (decoded.get("to") or "").lower() != MIGRATION:
                continue
            edge = {
                "old_wallet": old,
                "new_wallet": new,
                "tx_hash": decoded.get("tx_hash"),
                "time_utc": decoded.get("time_utc"),
                "block_number": decoded.get("block_number"),
                "migrated_usdt": 0.0,
                "migrated_nft_count": 0,
                "migrated_sbt_ids": [],
                "evidence": [],
            }
            edge_map[(old, new)] = edge
        if info.get("usdt"):
            edge["migrated_usdt"] += info["usdt"]
            edge["evidence"].append("direct_usdt_transfer")
        if info.get("nft"):
            edge["migrated_nft_count"] += info["nft"]
            edge["evidence"].append("direct_nft_transfer")

    for edge in edge_map.values():
        edge["evidence"] = sorted(set(edge.get("evidence") or []))
    return sorted(edge_map.values(), key=lambda e: (e.get("block_number") or 0, e.get("old_wallet"), e.get("new_wallet")))


def migration_component(primary, migrations):
    primary = primary.lower()
    undirected = collections.defaultdict(set)
    outgoing = collections.defaultdict(list)
    incoming = collections.defaultdict(list)
    for e in migrations:
        old, new = e["old_wallet"], e["new_wallet"]
        undirected[old].add(new); undirected[new].add(old)
        outgoing[old].append(e); incoming[new].append(e)
    component = {primary}
    queue = [primary]
    while queue:
        node = queue.pop(0)
        for nxt in undirected.get(node, set()):
            if nxt not in component:
                component.add(nxt); queue.append(nxt)
    terminals = sorted([w for w in component if not any(e["new_wallet"] in component for e in outgoing.get(w, []))])
    if not terminals:
        terminals = [primary]
    # If multiple terminal wallets exist, pick the one with the latest incoming migration as the display
    # current wallet, but surface ambiguity to the report.
    def latest_incoming_block(w):
        vals = [e.get("block_number") or 0 for e in incoming.get(w, [])]
        return max(vals) if vals else 0
    current = sorted(terminals, key=lambda w: (latest_incoming_block(w), w), reverse=True)[0]
    return current, sorted(component), terminals

def summarize_cluster(primary, history_by_wallet, decoded_by_hash, wallet_details):
    primary = primary.lower()
    migrations = []
    cluster = {primary}
    for d in decoded_by_hash.values():
        for e in migration_edges(d):
            migrations.append(e)
            cluster.add(e["old_wallet"]); cluster.add(e["new_wallet"])
    current_wallet, component_cluster, current_wallet_candidates = migration_component(primary, migrations) if migrations else (primary, [primary], [primary])
    cluster = sorted(set(component_cluster if migrations else cluster))
    component_set = set(cluster)
    migrations = [e for e in migrations if e.get("old_wallet") in component_set and e.get("new_wallet") in component_set]
    legacy_wallets = sorted([w for w in cluster if w != current_wallet])
    current_wallet_ambiguous = len(current_wallet_candidates) > 1

    counters = collections.Counter()
    nft_in = []; nft_out = []
    sbt_ids = set()
    usdt_in = 0.0; usdt_out = 0.0
    marketplace_buys = 0; marketplace_sells = 0; pack_buys = 0; buyback_candidates = 0
    marketplace_buy_spend_usdt = 0.0; marketplace_sell_income_usdt = 0.0
    pack_spend_usdt = 0.0; buyback_income_usdt = 0.0
    pack_count_total = 0
    pack_type_counts = collections.Counter(); pack_type_spend = collections.Counter(); pack_type_pack_counts = collections.Counter()
    pack_open_records = []
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
                purchase = infer_pack_purchase(tx_usdt_out, pack_catalog)
                pack_type = purchase["pack_type"]
                pack_count = purchase.get("pack_count") or (tx_nft_in if tx_nft_in else 0)
                pack_count_total += pack_count
                pack_type_counts[pack_type] += 1
                pack_type_spend[pack_type] += tx_usdt_out
                if pack_count:
                    pack_type_pack_counts[pack_type] += pack_count
                pack_open_records.append({
                    "tx_hash": h,
                    "time_utc": d.get("time_utc"),
                    "amount_usdt": tx_usdt_out,
                    "pack_type": pack_type,
                    "pack_count": purchase.get("pack_count"),
                    "batch_multiple": purchase.get("batch_multiple"),
                    "unit_price_usdt": purchase.get("unit_price_usdt"),
                    "nft_received_count": tx_nft_in,
                })
            # Buyback/sell-back flows can be NFT out + USDT in, or legacy payout-only selector 0xb24f1607.
            if tx_usdt_in and (tx_nft_out or selector in {"0xb24f1607"} or (d.get("from") or "").lower() in PACK_CONTRACTS):
                buyback_candidates += 1
                buyback_income_usdt += tx_usdt_in

    sbt_metadata = resolve_sbt_metadata(sbt_ids) if sbt_ids else []
    cluster_sbt_holdings = {}
    for wallet in cluster:
        try:
            cluster_sbt_holdings[wallet] = fetch_sbt_balances_for_owner(wallet)
        except Exception as e:
            cluster_sbt_holdings[wallet] = {"owner": wallet, "holdings": [], "sbt_count": 0, "unique_sbt_types": 0, "error": str(redact_secret_url(e))}
    current_wallet_sbt_holdings = cluster_sbt_holdings.get(current_wallet, {"holdings": [], "sbt_count": 0, "unique_sbt_types": 0})
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
        "current_wallet_candidates": current_wallet_candidates,
        "current_wallet_ambiguous": current_wallet_ambiguous,
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
        "pack_count_total": pack_count_total,
        "pack_open_records": pack_open_records,
        "pack_type_counts": dict(pack_type_counts),
        "pack_type_pack_counts": dict(pack_type_pack_counts),
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
        "current_wallet_sbt_count": current_wallet_sbt_holdings.get("sbt_count", 0),
        "current_wallet_unique_sbt_types": current_wallet_sbt_holdings.get("unique_sbt_types", 0),
        "current_wallet_sbt_holdings": current_wallet_sbt_holdings.get("holdings", []),
        "cluster_sbt_holdings": cluster_sbt_holdings,
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
            "Wallet history is collected through Alchemy Transfers API when configured; very active wallets may still need a higher --max-pages or a dedicated archival/indexer export.",
            "Pack count inference supports batch opens by matching USDT spend to integer multiples of active pack prices.",
            "Current SBT holdings are reconstructed from RenaissSBT ERC-1155 transfer history; incomplete Alchemy pagination makes SBT counts partial.",
        ],
    }


def build_wallet_report(address, limit=100, source="auto", max_pages=5, max_wallets=20):
    address = address.lower()
    history_by_wallet = {}
    wallet_details = {}
    decoded_by_hash = {}
    queue = [address]
    seen_wallets = set()
    wallet_scan_truncated = False
    while queue and len(seen_wallets) < max(1, max_wallets):
        w = queue.pop(0).lower()
        if w in seen_wallets:
            continue
        seen_wallets.add(w)
        try:
            hist = fetch_wallet_history(w, limit=limit, source=source, max_pages=max_pages)
        except Exception as e:
            hist = {"source": source, "data": [], "meta": {}, "error": str(redact_secret_url(e))}
        history_by_wallet[w] = hist
        try:
            wallet_details[w] = fetch_wallet_detail(w, source=source)
        except Exception as e:
            wallet_details[w] = {"source": None, "data": {}, "meta": {}, "error": str(redact_secret_url(e))}
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
        # Find migration-linked wallets and add only the primary wallet's connected component.
        all_edges = []
        for d in list(decoded_by_hash.values()):
            all_edges.extend(migration_edges(d))
        if all_edges:
            _current, connected_wallets, _terminals = migration_component(address, all_edges)
            for candidate in connected_wallets:
                if candidate not in seen_wallets and candidate not in queue:
                    queue.append(candidate)
    wallet_scan_truncated = bool(queue)
    wallets_pending = sorted(set(queue))
    summary = summarize_cluster(address, history_by_wallet, decoded_by_hash, wallet_details)
    history_incomplete_wallets = []
    history_errors = {}
    for wallet, hist in history_by_wallet.items():
        meta = hist.get("meta") or {}
        if meta.get("has_more_last") or hist.get("error"):
            history_incomplete_wallets.append(wallet)
            if hist.get("error"):
                history_errors[wallet] = hist.get("error")
    decode_error_count = sum(1 for tx in decoded_by_hash.values() if tx.get("error"))
    report_partial = bool(wallet_scan_truncated or history_incomplete_wallets or decode_error_count)
    partial_reasons = []
    if wallet_scan_truncated:
        partial_reasons.append("wallet_scan_truncated")
    if history_incomplete_wallets:
        partial_reasons.append("history_scan_truncated_or_error")
    if decode_error_count:
        partial_reasons.append("decode_errors")
    summary["wallet_scan_truncated"] = wallet_scan_truncated
    summary["wallets_scanned"] = len(seen_wallets)
    summary["wallets_pending"] = wallets_pending
    summary["max_wallets"] = max_wallets
    summary["history_scan_truncated"] = bool(history_incomplete_wallets)
    summary["history_incomplete_wallets"] = sorted(history_incomplete_wallets)
    summary["history_errors"] = history_errors
    summary["decode_error_count"] = decode_error_count
    summary["pnl_completeness"] = "partial" if report_partial else "complete_within_fetched_history"
    summary["pnl_partial_reasons"] = partial_reasons
    if wallet_scan_truncated:
        summary.setdefault("data_notes", []).append("Wallet scan hit --max-wallets; spend/income/net spend are partial until pending wallets are scanned.")
    if history_incomplete_wallets:
        summary.setdefault("data_notes", []).append("Wallet history pagination did not fully exhaust for at least one scanned wallet, or the history source returned an error; spend/income/net spend are partial.")
    if decode_error_count:
        summary.setdefault("data_notes", []).append("One or more transaction receipts failed to decode; spend/income/net spend are partial.")
    history_sources = sorted(set(h.get("source") for h in history_by_wallet.values() if h.get("source")))
    receipt_source = "Alchemy BNB RPC receipts" if is_alchemy_configured() else "BSC RPC receipts"
    source_label = (", ".join(history_sources) if history_sources else "wallet-history index") + f" + {receipt_source}"
    return {
        "generated_at_utc": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        "source": source_label,
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
    lines.append(f"- Wallet scan completeness: {s.get('pnl_completeness', 'unknown')}")
    if s.get('pnl_partial_reasons'):
        lines.append(f"- Partial reasons: {', '.join(s.get('pnl_partial_reasons', []))}")
    if s.get('wallet_scan_truncated'):
        lines.append(f"- Pending wallets not scanned: {', '.join('`'+w+'`' for w in s.get('wallets_pending', []))}")
    if s.get('history_incomplete_wallets'):
        lines.append(f"- Wallet history incomplete: {', '.join('`'+w+'`' for w in s.get('history_incomplete_wallets', []))}")
    if s.get('decode_error_count'):
        lines.append(f"- Decode errors: {s.get('decode_error_count')}")
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
    lines.append(f"| Inferred pack count | {s.get('pack_count_total', 0)} |")
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
        lines.append("| Pack type | Transactions | Inferred packs | Spend USDT |")
        lines.append("|---|---:|---:|---:|")
        for name, count in s['pack_type_counts'].items():
            lines.append(f"| {name} | {count} | {s.get('pack_type_pack_counts', {}).get(name, 0)} | {s['pack_type_spend_usdt'].get(name, 0):.6f} |")
    else:
        lines.append("No pack type inferred.")
    lines.append("")
    lines.append("## SBT")
    lines.append("")
    if s.get('current_wallet_sbt_holdings'):
        lines.append(f"Current wallet SBT count: {s.get('current_wallet_sbt_count', 0)} across {s.get('current_wallet_unique_sbt_types', 0)} types.")
        lines.append("")
        lines.append("| ID | Name | Balance |")
        lines.append("|---:|---|---:|")
        for item in s['current_wallet_sbt_holdings']:
            lines.append(f"| {item.get('id')} | {item.get('name') or 'unknown'} | {item.get('balance')} |")
    elif s.get('sbt_metadata'):
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
    report = build_wallet_report(args.address, limit=args.limit, source=args.history_source, max_pages=args.max_pages, max_wallets=args.max_wallets)
    if args.out:
        os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
    if args.out_md:
        os.makedirs(os.path.dirname(args.out_md) or ".", exist_ok=True)
        write_wallet_markdown(report, args.out_md)
    print(json.dumps(report if args.verbose else report["summary"], ensure_ascii=False, indent=2))


def cmd_sbt_holder_ranking(args):
    report = build_sbt_holder_ranking(max_pages=args.max_pages, limit=args.limit)
    if args.out:
        os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
    if args.out_csv:
        os.makedirs(os.path.dirname(args.out_csv) or ".", exist_ok=True)
        with open(args.out_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["id", "name", "holder_count", "current_supply"])
            writer.writeheader()
            writer.writerows(report["ranking"])
    print(json.dumps(report, ensure_ascii=False, indent=2))


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("decode-tx"); d.add_argument("--tx", required=True); d.set_defaults(func=lambda a: print(json.dumps(decode_tx(a.tx), ensure_ascii=False, indent=2)))
    m = sub.add_parser("decode-migration-tx"); m.add_argument("--tx", required=True); m.set_defaults(func=lambda a: print(json.dumps(decode_tx(a.tx), ensure_ascii=False, indent=2)))
    w = sub.add_parser("wallet-report")
    w.add_argument("--address", required=True)
    w.add_argument("--limit", type=int, default=100)
    w.add_argument("--max-pages", type=int, default=5, help="wallet-history pages to fetch per wallet via before cursor")
    w.add_argument("--max-wallets", type=int, default=20, help="maximum wallet-cluster addresses to scan before marking the report partial")
    w.add_argument("--history-source", choices=["auto", "alchemy", "surf"], default="auto", help="auto prefers Alchemy when ALCHEMY_API_KEY/ALCHEMY_BNB_RPC_URL is configured")
    w.add_argument("--out")
    w.add_argument("--out-md")
    w.add_argument("--verbose", action="store_true")
    w.set_defaults(func=cmd_wallet_report)
    r = sub.add_parser("sbt-holder-ranking", help="Reconstruct current holder counts for each RenaissSBT ID from ERC-1155 transfer history")
    r.add_argument("--max-pages", type=int, default=500, help="maximum Alchemy transfer pages to scan; increase until complete=true")
    r.add_argument("--limit", type=int, default=1000, help="Alchemy transfers per page, max 1000")
    r.add_argument("--out")
    r.add_argument("--out-csv")
    r.set_defaults(func=cmd_sbt_holder_ranking)
    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
