#!/usr/bin/env python3
"""构建精选列表、发现上游候选、检测视频。检测不会自动换源。"""
import argparse
import collections
import concurrent.futures
import datetime
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import time
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
JAPAN_CHANNELS = {
    "NHK G": r"NHK\s*(?:G|総合|综合)|JOAK",
    "NHK E": r"NHK\s*(?:E|Eテレ|教育)|JOAB",
    "NTV": r"(?:NTV|日テレ|日本テレビ|Nippon TV)",
    "TBS": r"TBS|JORX",
    "Fuji": r"Fuji|フジ|富士|JOCX",
    "TV Asahi": r"(?:TV Asahi|テレビ朝日|朝日)|JOEX",
    "TV Tokyo": r"(?:TV Tokyo|テレビ東京|テレ東)|JOTX",
    "TOKYO MX": r"(?:TOKYO\s*MX|東京MX|tokyo_mx)",
}
HIGH_RISK_RELAYS = (
    "ayaka-proxy.onrender.com",
    "akariko.netgenx.site",
    "naori-test.netgenx.site",
    "proxyv2.utako.moe",
    "stream01.willfonk.com",
    "ythls-v3.onrender.com",
)


def load_channels():
    data = json.loads((ROOT / "channels.json").read_text())
    seen = set()
    for c in data["channels"]:
        if c["id"] in seen:
            raise ValueError("重复频道 ID：" + c["id"])
        seen.add(c["id"])
        u = urllib.parse.urlsplit(c["url"])
        if u.scheme not in ("http", "https") or not u.hostname or u.username:
            raise ValueError("频道地址必须是没有登录凭据的 HTTP(S) URL")
        for key in ("name", "group", "id", "url"):
            if any(ch in c[key] for ch in ("\r", "\n", '"')):
                raise ValueError("频道字段含无效控制字符")
    return data


def build(check=False):
    data = load_channels()
    lines = ["#EXTM3U", "# Personal curated playlist. See README.md for validation and limitations."]
    for c in data["channels"]:
        lines.extend([
            f'#EXTINF:-1 tvg-id="{c["id"]}" tvg-name="{c["name"]}" '
            f'group-title="{c["group"]}",{c["name"]}', c["url"],
        ])
    text = "\n".join(lines) + "\n"
    path = ROOT / "playlist.m3u"
    if check:
        if not path.exists() or path.read_text() != text:
            raise ValueError("playlist.m3u 与 channels.json 不一致，请运行 build")
    else:
        path.write_text(text)
    print(f"精选列表：{len(data['channels'])} 条线路")


def opener():
    # 不继承 Mac 的其他代理，避免把其他出口误当作 Home。
    proxy = os.environ.get("IPTV_HTTP_PROXY")
    return urllib.request.build_opener(urllib.request.ProxyHandler(
        {"http": proxy, "https": proxy} if proxy else {}))


def fetch(client, url, limit=8_000_000):
    started = time.monotonic()
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with client.open(request, timeout=15) as r:
        body = r.read(limit + 1)
        if len(body) > limit:
            raise ValueError("响应超过读取上限")
        return body, r.geturl(), round(time.monotonic() - started, 3)


def parse_m3u(text):
    rows, info = [], None
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("#EXTINF:"):
            info = line
        elif line.startswith(("http://", "https://")) and info:
            rows.append({"name": info.rsplit(",", 1)[-1], "url": line, "metadata": info})
            info = None
    return rows


def source_coverage(body):
    text = body.decode() if isinstance(body, bytes) else body
    rows = parse_m3u(text)
    coverage = {
        name: sum(bool(re.search(pattern, row["name"], re.I)) for row in rows)
        for name, pattern in JAPAN_CHANNELS.items()
    }
    hosts = collections.Counter(urllib.parse.urlsplit(row["url"]).hostname for row in rows)
    hosts = {host: count for host, count in hosts.items() if host}
    risky = sum(count for host, count in hosts.items()
                if any(relay in host for relay in HIGH_RISK_RELAYS))
    return rows, coverage, hosts, risky


def curl_fetch(url, limit=12_000_000):
    curl = shutil.which("curl")
    if not curl:
        raise ValueError("缺少 curl，无法执行基线审计")
    result = subprocess.run(
        [curl, "-fsSL", "--connect-timeout", "8", "--max-time", "25",
         "--max-filesize", str(limit), "-A", "Mozilla/5.0", url],
        capture_output=True,
    )
    if result.returncode:
        raise ValueError(f"curl 读取失败（退出码 {result.returncode}）")
    return result.stdout, url


def audit(site):
    sources = json.loads((ROOT / "sources.json").read_text())
    results = []
    for source in sources:
        row = {key: source.get(key) for key in ("name", "url", "kind", "enabled", "role")}
        if not source.get("enabled", True):
            row["skipped"] = "disabled"
            results.append(row)
            continue
        try:
            body, _ = curl_fetch(source["url"])
            if not body.lstrip().startswith(b"#EXTM3U"):
                raise ValueError("上游没有返回 M3U")
            rows, coverage, hosts, risky = source_coverage(body)
            row.update({
                "ok": True,
                "entries": len(rows),
                "coverage": coverage,
                "coverage_score": sum(bool(v) for v in coverage.values())
                + sum(v > 1 for v in coverage.values()),
                "top_hosts": collections.Counter(hosts).most_common(8),
                "high_risk_relay_entries": risky,
            })
        except Exception as e:
            row.update({"ok": False, "error": safe_error(e)})
        results.append(row)
    report = {
        "checked_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "site": site,
        "scope": "First-level playlist and channel-label audit; not playback, continuity, or content verification.",
        "sources": results,
    }
    save_report("baseline-audit.json", report)
    for row in results:
        state = "skipped" if row.get("skipped") else ("ok" if row.get("ok") else row.get("error"))
        print(f"{row['name']}: {state}", flush=True)
    return 0 if all(row.get("ok") or row.get("skipped") for row in results) else 1


