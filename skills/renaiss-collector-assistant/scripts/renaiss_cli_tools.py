#!/usr/bin/env python3
"""Renaiss CLI helper utilities for Renaiss Collector Assistant.

Requires Node.js >=22 and Renaiss CLI via `npx --yes renaiss`.
Uses only Python stdlib.
"""
import argparse, asyncio, csv, json, os, re, subprocess, sys, time, urllib.parse, urllib.request, urllib.error
from datetime import datetime, timezone
from pathlib import Path

try:
    from common_env import load_dotenv_files
    load_dotenv_files()
except Exception:
    pass

FEE_RATE = float(os.getenv("RENAISS_SELLER_FEE_RATE", "0.02"))
CARD_URL_PREFIX = "https://www.renaiss.xyz/card/"


def utc_now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def normalize_cert(value):
    text = str(value or "").upper().strip()
    m = re.search(r"(?:PSA\s*)?(\d{4,})", text)
    return f"PSA{m.group(1)}" if m else None


def parse_iso_datetime(value):
    if not value:
        return None
    try:
        text = str(value).strip()
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        dt = datetime.fromisoformat(text)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def is_expired_ask(value, now=None):
    dt = parse_iso_datetime(value)
    if not dt:
        return False
    return dt <= (now or datetime.now(timezone.utc))


def parse_token_id(value: str) -> str | None:
    m = re.search(r"(\d{18,})", value or "")
    return m.group(1) if m else None


def usdt_wei_to_float(v):
    if not v or str(v).startswith("NO-"):
        return None
    try:
        return int(str(v)) / 1e18
    except Exception:
        try:
            return float(v)
        except Exception:
            return None


def usd_cents_to_float(v):
    if not v or str(v).startswith("NO-"):
        return None
    try:
        return int(str(v)) / 100
    except Exception:
        try:
            return float(v)
        except Exception:
            return None


def extract_attr(attrs, name):
    for a in attrs or []:
        if str(a.get("trait", "")).lower() == name.lower():
            return a.get("value")
    return None


def serial_number(serial_raw):
    if not serial_raw:
        return None
    m = re.search(r"(\d+)", str(serial_raw))
    return int(m.group(1)) if m else None


def run_json(cmd, timeout=None):
    timeout = timeout or env_int("RENAISS_CLI_TIMEOUT", 180)
    try:
        p = subprocess.run(cmd, text=True, capture_output=True, timeout=timeout)
    except subprocess.TimeoutExpired as e:
        raise RuntimeError(f"Command timed out after {timeout}s: {' '.join(cmd)}") from e
    if p.returncode != 0:
        raise RuntimeError(p.stderr.strip() or p.stdout.strip())
    return json.loads(p.stdout)


def normalize_market_card(card, collected_at):
    ask = card.get("askPriceInUSDT")
    fmv = card.get("fmvPriceInUSD")
    ask_expires_at = card.get("askExpiresAt")
    token_id = card.get("tokenId")
    attrs = card.get("attributes") or []
    serial_raw = extract_attr(attrs, "Serial")
    lang = extract_attr(attrs, "Language")
    return {
        "collected_at_utc": collected_at,
        "source": "Renaiss CLI",
        "tokenId": token_id,
        "card_url": CARD_URL_PREFIX + str(token_id) if token_id else None,
        "name": card.get("name"),
        "type": card.get("type"),
        "setName": card.get("setName"),
        "cardNumber": card.get("cardNumber"),
        "pokemonName": card.get("pokemonName"),
        "ownerAddress": card.get("ownerAddress"),
        "ownerUsername": (card.get("owner") or {}).get("username"),
        "askPriceInUSDT_raw": ask,
        "ask_usdt": usdt_wei_to_float(ask),
        "askExpiresAt": ask_expires_at,
        "ask_is_expired_at_collection": is_expired_ask(ask_expires_at),
        "fmvPriceInUSD_raw": fmv,
        "fmv_usd": usd_cents_to_float(fmv),
        "vaultLocation": card.get("vaultLocation"),
        "gradingCompany": card.get("gradingCompany"),
        "grade": card.get("grade"),
        "year": card.get("year"),
        "tier": card.get("tier"),
        "serial_raw": serial_raw,
        "serial_number": serial_number(serial_raw),
        "language": lang,
        "attributes_json": attrs,
        "raw": card,
    }


def cmd_check(_):
    timeout = env_int("RENAISS_CLI_TIMEOUT", 180)
    print(subprocess.check_output(["node", "--version"], text=True, timeout=30).strip())
    print(subprocess.check_output(["npm", "--version"], text=True, timeout=30).strip())
    subprocess.run(["npx", "--yes", "renaiss", "--help"], check=True, timeout=timeout)


def cmd_extract_token(args):
    token_id = parse_token_id(args.value)
    if not token_id:
        raise SystemExit("No decimal tokenId found.")
    print(token_id)


def cmd_marketplace_snapshot(args):
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(out.suffix + ".tmp")
    meta_path = out.with_suffix(out.suffix + ".meta.json")
    offset = args.offset
    total = 0
    pages = 0
    collected_at = utc_now()
    try:
        with tmp.open("w", encoding="utf-8") as f:
            while True:
                cmd = ["npx", "--yes", "renaiss", "marketplace", "--limit", str(args.limit), "--offset", str(offset), "--json"]
                if args.listed:
                    cmd.append("--listed")
                if args.grading:
                    cmd += ["--grading", args.grading]
                if args.category:
                    cmd += ["--category", args.category]
                if args.search:
                    cmd += ["--search", args.search]
                data = run_json(cmd)
                pages += 1
                for card in data.get("collection", []):
                    f.write(json.dumps(normalize_market_card(card, collected_at), ensure_ascii=False) + "\n")
                    total += 1
                pag = data.get("pagination", {})
                if not pag.get("hasMore"):
                    break
                offset += int(pag.get("limit", args.limit))
        os.replace(tmp, out)
        meta = {"complete": True, "pages": pages, "rows": total, "started_at_utc": collected_at, "completed_at_utc": utc_now(), "out": str(out)}
        meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        try:
            tmp.unlink(missing_ok=True)
        except Exception:
            pass
        raise
    print(json.dumps({"out": str(out), "rows": total, "pages": pages, "meta_out": str(meta_path), "collected_at_utc": collected_at}, ensure_ascii=False, indent=2))

