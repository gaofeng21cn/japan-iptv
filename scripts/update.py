#!/usr/bin/env python3
"""收集公开上游，自动检查、选源并生成订阅；不需要人工审批。"""
import argparse
import concurrent.futures
import copy
import datetime
import hashlib
import json
from pathlib import Path
import re
import sys
import urllib.parse
import urllib.request

import maintain

ROOT = Path(__file__).resolve().parents[1]


def load(name, default=None):
    path = ROOT / name
    return json.loads(path.read_text()) if path.exists() else default


def normalized(name):
    name = re.sub(r"\[[^]]*\]", "", name)
    name = re.sub(r"\((?:\d+p|[SF]?HD|HD\s*\d+p)\)", "", name, flags=re.I)
    name = name.replace("(東京)", "東京").replace("（東京）", "東京")
    return re.sub(r"[\s・]", "", name).casefold()


def identify(row, targets):
    # 精确频道 ID 或别名；新闻台、海外台和子频道不靠模糊匹配混入地上波。
    metadata = row.get("metadata", "")
    match = re.search(r'tvg-id="([^"]+)"', metadata)
    for target in targets:
        if match and match.group(1) == target["id"]:
            return target
        if normalized(row["name"]) in {normalized(x) for x in target["aliases"]}:
            return target
    return None


def valid_url(url):
    u = urllib.parse.urlsplit(url)
    return (u.scheme in ("http", "https") and bool(u.hostname)
            and u.username is None and not any(c in url for c in '\r\n"'))


def family(url):
    host = urllib.parse.urlsplit(url).hostname or ""
    # 已知同一中转服务的不同域名不会被算作独立备用。
    for domain in ("mov3.co", "utako.moe", "jp-primehome.com", "netgenx.site"):
        if host == domain or host.endswith("." + domain):
            return domain
    return host


def collect(data, policy):
    by_channel = {x["id"]: {} for x in policy["channels"]}
    sources = []

    def add(row, target, source, incumbent=False):
        url = row["url"]
        if not valid_url(url):
            return
        pool = by_channel[target["id"]]
        if url not in pool:
            pool[url] = {"id": target["id"], "name": target["name"], "url": url,
                         "source": source, "incumbent": incumbent}
            if row.get("transport"):
                pool[url]["transport"] = row["transport"]
        elif incumbent:
            pool[url]["incumbent"] = True

    for row in data["channels"] + data.get("candidates", []):
        target = next((t for t in policy["channels"]
                       if row["id"].split(".backup")[0] == t["id"]), None)
        if target:
            add(row, target, row.get("source", ""), row in data["channels"])

    def one(source):
        try:
            body, _ = maintain.curl_fetch(source["url"])
            if not body.lstrip().startswith(b"#EXTM3U"):
                raise ValueError("上游没有返回 M3U")
            return source, maintain.parse_m3u(body.decode()), None
        except Exception as e:
            return source, [], maintain.safe_error(e)

    enabled = [s for s in load("sources.json") if s.get("enabled", True)]
    with concurrent.futures.ThreadPoolExecutor(max_workers=policy["workers"]) as pool:
        for source, rows, error in pool.map(one, enabled):
            sources.append({"name": source["name"], "entries": len(rows), "error": error})
            for row in rows:
                target = identify(row, policy["channels"])
                if target:
                    add(row, target, source["url"])
    candidates = []
    for rows in by_channel.values():
        # 各中转轮流取地址，避免一个聚合站耗尽整个频道的检测额度。
        groups = {}
        for row in rows.values():
            groups.setdefault(family(row["url"]), []).append(row)
        chosen = [r for r in rows.values() if r["incumbent"]]
        while len(chosen) < policy["max_candidates_per_channel"] and any(groups.values()):
            for group in groups.values():
                if group:
                    row = group.pop(0)
                    if row not in chosen:
                        chosen.append(row)
                    if len(chosen) >= policy["max_candidates_per_channel"]:
                        break
        candidates.extend(chosen)
    return candidates, sources


def probe_auto(row):
    if row.get("transport") == "mpegts":
        result = maintain.probe_ts(row)
        result["transport"] = "mpegts"
    elif row.get("transport") == "hls":
        result = maintain.probe(row)
        result["transport"] = "hls"
    else:
        # 小段读取识别协议，避免对持续 TS 使用读取完整响应的方法。
        req = urllib.request.Request(row["url"], headers={"User-Agent": "Mozilla/5.0"})
        with maintain.opener().open(req, timeout=15) as response:
            start = response.read(4096)
        transport = "hls" if start.lstrip().startswith(b"#EXTM3U") else "mpegts"
        return probe_auto(dict(row, transport=transport))
    if result["ok"]:
        # 播放器缓冲可吸收单个分片的抖动；判断样本的总读取速率。
        if result["transport"] == "hls" and (
            result["media_seconds"] <= 0
            or result["read_seconds"] > result["media_seconds"] * 1.15 + 0.5
        ):
            result.update(ok=False, error="分片读取慢于播放时长")
        duration = result.get("video", {}).get("duration", 0)
        # 实时 TS 本来就按播放速度推送，连接和解码耗时不是下载速率。
        # 少量封包抖动允许 15% 加 0.5 秒余量，持续慢速仍不收录。
        if result["transport"] == "mpegts" and (
            duration <= 0 or result["read_seconds"] > duration * 1.15 + 0.5
        ):
            result.update(ok=False, error="视频样本读取慢于播放时长")
    return result