def discover():
    client, results = opener(), []
    for source in json.loads((ROOT / "sources.json").read_text()):
        try:
            body, _, _ = fetch(client, source["url"])
            if not body.lstrip().startswith(b"#EXTM3U"):
                raise ValueError("上游没有返回 M3U")
            results.append({"source": source["name"], "candidates": parse_m3u(body.decode())})
        except Exception as e:
            results.append({"source": source["name"], "error": safe_error(e)})
    save_report("candidates.json", results)
    print("候选已保存到 reports/candidates.json；尚未加入精选列表。")


def safe_error(e):
    # 网络异常可能包含代理或带签名的 URL；报告只保留异常类型及 HTTP 状态。
    code = getattr(e, "code", None)
    if code:
        return f"HTTP {code}"
    if isinstance(e, ValueError):
        return str(e)
    return type(e).__name__


def media_info(body):
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        raise ValueError("缺少 ffprobe，无法确认视频，不能判为通过")
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "sample.bin"
        path.write_bytes(body)
        p = subprocess.run([ffprobe, "-v", "error", "-show_streams", "-of", "json", str(path)],
                           capture_output=True, timeout=20)
        data = json.loads(p.stdout or b"{}")
        videos = [s for s in data.get("streams", []) if s.get("codec_type") == "video"]
        if p.returncode or not videos:
            raise ValueError("响应中未识别出可播放的视频")
        v = videos[0]
        return {k: v.get(k) for k in ("codec_name", "width", "height", "r_frame_rate")}


def probe(channel):
    row = {"id": channel["id"], "name": channel["name"], "ok": False}
    try:
        client = opener()
        body, url, elapsed = fetch(client, channel["url"])
        row["playlist_seconds"] = elapsed
        for _ in range(4):
            if not body.lstrip().startswith(b"#EXTM3U"):
                # 部分频道为持续 MPEG-TS；fetch 的有界读取需要单独处理。
                raise ValueError("不是 HLS 播放列表，持续 TS 流需在清单中标记 transport=mpegts")
            text = body.decode()
            links = [x.strip() for x in text.splitlines() if x.strip() and not x.startswith("#")]
            if not links:
                raise ValueError("空播放列表")
            if "#EXT-X-STREAM-INF:" in text:
                body, url, _ = fetch(client, urllib.parse.urljoin(url, links[0]))
                continue
            if "#EXTINF:" not in text:
                raise ValueError("没有视频分片")
            durations = [float(x) for x in re.findall(r"#EXTINF:([\d.]+)", text)]
            if "#EXT-X-KEY:" in text and 'METHOD=NONE' not in text:
                raise ValueError("加密 HLS 需由播放器进一步验证")
            segments = []
            for segment in links[-3:]:
                sample, _, cost = fetch(client, urllib.parse.urljoin(url, segment))
                segments.append({"bytes": len(sample), "seconds": cost})
                video = media_info(sample)
            row.update(ok=True, video=video, segments=segments,
                       slow_segments=sum(s["seconds"] > durations[-len(segments)+i]
                                         for i, s in enumerate(segments)))
            return row
        raise ValueError("播放列表层数过多")
    except Exception as e:
        row["error"] = safe_error(e)
        return row


def probe_ts(channel):
    row = {"id": channel["id"], "name": channel["name"], "ok": False}
    try:
        client = opener()
        req = urllib.request.Request(channel["url"], headers={"User-Agent": "Mozilla/5.0"})
        started = time.monotonic()
        with client.open(req, timeout=15) as r:
            body = r.read(2_000_000)
        row.update(ok=True, video=media_info(body), bytes=len(body),
                   sample_seconds=round(time.monotonic() - started, 3))
    except Exception as e:
        row["error"] = safe_error(e)
    return row


def save_report(name, data):
    path = ROOT / "reports" / name
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")


def check(site):
    if site == "home" and not os.environ.get("IPTV_HTTP_PROXY"):
        raise ValueError("Home 检测必须显式设置 IPTV_HTTP_PROXY，不能猜测出口")
    rows = load_channels()["channels"]
    def one(c):
        # URL 的协议类型由已审阅的清单记录，不从频道名字推断。
        result = probe_ts(c) if c.get("transport") == "mpegts" else probe(c)
        print(c["name"], "通过" if result["ok"] else result.get("error"), flush=True)
        return result
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        results = list(pool.map(one, rows))
    save_report("health.json", {"checked_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                               "site": site, "proxy_explicit": bool(os.environ.get("IPTV_HTTP_PROXY")),
                               "scope": "短时视频读取；不是连续播放或频道内容审核", "channels": results})
    return 0 if all(x["ok"] for x in results) else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("build", "check", "discover", "audit"))
    parser.add_argument("--verify", action="store_true", help="只检查生成文件一致性")
    parser.add_argument("--site", default="local-unqualified", help="检测地点；home 需显式代理")
    args = parser.parse_args()
    if args.command == "build":
        build(args.verify)
    elif args.command == "discover":
        discover()
    elif args.command == "audit":
        return audit(args.site)
    else:
        return check(args.site)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, OSError) as error:
        print(safe_error(error))
        raise SystemExit(1)
