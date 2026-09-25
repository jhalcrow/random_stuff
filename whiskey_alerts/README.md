# whiskey_alerts

Watches Atlanta liquor stores for allocated whiskey and sends a phone or email
alert when something new appears. It looks for two kinds of news:

- **Bottles showing up for sale.** It runs site searches such as "weller",
  "blanton" and "van winkle" on the stores' web shops and alerts when a watched
  bottle is listed with Add to Cart. It alerts again if the bottle comes back
  after being gone for 24 hours.
- **Announcements.** It reads store feeds and pages for words like raffle,
  lottery, allocated, BTAC and bourbon club, and alerts once per new post.

The first check of each source is a baseline. You get one "Now watching"
message listing what already matches, and after that only changes.

## Stores

| Store | Area | What's checked |
|---|---|---|
| Tower Beer, Wine & Spirits | Buckhead / Doraville | shop search, events page |
| Green's Beverages | Ponce / Buford Hwy | shop search |
| Mac's Beer & Wine | Midtown | shop search |
| Brookhaven Bottle Shop | Brookhaven | shop search |
| MetroBottle | Atlanta | shop search, Bourbon Club page |
| Corners Fine Wine & Spirits | Peachtree Corners | blog feed (they have posted raffles there) |
| Ansley Wine Merchants | Ansley Park | bourbon and rye listings |
| Holeman & Finch Bottle Shop | Buckhead | homepage |
| Corks & Caps | Chastain Park | homepage |
| Sherlock's | Marietta / Decatur / Buckhead | events page |

The first five run on City Hive behind a Cloudflare bot check. Plain HTTP gets
a 403 there, so they are loaded in headless Chromium through Playwright.

Edit `stores.yaml` to add stores, bottles, search terms or exclusions. The
comments at the top of that file explain each field.

### What this can't see

Most Atlanta shops announce raffles and allocation drops on Instagram or to
an email list, not on their websites. Signing up is worth doing alongside this
tool:

- Holeman & Finch Whiskey Society newsletter: http://mailchi.mp/hfbottleshop/whiskeysociety
- MetroBottle bourbon newsletter and Elite Bourbon Club waitlist: https://metrobottle.com/pages/bourbonclub
- Toco Giant (Toco Hills) bourbon list: email toco.giant.bourbon@gmail.com
- Local Vine (Johns Creek) Bourbon Chasers Club: https://www.localvinestore.com/johns-creek
- Total Wine Priority Access (Pappy/BTAC lottery): https://www.totalwine.com/and-more-rewards/priority-access
- Instagram post notifications for @tocogiant, @brookhavenbottleshop,
  @metrobottle_atl, @macsbeerandwine, @hfbottleshop and @cornersatl

Instagram blocks scraping without a login, so this tool doesn't try it.

## Notifications

Set environment variables for any channels you want. Each channel that has its
variables set gets every alert.

| Channel | Variables |
|---|---|
| [ntfy](https://ntfy.sh) phone push (easiest) | `NTFY_TOPIC`, and optionally `NTFY_SERVER`, `NTFY_TOKEN` |
| Pushover | `PUSHOVER_TOKEN`, `PUSHOVER_USER` |
| Email (SMTP) | `SMTP_HOST`, `SMTP_USER`, `SMTP_PASSWORD`, `EMAIL_TO`, and optionally `SMTP_PORT` (587), `EMAIL_FROM` |
| Discord | `DISCORD_WEBHOOK_URL` |
| Slack | `SLACK_WEBHOOK_URL` |

To use ntfy, install the ntfy app and subscribe to a topic with a long random
name, such as `atl-whiskey-8f3k2q9x`. Anyone who knows the topic name can read
it. For Gmail, use an [app password](https://myaccount.google.com/apppasswords)
with `SMTP_HOST=smtp.gmail.com`.

If a source fails four runs in a row (site redesign, stricter bot check), you
get one "sources failing" message.

## Running it

### GitHub Actions (no machine needed)

`.github/workflows/whiskey-alerts.yml` runs every two hours from 7am to 7pm
Eastern, and once more at 9pm. To set it up:

1. Merge to the default branch. Scheduled workflows only run from there.
2. Under **Settings → Secrets and variables → Actions**, add `NTFY_TOPIC` (or
   another channel's variables) as repository secrets.
3. Under **Actions → whiskey-alerts → Run workflow**, tick "Only send a test
   notification" to check delivery. Then run it once without the box ticked to
   get the baseline.

State is kept in the Actions cache between runs. GitHub turns off scheduled
workflows after 60 days with no repository activity. If that happens,
re-enable it from the Actions tab.

### Locally or with cron

```sh
cd whiskey_alerts
pip install -r requirements.txt
python -m playwright install chromium
python watch.py --dry-run -v          # look without notifying or saving
NTFY_TOPIC=atl-whiskey-8f3k2q9x python watch.py --test-notify
```

Example crontab entry:

```
23 7-21/2 * * * cd ~/random_stuff/whiskey_alerts && NTFY_TOPIC=... python3 watch.py >> watch.log 2>&1
```

State goes in `state.json` next to the script. Set `--state` or
`WHISKEY_STATE` to keep it somewhere else. Use `--only tower` to check one
store. A full run takes about four minutes, and nearly all of that is the
browser searches.

## Tests

```sh
python -m unittest test_watch
```
