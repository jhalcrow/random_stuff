"""Offline tests: python -m unittest test_watch"""

import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

import watch

CFG = watch.load_config(Path(__file__).parent / "stores.yaml")
NOW = datetime(2026, 9, 25, 12, tzinfo=timezone.utc)

RSS = b"""<?xml version="1.0"?><rss version="2.0"><channel>
<item><title>Pappy Van Winkle 15 YR Raffle OPEN February 23 &#8211; 26</title>
<link>https://example.com/pvw15/</link><guid>p5553</guid>
<description><![CDATA[<p>Pappy 15 raffle. Buy 2 store picks for entry.</p>]]></description>
<category>allocated bourbon</category></item>
<item><title>Rose season is here</title><link>https://example.com/rose/</link>
<guid>p1</guid><description>Pink wine.</description></item>
</channel></rss>"""


def src(**kw):
    return dict({"key": "Store|u", "store": "Store", "area": "", "url": "u",
                 "match": ["announcements", "bottles"]}, **kw)


def inv(name, available=True):
    return (name, "https://shop/x", None, available)


class Matching(unittest.TestCase):
    def hit(self, text, cats=("announcements", "bottles"), inventory=False):
        return watch.match(text, CFG, cats, inventory)

    def test_bottles(self):
        for name in ["W. L. Weller C.Y.P.B. Wheated Bourbon", "Blanton's Gold Edition",
                     "Blanton’s Single Barrel", "Colonel E.H. Taylor Small Batch",
                     "E H Taylor Single Barrel", "Stagg Jr. Kentucky Straight Bourbon",
                     "Old Forester Birthday Bourbon", "King Of Kentucky 12 Years Old",
                     "Old Rip Van Winkle 10 Year", "Michter's 10 Year Single Barrel Rye",
                     "Heaven Hill Heritage Collection 22 Years Old"]:
            self.assertIsNotNone(self.hit(name, ["bottles"]), name)

    def test_non_bottles(self):
        for name in ["Helenental Kellerei Zweigelt", "Taylor Fladgate 10 Year Tawny Port",
                     "Jim Beam Bourbon Whiskey", "Michter's US*1 Bourbon", "Buffalo Trace"]:
            self.assertIsNone(self.hit(name, ["bottles"]), name)

    def test_announcements(self):
        for text in ["Allocated bourbon raffle this weekend", "BTAC lottery entries open",
                     "Enter our allocation drawing"]:
            self.assertEqual(self.hit(text)[0], "announcements", text)

    def test_exclude_applies_to_inventory_only(self):
        self.assertIsNone(self.hit("Pappy Van Winkle Churchill", inventory=True))
        self.assertIsNotNone(self.hit("Pappy raffle: buy 2 glasses to enter"))


class Feed(unittest.TestCase):
    def test_rss(self):
        items = watch.feed_items(RSS)
        self.assertEqual(len(items), 2)
        text, link, guid, _ = items[0]
        self.assertIn("Pappy Van Winkle 15 YR Raffle", text)
        self.assertIn("allocated bourbon", text)
        self.assertEqual((link, guid), ("https://example.com/pvw15/", "p5553"))


class State(unittest.TestCase):
    def setUp(self):
        self.state = {"version": 1, "sources": {}}

    def run_at(self, s, items, t):
        return watch.process(s, items, self.state, CFG, t)

    def test_first_check_is_baseline_then_only_changes(self):
        s = src()
        items = watch.feed_items(RSS)
        new, base = self.run_at(s, items, NOW)
        self.assertEqual((len(new), len(base)), (0, 1))
        self.assertEqual(self.run_at(s, items, NOW + timedelta(hours=2)), ([], []))
        extra = [("Weller 12 lottery Saturday", "l", "g2", True)]
        new, _ = self.run_at(s, items + extra, NOW + timedelta(hours=4))
        self.assertEqual([h["tag"] for h in new], ["announcement"])

    def test_announcement_never_realerts(self):
        s = src()
        self.run_at(s, [], NOW)
        item = [("Pappy raffle", "l", "g", True)]
        self.assertEqual(len(self.run_at(s, item, NOW)[0]), 1)
        self.run_at(s, [], NOW + timedelta(days=3))
        self.assertEqual(self.run_at(s, item, NOW + timedelta(days=6))[0], [])

    def test_inventory_restock_and_price_changes(self):
        s = src(inventory=True, match=["bottles"])
        self.run_at(s, [], NOW)
        new, _ = self.run_at(s, [inv("Blanton's Single Barrel — $139.99")], NOW + timedelta(hours=2))
        self.assertEqual(new[0]["tag"], "in stock")
        # Price change alone is not news.
        self.assertEqual(self.run_at(s, [inv("Blanton's Single Barrel — $149.99")],
                                     NOW + timedelta(hours=4))[0], [])
        # Gone for a day, then back: alert again.
        self.run_at(s, [], NOW + timedelta(hours=6))
        new, _ = self.run_at(s, [inv("Blanton's Single Barrel — $149.99")], NOW + timedelta(hours=40))
        self.assertEqual(new[0]["tag"], "back in stock")

    def test_unavailable_ignored(self):
        s = src(inventory=True, match=["bottles"])
        self.run_at(s, [], NOW)
        self.assertEqual(self.run_at(s, [inv("Weller 12", available=False)], NOW)[0], [])

    def test_failure_alert_once_per_streak(self):
        s = src()
        alerts = [watch.record_failure(s, self.state, CFG, "boom") for _ in range(6)]
        self.assertEqual(alerts.count(True), 1)
        self.assertTrue(alerts[CFG["failure_alert_after"] - 1])
        self.run_at(s, [], NOW)
        self.assertEqual(self.state["sources"][s["key"]]["fail_streak"], 0)


class Config(unittest.TestCase):
    def test_expand(self):
        sources = list(watch.expand_sources(CFG))
        keys = [s["key"] for s in sources]
        self.assertEqual(len(keys), len(set(keys)))
        tower = [s for s in sources if s["store"].startswith("Tower") and s.get("query")]
        self.assertEqual(len(tower), len(CFG["search_terms"]))
        self.assertTrue(all(s["render"] == "browser" and s["inventory"] for s in tower))
        self.assertIn("ch-query=van+winkle", tower[0]["url"])


if __name__ == "__main__":
    unittest.main()
