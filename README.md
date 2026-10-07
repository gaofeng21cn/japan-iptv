# Japan IPTV Curation

Curated Japanese IPTV playlists for a Home OpenWrt + Mihomo network and APTV. The subscription entry point is [`playlist.m3u`](playlist.m3u); [`channels.json`](channels.json) is the only source of truth for what is published.

This repository does not try to mirror every public list. It keeps the small set of channels that have passed short playback checks on the Home network, records where each stream came from, and keeps the maintenance and review steps repeatable.

## Current Playlist

| Channel | Resolution | Status |
| --- | --- | --- |
| NHK G | 1440x1080, 29.97 fps | Primary |
| TV Asahi | 960x540, 25 fps | Primary |
| TBS | 960x540, 25 fps | Primary |
| TV Tokyo | 960x540, 25 fps | Primary |
| NHK G | 960x540, 25 fps | Backup |

The current playlist has 4 channels and 5 lines. NHK E, NTV, Fuji, TOKYO MX1, and TOKYO MX2 do not have a retained primary line yet. NTV and Fuji were excluded after review because repeated frame samples stayed on stale or relay-owned advertising content.

## Use In APTV

Add this URL as a remote M3U subscription:

```text
https://raw.githubusercontent.com/gaofeng21cn/japan-iptv/main/playlist.m3u
```

Refresh the same subscription in APTV after this repository changes. GitHub only hosts the small playlist; the video bytes still come directly from the upstream servers to the player.

If the repository is private, APTV usually cannot read the raw file without GitHub authentication. Do not put a GitHub token into a subscription URL. This public repository must not contain home network credentials, proxy subscriptions, node data, cookies, or provider secrets.

## Source Baselines

The baselines are deliberately mixed. `community` means a maintained public catalog, `aggregator` means a Japanese list that combines several upstream relays, and `legacy` means an old list kept only for comparison. Run `python3 scripts/maintain.py audit` before trusting a baseline: several apparent high-coverage lists are repeated aliases of the same relay.

| Baseline | Kind | First-Level Result | Notes |
| --- | --- | --- | --- |
| [Free-TV/IPTV](https://github.com/Free-TV/IPTV) | community | 27 entries, 8/8 channel labels | Small Japanese section. The NHK E and NTV addresses returned a verification page in playback checks. |
| [iptv-org/iptv](https://github.com/iptv-org/iptv) | community | 7 entries, 2/8 channel labels | Useful for official FAST and news streams, not a complete terrestrial source. |
| [skinred78/jp-iptv-epg](https://github.com/skinred78/jp-iptv-epg) | community | 167 entries, 8/8 channel labels | The original recommendation. It contains the current NHK G 1080 line, but 107 entries share a Render relay and many return 404. Its EPG data stopped on 2026-08-18. |
| [MrKagesan/JP-IPTV](https://github.com/MrKagesan/JP-IPTV) | aggregator | 163 entries, 8/8 channel labels | Broad coverage, but several Primehome child manifests returned 403 in the Home check. |
| [rloim024/IPTV-jp](https://github.com/rloim024/IPTV-jp) | aggregator | 152 entries, 8/8 channel labels | Best nominal coverage score, but most primary lines share the same `willfonk` relay, which timed out from Home during the sample. |
| [Jsan-PC/IPTV_JP](https://github.com/Jsan-PC/IPTV_JP) | aggregator | 144 entries, 8/8 channel labels | Mostly Utako aliases. Treat repeated URLs as one upstream, not as separate fallbacks. |
| [koneMorris1625/iptvNippon](https://github.com/koneMorris1625/iptvNippon) | aggregator | 63 entries, 7/8 channel labels | Primehome-heavy. Helpful for testing that upstream without the community mirrors. |
| [DimaSvitenko2009/IPTV-JP](https://github.com/DimaSvitenko2009/IPTV-JP) | aggregator | 39 entries, 8/8 channel labels | Small, stale, and Primehome-heavy. Retained as a historical baseline only. |
| [ytpit20218/Japan-IPTV](https://github.com/ytpit20218/Japan-IPTV) | legacy | 92 entries, 8/8 channel labels | Old luongz-derived list with numeric IP streams. Requires separate Home validation. |
| [tocotoco0013/japan-iptv-m3u8](https://github.com/tocotoco0013/japan-iptv-m3u8) | legacy | 404 | Disabled. |
| [vovanlocpro/IPTV-JPN](https://github.com/vovanlocpro/IPTV-JPN) | legacy | 1 generic entry | Disabled. |

The current baseline matrix is in [`reports/baseline-audit.json`](reports/baseline-audit.json) when generated. It records first-level readability, channel-label coverage, top hosts, and high-risk relay counts. First-level success is not a playback guarantee.

## Validation

Two checks matter, and neither one alone is enough:

1. `audit` checks playlist availability and nominal channel coverage.
2. `check` reads real HLS segments or a bounded MPEG-TS sample and asks `ffprobe` whether video exists.

On 2026-10-08, the retained lines were checked through the Home OpenWrt + Mihomo exit. Each line decoded for about 90 seconds. NHK G was 1440x1080 at 29.97 fps; the other retained lines were 960x540 at 25 fps. Some connections completed only after retrying.

This is short network and decoding evidence, not Apple TV/APTV device acceptance and not proof of evening or long-term stability. A stream can advance its HLS sequence while continuing to show stale or relay-owned advertising, so content review remains a separate acceptance gate. See [`home-validation.json`](home-validation.json).

## Maintenance

Requirements: Python 3.10+ and FFmpeg `ffprobe`. The maintenance script uses only the Python standard library.

```sh
# Rebuild the subscription from channels.json
python3 scripts/maintain.py build

# Check that playlist.m3u matches channels.json
python3 scripts/maintain.py build --verify

# Audit every enabled baseline and write reports/baseline-audit.json
python3 scripts/maintain.py audit

# Read upstream candidates without changing the curated playlist
python3 scripts/maintain.py discover

# Read real video segments and identify the video stream
python3 scripts/maintain.py check --site local-unqualified
```

`check` reads the latest three HLS segments and runs `ffprobe`; for a continuous MPEG-TS channel it reads a bounded sample instead. It never deletes channels, changes sources, or overwrites the curated list.

For Home validation, provide the existing Home proxy through the private `IPTV_HTTP_PROXY` environment variable. `check --site home` refuses to label an ordinary local result as Home when that variable is missing. Verify the exit identity separately and never commit the value or upload it in a report.

GitHub Actions verifies the generated playlist and the negative playback cases on every push. A manual workflow run also performs a GitHub-hosted online check and uploads `reports/health.json`. GitHub-hosted results only find generic dead links; they do not replace Home validation.

Update flow: audit baselines, test candidates on Home, review the actual channel content and latency, edit `channels.json`, rebuild `playlist.m3u`, then commit. A stale or broken line can be rolled back from the previous Git revision and refreshed in APTV. EPG is not attached until a fresh source and matching channel IDs are available.
