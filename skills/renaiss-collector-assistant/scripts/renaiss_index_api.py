#!/usr/bin/env python3
"""Minimal Renaiss OS Index API helper."""
import argparse, json, os, urllib.parse, urllib.request

BASE = os.getenv("RENAISS_INDEX_API_BASE", "https://api.renaissos.com").rstrip("/")
KEY = os.getenv("RENAISS_INDEX_API_KEY")
SECRET = os.getenv("RENAISS_INDEX_API_SECRET")


def req(method, path, body=None, headers=None):
    h = {"Accept": "application/json", "User-Agent": "RenaissCollectorAssistant/0.1"}
    if KEY and SECRET:
        h["X-Api-Key"] = KEY
        h["X-Api-Secret"] = SECRET
    if headers: h.update(headers)
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        h["Content-Type"] = "application/json"
    r = urllib.request.Request(BASE + path, data=data, headers=h, method=method)
    with urllib.request.urlopen(r, timeout=60) as resp:
        raw = resp.read().decode()
        try:
            payload = json.loads(raw)
        except Exception:
            payload = raw
        return {"status": resp.status, "rate_limit_remaining": resp.headers.get("X-RateLimit-Remaining"), "data": payload}


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("search"); s.add_argument("--q", required=True); s.add_argument("--limit", type=int, default=12)
    sub.add_parser("indices")
    g = sub.add_parser("graded"); g.add_argument("--cert", required=True)
    c = sub.add_parser("card-by-href"); c.add_argument("--href", required=True)
    args = p.parse_args()
    if args.cmd == "search":
        path = "/v1/search?" + urllib.parse.urlencode({"q": args.q, "limit": args.limit})
        out = req("GET", path)
    elif args.cmd == "indices":
        out = req("GET", "/v1/indices")
    elif args.cmd == "graded":
        out = req("GET", "/v1/graded/" + urllib.parse.quote(args.cert))
    elif args.cmd == "card-by-href":
        # href like /card/{game}/{set}/{card}
        parts = args.href.strip("/").split("/")
        if len(parts) != 4 or parts[0] != "card":
            raise SystemExit("href must look like /card/{game}/{set}/{card}")
        out = req("GET", f"/v1/cards/{parts[1]}/{parts[2]}/{parts[3]}")
    print(json.dumps(out, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
