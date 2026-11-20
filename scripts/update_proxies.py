#!/usr/bin/env python3
"""Read the public preview of the Telegram channel and write the latest proxies to proxies.json."""
import html, json, re, sys, urllib.request
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlparse

CHANNEL = "ProxyPeak"
LIMIT = 40
OUT = Path(__file__).resolve().parent.parent / "proxies.json"
HOST = re.compile(r"^[A-Za-z0-9.-]{1,253}$")
SECRET = re.compile(r"^[A-Za-z0-9_=+/-]{10,200}$")
FLAG = re.compile("([\U0001F1E6-\U0001F1FF]{2})")


def fetch(before=None):
    url = f"https://t.me/s/{CHANNEL}" + (f"?before={before}" if before else "")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", "replace")


def parse(page):
    items, ids = [], []
    for block in page.split("tgme_widget_message_wrap")[1:]:
        post = re.search(r'data-post="[^"/]+/(\d+)"', block)
        if not post:
            continue
        ids.append(int(post.group(1)))
        link = re.search(r'href="(tg://proxy\?[^"]+)"', block)
        if not link:
            continue
        q = parse_qs(urlparse(html.unescape(link.group(1))).query)
        server = q.get("server", [""])[0]
        port = q.get("port", [""])[0]
        secret = q.get("secret", [""])[0]
        if not (HOST.match(server) and port.isdigit() and SECRET.match(secret)):
            continue
        when = re.search(r'<time[^>]*datetime="([^"]+)"', block)
        text = html.unescape(re.sub(r"<[^>]+>", " ", block))
        flag = FLAG.search(text)
        cc = "".join(chr(ord(c) - 0x1F1E6 + 65) for c in flag.group(1)) if flag else ""
        items.append({
            "id": int(post.group(1)),
            "time": when.group(1) if when else "",
            "cc": cc,
            "server": server.rstrip("."),
            "port": int(port),
            "secret": secret,
        })
    return items, ids


def main():
    found, before = {}, None
    for _ in range(6):
        items, ids = parse(fetch(before))
        found.update({i["id"]: i for i in items})
        if len(found) >= LIMIT or not ids:
            break
        before = min(ids)
    if not found:
        sys.exit("No proxies parsed: Telegram's page structure may have changed.")
    latest = sorted(found.values(), key=lambda i: i["id"], reverse=True)[:LIMIT]
    payload = {"updated": datetime.now(timezone.utc).isoformat(timespec="seconds"), "items": latest}
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Wrote {len(latest)} proxies to {OUT}")


if __name__ == "__main__":
    main()
