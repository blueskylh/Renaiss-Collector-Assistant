#!/usr/bin/env python3
"""Minimal Renaiss OS Index API helper with structured retry/error output."""
import argparse, json, os, time, urllib.error, urllib.parse, urllib.request

try:
    from common_env import load_dotenv_files
    load_dotenv_files()
except Exception:
    pass

BASE = os.getenv("RENAISS_INDEX_API_BASE", "https://api.renaissos.com").rstrip("/")
KEY = os.getenv("RENAISS_INDEX_API_KEY")
SECRET = os.getenv("RENAISS_INDEX_API_SECRET")
RETRYABLE_HTTP = {429, 500, 502, 503, 504}


def parse_retry_after(value):
    if not value:
        return None
    try:
        return max(0.0, float(value))
    except Exception:
        return None


def decode_body(raw):
    try:
        return json.loads(raw)
    except Exception:
        return raw


def req(method, path, body=None, headers=None, *, timeout=60, retries=2, retry_delay=1.0):
    h = {"Accept": "application/json", "User-Agent": "RenaissCollectorAssistant/0.1"}
    if KEY and SECRET:
        h["X-Api-Key"] = KEY
        h["X-Api-Secret"] = SECRET
    if headers:
        h.update(headers)
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        h["Content-Type"] = "application/json"

    last_error = None
    for attempt in range(max(0, retries) + 1):
        try:
            r = urllib.request.Request(BASE + path, data=data, headers=h, method=method)
            with urllib.request.urlopen(r, timeout=timeout) as resp:
                raw = resp.read().decode()
                return {
                    "status": resp.status,
                    "rate_limit_remaining": resp.headers.get("X-RateLimit-Remaining"),
                    "data": decode_body(raw) if raw else {},
                }
        except urllib.error.HTTPError as exc:
            raw = ""
            try:
                raw = exc.read().decode(errors="replace")
            except Exception:
                pass
            last_error = {
                "status": exc.code,
                "error": raw[:1000] or str(exc.reason),
                "error_type": "HTTPError",
                "retryable": exc.code in RETRYABLE_HTTP,
                "attempts": attempt + 1,
                "rate_limit_remaining": exc.headers.get("X-RateLimit-Remaining") if exc.headers else None,
            }
            if exc.code in RETRYABLE_HTTP and attempt < retries:
                retry_after = parse_retry_after(exc.headers.get("Retry-After") if exc.headers else None)
                time.sleep(retry_after if retry_after is not None else retry_delay * (2 ** attempt))
                continue
            return last_error
        except urllib.error.URLError as exc:
            last_error = {"status": None, "error": str(exc.reason), "error_type": "URLError", "retryable": True, "attempts": attempt + 1}
            if attempt < retries:
                time.sleep(retry_delay * (2 ** attempt))
                continue
            return last_error
        except Exception as exc:
            last_error = {"status": None, "error": str(exc), "error_type": type(exc).__name__, "retryable": True, "attempts": attempt + 1}
            if attempt < retries:
                time.sleep(retry_delay * (2 ** attempt))
                continue
            return last_error
    return last_error or {"status": None, "error": "request failed", "error_type": "Unknown"}


def quote_path_segment(value):
    return urllib.parse.quote(str(value), safe="")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--retries", type=int, default=2)
    p.add_argument("--timeout", type=int, default=60)
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("search"); s.add_argument("--q", required=True); s.add_argument("--limit", type=int, default=12)
    sub.add_parser("indices")
    g = sub.add_parser("graded"); g.add_argument("--cert", required=True)
    c = sub.add_parser("card-by-href"); c.add_argument("--href", required=True)
    args = p.parse_args()
    req_kwargs = {"timeout": args.timeout, "retries": args.retries}
    if args.cmd == "search":
        path = "/v1/search?" + urllib.parse.urlencode({"q": args.q, "limit": args.limit})
        out = req("GET", path, **req_kwargs)
    elif args.cmd == "indices":
        out = req("GET", "/v1/indices", **req_kwargs)
    elif args.cmd == "graded":
        out = req("GET", "/v1/graded/" + quote_path_segment(args.cert), **req_kwargs)
    elif args.cmd == "card-by-href":
        # href like /card/{game}/{set}/{card}
        parts = args.href.strip("/").split("/")
        if len(parts) != 4 or parts[0] != "card":
            raise SystemExit("href must look like /card/{game}/{set}/{card}")
        out = req("GET", "/v1/cards/" + "/".join(quote_path_segment(p) for p in parts[1:]), **req_kwargs)
    print(json.dumps(out, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
