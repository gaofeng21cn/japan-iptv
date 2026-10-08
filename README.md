# 日本电视精选订阅

一份自动维护的日本电视 M3U 播放列表，根据视频播放检查结果持续更新线路，重点收录常用地上波频道，并提供备用线路。可在 APTV 等支持远程 M3U 订阅的播放器中使用。

## 添加订阅

在播放器中添加远程 M3U 订阅，填入以下地址：

```text
https://raw.githubusercontent.com/gaofeng21cn/japan-iptv/main/playlist.m3u
```

以 APTV 为例，添加远程 M3U 配置并保存后，即可查看频道列表。以后刷新这份配置就能获取最新列表，订阅地址始终保持不变。GitHub 提供播放列表文件，视频由各上游服务器直接传给播放器。

## 当前频道

<!-- CHANNELS:START -->
| 频道 | 画质 | 列表来源 |
| --- | --- | --- |
| NHK総合 東京 | 1080p | skinred78/jp-iptv-epg |
| NHK総合 東京 备用 | 540p | Free-TV/IPTV |
| 日本テレビ | 540p | 公开来源 |
| テレビ朝日 | 540p | Free-TV/IPTV |
| TBS | 540p | Free-TV/IPTV |
| テレビ東京 | 540p | Free-TV/IPTV |
| フジテレビ | 540p | Free-TV/IPTV |

当前共收录 6 个频道、7 条线路，其中 1 条位于“备用”分组。频道和线路以实际订阅列表为准。
<!-- CHANNELS:END -->

## 维护方式

### 上游项目与地址

以下公开项目用于收集和对照日本频道地址。它们是候选来源，具体采用的线路记录在 [`channels.json`](channels.json) 的 `source` 字段中；订阅只包含精选条目。