def env_int(name, default):
    try:
        return int(os.getenv(name, str(default)))
    except Exception:
        return default


def env_float(name, default):
    try:
        return float(os.getenv(name, str(default)))
    except Exception:
        return default


def classify_card_detail_error(message):
    text = (message or "").lower()
    if "http 403" in text or "forbidden" in text:
        return "forbidden"
    if "http 429" in text or "too many requests" in text:
        return "rate_limit"
    if "timeout" in text:
        return "timeout"
    if "rate" in text and "limit" in text:
        return "rate_limit"
    if "api error" in text:
        return "api_error"
    if "json" in text:
        return "json_error"
    return "error"



def card_api_url(token_id):
    base = os.getenv("RENAISS_CARD_API_BASE", "https://api.renaiss.xyz/v0/cards").rstrip("/")
    return f"{base}/{token_id}?verbosePrice=true"


def fetch_card_detail_api_sync(token_id, timeout=120):
    started = utc_now()
    t0 = time.perf_counter()
    url = card_api_url(token_id)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "RenaissCollectorAssistant/0.1"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.load(r)
        data["_fetch_meta"] = {"started_at_utc": started, "latency_s": time.perf_counter() - t0, "status": "ok", "method": "api", "url": url}
        return data
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode(errors="replace")[:500]
        except Exception:
            pass
        msg = f"HTTP {e.code}: {body or e.reason}"
        return {"error": msg, "error_status": classify_card_detail_error(msg), "tokenId": token_id, "latency_s": time.perf_counter() - t0, "started_at_utc": started, "method": "api", "url": url}
    except Exception as e:
        msg = str(e)
        return {"error": msg, "error_status": classify_card_detail_error(msg), "tokenId": token_id, "latency_s": time.perf_counter() - t0, "started_at_utc": started, "method": "api", "url": url}


