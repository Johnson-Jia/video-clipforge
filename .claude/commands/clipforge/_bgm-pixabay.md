# Pixabay BGM 批量下载

> **用途：** 从 Pixabay 批量下载无版权 BGM 到 `workspace/bgm/`，按主题风格分类命名。
> **触发：** 需要补充 BGM 素材库时，由 Stage 4 调用或独立执行。

## 下载原理

Pixabay 音频的 CDN 直链格式为：

```
https://cdn.pixabay.com/audio/YYYY/MM/DD/audio_<hash>.mp3
```

**必须携带 `Referer: https://pixabay.com/` 头，否则返回 403。** yt-dlp 无法下载（Cloudflare 拦截）。

## 三步流程

### Step 1：搜索并提取 CDN URL

通过浏览器（Chrome MCP）导航到 Pixabay 搜索页：

```
https://pixabay.com/music/search/<关键词>/
```

从页面 HTML 中用正则提取 CDN URL（搜索结果中的预览音频即为直链）：

```bash
# 从浏览器保存的 HTML 文件中提取
grep -oP 'cdn\.pixabay\.com/audio/[^"'\''\\s]+\.mp3' <html文件路径> | head -10
```

### Step 2：下载

```bash
# 单首下载
curl -sL -o workspace/bgm/<主题名>-<序号>.mp3 \
  -w "HTTP %{http_code} Size %{size_download}" \
  -H "Referer: https://pixabay.com/" \
  -H "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36" \
  "https://cdn.pixabay.com/audio/YYYY/MM/DD/audio_xxxxxx.mp3"

# 批量下载（5 首）
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36"
REF="Referer: https://pixabay.com/"
curl -sL -o workspace/bgm/<主题>-1.mp3 -w "%{http_code} %{size_download}\n" -H "$REF" -H "User-Agent: $UA" "<URL1>" && \
curl -sL -o workspace/bgm/<主题>-2.mp3 -w "%{http_code} %{size_download}\n" -H "$REF" -H "User-Agent: $UA" "<URL2>" && \
curl -sL -o workspace/bgm/<主题>-3.mp3 -w "%{http_code} %{size_download}\n" -H "$REF" -H "User-Agent: $UA" "<URL3>" && \
curl -sL -o workspace/bgm/<主题>-4.mp3 -w "%{http_code} %{size_download}\n" -H "$REF" -H "User-Agent: $UA" "<URL4>" && \
curl -sL -o workspace/bgm/<主题>-5.mp3 -w "%{http_code} %{size_download}\n" -H "$REF" -H "User-Agent: $UA" "<URL5>"
```

**关键参数：**
- `-H "Referer: https://pixabay.com/"` — **必须有**，否则 403
- `-H "User-Agent: ..."` — 浏览器 UA，避免被拦截
- `https_proxy` / `http_proxy` — 如需代理访问 Pixabay CDN，请在执行前设置环境变量

### Step 3：验证

```bash
# 检查文件是否为有效 MP3
file workspace/bgm/<主题>-1.mp3
# 应输出类似：MPEG ADTS, layer III, v1, 256 kbps, 44.1 kHz, JntStereo

# 统计总数和大小
ls workspace/bgm/*.mp3 | wc -l
du -sh workspace/bgm/
```

## 主题风格→搜索词映射

以下映射对应 HyperFrames 视觉主题的配乐需求：

| 主题名 | Pixabay 搜索词 | 风格特征 |
|--------|---------------|---------|
| `bold-energetic` | `energetic upbeat` | 高能、节奏强、适合科技资讯 |
| `clean-corporate` | `corporate clean business` | 专业、干净、适合商业演示 |
| `dark-premium` | `dark cinematic dramatic` | 暗黑、电影感、适合高端产品 |
| `jewel-rich` | `luxury elegant cinematic` | 奢华、优雅、适合精品展示 |
| `monochrome` | `minimal ambient piano` | 极简、氛围、钢琴为主 |
| `nature-earth` | `nature acoustic folk` | 自然、原声、民谣风 |
| `neon-electric` | `synthwave electronic neon` | 合成波、电子、赛博朋克 |
| `pastel-soft` | `soft gentle ambient calm` | 柔和、轻缓、治愈系 |
| `warm-editorial` | `warm acoustic cozy` | 温暖、原声、舒适 |

## 文件命名规范

```
workspace/bgm/<主题名>-<序号>.mp3
```

- 主题名与上表 `主题名` 列一致（kebab-case）
- 序号 1-5
- 例：`bold-energetic-1.mp3`、`dark-premium-3.mp3`

## 批量补全脚本

当需要一次性补齐所有主题的 BGM 时，按以下流程执行：

```
对于每个主题：
  1. 浏览器导航到 https://pixabay.com/music/search/<搜索词>/
  2. 从 HTML 提取前 5 个 CDN URL
  3. 批量下载为 <主题名>-1~5.mp3
  4. 验证 HTTP 200 + 文件大小 > 500KB
```

> **浏览器必须已登录 Pixabay**，否则搜索页可能不返回完整结果。首次使用需用户手动登录一次。

## 注意事项

| 事项 | 说明 |
|------|------|
| **Referer 必填** | 无 Referer → 403 XML 错误页 |
| **代理可能必需** | 国内直连 Pixabay CDN 不稳定，按需设置 `https_proxy` |
| **SSL 超时** | 偶发 `exit code 35`，单首重试即可 |
| **yt-dlp 无效** | Pixabay 有 Cloudflare 防护，yt-dlp 全部 403 |
| **登录状态** | 浏览器需已登录 Pixabay 才能获取完整搜索结果 |
| **版权合规** | Pixabay 音乐为免版税（royalty-free），可商用 |