| 项目 | 播放列表 | 维护用途 |
| --- | --- | --- |
| [Free-TV/IPTV](https://github.com/Free-TV/IPTV) | [日本列表](https://raw.githubusercontent.com/Free-TV/IPTV/master/playlists/playlist_japan.m3u8) | 收集综合社区列表中的日本地上波及其他频道地址。 |
| [iptv-org/iptv](https://github.com/iptv-org/iptv) | [日本列表](https://iptv-org.github.io/iptv/countries/jp.m3u) | 对照新闻、免费流媒体电视（FAST）等频道，补充地上波以外的候选。 |
| [skinred78/jp-iptv-epg](https://github.com/skinred78/jp-iptv-epg) | [日本列表](https://skinred78.github.io/jp-iptv-epg/jp-playlist.m3u) | 对照 NHK 等日本频道地址及节目表信息。 |
| [MrKagesan/JP-IPTV](https://github.com/MrKagesan/JP-IPTV) | [JP.m3u](https://raw.githubusercontent.com/MrKagesan/JP-IPTV/main/JP.m3u) | 收集地上波、BS、CS 频道候选，逐条核对实际内容和播放表现。 |
| [rloim024/IPTV-jp](https://github.com/rloim024/IPTV-jp) | [jp.m3u](https://raw.githubusercontent.com/rloim024/IPTV-jp/main/jp.m3u) | 对照频道覆盖；多条地址可能共用同一个中转服务。 |
| [Jsan-PC/IPTV_JP](https://github.com/Jsan-PC/IPTV_JP) | [jp.m3u](https://raw.githubusercontent.com/Jsan-PC/IPTV_JP/main/jp.m3u) | 对照 Utako 系列聚合地址，按实际 URL 去重。 |
| [koneMorris1625/iptvNippon](https://github.com/koneMorris1625/iptvNippon) | [playlist.m3u](https://raw.githubusercontent.com/koneMorris1625/iptvNippon/main/playlist.m3u) | 收集 Primehome 系列线路，与其他中转来源分别评估。 |
| [DimaSvitenko2009/IPTV-JP](https://github.com/DimaSvitenko2009/IPTV-JP) | [JPIPTV.m3u](https://raw.githubusercontent.com/DimaSvitenko2009/IPTV-JP/main/JPIPTV.m3u) | 补充 Primehome 地址对照，使用前核对更新情况。 |
| [ytpit20218/Japan-IPTV](https://github.com/ytpit20218/Japan-IPTV) | [jp.m3u](https://raw.githubusercontent.com/ytpit20218/Japan-IPTV/main/jp.m3u) | 对照较早的 IP 直连地址，作为补充候选。 |

[`sources.json`](sources.json) 统一保存项目名称、列表地址、类型、用途和是否启用。另登记了 [tocotoco0013/japan-iptv-m3u8](https://github.com/tocotoco0013/japan-iptv-m3u8) 和 [vovanlocpro/IPTV-JPN](https://github.com/vovanlocpro/IPTV-JPN)，目前未启用自动上游检查；重新采用前应先确认列表地址、频道覆盖和视频可用性。

列表来源不一定是视频服务的提供方。多个项目也可能引用相同中转地址，因此项目数量、频道标签数量都不能直接代表可用频道或独立备用线路的数量。

### 选源与检查

自动维护从已启用的公开上游和额外候选池收集地址，通过精确频道 ID 或别名匹配常用地上波频道，并按 URL 去重。新闻专台、海外频道和子频道不会通过模糊名称混入主频道。每个频道最多检查 24 条候选，各中转来源轮流取样，避免重复地址占满检测额度。

线路必须连续两次通过视频检查，最多尝试三次：HLS 读取最近最多三个分片，持续 MPEG-TS 读取一段视频样本，由 `ffprobe` 获取视频信息，再用 `ffmpeg` 实际解码画面。HTML 页面、空列表、无法解码的视频、已结束的 HLS 列表，以及下载速度慢于播放时长的线路都不会通过检查。

通过检查的现有线路优先保留，新线路优先选择较高分辨率。每个频道最多保留一条主线路和一条来自不同中转服务的备用线路。原线路失效而有可用替代时立即换源；没有替代时，连续两轮更新失败才移除，避免短暂故障造成频繁上下架。

自动检查确认的是视频可读取、可解码和读取速度，频道标签来自上游列表。它不鉴别节目画面、占位视频或中转广告，也不保证全天无中断；实际观看体验以播放器为准。

### 更新与发布

GitHub Actions 每天北京时间 **07:15** 自动收集、检测和更新订阅，也可以随时手动触发。定时任务由 GitHub 调度，实际开始时间可能略有延迟。

检查完成后，工作流自动生成 `playlist.m3u` 和上面的频道表，将变化直接提交到 `main`，无需人工审核；没有变化就不提交。固定订阅地址始终不变，用户刷新订阅即可获取最新列表。

如果全部候选都检查失败，工作流保留上一版订阅并标记失败，不发布空列表。每轮结果保存在 Actions 的检查报告中，保留 14 天；每次发布都有 Git 记录，必要时可以回退。

## 参与维护

日常选源和发布由自动更新脚本完成。开发者主要维护上游地址、频道匹配规则和检测策略，也可以添加额外候选地址，由后续自动更新检查。

| 文件 | 用途 |
| --- | --- |
| [`channels.json`](channels.json) | `channels` 为自动选出的发布线路，`candidates` 为额外候选池，`missing` 记录当前缺少的频道 |
| [`sources.json`](sources.json) | 上游列表及收集范围；`enabled` 控制是否参与收集和上游检查 |
| [`automation.json`](automation.json) | 目标频道、精确别名、确认次数、失败移除阈值、并发和候选额度 |
| [`automation-state.json`](automation-state.json) | 原线路连续失败计数，由自动更新维护 |
| [`playlist.m3u`](playlist.m3u) | 播放器订阅入口 |
| [`scripts/maintain.py`](scripts/maintain.py) | 上游收集、线路检查和清单生成 |
| [`scripts/update.py`](scripts/update.py) | 全自动收集、检测、选源和生成订阅 |

运行维护命令需要 Python 3.10+、curl，以及 FFmpeg 提供的 `ffprobe` 和 `ffmpeg`。

```sh
# 检查已启用的上游列表，收集登记来源中的候选地址
python3 scripts/maintain.py audit
python3 scripts/maintain.py discover

# 检查精选线路能否读取视频
python3 scripts/maintain.py check

# 完整自动选源，只生成报告
python3 scripts/update.py --dry-run

# 完整自动选源，更新本地订阅和频道表
python3 scripts/update.py

# 单独生成订阅文件，并检查一致性
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
| `reports/update.json` | 自动更新的上游收集结果、逐条检测、选中线路和缺少的频道 |

这些报告保存在本地，不进入订阅。`audit` 和 `discover` 只读取已启用来源，不修改精选线路；`check` 只检测当前发布线路。`update.py` 才执行自动选源，`--dry-run` 会完成同样的网络检查和选择，但不修改发布文件或失败计数。

新增上游时同步更新 `sources.json` 和上面的来源表。新增目标频道时，在 `automation.json` 中填写频道 ID、名称和精确别名；额外地址可加入 `channels.json` 的 `candidates`，填写对应频道 ID、名称、URL 和来源。协议可通过 `transport` 指定为 `hls` 或 `mpegts`，未指定时由自动更新识别。频道表位于 README 的 `CHANNELS:START` / `CHANNELS:END` 标记之间，由脚本生成。

本地线路检查默认直接连接上游；如需代理，可通过环境变量 `IPTV_HTTP_PROXY` 指定 HTTP 代理，`--site` 用于标记检测环境。上游 `audit` 使用 curl，其代理设置遵循 curl 的环境变量。报告对应运行检查时的网络环境，选源时应结合实际播放器的表现。

在 [Update playlist automatically](https://github.com/gaofeng21cn/japan-iptv/actions/workflows/update.yml) 页面选择 **Run workflow** 可立即更新；勾选 `dry_run` 时只检查、不发布。结果位于运行页面的 `playlist-update-report` 附件中。工作流串行运行，推送冲突时停止发布，不覆盖他人提交。

[Validate curated playlist](https://github.com/gaofeng21cn/japan-iptv/actions/workflows/check.yml) 在普通推送和 PR 时检查生成文件、维护脚本和已启用上游。自动更新也会在发布前运行脚本测试和生成一致性检查。

如果发现频道打不开、播放卡顿或内容不符，欢迎在 [Issues](https://github.com/gaofeng21cn/japan-iptv/issues) 中提供频道名称、播放器及大致发生时间，方便维护。
