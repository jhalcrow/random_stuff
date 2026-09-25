"""Fetching pages: plain HTTP first, a headless browser when a site demands it.

Most Atlanta shops worth watching (Tower, Green's, Mac's, Brookhaven Bottle
Shop, MetroBottle) run on City Hive behind a Cloudflare challenge that plain
HTTP clients cannot pass, so those sources use Playwright's Chromium.
"""

import logging

import requests
from bs4 import BeautifulSoup

log = logging.getLogger(__name__)

USER_AGENT = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/140.0 Safari/537.36")
TIMEOUT = 30
NOISE_TAGS = ["script", "style", "noscript", "nav", "header", "footer", "svg"]


class FetchError(Exception):
    pass


class Blocked(FetchError):
    """The site answered with a bot challenge instead of content."""


def looks_blocked(status, headers, body):
    if status in (403, 429, 503):
        if headers.get("cf-mitigated") or "Just a moment" in body[:3000]:
            return True
        if "Access to this page has been denied" in body[:5000]:  # PerimeterX
            return True
    return False


_session = None


def http_get(url):
    global _session
    if _session is None:
        _session = requests.Session()
        _session.headers.update({"User-Agent": USER_AGENT,
                                 "Accept-Language": "en-US,en;q=0.9"})
    try:
        r = _session.get(url, timeout=TIMEOUT)
    except requests.RequestException as e:
        raise FetchError(f"{url}: {e}") from e
    if looks_blocked(r.status_code, r.headers, r.text):
        raise Blocked(f"{url}: bot challenge (HTTP {r.status_code})")
    if r.status_code >= 400:
        raise FetchError(f"{url}: HTTP {r.status_code}")
    return r


def html_items(html, base_url, selector=None):
    """Turn HTML into (text, link) items.

    With a CSS selector, each matching element is one item. Otherwise every
    visible line of text is an item, with page chrome (nav/header/footer)
    stripped so menus don't produce matches.
    """
    soup = BeautifulSoup(html, "html.parser")
    if selector:
        items = []
        for el in soup.select(selector):
            a = el if el.name == "a" else (el.find_parent("a") or el.find("a"))
            href = a.get("href") if a else None
            link = requests.compat.urljoin(base_url, href) if href else base_url
            items.append((el.get_text(" ", strip=True), link))
        return items
    for tag in soup(NOISE_TAGS):
        tag.decompose()
    return [(line, base_url) for line in text_lines(soup.get_text("\n"))]


def text_lines(text):
    return [" ".join(l.split()) for l in text.splitlines() if l.strip()]


class Browser:
    """Lazily-started headless Chromium shared by every source in a run."""

    def __init__(self):
        self._pw = None
        self._browser = None
        self._page = None

    def _start(self):
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as e:
            raise FetchError("playwright is not installed; run "
                             "`pip install playwright && playwright install chromium`") from e
        self._pw = sync_playwright().start()
        self._browser = self._pw.chromium.launch(
            headless=True, args=["--disable-blink-features=AutomationControlled"])
        ctx = self._browser.new_context(user_agent=USER_AGENT, locale="en-US",
                                        viewport={"width": 1280, "height": 1600})
        self._page = ctx.new_page()

    def items(self, url, selector=None, wait_ms=4000):
        if self._page is None:
            self._start()
        pg = self._page
        try:
            pg.goto(url, wait_until="domcontentloaded", timeout=60000)
            # Wait out a Cloudflare interstitial if we landed on one.
            for _ in range(20):
                if "Just a moment" not in pg.title():
                    break
                pg.wait_for_timeout(1000)
            else:
                raise Blocked(f"{url}: stuck on bot challenge")
            try:
                pg.wait_for_load_state("networkidle", timeout=15000)
            except Exception:
                pass  # analytics beacons can keep the network busy forever
            if selector:
                try:
                    pg.wait_for_selector(selector, timeout=wait_ms)
                except Exception:
                    pass  # zero results is a valid answer
                return pg.evaluate(
                    """sel => [...document.querySelectorAll(sel)].map(el => {
                         const a = el.closest('a[href]') ||
                                   el.closest('ch-product-item, article, li, .product')?.querySelector('a[href]');
                         const tile = el.closest('ch-product-item, article, li, .product') || el.parentElement;
                         return [el.innerText.trim(), a ? a.href : location.href, tile.innerText];
                       })""", selector)
            pg.wait_for_timeout(wait_ms)
            text = pg.evaluate(
                """tags => { document.querySelectorAll(tags.join(',')).forEach(e => e.remove());
                             return document.body.innerText; }""", NOISE_TAGS)
            return [(line, pg.url) for line in text_lines(text)]
        except FetchError:
            raise
        except Exception as e:
            raise FetchError(f"{url}: {e}") from e

    def close(self):
        if self._browser:
            self._browser.close()
        if self._pw:
            self._pw.stop()
