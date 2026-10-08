# 日本电视精选订阅

一份持续维护的日本电视 M3U 播放列表，精选经过验证、播放表现较稳定的线路，重点收录常用地上波频道，并提供备用线路。可在 APTV 等支持远程 M3U 订阅的播放器中使用。

## 添加订阅

在播放器中添加远程 M3U 订阅，填入以下地址：

```text
https://raw.githubusercontent.com/gaofeng21cn/japan-iptv/main/playlist.m3u
```

以 APTV 为例，添加远程 M3U 配置并保存后，即可查看频道列表。以后刷新这份配置就能获取最新列表，订阅地址始终保持不变。GitHub 提供播放列表文件，视频由各上游服务器直接传给播放器。

## 当前频道

| 频道 | 画质 |
| --- | --- |
| NHK総合 東京 | 1080p |
| テレビ朝日 | 540p |
| TBS | 540p |
| テレビ東京 | 540p |

另提供一条 NHK総合 東京 540p 备用线路，位于播放器的“备用”分组。主线路播放不畅时，可以切换到备用线路。

当前共收录 4 个频道、5 条线路。频道范围和线路会随上游可用情况调整，以实际订阅列表为准。

## 维护方式

维护列表时，会从多个公开上游收集候选地址，优先考虑播放稳定性、频道内容是否准确、画质和切台速度。同一上游在不同列表中的重复地址不会被当成独立备用线路。

自动检查用于发现地址失效、视频无法读取等问题；选源还会结合实际播放表现和画面内容判断。失效线路会替换或移除，新增线路确认可用后再加入精选列表。这样，播放器始终使用一份经过整理的清单。

上游变化或用户反馈都可以触发维护。每次提交会自动检查清单一致性、上游列表可访问性和维护脚本；也可以在 GitHub Actions 中手动运行在线线路检查。

更新提交到 `main` 分支后，固定订阅地址就会提供新的 `playlist.m3u`。用户只需刷新订阅。每次变更都有 Git 记录，出现问题时可以回退到之前的版本。

## 参与维护

频道和线路统一在 [`channels.json`](channels.json) 中维护，订阅文件由脚本生成。新增或更换线路时，同时记录来源，方便后续追踪。

| 文件 | 用途 |
| --- | --- |
| [`channels.json`](channels.json) | 精选频道、备用线路和待评估候选 |
| [`sources.json`](sources.json) | 上游列表及收集范围 |
| [`playlist.m3u`](playlist.m3u) | 播放器订阅入口 |
| [`scripts/maintain.py`](scripts/maintain.py) | 上游收集、线路检查和清单生成 |

运行维护命令需要 Python 3.10+、curl，以及 FFmpeg 提供的 `ffprobe`。

```sh
# 检查上游列表并收集候选
python3 scripts/maintain.py audit
python3 scripts/maintain.py discover

# 检查精选线路能否读取视频
python3 scripts/maintain.py check

# 修改 channels.json 后生成订阅文件，并检查一致性
python3 scripts/maintain.py build
python3 scripts/maintain.py build --verify
```

检查报告保存在本地 `reports/` 目录，供选源和排查使用。检查与收集命令不会自行替换精选线路；发布时将修改后的 `channels.json` 和生成的 `playlist.m3u` 一起提交。

如果发现频道打不开、播放卡顿或内容不符，欢迎在 [Issues](https://github.com/gaofeng21cn/japan-iptv/issues) 中提供频道名称、播放器及大致发生时间，方便维护。