def confirm(row, policy):
    results = []
    streak = 0
    for _ in range(policy["attempts"]):
        try:
            result = probe_auto(row)
        except Exception as e:
            result = {"ok": False, "error": maintain.safe_error(e)}
        results.append(result)
        streak = streak + 1 if result["ok"] else 0
        if streak >= policy["confirmations"]:
            break
    ok = streak >= policy["confirmations"]
    print(f'{row["name"]}: {"可用" if ok else "不可用"}', flush=True)
    return dict(row, ok=ok, checks=results)


def failure_key(url):
    return hashlib.sha256(url.encode()).hexdigest()


def select(data, rows, state, policy):
    if not any(row["ok"] for row in rows):
        raise ValueError("全部线路检查失败，保留上一版订阅，本次不发布")
    old = {c["url"]: c for c in data["channels"]}
    failures = {}
    selected = []
    for target in policy["channels"]:
        pool = [r for r in rows if r["id"] == target["id"] and r["ok"]]
        pool.sort(key=lambda r: (
            not r["incumbent"],
            -r["checks"][-1]["video"].get("height", 0), r["url"],
        ))
        picks = []
        for row in pool:
            if any(family(p["url"]) == family(row["url"]) for p in picks):
                continue
            video = row["checks"][-1]["video"]
            picks.append({"id": target["id"], "name": target["name"],
                          "group": "日本地上波", "url": row["url"], "source": row["source"],
                          "resolution": f'{video["width"]}×{video["height"]}',
                          "fps": video["r_frame_rate"], "notes": [],
                          "transport": row["checks"][-1]["transport"]})
            if len(picks) == 2:
                break
        # 单次偶发故障保留原线路；有可用替代时立即换源，无需等待。
        if not picks:
            for row in rows:
                if row["id"] != target["id"] or row["url"] not in old:
                    continue
                key = failure_key(row["url"])
                count = state.get("failures", {}).get(key, 0) + 1
                if count < policy["remove_after_failures"]:
                    failures[key] = count
                    picks.append(copy.deepcopy(old[row["url"]]))
        for i, row in enumerate(picks):
            row["id"] = target["id"] + (".backup" if i else "")
            row["name"] = target["name"] + (" 备用" if i else "")
            row["group"] = "备用" if i else "日本地上波"
            selected.append(row)
    if not selected:
        raise ValueError("本次没有可发布线路，保留上一版订阅")
    result = dict(data, channels=selected,
                  missing=[t["name"] for t in policy["channels"]
                           if not any(c["id"] == t["id"] for c in selected)])
    return result, {"failures": failures}


def channel_table(data):
    sources = {s["url"]: s["name"] for s in load("sources.json")}
    lines = ["| 频道 | 画质 | 列表来源 |", "| --- | --- | --- |"]
    primary = [c for c in data["channels"] if c["group"] != "备用"]
    backups = [c for c in data["channels"] if c["group"] == "备用"]
    for c in data["channels"]:
        height = c.get("resolution", "").split("×")[-1]
        quality = height + "p" if height.isdigit() else "—"
        source = sources.get(c.get("source"), "公开来源")
        lines.append(f'| {c["name"]} | {quality} | {source} |')
    lines += ["", f"当前共收录 {len(primary)} 个频道、{len(data['channels'])} 条线路，其中 {len(backups)} 条位于“备用”分组。频道和线路以实际订阅列表为准。"]
    return "\n".join(lines)


def update(site, dry_run=False):
    policy = load("automation.json")
    if not (1 <= policy["confirmations"] <= policy["attempts"] <= 5
            and policy["remove_after_failures"] >= 1 and 1 <= policy["workers"] <= 8):
        raise ValueError("自动更新策略参数无效")
    data = load("channels.json")
    state = load("automation-state.json", {"failures": {}})
    candidates, sources = collect(data, policy)
    with concurrent.futures.ThreadPoolExecutor(max_workers=policy["workers"]) as pool:
        rows = list(pool.map(lambda r: confirm(r, policy), candidates))
    report = {"checked_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
              "site": site, "sources": sources, "results": rows, "dry_run": dry_run}
    try:
        result, state = select(data, rows, state, policy)
    except ValueError as error:
        report.update(published=False, error=str(error))
        maintain.save_report("update.json", report)
        raise
    readme = (ROOT / "README.md").read_text()
    start, end = "<!-- CHANNELS:START -->", "<!-- CHANNELS:END -->"
    if readme.count(start) != 1 or readme.count(end) != 1:
        raise ValueError("README 缺少唯一频道表生成标记")
    readme = readme.split(start)[0] + start + "\n" + channel_table(result) + "\n" + end + readme.split(end)[1]
    report.update(selected=result["channels"], missing=result["missing"],
                  playable=sum(r["ok"] for r in rows), tested=len(rows))
    maintain.save_report("update.json", report)
    if not dry_run:
        for name, value in (("channels.json", result), ("automation-state.json", state)):
            (ROOT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
        (ROOT / "README.md").write_text(readme)
        maintain.build()
        maintain.build(check=True)
    print(f'检测 {len(rows)} 条候选，{report["playable"]} 条可用，选出 {len(result["channels"])} 条订阅线路', flush=True)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", default="local")
    parser.add_argument("--dry-run", action="store_true", help="完成选源并生成报告，不改订阅")
    args = parser.parse_args()
    try:
        update(args.site, args.dry_run)
    except (ValueError, OSError) as error:
        print(str(error), file=sys.stderr)
        raise SystemExit(1)
