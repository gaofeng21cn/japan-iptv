# 日本电视精选订阅

一份持续维护的日本电视 M3U 播放列表，精选经过验证、播放表现较稳定的线路，重点收录常用地上波频道，并提供备用线路。可在 APTV 等支持远程 M3U 订阅的播放器中使用。

## 添加订阅

在播放器中添加远程 M3U 订阅，填入以下地址：

```text
https://raw.githubusercontent.com/gaofeng21cn/japan-iptv/main/playlist.m3u
```

以 APTV 为例，添加远程 M3U 配置并保存后，即可查看频道列表。以后刷新这份配置就能获取最新列表，订阅地址始终保持不变。GitHub 提供播放列表文件，视频由各上游服务器直接传给播放器。

## 当前频道

| 频道 | 画质 | 列表来源 |
| --- | --- | --- |
| NHK総合 東京 | 1080p | skinred78/jp-iptv-epg |
| テレビ朝日 | 540p | Free-TV/IPTV |
| TBS | 540p | Free-TV/IPTV |
| テレビ東京 | 540p | Free-TV/IPTV |

另提供一条来自 Free-TV/IPTV 的 NHK総合 東京 540p 备用线路，位于播放器的“备用”分组。主线路播放不畅时，可以切换到备用线路。

当前共收录 4 个频道、5 条线路。频道范围和线路会随上游可用情况调整，以实际订阅列表为准。

## 维护方式

### 上游项目与地址

以下公开项目用于收集和对照日本频道地址。它们是候选来源，具体采用的线路记录在 [`channels.json`](channels.json) 的 `source` 字段中；订阅只包含精选条目。

