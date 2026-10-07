# 日本电视精选列表

面向家庭网络与 APTV 的个人日本电视播放列表。固定入口为 `playlist.m3u`；`channels.json` 是选台与选线的唯一维护文件。

当前主订阅保留 4 个频道、5 条线路：NHK総合 1080p 主线及 540p 备用，电视朝日、TBS、电视东京各一条 540p 线路。NHK E、NTV、富士、MX1、MX2 仍缺合格源，因此没有用失效或内容不合格的地址凑数。

2026-10-08 经 Home 的 OpenWrt/Mihomo 实际出口逐路完成约 90 秒连续视频解码。主线 NHK 为 1440×1080、约 29.97fps；其余为 960×540、25fps。部分连接重试后完成。详见 `home-validation.json`。这是短时网络与解码证据，尚未做 Apple TV/APTV 实机验收，也不代表晚间或长期稳定。

NTV、富士虽然都能解码，但多次画面抽样仍停留在同一旧广告或中转商广告，暂放在 `channels.json` 的 candidates 区，不进入主订阅。朝日出现过中转商广告，但后续画面已回到时间吻合的 Morning Show 节目；不能当作原台纯净信号。原推荐 EPG 最后节目截止到 2026-08-18，当前不绑定这份过期节目表。

## 在 APTV 中使用

发布到 `gaofeng21cn/japan-iptv` 的公开 `main` 分支后，将下列地址填入 APTV 的远程 M3U 配置：

```text
https://raw.githubusercontent.com/gaofeng21cn/japan-iptv/main/playlist.m3u
```

以后只更新仓库里的精选列表，在 APTV 刷新同一份配置即可。地址不需要随每次换源改变。GitHub 只提供很小的频道清单；视频仍由各源直接传给播放器，并不经过 GitHub。

如果采用私有仓库，APTV 通常无法直接读取需 GitHub 登录的 Raw 文件；不要把 GitHub token 填进订阅地址。公开仓库只包含公开频道链接，不保存家庭网络配置、机场订阅、节点、Cookie 或代理凭据。

## 候选基线

| 基线 | 当前用途与限制 |
| --- | --- |
| [Free-TV/IPTV](https://github.com/Free-TV/IPTV) | 商业地上波候选；目前朝日、TBS、东京、富士的视频可读，列表中的 NHK E/NTV 旧地址返回验证页。 |
| [skinred78/jp-iptv-epg](https://github.com/skinred78/jp-iptv-epg) | 保留可用的 NHK G 1080 线路；大量 Render 中转地址返回 404，EPG 已过期。 |
| [iptv-org/iptv](https://github.com/iptv-org/iptv) | 公开免费频道与 NHK G 备用候选；目前无法覆盖完整地上波。 |

NTV 的替代地址由[此频道说明](https://tadasore2027.blogspot.com/2026/08/iptv-20260829.html)发现，并与 [MOV3 当前播放器](https://mov3.co/embedntv.html)核对；技术可读但内容未通过，暂不进入精选。Utako/Gitflic 与 MrKagesan 的列表也做了对照：前者当前主要服务器域名无 DNS 记录，后者能打开首层清单但视频子清单返回 403，暂不采用。三个基线不是三套独立信号，上游经常共享相同服务器。

## 维护

需要 Python 3.10+ 和 FFmpeg 的 `ffprobe`。检测脚本只依赖 Python 标准库。

```sh
# 编辑 channels.json 后生成订阅文件
python3 scripts/maintain.py build
# 检查生成文件是否与维护文件一致
python3 scripts/maintain.py build --verify
# 拉取上游候选，结果放在 reports/candidates.json
python3 scripts/maintain.py discover
# 短时读取视频分片并识别视频格式
python3 scripts/maintain.py check --site local-unqualified
```

`check` 的 HLS 路径读取当前 3 个分片并用 ffprobe 识别视频；持续 TS 路径有界读取约 2 MB 并识别视频。检测不会自动删除频道、换源或覆盖已经选好的列表。响应 200、非空正文、首层 M3U 成功都不足以判为视频可用。

Home 验证须显式通过 Home 的已有代理入口，用私有环境变量 `IPTV_HTTP_PROXY` 提供入口；`check --site home` 在没有显式代理时拒绝把普通本机结果标为 Home。代理连接与出口身份应在本机核对。不要把这个变量的值写进 Git 或上传报告。脚本不继承本机其他代理；没有显式设置时只能算本机环境检测。

GitHub Actions 在提交时检查生成文件和失败场景；手动运行工作流时还会进行 GitHub 机房的在线检测，并上传检测报告。GitHub 机房的结果只能发现通用死链，不能替代 Home 验证。当前没有启用定时换源或定时写入。`check` 通过只表示短时视频读取通过，不能确认画面不是重复广告；频道内容仍须人工或 AI 看画面审核。

更新时先从基线发现候选，再在 Home 测实际视频，核对频道内容、时延、广告与画质，然后修改 `channels.json`、生成 `playlist.m3u` 并提交。遇到换源问题，可回退上一次 Git 提交，再在 APTV 刷新配置。EPG 将在数据新鲜、频道 ID 能对应后另行接入。
