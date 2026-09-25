#!/usr/bin/env python3
"""Watch Atlanta liquor stores for allocated-whiskey announcements and drops.

Each run fetches every source in stores.yaml, picks out the items (feed posts,
lines of page text, product names) that match the keyword lists, compares them
with what earlier runs saw (state.json), and sends one digest notification
covering whatever is new.

    python watch.py                 # check everything, notify, save state
    python watch.py --dry-run -v    # check everything, print, change nothing
    python watch.py --only tower    # just the stores whose name contains "tower"
    python watch.py --test-notify   # send a test message to your channels
"""

import argparse
import json
import logging
import os
import re
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml
from bs4 import BeautifulSoup

import fetch
import notify

log = logging.getLogger("whiskey")
HERE = Path(__file__).resolve().parent
PRUNE_AFTER = timedelta(days=180)
CITYHIVE_SELECTOR = "ch-product-item .ch-product-name"
PRICE = re.compile(r"\$\d[\d,]*(\.\d\d)?")
UNAVAILABLE = re.compile(r"\b(sold out|out of stock|unavailable)\b", re.I)


# ---------------------------------------------------------------- config

def load_config(path):
    with open(path) as f:
        cfg = yaml.safe_load(f)
    cfg.setdefault("realert_after_hours", 24)
    cfg.setdefault("failure_alert_after", 4)
    cfg["_patterns"] = {cat: [re.compile(p, re.I) for p in pats]
                        for cat, pats in cfg["keywords"].items()}
    cfg["_exclude"] = [re.compile(p, re.I) for p in cfg.get("exclude", [])]
    return cfg


def expand_sources(cfg):
    """Yield one fully-specified source dict per URL to fetch."""
    for store in cfg["stores"]:
        if store.get("disabled"):
            continue
        for src in store["sources"]:
            src = dict(src)
            if src["kind"] == "cityhive_search":
                base = src.pop("base").rstrip("/")
                src.update(kind="page", render="browser",
                           selector=CITYHIVE_SELECTOR,
                           url=base + "/shop/?ch-query={query}")
                src.setdefault("queries", cfg["search_terms"])
                src.setdefault("match", ["bottles"])
                src.setdefault("inventory", True)
            if src["kind"] == "lightspeed":
                src.setdefault("match", ["bottles"])
                src.setdefault("inventory", True)
            src.setdefault("match", list(cfg["_patterns"]))
            queries = src.pop("queries", None) or [None]
            for q in queries:
                s = dict(src, store=store["name"], area=store.get("area", ""))
                if q is not None:
                    s["url"] = src["url"].replace("{query}", q.replace(" ", "+"))
                    s["query"] = q
                s["key"] = f"{store['name']}|{s['url']}"
                yield s


# ---------------------------------------------------------------- sources

def get_items(src, browser):
    """Return [(text, link, fingerprint_or_None, available)] for a source."""
    kind = src["kind"]
    if kind == "feed":
        return feed_items(fetch.http_get(src["url"]).content)
    if kind == "lightspeed":
        return lightspeed_items(fetch.http_get(src["url"]).json(), src["url"])
    if kind == "page":
        selector = src.get("selector")
        render = src.get("render", "auto")
        if render != "browser":
            try:
                r = fetch.http_get(src["url"])
                return [(t, l, None, True) for t, l in
                        fetch.html_items(r.text, r.url, selector)]
            except fetch.Blocked:
                if render == "http":
                    raise
                log.info("  blocked over plain HTTP, retrying in browser")
        items = []
        for name, link, *tile in browser.items(src["url"], selector):
            tile = tile[0] if tile else ""
            price = PRICE.search(tile)
            if price and price.group(0) not in name:
                name = f"{name} — {price.group(0)}"
            items.append((name, link, None, not UNAVAILABLE.search(tile)))
        return items
    raise ValueError(f"unknown source kind {kind!r}")


def _strip_html(s):
    return " ".join(BeautifulSoup(s or "", "html.parser").get_text(" ").split())