async def fetch_card_detail_once(token_id, timeout=120, method="cli"):
    if method == "api":
        return await asyncio.to_thread(fetch_card_detail_api_sync, token_id, timeout)
    started = utc_now()
    t0 = time.perf_counter()
    try:
        proc = await asyncio.create_subprocess_exec(
            "npx", "--yes", "renaiss", "card", token_id, "--price", "--verbose", "--json",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        except asyncio.TimeoutError:
            proc.kill()
            stdout, stderr = await proc.communicate()
            return {"error": f"timeout after {timeout}s", "error_status": "timeout", "tokenId": token_id, "latency_s": time.perf_counter() - t0, "started_at_utc": started, "method": "cli"}
        except asyncio.CancelledError:
            proc.kill()
            await proc.communicate()
            raise
        latency = time.perf_counter() - t0
        out = stdout.decode(errors="replace")
        err = stderr.decode(errors="replace")
        if proc.returncode == 0:
            try:
                data = json.loads(out)
                data["_fetch_meta"] = {"started_at_utc": started, "latency_s": latency, "status": "ok", "method": "cli"}
                return data
            except Exception as e:
                msg = f"JSON parse error: {e}; stdout={out[:500]}"
                return {"error": msg, "error_status": "json_error", "tokenId": token_id, "latency_s": latency, "started_at_utc": started, "method": "cli"}
        msg = err or out or f"renaiss card exited with {proc.returncode}"
        return {"error": msg, "error_status": classify_card_detail_error(msg), "tokenId": token_id, "latency_s": latency, "started_at_utc": started, "method": "cli"}
    except Exception as e:
        msg = str(e)
        return {"error": msg, "error_status": classify_card_detail_error(msg), "tokenId": token_id, "latency_s": time.perf_counter() - t0, "started_at_utc": started, "method": "cli"}


async def fetch_card_detail_with_retries(token_id, retries=1, timeout=120, method="cli"):
    last = None
    for attempt in range(retries + 1):
        result = await fetch_card_detail_once(token_id, timeout=timeout, method=method)
        if "error" not in result:
            result.setdefault("_fetch_meta", {})["attempts"] = attempt + 1
            return result
        last = result
        # 429/403 share the same backend/WAF with CLI. Do not immediately fallback; let cooldown handle it.
        if result.get("error_status") in {"forbidden", "rate_limit"}:
            break
        if attempt < retries:
            await asyncio.sleep(min(30, 3 * (attempt + 1)))
    if last is None:
        last = {"error": "unknown error", "error_status": "error", "tokenId": token_id, "method": method}
    last["attempts"] = min(retries + 1, last.get("attempts", retries + 1))
    return last


def normalize_detail(resp, collected_at):
    c = resp.get("collectible") or resp.get("raw", {}).get("collectible") or {}
    pricing = resp.get("pricing") or {}
    attrs = c.get("attributes") or []
    serial_raw = extract_attr(attrs, "Serial")
    lang = extract_attr(attrs, "Language")
    token_id = c.get("tokenId") or resp.get("tokenId")
    top_offer = pricing.get("top_offer") or {}
    last_sale = pricing.get("last_sale") or {}
    price = pricing.get("price") or {}
    method = (resp.get("_fetch_meta") or {}).get("method") or resp.get("method")
    return {
        "collected_at_utc": collected_at,
        "source": "Renaiss Card API" if method == "api" else "Renaiss CLI",
        "request_method": method,
        "tokenId": token_id,
        "card_url": CARD_URL_PREFIX + str(token_id) if token_id else None,
        "name": c.get("name"),
        "setName": c.get("setName"),
        "cardNumber": c.get("cardNumber"),
        "pokemonName": c.get("pokemonName"),
        "ownerAddress": c.get("ownerAddress"),
        "ownerUsername": (c.get("owner") or {}).get("username"),
        "gradingCompany": c.get("gradingCompany"),
        "grade": c.get("grade"),
        "year": c.get("year"),
        "serial_raw": serial_raw,
        "serial_number": serial_number(serial_raw),
        "language": lang,
        "askPriceInUSDT_raw": c.get("askPriceInUSDT") or price.get("value"),
        "ask_usdt": usdt_wei_to_float(c.get("askPriceInUSDT") or price.get("value")),
        "fmvPriceInUSD_raw": c.get("fmvPriceInUSD"),
        "fmv_usd": usd_cents_to_float(c.get("fmvPriceInUSD")),
        "top_offer_raw": top_offer.get("value"),
        "top_offer_usdt": usdt_wei_to_float(top_offer.get("value")),
        "last_sale_raw": last_sale.get("value"),
        "last_sale_usdt": usdt_wei_to_float(last_sale.get("value")),
        "askExpiresAt": c.get("askExpiresAt"),
        "frontImageUrl": c.get("frontImageUrl"),
        "backImageUrl": c.get("backImageUrl"),
        "attributes_json": attrs,
        "price_history_json": pricing.get("price_history"),
        "offers_json": pricing.get("offers"),
        "raw": resp,
    }


def read_jsonl(path, tolerate_last_truncated=True):
    rows = []
    p = Path(path)
    lines = p.read_text(encoding="utf-8").splitlines()
    for line_no, line in enumerate(lines, 1):
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as e:
            is_last = line_no == len(lines)
            if tolerate_last_truncated and is_last:
                print(json.dumps({
                    "event": "jsonl_truncated_line_skipped",
                    "path": str(path),
                    "line": line_no,
                    "error": str(e),
                }, ensure_ascii=False), file=sys.stderr)
                continue
            raise ValueError(f"Invalid JSONL at {path}:{line_no}: {e}") from e
    return rows


def write_jsonl(path, rows):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")



def load_existing_detail_state(out_path):
    """Return tokenIds already completed and tokenIds already attempted in an output JSONL."""
    p = Path(out_path)
    completed, attempted = set(), set()
    if not p.exists():
        return completed, attempted
    for row in read_jsonl(p):
        tid = row.get("tokenId")
        if not tid:
            continue
        tid = str(tid)
        attempted.add(tid)
        if not row.get("error") and not row.get("error_status"):
            completed.add(tid)
    return completed, attempted


def append_jsonl(path, rows):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


async def run_card_detail_batch(token_ids, concurrency, inter_request_delay, retries, timeout, method):
    sem = asyncio.Semaphore(concurrency)
    rate_lock = asyncio.Lock()
    last_request_at = 0.0

    async def wait_for_rate_limit():
        nonlocal last_request_at
        if inter_request_delay <= 0:
            return
        async with rate_lock:
            now = time.monotonic()
            wait = inter_request_delay - (now - last_request_at)
            if wait > 0:
                await asyncio.sleep(wait)
            last_request_at = time.monotonic()

    async def worker(_idx, tid):
        async with sem:
            # This limiter runs immediately before the actual request, not before
            # semaphore queueing, so request starts remain spaced even with concurrency > 1.
            await wait_for_rate_limit()
            return await fetch_card_detail_with_retries(tid, retries=retries, timeout=timeout, method=method)

    return await asyncio.gather(*(worker(i, tid) for i, tid in enumerate(token_ids)))


def cmd_card_details(args):
    rows = read_jsonl(args.input)
    token_ids = []
    seen = set()
    skipped_rows = []
    for idx, r in enumerate(rows):
        tid = r.get("tokenId") or parse_token_id(str(r.get("card_url", "")))
        if tid and str(tid) not in seen:
            seen.add(str(tid)); token_ids.append(str(tid))
        elif not tid:
            skipped_rows.append({"row_index": idx, "error": "missing_or_invalid_token_id", "row": r})
    if args.limit:
        token_ids = token_ids[:args.limit]

    method = args.method
    if method == "auto":
        method = "cli" if len(token_ids) <= args.api_threshold else "api"
    if method == "api":
        max_concurrency = env_int("RENAISS_CARD_DETAIL_MAX_CONCURRENCY", 1)
        concurrency_default = env_int("RENAISS_CARD_DETAIL_API_CONCURRENCY", 1)
        batch_default = env_int("RENAISS_CARD_DETAIL_API_BATCH_SIZE", 10)
        delay_default = env_float("RENAISS_CARD_DETAIL_API_INTER_REQUEST_DELAY", 1)
        cooldown_default = env_float("RENAISS_CARD_DETAIL_API_BATCH_COOLDOWN", 5)
    else:
        max_concurrency = env_int("RENAISS_CARD_DETAIL_MAX_CONCURRENCY", 3)
        concurrency_default = env_int("RENAISS_CARD_DETAIL_CONCURRENCY", 2)
        batch_default = env_int("RENAISS_CARD_DETAIL_BATCH_SIZE", 20)
        delay_default = env_float("RENAISS_CARD_DETAIL_INTER_REQUEST_DELAY", 8)
        cooldown_default = env_float("RENAISS_CARD_DETAIL_BATCH_COOLDOWN", 90)
    concurrency = min(max(1, args.concurrency or concurrency_default), max_concurrency)
    batch_size = max(1, args.batch_size or batch_default)
    inter_request_delay = max(0.0, args.inter_request_delay if args.inter_request_delay is not None else delay_default)
    batch_cooldown = max(0.0, args.batch_cooldown if args.batch_cooldown is not None else cooldown_default)
    forbidden_cooldown = max(0.0, args.forbidden_cooldown if args.forbidden_cooldown is not None else env_float("RENAISS_CARD_DETAIL_FORBIDDEN_COOLDOWN", 300 if method == "api" else 900))
    retries = max(0, args.retries if args.retries is not None else env_int("RENAISS_CARD_DETAIL_RETRIES", 1))
    timeout = max(30, args.timeout if args.timeout is not None else env_int("RENAISS_CARD_DETAIL_TIMEOUT", 120))

    if not args.resume and Path(args.out).exists():
        Path(args.out).unlink()
    completed, attempted = load_existing_detail_state(args.out) if args.resume else (set(), set())
    if args.resume:
        skip = completed if args.retry_errors else attempted
        pending = [tid for tid in token_ids if tid not in skip]
    else:
        pending = token_ids

    collected_at = utc_now()
    summary = {
        "out": args.out,
        "input_rows": len(rows),
        "unique_token_ids": len(token_ids),
        "skipped_input_rows": len(skipped_rows),
        "resume": args.resume,
        "retry_errors": args.retry_errors,
        "already_completed": len(completed),
        "already_attempted": len(attempted),
        "pending": len(pending),
        "method": method,
        "api_threshold": args.api_threshold,
        "estimated_seconds": (len(pending) * inter_request_delay + max(0, ((len(pending) + batch_size - 1) // batch_size) - 1) * batch_cooldown),
        "concurrency": concurrency,
        "max_concurrency": max_concurrency,
        "batch_size": batch_size,
        "inter_request_delay_s": inter_request_delay,
        "batch_cooldown_s": batch_cooldown,
        "forbidden_cooldown_s": forbidden_cooldown,
        "retries": retries,
        "timeout_s": timeout,
        "started_at_utc": collected_at,
        "batches": 0,
        "new_success": 0,
        "new_failures": 0,
        "new_forbidden": 0,
        "new_timeouts": 0,
    }

    for batch_start in range(0, len(pending), batch_size):
        batch = pending[batch_start:batch_start + batch_size]
        batch_no = batch_start // batch_size + 1
        summary["batches"] += 1
        batch_t0 = time.perf_counter()
        results = asyncio.run(run_card_detail_batch(batch, concurrency, inter_request_delay, retries, timeout, method))
        normalized = []
        forbidden_count = 0
        rate_limit_count = 0
        timeout_count = 0
        success_count = 0
        for r in results:
            if "error" in r:
                status = r.get("error_status") or classify_card_detail_error(r.get("error"))
                forbidden_count += 1 if status == "forbidden" else 0
                rate_limit_count += 1 if status == "rate_limit" else 0
                timeout_count += 1 if status == "timeout" else 0
                normalized.append({
                    "source": "Renaiss Card API" if r.get("method") == "api" else "Renaiss CLI",
                    "request_method": r.get("method"),
                    "tokenId": r.get("tokenId"),
                    "error": r.get("error"),
                    "error_status": status,
                    "attempts": r.get("attempts"),
                    "latency_s": r.get("latency_s"),
                    "started_at_utc": r.get("started_at_utc"),
                    "collected_at_utc": utc_now(),
                })
            else:
                row = normalize_detail(r, utc_now())
                meta = r.get("_fetch_meta") or {}
                row["latency_s"] = meta.get("latency_s")
                row["attempts"] = meta.get("attempts")
                row["started_at_utc"] = meta.get("started_at_utc")
                normalized.append(row)
                success_count += 1
        append_jsonl(args.out, normalized)
        summary["new_success"] += success_count
        summary["new_failures"] += len(batch) - success_count
        summary["new_forbidden"] += forbidden_count
        summary.setdefault("new_rate_limits", 0)
        summary["new_rate_limits"] += rate_limit_count
        summary["new_timeouts"] += timeout_count
        batch_elapsed = time.perf_counter() - batch_t0
        print(json.dumps({
            "event": "card_detail_batch_done",
            "batch": batch_no,
            "batch_size": len(batch),
            "success": success_count,
            "failures": len(batch) - success_count,
            "forbidden": forbidden_count,
            "rate_limit": rate_limit_count,
            "timeouts": timeout_count,
            "elapsed_s": round(batch_elapsed, 3),
            "written_to": args.out,
        }, ensure_ascii=False), file=sys.stderr)

        if batch_start + batch_size < len(pending):
            if (forbidden_count + rate_limit_count) >= args.max_forbidden_per_batch and forbidden_cooldown:
                print(json.dumps({"event": "waf_cooldown", "sleep_s": forbidden_cooldown, "reason": "429/403 responses in batch"}, ensure_ascii=False), file=sys.stderr)
                time.sleep(forbidden_cooldown)
            elif batch_cooldown:
                time.sleep(batch_cooldown)

    summary["ended_at_utc"] = utc_now()
    print(json.dumps(summary, ensure_ascii=False, indent=2))


def relation_tags(a, b):
    tags = []
    if a.get("name") and a.get("name") == b.get("name") and a.get("cardNumber") == b.get("cardNumber"):
        tags.append("same_card")
    if a.get("setName") and a.get("setName") == b.get("setName"):
        tags.append("same_set")
    if a.get("pokemonName") and a.get("pokemonName") == b.get("pokemonName"):
        tags.append("same_character")
    if a.get("language") and a.get("language") == b.get("language"):
        tags.append("same_language")
    if a.get("grade") and a.get("grade") == b.get("grade"):
        tags.append("same_grade")
    if a.get("year") and a.get("year") == b.get("year"):
        tags.append("same_year")
    if a.get("ownerAddress") and a.get("ownerAddress") == b.get("ownerAddress"):
        tags.append("same_owner")
    ask_total = (a.get("ask_usdt") or 0) + (b.get("ask_usdt") or 0)
    fmv_total = (a.get("fmv_usd") or 0) + (b.get("fmv_usd") or 0)
    if ask_total and fmv_total > ask_total:
        tags.append("fmv_discount")
    if ask_total and ask_total < 200:
        tags.append("low_total_cost")
    if fmv_total > 500 or "10" in str(a.get("grade")) or "10" in str(b.get("grade")):
        tags.append("rare_or_high_value")
    return tags



SEQUENTIAL_FIELDNAMES = [
    "serial_a", "serial_b", "serial_number_a", "serial_number_b", "serial_gap",
    "tokenId_a", "tokenId_b", "name_a", "name_b", "setName_a", "setName_b",
    "grade_a", "grade_b", "ask_total_usdt", "fmv_total_usd", "special_tags",
    "candidate_strength", "risk_note", "source",
]

ARBITRAGE_FIELDNAMES = [
    "tokenId", "name", "ask_usdt", "top_offer_usdt", "top_offer_net_usdt",
    "direct_arbitrage_profit", "direct_arbitrage_profit_pct", "fmv_usd", "fmv_net_usd",
    "fmv_spread_net", "fmv_spread_pct", "last_sale_usdt", "fee_rate",
    "opportunity_type", "ranking_value", "risk_notes", "source",
]

INDEX_ARBITRAGE_FIELDNAMES = [
    "tokenId", "name", "serial_raw", "serial_number", "ask_usdt", "index_query",
    "index_result_count", "index_price_usd", "index_price_net_usd", "index_spread_usdt",
    "index_spread_pct", "index_confidence", "index_last_sale_at", "index_href",
    "index_match_name", "index_match_grade", "index_match_company", "fee_rate",
    "exact_cert_match", "index_response_cert", "ranking_value", "risk_notes", "source",
]


def write_csv(path, rows, fieldnames):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def append_csv_rows(path, rows, fieldnames):
    if not rows:
        return
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    needs_header = not p.exists() or p.stat().st_size == 0
    with p.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        if needs_header:
            w.writeheader()
        w.writerows(rows)


def read_csv_key_set(path, *fields):
    p = Path(path)
    if not p.exists() or p.stat().st_size == 0:
        return set()
    out = set()
    with p.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            key = tuple(row.get(field) for field in fields)
            if any(key):
                out.add(key)
    return out


def index_state_key(token_id, serial):
    return (str(token_id or ""), str(serial or ""))


def read_terminal_state_keys(path):
    p = Path(path)
    if not p.exists() or p.stat().st_size == 0:
        return set()
    keys = set()
    for row in read_jsonl(p):
        if row.get("terminal"):
            keys.add(index_state_key(row.get("tokenId"), row.get("serial")))
    return keys


def build_index_state(row, status, *, terminal=True, error=None, extra=None):
    serial = row.get("serial_raw") or row.get("serial_number")
    out = {
        "processed_at_utc": utc_now(),
        "tokenId": row.get("tokenId"),
        "serial": serial,
        "status": status,
        "terminal": terminal,
    }
    if error:
        out["error"] = str(error)
    if extra:
        out.update(extra)
    return out


def build_sequential_candidates(rows, require_psa=True):
    by_serial = {}
    for r in rows:
        sn = r.get("serial_number")
        if sn is None:
            continue
        if require_psa and str(r.get("gradingCompany") or "").upper() != "PSA":
            continue
        by_serial.setdefault(int(sn), []).append(r)
    out_rows = []
    for sn in sorted(by_serial):
        if sn + 1 not in by_serial:
            continue
        for a in by_serial[sn]:
            for b in by_serial[sn + 1]:
                tags = relation_tags(a, b)
                strength = "strong" if len(tags) >= 3 else "medium" if tags else "weak"
                out_rows.append({
                    "serial_a": a.get("serial_raw"), "serial_b": b.get("serial_raw"),
                    "serial_number_a": sn, "serial_number_b": sn + 1, "serial_gap": 1,
                    "tokenId_a": a.get("tokenId"), "tokenId_b": b.get("tokenId"),
                    "name_a": a.get("name"), "name_b": b.get("name"),
                    "setName_a": a.get("setName"), "setName_b": b.get("setName"),
                    "grade_a": a.get("grade"), "grade_b": b.get("grade"),
                    "ask_total_usdt": (a.get("ask_usdt") or 0) + (b.get("ask_usdt") or 0),
                    "fmv_total_usd": (a.get("fmv_usd") or 0) + (b.get("fmv_usd") or 0),
                    "special_tags": ";".join(tags), "candidate_strength": strength,
                    "risk_note": "Sequential Cert SBT 最终是否有效，需要 Renaiss team 验证。",
                    "source": "Renaiss CLI marketplace attributes.Serial",
                })
    return out_rows


def cmd_sequential_scan(args):
    rows = [r for r in read_jsonl(args.cards) if r.get("serial_number") is not None]
    out_rows = build_sequential_candidates(rows, require_psa=not args.allow_non_psa)
    write_csv(args.out, out_rows, SEQUENTIAL_FIELDNAMES)
    print(json.dumps({"out": args.out, "candidates": len(out_rows)}, ensure_ascii=False, indent=2))


def build_arbitrage_candidates(rows):
    out_rows = []
    for r in rows:
        ask = r.get("ask_usdt")
        if not ask or ask <= 0:
            continue
        if is_expired_ask(r.get("askExpiresAt")):
            continue
        top = r.get("top_offer_usdt")
        fmv = r.get("fmv_usd")
        net_offer = top * (1 - FEE_RATE) if top else None
        direct_profit = net_offer - ask if net_offer is not None else None
        fmv_net = fmv * (1 - FEE_RATE) if fmv else None
        fmv_spread = fmv_net - ask if fmv_net is not None else None
        positive_direct = direct_profit if direct_profit is not None and direct_profit > 0 else None
        positive_fmv = fmv_spread if fmv_spread is not None and fmv_spread > 0 else None
        if positive_direct is None and positive_fmv is None:
            continue
        if positive_direct is not None and (positive_fmv is None or positive_direct >= positive_fmv):
            opportunity_type = "top_offer_arbitrage"
            ranking_value = positive_direct
        else:
            opportunity_type = "fmv_discount"
            ranking_value = positive_fmv
        out_rows.append({
            "tokenId": r.get("tokenId"), "name": r.get("name"), "ask_usdt": ask,
            "top_offer_usdt": top, "top_offer_net_usdt": net_offer,
            "direct_arbitrage_profit": direct_profit,
            "direct_arbitrage_profit_pct": (direct_profit / ask) if direct_profit is not None else None,
            "fmv_usd": fmv, "fmv_net_usd": fmv_net,
            "fmv_spread_net": fmv_spread,
            "fmv_spread_pct": (fmv_spread / ask) if fmv_spread is not None else None,
            "last_sale_usdt": r.get("last_sale_usdt"), "fee_rate": FEE_RATE,
            "opportunity_type": opportunity_type,
            "ranking_value": ranking_value,
            "risk_notes": "2% seller fee included; top offer may expire or have unknown acceptance conditions; FMV is not executable liquidity; refresh data before trading.",
            "source": r.get("source") or "Renaiss CLI",
        })
    out_rows.sort(key=lambda x: x.get("ranking_value") or 0, reverse=True)
    return out_rows


def cmd_arbitrage_scan(args):
    rows = read_jsonl(args.cards)
    out_rows = build_arbitrage_candidates(rows)
    write_csv(args.out, out_rows, ARBITRAGE_FIELDNAMES)
    print(json.dumps({"out": args.out, "candidates": len(out_rows), "fee_rate": FEE_RATE}, ensure_ascii=False, indent=2))


def index_credentials_available():
    return bool(os.getenv("RENAISS_INDEX_API_KEY") and os.getenv("RENAISS_INDEX_API_SECRET"))


def renaiss_index_get(path, timeout=60, retries=2, retry_delay=1.0):
    base = os.getenv("RENAISS_INDEX_API_BASE", "https://api.renaissos.com").rstrip("/")
    headers = {"Accept": "application/json", "User-Agent": "RenaissCollectorAssistant/0.1"}
    if os.getenv("RENAISS_INDEX_API_KEY") and os.getenv("RENAISS_INDEX_API_SECRET"):
        headers["X-Api-Key"] = os.getenv("RENAISS_INDEX_API_KEY")
        headers["X-Api-Secret"] = os.getenv("RENAISS_INDEX_API_SECRET")
    last_error = None
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(base + path, headers=headers)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw = resp.read().decode()
                payload = json.loads(raw) if raw else {}
                return {"status": resp.status, "rate_limit_remaining": resp.headers.get("X-RateLimit-Remaining"), "data": payload}
        except urllib.error.HTTPError as e:
            body = e.read().decode(errors="replace")[:500] if hasattr(e, "read") else ""
            last_error = RuntimeError(f"Renaiss OS Index API HTTP {e.code}: {body or e.reason}")
            if e.code not in {429, 500, 502, 503, 504} or attempt >= retries:
                raise last_error
        except Exception as e:
            last_error = e
            if attempt >= retries:
                raise
        time.sleep(retry_delay * (2 ** attempt))
    if last_error:
        raise last_error
    raise RuntimeError("Renaiss OS Index API request failed")


def graded_index_lookup(cert, *, retries=2):
    normalized = normalize_cert(cert)
    if not normalized:
        return {"cert": cert, "normalized_cert": None, "found": False, "error": "invalid_cert"}
    path = "/v1/graded/" + urllib.parse.quote(normalized)
    response = renaiss_index_get(path, retries=retries)
    data = response.get("data") or {}
    response_cert = normalize_cert(data.get("cert") or data.get("certNumber") or ((data.get("collectible") or {}).get("cardIdentifier")))
    exact = response_cert == normalized
    explicit_found = data.get("found")
    found = (bool(explicit_found) if explicit_found is not None else bool(data.get("card") or data.get("collectible"))) and exact
    return {
        "query_cert": cert,
        "normalized_cert": normalized,
        "response_cert": response_cert,
        "exact_cert_match": exact,
        "found": found,
        "data": data,
        "rate_limit_remaining": response.get("rate_limit_remaining"),
    }


def graded_price_candidate(card, lookup):
    if not lookup.get("found") or not lookup.get("exact_cert_match"):
        return None
    data = lookup.get("data") or {}
    card_data = data.get("card") or {}
    collectible = data.get("collectible") or {}
    price_cents = card_data.get("priceUsdCents")
    if price_cents is None:
        return None
    return {
        "priceUsdCents": price_cents,
        "confidence": card_data.get("confidence"),
        "lastSaleAt": card_data.get("lastSaleAt"),
        "href": card_data.get("href"),
        "name": card_data.get("name"),
        "gradeLabel": card_data.get("gradeLabel") or data.get("gradeLabel"),
        "grade": card_data.get("grade") or data.get("grade"),
        "company": card_data.get("company") or data.get("company") or collectible.get("gradingCompany"),
        "cert": lookup.get("response_cert"),
        "exact_cert_match": lookup.get("exact_cert_match"),
    }


def build_index_arbitrage_candidates(rows, *, search_limit=3, min_spread=0.0, delay=0.25, max_cards=0, retries=2, skip_keys=None):
    """Build Index arbitrage candidates using exact /v1/graded/{cert} matching.

    `search_limit` is kept for backward-compatible tests/CLI signatures, but exact
    graded lookup is intentionally used to avoid matching the wrong card.
    Returns candidates, searched_count, error_rows, and per-card state rows.
    """
    out_rows = []
    errors = []
    states = []
    searched = 0
    skip_keys = skip_keys or set()
    cards = rows[:max_cards] if max_cards else rows
    for r in cards:
        ask = r.get("ask_usdt")
        serial = r.get("serial_raw") or r.get("serial_number")
        token_id = r.get("tokenId")
        key = index_state_key(token_id, serial)
        if key in skip_keys:
            continue
        if not ask or ask <= 0 or not serial:
            states.append(build_index_state(r, "invalid_input", terminal=True, error="missing ask_usdt or serial"))
            continue
        if is_expired_ask(r.get("askExpiresAt")) or r.get("ask_is_expired_at_collection") is True:
            err = {"tokenId": token_id, "serial": serial, "error": "expired_ask_skipped"}
            errors.append(err)
            states.append(build_index_state(r, "expired", terminal=True, error="expired_ask_skipped"))
            continue
        try:
            lookup = graded_index_lookup(serial, retries=retries)
            searched += 1
            best = graded_price_candidate(r, lookup)
            if not best:
                status = "no_exact_match" if not lookup.get("exact_cert_match") or not lookup.get("found") else "no_price"
                err = {
                    "tokenId": token_id,
                    "serial": serial,
                    "error": "no_exact_index_price",
                    "status": status,
                    "found": lookup.get("found"),
                    "exact_cert_match": lookup.get("exact_cert_match"),
                    "response_cert": lookup.get("response_cert"),
                }
                errors.append(err)
                states.append(build_index_state(r, status, terminal=True, error="no_exact_index_price", extra={
                    "exact_cert_match": lookup.get("exact_cert_match"),
                    "response_cert": lookup.get("response_cert"),
                }))
                continue
            price_usd = float(best.get("priceUsdCents")) / 100.0
            net = price_usd * (1 - FEE_RATE)
            spread = net - float(ask)
            if spread < min_spread:
                states.append(build_index_state(r, "no_spread", terminal=True, extra={
                    "index_price_usd": price_usd,
                    "index_spread_usdt": spread,
                    "index_confidence": best.get("confidence"),
                    "exact_cert_match": best.get("exact_cert_match"),
                    "index_response_cert": best.get("cert"),
                }))
                continue
            candidate = {
                "tokenId": token_id, "name": r.get("name"),
                "serial_raw": r.get("serial_raw"), "serial_number": r.get("serial_number"),
                "ask_usdt": ask, "index_query": lookup.get("normalized_cert") or str(serial),
                "index_result_count": 1, "index_price_usd": price_usd,
                "index_price_net_usd": net, "index_spread_usdt": spread,
                "index_spread_pct": spread / float(ask) if ask else None,
                "index_confidence": best.get("confidence"),
                "index_last_sale_at": best.get("lastSaleAt"), "index_href": best.get("href"),
                "index_match_name": best.get("name"), "index_match_grade": best.get("gradeLabel") or best.get("grade"),
                "index_match_company": best.get("company"), "fee_rate": FEE_RATE,
                "exact_cert_match": best.get("exact_cert_match"),
                "index_response_cert": best.get("cert"),
                "ranking_value": spread,
                "risk_notes": "Renaiss OS Index price is a benchmark, not executable liquidity; exact cert match required; 2% seller fee included; refresh marketplace and index data before trading.",
                "source": "Renaiss marketplace + Renaiss OS Index API /v1/graded exact cert lookup",
            }
            out_rows.append(candidate)
            states.append(build_index_state(r, "candidate", terminal=True, extra={
                "index_price_usd": price_usd,
                "index_spread_usdt": spread,
                "index_confidence": best.get("confidence"),
                "exact_cert_match": best.get("exact_cert_match"),
                "index_response_cert": best.get("cert"),
            }))
        except Exception as exc:
            errors.append({"tokenId": token_id, "serial": serial, "error": str(exc), "error_type": type(exc).__name__})
            states.append(build_index_state(r, "transient_error", terminal=False, error=str(exc), extra={"error_type": type(exc).__name__}))
        if delay:
            time.sleep(delay)
    out_rows.sort(key=lambda x: x.get("ranking_value") or 0, reverse=True)
    return out_rows, searched, errors, states


def cmd_index_arbitrage_scan(args):
    if args.require_key and not index_credentials_available():
        raise SystemExit("Renaiss OS Index API key/secret required for index-arbitrage-scan. Fill .env or pass --allow-public-index for a tiny public-quota smoke test.")
    rows = read_jsonl(args.cards)
    errors_out = args.errors_out or (args.out + ".errors.jsonl")
    state_out = args.state_out or (args.out + ".state.jsonl")
    skip_keys = read_terminal_state_keys(state_out) if args.resume else set()
    if args.resume:
        skip_keys |= read_csv_key_set(args.out, "tokenId", "serial_raw")
    if not args.resume:
        write_csv(args.out, [], INDEX_ARBITRAGE_FIELDNAMES)
        Path(errors_out).parent.mkdir(parents=True, exist_ok=True)
        Path(errors_out).write_text("", encoding="utf-8")
        Path(state_out).parent.mkdir(parents=True, exist_ok=True)
        Path(state_out).write_text("", encoding="utf-8")
    out_rows, searched, errors, states = build_index_arbitrage_candidates(
        rows,
        search_limit=args.search_limit,
        min_spread=args.min_spread,
        delay=args.inter_request_delay,
        max_cards=args.max_cards,
        retries=args.retries,
        skip_keys=skip_keys,
    )
    append_csv_rows(args.out, out_rows, INDEX_ARBITRAGE_FIELDNAMES)
    if errors:
        append_jsonl(errors_out, errors)
    if states:
        append_jsonl(state_out, states)
    print(json.dumps({
        "out": args.out,
        "errors_out": errors_out,
        "state_out": state_out,
        "cards_input": len(rows),
        "cards_skipped_by_resume": len(skip_keys),
        "cards_searched": searched,
        "candidates": len(out_rows),
        "errors": len(errors),
        "states_written": len(states),
        "fee_rate": FEE_RATE,
        "requires_index_api_key": args.require_key,
        "match_mode": "exact_/v1/graded_cert",
    }, ensure_ascii=False, indent=2))


def read_watchlist(path):
    token_ids = []
    seen = set()
    p = Path(path)
    if not p.exists():
        raise SystemExit(f"watchlist file not found: {path}")
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        tid = None
        if line.startswith("{"):
            try:
                row = json.loads(line)
                tid = row.get("tokenId") or parse_token_id(str(row.get("card_url", "")))
            except Exception:
                tid = parse_token_id(line)
        else:
            # Works for plain tokenId, Renaiss card URL, or simple CSV first cell.
            tid = parse_token_id(line.split(",")[0]) or parse_token_id(line)
        if tid and tid not in seen:
            seen.add(tid); token_ids.append(tid)
    return token_ids


def cmd_watchlist_snapshot(args):
    token_ids = []
    if args.watchlist:
        token_ids.extend(read_watchlist(args.watchlist))
    for value in args.token_id or []:
        tid = parse_token_id(value)
        if tid:
            token_ids.append(tid)
    token_ids = list(dict.fromkeys(token_ids))
    if args.limit:
        token_ids = token_ids[:args.limit]
    if not token_ids:
        raise SystemExit("No tokenIds found in watchlist.")
    results = asyncio.run(run_card_detail_batch(token_ids, concurrency=1, inter_request_delay=args.inter_request_delay, retries=args.retries, timeout=args.timeout, method=args.method))
    rows = []
    collected_at = utc_now()
    for r in results:
        if "error" in r:
            rows.append({"tokenId": r.get("tokenId"), "error": r.get("error"), "error_status": r.get("error_status"), "collected_at_utc": collected_at, "source": r.get("method")})
        else:
            row = normalize_detail(r, collected_at)
            row["watchlist_snapshot_at_utc"] = collected_at
            rows.append(row)
    write_jsonl(args.out, rows)
    print(json.dumps({"out": args.out, "token_ids": len(token_ids), "rows": len(rows), "collected_at_utc": collected_at}, ensure_ascii=False, indent=2))

def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("check").set_defaults(func=cmd_check)
    e = sub.add_parser("extract-token-id"); e.add_argument("value"); e.set_defaults(func=cmd_extract_token)
    m = sub.add_parser("marketplace-snapshot")
    m.add_argument("--listed", action="store_true"); m.add_argument("--grading"); m.add_argument("--category"); m.add_argument("--search")
    m.add_argument("--limit", type=int, default=100); m.add_argument("--offset", type=int, default=0); m.add_argument("--out", required=True)
    m.set_defaults(func=cmd_marketplace_snapshot)
    d = sub.add_parser("card-details")
    d.add_argument("--input", required=True); d.add_argument("--out", required=True)
    d.add_argument("--method", choices=["auto", "api", "cli"], default=os.getenv("RENAISS_CARD_DETAIL_METHOD", "auto"))
    d.add_argument("--api-threshold", type=int, default=env_int("RENAISS_CARD_DETAIL_API_THRESHOLD", 10), help="auto mode uses API when token count is above this threshold")
    d.add_argument("--concurrency", type=int, default=None)
    d.add_argument("--batch-size", type=int, default=None)
    d.add_argument("--inter-request-delay", type=float, default=None)
    d.add_argument("--batch-cooldown", type=float, default=None)
    d.add_argument("--forbidden-cooldown", type=float, default=None)
    d.add_argument("--max-forbidden-per-batch", type=int, default=env_int("RENAISS_CARD_DETAIL_MAX_FORBIDDEN_PER_BATCH", 1))
    d.add_argument("--retries", type=int, default=None)
    d.add_argument("--timeout", type=int, default=None)
    d.add_argument("--limit", type=int, default=0, help="Optional test limit; 0 means all tokenIds")
    d.add_argument("--no-resume", dest="resume", action="store_false", default=True)
    d.add_argument("--no-retry-errors", dest="retry_errors", action="store_false", default=True)
    d.set_defaults(func=cmd_card_details)
    s = sub.add_parser("sequential-scan"); s.add_argument("--cards", required=True); s.add_argument("--out", required=True); s.add_argument("--allow-non-psa", action="store_true", help="override PSA-only default for debugging/custom scans"); s.set_defaults(func=cmd_sequential_scan)
    a = sub.add_parser("arbitrage-scan"); a.add_argument("--cards", required=True); a.add_argument("--out", required=True); a.set_defaults(func=cmd_arbitrage_scan)
    ia = sub.add_parser("index-arbitrage-scan", help="Compare Renaiss marketplace ask with Renaiss OS Index benchmark price using attributes.Serial")
    ia.add_argument("--cards", required=True); ia.add_argument("--out", required=True)
    ia.add_argument("--search-limit", type=int, default=3)
    ia.add_argument("--min-spread", type=float, default=0.0)
    ia.add_argument("--inter-request-delay", type=float, default=0.35)
    ia.add_argument("--max-cards", type=int, default=0, help="optional cap for smoke tests; 0 means all eligible cards")
    ia.add_argument("--errors-out", help="JSONL file for per-card Index API errors/skips; default is OUT.errors.jsonl")
    ia.add_argument("--state-out", help="JSONL checkpoint state for every processed card; default is OUT.state.jsonl")
    ia.add_argument("--resume", action="store_true", help="append to existing output and skip tokenId+serial pairs with terminal state")
    ia.add_argument("--retries", type=int, default=2, help="per-card Index API retry count for 429/5xx/network failures")
    ia.add_argument("--allow-public-index", dest="require_key", action="store_false", default=True, help="allow public 10/day Index API quota for tiny smoke tests")
    ia.set_defaults(func=cmd_index_arbitrage_scan)
    wl = sub.add_parser("watchlist-snapshot", help="Snapshot selected Renaiss cards for report-only watchlist monitoring")
    wl.add_argument("--watchlist"); wl.add_argument("--token-id", action="append")
    wl.add_argument("--out", required=True); wl.add_argument("--method", choices=["api", "cli"], default="api")
    wl.add_argument("--inter-request-delay", type=float, default=1.0); wl.add_argument("--retries", type=int, default=1); wl.add_argument("--timeout", type=int, default=120); wl.add_argument("--limit", type=int, default=0)
    wl.set_defaults(func=cmd_watchlist_snapshot)
    args = p.parse_args(); args.func(args)

if __name__ == "__main__":
    main()