| 项目 | 播放列表 | 维护用途 |
| --- | --- | --- |
| [Free-TV/IPTV](https://github.com/Free-TV/IPTV) | [日本列表](https://raw.githubusercontent.com/Free-TV/IPTV/master/playlists/playlist_japan.m3u8) | 综合社区列表中的日本频道，也是当前多条精选线路的来源。 |
| [iptv-org/iptv](https://github.com/iptv-org/iptv) | [日本列表](https://iptv-org.github.io/iptv/countries/jp.m3u) | 对照新闻、免费流媒体电视（FAST）等频道，补充地上波以外的候选。 |
| [skinred78/jp-iptv-epg](https://github.com/skinred78/jp-iptv-epg) | [日本列表](https://skinred78.github.io/jp-iptv-epg/jp-playlist.m3u) | 日本频道与节目表项目，当前 NHK総合 東京主线路的列表来源。 |
| [MrKagesan/JP-IPTV](https://github.com/MrKagesan/JP-IPTV) | [JP.m3u](https://raw.githubusercontent.com/MrKagesan/JP-IPTV/main/JP.m3u) | 收集地上波、BS、CS 频道候选，逐条核对实际内容和播放表现。 |
| [rloim024/IPTV-jp](https://github.com/rloim024/IPTV-jp) | [jp.m3u](https://raw.githubusercontent.com/rloim024/IPTV-jp/main/jp.m3u) | 对照频道覆盖；多条地址可能共用同一个中转服务。 |
| [Jsan-PC/IPTV_JP](https://github.com/Jsan-PC/IPTV_JP) | [jp.m3u](https://raw.githubusercontent.com/Jsan-PC/IPTV_JP/main/jp.m3u) | 对照 Utako 系列聚合地址，按实际 URL 去重。 |
| [koneMorris1625/iptvNippon](https://github.com/koneMorris1625/iptvNippon) | [playlist.m3u](https://raw.githubusercontent.com/koneMorris1625/iptvNippon/main/playlist.m3u) | 收集 Primehome 系列线路，与其他中转来源分别评估。 |
| [DimaSvitenko2009/IPTV-JP](https://github.com/DimaSvitenko2009/IPTV-JP) | [JPIPTV.m3u](https://raw.githubusercontent.com/DimaSvitenko2009/IPTV-JP/main/JPIPTV.m3u) | 补充 Primehome 地址对照，使用前核对更新情况。 |
| [ytpit20218/Japan-IPTV](https://github.com/ytpit20218/Japan-IPTV) | [jp.m3u](https://raw.githubusercontent.com/ytpit20218/Japan-IPTV/main/jp.m3u) | 对照较早的 IP 直连地址，作为补充候选。 |

[`sources.json`](sources.json) 统一保存项目名称、列表地址、类型、用途和是否启用。另登记了 [tocotoco0013/japan-iptv-m3u8](https://github.com/tocotoco0013/japan-iptv-m3u8) 和 [vovanlocpro/IPTV-JPN](https://github.com/vovanlocpro/IPTV-JPN)，目前未启用自动上游检查；重新采用前应先确认列表地址、频道覆盖和视频可用性。

列表来源不一定是视频服务的提供方。多个项目也可能引用相同中转地址，因此项目数量、频道标签数量都不能直接代表可用频道或独立备用线路的数量。

### 选源与检查

维护列表时，会从多个公开上游收集候选地址，优先考虑播放稳定性、频道内容是否准确、画质和切台速度。同一上游在不同列表中的重复地址不会被当成独立备用线路。

检查分为三部分：上游检查确认列表格式、频道标签覆盖和地址分布；线路检查读取实际视频，并记录分辨率、帧率及读取耗时；最后结合播放器中的连续播放、切台表现和画面内容决定是否收录。HLS 线路抽取最近最多三个分片，持续 MPEG-TS 线路读取一段视频样本，由 `ffprobe` 确认视频信息。

短时读取成功只能说明当次样本可用，不能替代连续播放和频道内容确认。频道名称与画面不符、长期停留在占位画面或中转广告的地址不作为正式频道收录。失效线路会替换或移除，新增线路确认可用后再加入精选列表。

### 更新与发布

上游变化或用户反馈都可以触发维护。每次提交会自动检查清单一致性、上游列表可访问性和维护脚本；也可以在 GitHub Actions 中手动运行在线线路检查。

更新提交到 `main` 分支后，固定订阅地址就会提供新的 `playlist.m3u`。用户只需刷新订阅。每次变更都有 Git 记录，出现问题时可以回退到之前的版本。

## 参与维护

频道和线路统一在 [`channels.json`](channels.json) 中维护，订阅文件由脚本生成。新增或更换线路时，同时记录来源，方便后续追踪。

| 文件 | 用途 |
| --- | --- |
| [`channels.json`](channels.json) | `channels` 为发布线路，`candidates` 为待评估候选，`missing` 记录待补充频道 |
| [`sources.json`](sources.json) | 上游列表及收集范围；`enabled` 控制是否参加 `audit` |
| [`playlist.m3u`](playlist.m3u) | 播放器订阅入口 |
| [`scripts/maintain.py`](scripts/maintain.py) | 上游收集、线路检查和清单生成 |

运行维护命令需要 Python 3.10+、curl，以及 FFmpeg 提供的 `ffprobe`。

```sh
# 检查已启用的上游列表，收集登记来源中的候选地址
python3 scripts/maintain.py audit
python3 scripts/maintain.py discover

# 检查精选线路能否读取视频
python3 scripts/maintain.py check

# 修改 channels.json 后生成订阅文件，并检查一致性
python3 scripts/maintain.py build
python3 scripts/maintain.py build --verify

# 检查维护脚本
python3 -m unittest discover -s scripts -p 'test_*.py'
```

| 报告 | 查看内容 |
| --- | --- |
| `reports/baseline-audit.json` | 上游是否可读取、频道标签覆盖、主要视频域名分布 |
| `reports/candidates.json` | 各来源的候选名称、URL 和 M3U 元数据 |
| `reports/health.json` | 精选线路的视频信息、读取耗时和错误 |

这些报告保存在本地，不进入订阅。`audit` 只检查已启用来源，`discover` 会尝试读取所有登记来源；两者都不会把候选自动加入精选列表。`check` 检查 `channels` 中的发布线路，候选需要先单独验证。

新增或更换线路时，在 `channels.json` 中填写频道 ID、名称、分组、URL、来源、画质和 `transport`（`hls` 或 `mpegts`），备用线路放入“备用”分组。确认内容和播放表现后运行 `build`，再用 `build --verify` 核对生成文件；发布时将修改后的 `channels.json` 和生成的 `playlist.m3u` 一起提交。新增上游时同步更新 `sources.json` 和上面的来源表。

本地线路检查默认直接连接上游；如需代理，可通过环境变量 `IPTV_HTTP_PROXY` 指定 HTTP 代理，`--site` 用于标记检测环境。上游 `audit` 使用 curl，其代理设置遵循 curl 的环境变量。报告对应运行检查时的网络环境，选源时应结合实际播放器的表现。

GitHub Actions 的 [Validate curated playlist](https://github.com/gaofeng21cn/japan-iptv/actions/workflows/check.yml) 在推送和 PR 时检查生成文件、维护脚本和已启用上游。需要在线线路检查时，在该工作流页面选择 **Run workflow**；结果可在运行页面的 `github-stream-health` 附件中查看。工作流不会自动换源或提交更新，选源和发布由维护者完成。

如果发现频道打不开、播放卡顿或内容不符，欢迎在 [Issues](https://github.com/gaofeng21cn/japan-iptv/issues) 中提供频道名称、播放器及大致发生时间，方便维护。