def feed_items(xml_bytes):
    """Items from an RSS 2.0 or Atom feed."""
    root = ET.fromstring(xml_bytes)
    atom = "{http://www.w3.org/2005/Atom}"
    items = []
    for it in root.iter("item"):
        title = _strip_html(it.findtext("title"))
        desc = _strip_html(it.findtext("description"))
        cats = " ".join(c.text or "" for c in it.findall("category"))
        link = (it.findtext("link") or "").strip()
        guid = (it.findtext("guid") or link).strip()
        items.append((f"{title} — {desc} [{cats}]", link, guid, True))
    for it in root.iter(atom + "entry"):
        title = _strip_html(it.findtext(atom + "title"))
        desc = _strip_html(it.findtext(atom + "summary") or it.findtext(atom + "content"))
        link_el = it.find(atom + "link")
        link = link_el.get("href", "") if link_el is not None else ""
        guid = (it.findtext(atom + "id") or link).strip()
        items.append((f"{title} — {desc}", link, guid, True))
    return items


def lightspeed_items(data, url):
    """Products from a Lightspeed eCom category page fetched with ?format=json."""
    base = url.split("?")[0].split("/", 3)[:3]
    base = "/".join(base) + "/"
    if "collection" not in data:
        raise fetch.FetchError(f"{url}: no product list (use a leaf category URL)")
    products = data["collection"]["products"]
    products = products.values() if isinstance(products, dict) else products
    return [(p["fulltitle"], base + p["url"], f"ls:{p['id']}", bool(p.get("available")))
            for p in products]


# ---------------------------------------------------------------- matching

def fingerprint(text):
    """Normalize a line so trivial changes (price, filter counts) don't re-alert."""
    t = text.lower()
    t = PRICE.sub("", t)
    t = re.sub(r"\(\d+\)", "", t)
    t = re.sub(r"[^\w]+", " ", t)
    return t.strip()


def match(text, cfg, categories, inventory=False):
    if inventory and any(p.search(text) for p in cfg["_exclude"]):
        return None
    for cat in categories:
        for pat in cfg["_patterns"].get(cat, []):
            m = pat.search(text)
            if m:
                return cat, m.group(0)
    return None


def short(text, n=220):
    text = " ".join(text.split())
    return text if len(text) <= n else text[:n - 1] + "…"


# ---------------------------------------------------------------- state

def load_state(path):
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return {"version": 1, "sources": {}}


def save_state(state, path):
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w") as f:
        json.dump(state, f, indent=1, sort_keys=True)
    os.replace(tmp, path)


