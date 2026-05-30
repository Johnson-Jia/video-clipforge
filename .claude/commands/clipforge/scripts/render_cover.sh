#!/usr/bin/env bash
# 封面渲染（三级降级 → 两级，禁止 ffmpeg 首帧提取）
#
# 用法: bash scripts/render_cover.sh [项目目录]
# 项目目录默认为当前目录
#
# 降级策略: HyperFrames 隔离渲染 → puppeteer-core Chrome 截图 → 报错退出
# 禁止: ffmpeg 从视频首帧提取（首帧是 hook 场景，不是封面设计）

set -e
PROJECT_DIR="${1:-.}"
cd "$PROJECT_DIR"

echo "[render_cover] 检查封面..."

if [ -s cover.png ]; then
  echo "[render_cover] cover.png 已存在，跳过"
  exit 0
fi

echo "[render_cover] cover.png 缺失，尝试渲染..."

# ── 门禁: 验证 cover.html 7 层结构 ──
if [ -s cover.html ]; then
  echo "[render_cover] 验证封面 7 层结构..."
  python .claude/commands/clipforge/scripts/validate_cover.py cover.html || {
    echo "FATAL: cover.html 缺少必需的视觉层次，请先修复后再渲染"
    exit 1
  }
fi

# ── 方案 A: HyperFrames 隔离渲染 ──
# 从 cover.html 检测封面尺寸
COVER_W=$(grep -oP 'width:\s*\K\d+' cover.html | head -1)
COVER_H=$(grep -oP 'height:\s*\K\d+' cover.html | head -1)
COVER_W=${COVER_W:-2160}
COVER_H=${COVER_H:-3840}
# 输出尺寸 = 封面尺寸 / 2
OUT_W=$((COVER_W / 2))
OUT_H=$((COVER_H / 2))

TMPDIR="${TEMP:-/tmp}/cover-render"
mkdir -p "$TMPDIR"
cp cover.html "$TMPDIR/index.html" 2>/dev/null || true
if npx hyperframes render "$TMPDIR" --output "$TMPDIR/cover.mp4" --video-bitrate 5M 2>/dev/null; then
  ffmpeg -y -i "$TMPDIR/cover.mp4" -vf "select=eq(n\,0),scale=${OUT_W}:${OUT_H}:flags=lanczos" -vframes 1 -update 1 cover.png 2>/dev/null
  rm -rf "$TMPDIR"
  if [ -s cover.png ]; then
    echo "[render_cover] 方案A成功: HyperFrames 隔离渲染"
  fi
fi

# ── 方案 B: puppeteer-core + Chrome headless 截图 ──
if [ ! -s cover.png ]; then
  rm -rf "$TMPDIR"
  echo "[render_cover] 方案A失败，尝试方案B: puppeteer-core Chrome 截图..."

  CHROME_PATH="C:/Program Files/Google/Chrome/Application/chrome.exe"
  if [ ! -f "$CHROME_PATH" ]; then
    echo "[render_cover] Chrome not found at $CHROME_PATH"
  else
    # 获取 cover.html 的绝对路径（file:// URL）
    COVER_ABS="$(pwd)/cover.html"
    COVER_URL="file:///${COVER_ABS#\/}"

    node -e "
      const puppeteer = require('puppeteer-core');
      const path = '$CHROME_PATH';
      (async () => {
        try {
          const browser = await puppeteer.launch({
            executablePath: path,
            headless: 'new',
            args: ['--no-sandbox', '--disable-gpu']
          });
          const page = await browser.newPage();
          await page.setViewport({ width: ${COVER_W}, height: ${COVER_H}, deviceScaleFactor: 1 });
          await page.goto('file:///${COVER_ABS}', { waitUntil: 'networkidle0', timeout: 30000 });
          await page.evaluate(() => document.fonts.ready);
          await new Promise(r => setTimeout(r, 2000));
          await page.screenshot({ path: 'cover_raw.png', type: 'png' });
          await browser.close();
          console.log('OK');
        } catch(e) {
          console.error('FAIL: ' + e.message);
          process.exit(1);
        }
      })();
    " 2>/dev/null && \
    ffmpeg -y -i cover_raw.png -vf "scale=${OUT_W}:${OUT_H}:flags=lanczos" -q:v 2 cover.png 2>/dev/null && \
    rm -f cover_raw.png

    if [ -s cover.png ]; then
      echo "[render_cover] 方案B成功: puppeteer-core Chrome 截图"
    fi
  fi
fi

# ── 最终检查 ──
if [ -s cover.png ]; then
  # 内容验证：检查 PNG 是否真正包含文字（非纯背景）
  python .claude/commands/clipforge/scripts/validate_cover.py --check-render cover.png || {
    echo "FATAL: cover.png 已生成但未通过内容验证（可能缺少文字），请检查 cover.html 渲染"
    rm -f cover.png
    exit 1
  }
  echo "[render_cover] cover.png 已生成并通过验证 ($(du -h cover.png | cut -f1))"
else
  echo "[render_cover] FAIL: 所有封面渲染方案失败（HyperFrames + Chrome），请手动检查"
  exit 1
fi
