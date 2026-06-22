# YT Strategy Agent

A 24/7 system that watches a list of YouTube channels and turns the last 5 videos from each into a living trading-strategy document — automatically updated as new videos drop.

For every channel you watch, you get:
- **strategy.md** — the deduced strategy in plain English
- **rules.json** — structured buy rules, sell rules, risk notes, timing notes
- **changelog.md** — append-only log of when the strategy shifts
- **trades.md** — executed trades the host called out
- **videos/<id>.md** — per-video extracted notes + transcript

Plus an **email alert** to your inbox (sent from your own Gmail) whenever:
- a new video drops
- the deduced strategy shifts
- a new trade is called out

Newer videos are weighted more heavily, similar rules are grouped automatically, and strategy changes get flagged the moment they happen.

## Deployment target

This fork is customized for:

- Linux workstations and servers
- this PC directly
- other operator machines on the same Tailscale network
- optional systemd background service deployment

It is no longer treated as macOS-only.

## Quick start on Linux

1. Create a virtualenv:
   - `python3 -m venv .venv`
   - `. .venv/bin/activate`
2. Install dependencies:
   - `pip install -U pip`
   - `pip install -r requirements.txt`
3. Copy config template:
   - `cp .env.example .env`
4. Fill in:
   - `ANTHROPIC_API_KEY`
   - `APIFY_TOKEN` if using Apify
   - YouTube OAuth client secret path / file
   - SMTP settings only if you want email alerts
5. Run a one-time auth flow:
   - `python auth.py`
6. Test one pass:
   - `python ingest.py --once`
7. Run the watcher:
   - `python watcher.py`

## Runtime behavior in this fork

- model is configurable through `.env`
- transcript provider supports `auto`, `apify`, or `youtube`
- email alerts can be disabled with `YT_EMAIL_ENABLED=false`
- state, db, token, logs, and output directories are configurable
- logs write both to stdout and `runtime/logs/watcher.log`

## Tailscale notes

This repo itself does not require Tailscale to function, but it is suitable for operators on the same Tailscale network because:

- runtime paths are explicit and Linux-friendly
- no macOS-specific bootstrap assumptions remain
- you can keep identical repo/layout across multiple Tailscale-connected PCs
- optional metadata fields exist in `.env` for operator labeling

Recommended pattern:

- clone this repo onto each authorized Tailscale machine
- keep secrets local on each machine
- keep generated channel outputs in the configured runtime path
- use systemd on always-on machines

## Service deployment

Systemd unit provided at:

- `scripts/watcher.service`

Default fork paths expect:

- repo: `/srv/ai-hub/workspaces/yt-strategy-agent`
- env file: `/srv/ai-hub/workspaces/yt-strategy-agent/.env`
- venv: `/srv/ai-hub/workspaces/yt-strategy-agent/.venv`

## Customization priorities already applied in this fork

- Linux-first paths
- configurable runtime settings
- configurable model name
- transcript fallback support
- optional email notifications
- structured logging

## What it costs

- **Hostinger KVM 2 VPS:** ~£6/month — [get your account here](https://www.hostinger.com/uk?REFERRALCODE=EGBLEWISRZT6)
- **Anthropic API:** ~£0.10–£0.50/month for typical use
- **YouTube Data API:** free
- **Apify** (transcript fetcher): a few pence/month — [sign up here](https://apify.com?fpr=3ly3yd)
- **Email alerts:** free — sent from your own Gmail

## How it works under the hood

```
every 10 min:
  for each channel in channels.yaml:
    fetch latest 5 video IDs
    for any new video:
      pull transcript
      Claude extracts strategy / rules / risk / timing / executed trades
      detect strategy shifts vs prior state → changelog
      re-merge rolling window with recency weighting
      group similar rules via embedding similarity
```

### Recency weighting

| Position in window | Weight |
|---|---|
| Most recent | 1.00 |
| -1 | 0.70 |
| -2 | 0.50 |
| -3 | 0.35 |
| -4 | 0.25 |

Effective confidence = `mean(confidence × weight)` across appearances. Rules below 0.30 are dropped.

### Strategy change detection

A shift is logged if:
- a new rule contradicts an existing high-confidence rule
- the strategy summary moves >0.35 in semantic distance
- Claude flags `strategy_shift.changed = true`

## Repo layout

```
auth.py              OAuth flow
watcher.py           Main 10-min poll loop
ingest.py            Pull transcript + extract + merge
extract.py           Claude prompt + JSON schema
weighting.py         Recency weighting + similarity grouping
change_detect.py     Strategy-shift detection
store.py             SQLite + markdown IO
notify.py            Email sender (Gmail SMTP)
transcript.py        Apify transcript fetcher
settings.py          Runtime configuration
logging_utils.py     Logging setup
channels.yaml        Channels to watch (you edit this)
scripts/
  bootstrap_vps.sh   One-shot Linux VPS bootstrap
  watcher.service    systemd unit
tools/
  resolve_channel.py Handle/URL → channel ID
runtime/channels/<handle>/ Generated docs live here by default
```

## License

MIT.