def iso(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_iso(s):
    return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


def process(src, items, state, cfg, now):
    """Record a successful fetch; return (new_hits, baseline_hits)."""
    rec = state["sources"].get(src["key"])
    first_check = rec is None
    if first_check:
        rec = state["sources"][src["key"]] = {"items": {}}
    rec["last_ok"] = iso(now)
    rec["fail_streak"] = 0
    rec.pop("fail_alerted", None)

    realert = None
    if src.get("inventory"):
        realert = timedelta(hours=src.get("realert_after_hours", cfg["realert_after_hours"]))

    new, baseline, seen_now = [], [], set()
    for text, link, fp, available in items:
        if not available:
            continue
        m = match(text, cfg, src["match"], src.get("inventory"))
        if not m:
            continue
        fp = fp or fingerprint(text)
        if not fp or fp in seen_now:
            continue
        seen_now.add(fp)
        hit = {"store": src["store"], "area": src["area"], "text": short(text),
               "link": link or src["url"], "term": m[1],
               "tag": "in stock" if src.get("inventory") else
                      "announcement" if m[0] == "announcements" else "mentioned"}
        prev = rec["items"].get(fp)
        if prev is None:
            (baseline if first_check else new).append(hit)
            prev = rec["items"][fp] = {"first_seen": iso(now), "text": short(text, 120)}
        elif realert and now - parse_iso(prev["last_seen"]) >= realert:
            hit["tag"] = "back in stock"
            new.append(hit)
        prev["last_seen"] = iso(now)

    for fp in [fp for fp, r in rec["items"].items()
               if now - parse_iso(r["last_seen"]) > PRUNE_AFTER]:
        del rec["items"][fp]
    return new, baseline


def record_failure(src, state, cfg, err):
    rec = state["sources"].setdefault(src["key"], {"items": {}})
    rec["fail_streak"] = rec.get("fail_streak", 0) + 1
    rec["last_error"] = str(err)[:300]
    if rec["fail_streak"] >= cfg["failure_alert_after"] and not rec.get("fail_alerted"):
        rec["fail_alerted"] = True
        return True
    return False


# ---------------------------------------------------------------- digest

def dedupe(hits):
    out, seen = [], set()
    for h in hits:
        k = (h["store"], fingerprint(h["text"]))
        if k not in seen:
            seen.add(k)
            out.append(h)
    return out


def format_digest(hits):
    lines, store = [], None
    for h in sorted(hits, key=lambda h: h["store"]):
        if h["store"] != store:
            store = h["store"]
            lines.append(f"\n{store}" + (f" ({h['area']})" if h["area"] else ""))
        lines.append(f"• {h['text']}  [{h['tag']}]\n  {h['link']}")
    return "\n".join(lines).strip()


def title_for(hits, prefix):
    stores = sorted({h["store"] for h in hits})
    names = ", ".join(stores[:3]) + (f" +{len(stores) - 3}" if len(stores) > 3 else "")
    return f"🥃 {prefix}: {len(hits)} at {names}"


# ---------------------------------------------------------------- main

def run(args):
    cfg = load_config(args.config)
    state_path = Path(args.state)
    state = load_state(state_path)
    now = datetime.now(timezone.utc).replace(microsecond=0)
    browser = fetch.Browser()
    sources = [s for s in expand_sources(cfg)
               if not args.only or args.only.lower() in s["store"].lower()]

    new, baseline, broken = [], [], []
    try:
        for src in sources:
            log.info("%s: %s", src["store"], src["url"])
            try:
                items = get_items(src, browser)
            except Exception as e:
                log.warning("  FAILED: %s", e)
                if record_failure(src, state, cfg, e):
                    broken.append(src)
                continue
            n, b = process(src, items, state, cfg, now)
            log.info("  %d items, %d new, %d baseline", len(items), len(n), len(b))
            for h in n + b:
                log.debug("    %s %s", "NEW" if h in n else "base", h["text"])
            new += n
            baseline += b
    finally:
        browser.close()

    new, baseline = dedupe(new), dedupe(baseline)
    if args.dry_run:
        print(format_digest(new) or "No new hits.")
        if baseline:
            print("\nFirst check of some sources; currently matching:\n" + format_digest(baseline))
        return 0

    if new:
        notify.send(title_for(new, "Whiskey alert"), format_digest(new), new[0]["link"])
    if baseline:
        notify.send(title_for(baseline, "Now watching (already listed)"),
                    "First check of these sources; this is what already matches. "
                    "You'll only hear about changes from now on.\n\n" + format_digest(baseline),
                    baseline[0]["link"])
    if broken:
        notify.send("🥃 Whiskey watch: sources failing",
                    "\n".join(f"• {s['store']}: {s['url']}\n  "
                              f"{state['sources'][s['key']]['last_error']}" for s in broken))
    save_state(state, state_path)
    log.info("done: %d new, %d baseline, %d newly broken", len(new), len(baseline), len(broken))
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", default=HERE / "stores.yaml")
    ap.add_argument("--state", default=os.environ.get("WHISKEY_STATE", HERE / "state.json"))
    ap.add_argument("--only", help="only stores whose name contains this")
    ap.add_argument("--dry-run", action="store_true", help="print, don't notify or save")
    ap.add_argument("--test-notify", action="store_true", help="send a test message")
    ap.add_argument("-v", "--verbose", action="count", default=0)
    args = ap.parse_args()
    logging.basicConfig(level=[logging.WARNING, logging.INFO, logging.DEBUG][min(args.verbose, 2)],
                        format="%(asctime)s %(levelname)s %(message)s", datefmt="%H:%M:%S")
    if args.test_notify:
        ok = notify.send("🥃 Whiskey watch test", "Notifications are working.")
        return 0 if ok else 1
    return run(args)


if __name__ == "__main__":
    sys.exit(main())
