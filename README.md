# 日本电视精选订阅

这是给家庭网络和 APTV 用的日本电视播放列表。订阅入口是 [`playlist.m3u`](playlist.m3u)，实际维护的频道和线路在 [`channels.json`](channels.json)。

这个仓库不追求把网上所有列表都搬进来，只保留在 Home 网络里真正跑过的频道。每条线路都知道来自哪里，也知道它当前是正式线路、备用线路，还是还不能用的候选。

## 现在能用什么

| 频道 | 画质 | 状态 |
| --- | --- | --- |
| NHK G | 1440x1080，29.97 fps | 正式线路 |
| テレビ朝日 | 960x540，25 fps | 正式线路 |
| TBS | 960x540，25 fps | 正式线路 |
| テレビ東京 | 960x540，25 fps | 正式线路 |
| NHK G | 960x540，25 fps | 备用线路 |

目前共 4 个频道、5 条线路。NHK E、日本テレビ、フジテレビ、TOKYO MX1、TOKYO MX2 还没有留下来当正式线路。日本テレビ和フジテレビ不是打不开，而是反复抽到旧广告或中转商广告，所以暂时没有放进订阅。

## 在 APTV 里怎么用

在 APTV 的远程 M3U 配置里填这个地址：

```text
https://raw.githubusercontent.com/gaofeng21cn/japan-iptv/main/playlist.m3u
```

以后仓库更新了，在 APTV 里刷新同一个订阅就行，不需要重新添加。GitHub 只负责提供很小的播放列表文件，视频本身仍然由上游服务器直接传给播放器。

如果仓库改成私有，APTV 一般就读不到需要登录才能访问的文件。不要把 GitHub token 放进订阅地址。公开仓库里只放公开频道地址，不放家庭网络配置、机场订阅、节点信息、Cookie 或代理凭据。

## 我们参考了哪些源

基线分成三类：`community` 是维护中的公共目录，`aggregator` 是聚合了多个日本源的列表，`legacy` 是只留作对照的旧列表。看起来覆盖很多不代表线路就多，因为很多列表引用的其实是同一个中转。维护前先跑 `python3 scripts/maintain.py audit` 看一次矩阵。

| 基线 | 类型 | 首层检查 | 说明 |
| --- | --- | --- | --- |
| [Free-TV/IPTV](https://github.com/Free-TV/IPTV) | community | 27 条，8/8 个频道标签 | 日本部分不大。NHK E 和日本テレビ的旧地址在播放检查里返回验证页。 |
| [iptv-org/iptv](https://github.com/iptv-org/iptv) | community | 7 条，2/8 个频道标签 | 适合找官方 FAST 和新闻流，不适合拿来覆盖完整地上波。 |
| [skinred78/jp-iptv-epg](https://github.com/skinred78/jp-iptv-epg) | community | 167 条，8/8 个频道标签 | 最初推荐里用的列表。当前可用的 NHK G 1080 线路来自这里，但 107 条共用 Render 中转，很多返回 404；EPG 数据停在 2026-08-18。 |
| [MrKagesan/JP-IPTV](https://github.com/MrKagesan/JP-IPTV) | aggregator | 163 条，8/8 个频道标签 | 覆盖很宽，但 Home 检查时不少 Primehome 子清单返回 403。 |
| [rloim024/IPTV-jp](https://github.com/rloim024/IPTV-jp) | aggregator | 152 条，8/8 个频道标签 | 名义覆盖最好，但主要线路大多共用 `willfonk` 中转，Home 抽样时超时。 |
| [Jsan-PC/IPTV_JP](https://github.com/Jsan-PC/IPTV_JP) | aggregator | 144 条，8/8 个频道标签 | 基本都是 Utako 别名。重复地址要当成同一个上游，不要当成多条独立备选。 |
| [koneMorris1625/iptvNippon](https://github.com/koneMorris1625/iptvNippon) | aggregator | 63 条，7/8 个频道标签 | Primehome 很多。适合单独测试这个上游，而不是被社区镜像带跑。 |
| [DimaSvitenko2009/IPTV-JP](https://github.com/DimaSvitenko2009/IPTV-JP) | aggregator | 39 条，8/8 个频道标签 | 小、旧、Primehome 多。只作为历史对照保留。 |
| [ytpit20218/Japan-IPTV](https://github.com/ytpit20218/Japan-IPTV) | legacy | 92 条，8/8 个频道标签 | 衍生的旧 luongz 列表，里面有不少裸 IP 地址，需要单独在 Home 验证。 |
| [tocotoco0013/japan-iptv-m3u8](https://github.com/tocotoco0013/japan-iptv-m3u8) | legacy | 404 | 已停用。 |
| [vovanlocpro/IPTV-JPN](https://github.com/vovanlocpro/IPTV-JPN) | legacy | 只有 1 条通用条目 | 已停用。 |

基线矩阵会写在 [`reports/baseline-audit.json`](reports/baseline-audit.json)，里面记录首层是否可读、频道标签覆盖、主要域名和高风险中转数量。首层能打开，不等于视频能看。

## 验证做到哪一步

这里有两类检查，任何一类单独通过都不算完成：

1. `audit` 看播放列表能不能抓到，以及八个重点频道标签有没有覆盖。
2. `check` 读取真实 HLS 分片或有界 MPEG-TS 样本，并用 `ffprobe` 确认里面确实有视频。

2026-10-08 这版正式线路通过 Home 的 OpenWrt + Mihomo 出口做过检查，每条线路大约连续解码 90 秒。NHK G 是 1440x1080、29.97 fps，其余正式线路是 960x540、25 fps。个别连接需要重试后才完成。

这只能证明短时网络和解码可用，不能代替 Apple TV/APTV 实机验收，也不能证明晚高峰或长期都稳定。有些流虽然序号在前进，画面却一直停在中转商广告，所以内容复核仍然是单独一关。详细记录见 [`home-validation.json`](home-validation.json)。

## 维护方式

需要 Python 3.10+ 和 FFmpeg 的 `ffprobe`，维护脚本只依赖 Python 标准库。

```sh
# 从 channels.json 重新生成订阅文件
python3 scripts/maintain.py build

# 检查 playlist.m3u 是否和 channels.json 一致
python3 scripts/maintain.py build --verify

# 审计所有启用的基线，结果写入 reports/baseline-audit.json
python3 scripts/maintain.py audit

# 看一下上游有哪些候选，不改正式列表
python3 scripts/maintain.py discover

# 读取真实视频分片，确认视频格式
python3 scripts/maintain.py check --site local-unqualified
```

`check` 会读取最新三个 HLS 分片并调用 `ffprobe`；如果是连续 MPEG-TS，就只读一个有界样本。它不会自动删除频道、自动换源，也不会覆盖已经选好的精选列表。

做 Home 验证时，通过私有环境变量 `IPTV_HTTP_PROXY` 指向 Home 已有代理入口。`check --site home` 在缺少这个变量时会拒绝把普通本机结果标成 Home。出口身份要单独确认，变量值不要提交，也不要上传到报告里。

GitHub Actions 在每次推送时检查生成文件是否一致，并跑失败场景测试。手动触发时还会用 GitHub 机房出口做一次在线检查，并上传 `reports/health.json`。GitHub 机房只能发现通用死链，不能代替 Home 验证。

更新流程是：先审计基线，再在 Home 测候选，复核真实频道内容、延迟和广告，然后修改 `channels.json`、重新生成 `playlist.m3u`、提交。线路坏了可以回退到上一个 Git 提交，再去 APTV 刷新配置。EPG 要等到数据新鲜、频道 ID 对得上之后再接。
