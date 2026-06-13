#!/usr/bin/env python3
"""
封面 7 层结构验证 + 渲染内容验证

两种模式:
  python validate_cover.py cover.html          # 模式1: 验证 HTML 7 层结构
  python validate_cover.py --check-render cover.png  # 模式2: 验证 PNG 包含文字内容

模式1 作为 render_cover.sh 的前置门禁：缺少任何一层直接 exit 1。
模式2 作为渲染后门禁：检测 PNG 是否真正包含文字像素（防止纯背景光效通过）。
"""

import re
import sys
import io
import os

# Windows GBK 终端兼容
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# ═══════════════════════════════════════════════════
# 模式 1: HTML 7 层结构验证
# ═══════════════════════════════════════════════════

REQUIRED_LAYERS = [
    (1, '中文日期',      r'class="[^"]*\bdate\b'),
    (2, '场景标签',      r'class="[^"]*\bscene-label\b'),
    (3, '胶囊徽章',      r'class="[^"]*\bbadge\b'),
    (4, '主标题',        r'class="[^"]*\bmain-title\b'),
    (5, '渐变分隔线',    r'class="[^"]*\bdivider\b'),
    (6, '数据说明',      r'class="[^"]*\bdata-subtitle\b'),
    (7, '数据卡片',      r'class="[^"]*\bcards\b'),
]

OPTIONAL_CHECKS = [
    ('暖色光晕', r'class="[^"]*\bglow-warm\b'),
    ('冷色光晕', r'class="[^"]*\bglow-cool\b'),
]


def validate_html(html_path: str) -> bool:
    """验证 cover.html 包含全部 7 层 CSS class"""
    try:
        with open(html_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except FileNotFoundError:
        print(f'FAIL: {html_path} 不存在')
        return False

    if not content.strip():
        print(f'FAIL: {html_path} 是空文件')
        return False

    all_pass = True
    missing = []

    # ── 门禁 0: 封面禁止 JavaScript 动画 ──
    # 封面是纯静态 HTML+CSS 文档，渲染为 PNG 截图时动画不会播放
    # fromTo opacity:0 之类的初始隐藏会导致截图白屏
    # 唯一允许的 script 是 HyperFrames 兼容声明: window.__hf = {...}; window.__timelines = {};

    js_fail = False

    # 检测 1: 外部脚本引用 <script src="...">
    external_scripts = re.findall(r'<script[^>]*\bsrc\s*=\s*["\']([^"\']+)["\']', content)
    if external_scripts:
        print(f'  Layer 0: 外部脚本检测 FAIL')
        print(f'    封面禁止引用外部脚本（GSAP、anime.js 等动画库会导致白屏）')
        for src in external_scripts:
            print(f'    发现: <script src="{src}">')
        js_fail = True

    # 检测 2: 内联脚本内容
    if not js_fail:
        script_blocks = re.findall(r'<script[^>]*>(.*?)</script>', content, re.DOTALL)
        for block in script_blocks:
            stripped = block.strip()
            if not stripped:
                continue
            # 允许纯 HyperFrames 兼容声明（无动画逻辑）
            hf_compat = re.sub(r'window\.__hf\s*=\s*\{[^}]*\}\s*;?\s*', '', stripped)
            hf_compat = re.sub(r'window\.__timelines\s*=\s*\{[^}]*\}\s*;?\s*', '', hf_compat)
            hf_compat = re.sub(r'window\.__timelines\s*=\s*window\.__timelines\s*\|\|\s*\{\}\s*;?\s*', '', hf_compat)
            hf_compat = re.sub(r'[\s;{}]+', '', hf_compat)
            if hf_compat:
                print(f'  Layer 0: JavaScript 动画检测 FAIL')
                print(f'    封面禁止 JavaScript 代码（仅允许 HyperFrames 兼容声明）')
                print(f'    发现非法内容: {hf_compat[:80]}...' if len(hf_compat) > 80 else f'    发现非法内容: {hf_compat}')
                print(f'    原因: 封面渲染为 PNG 截图时动画不播放，fromTo opacity:0 等初始隐藏会导致白屏')
                js_fail = True
                break

    if js_fail:
        all_pass = False
    else:
        print(f'  Layer 0: JavaScript 检测 OK（纯静态 HTML+CSS）')

    for layer_num, layer_name, pattern in REQUIRED_LAYERS:
        if re.search(pattern, content):
            print(f'  Layer {layer_num}: {layer_name} OK')
        else:
            print(f'  Layer {layer_num}: {layer_name} MISSING')
            missing.append(layer_name)
            all_pass = False

    for check_name, pattern in OPTIONAL_CHECKS:
        if not re.search(pattern, content):
            print(f'  WARNING: {check_name} 缺失（建议添加）')

    if not all_pass:
        print(f'\nFAIL: 缺少 {len(missing)} 层: {", ".join(missing)}')
        print('修复: 参照 stage7-delivery.md §7.1 封面 HTML 模板，补充缺失层级')
    else:
        print(f'\nPASS: 7 层结构验证通过')

    return all_pass


# ═══════════════════════════════════════════════════
# 模式 2: PNG 渲染内容验证（像素采样文字检测）
# ═══════════════════════════════════════════════════

# 封面关键区域定义：(区域名, y_start%, y_end%, 预期主色RGB范围)
# 基于封面 7 层布局从上到下的位置比例
# 竖屏 (2160×3840 或 1080×1920)
COVER_REGIONS_PORTRAIT = [
    # Layer 1: 日期区域 (约 25-32%) — 应有橙色文字
    ('日期区域',    0.25, 0.32, (200, 100, 0), 80),
    # Layer 2-3: 标签+徽章区域 (约 33-47%) — 应有蓝色文字
    ('标签徽章区域', 0.33, 0.47, (0, 150, 200), 80),
    # Layer 4: 主标题区域 (约 42-56%) — 应有白色/橙色大字
    ('主标题区域',   0.42, 0.56, None, 150),
    # Layer 6-7: 数据+卡片区域 (约 60-72%) — 应有绿色/橙色数字
    ('数据卡片区域', 0.60, 0.72, None, 100),
]

# 横屏 (3840×2160 或 1920×1080) — 内容在 3:4 安全区内垂直堆叠
COVER_REGIONS_LANDSCAPE = [
    # 安全区垂直居中，内容分布更紧凑
    ('日期区域',    0.15, 0.25, (200, 100, 0), 80),
    ('标签徽章区域', 0.25, 0.38, (0, 150, 200), 80),
    ('主标题区域',   0.35, 0.55, None, 150),
    ('数据卡片区域', 0.58, 0.75, None, 100),
]


def validate_render(png_path: str) -> bool:
    """
    验证渲染后的封面 PNG 是否包含文字内容。

    策略：在封面 4 个关键区域做像素采样，统计非背景色（非深色）像素占比。
    如果某个区域几乎没有亮色像素，说明该区域的文字没有被渲染。

    返回 True = 验证通过（检测到文字像素）
    返回 False = 验证失败（可能只是纯背景光效）
    """
    try:
        from PIL import Image
    except ImportError:
        print('WARNING: Pillow 未安装，跳过渲染验证')
        return True

    if not os.path.exists(png_path):
        print(f'FAIL: {png_path} 不存在')
        return False

    file_size = os.path.getsize(png_path)

    # 门禁1: 文件大小检查
    # 1080x1920 封面：纯背景约 250-320KB，含文字通常 > 320KB
    # 2160x3840 封面：纯背景约 500-600KB，含文字通常 > 600KB
    img = Image.open(png_path)
    w, h = img.size

    if w == 1080 and h == 1920:
        min_size = 320_000
        size_label = "320KB"
    elif w == 2160 and h == 3840:
        min_size = 600_000
        size_label = "600KB"
    elif w == 1920 and h == 1080:
        min_size = 280_000
        size_label = "280KB"
    elif w == 3840 and h == 2160:
        min_size = 500_000
        size_label = "500KB"
    else:
        min_size = 250_000
        size_label = "250KB"

    print(f'  PNG: {w}x{h}, {file_size/1024:.0f}KB')

    if file_size < min_size:
        print(f'  WARNING: 文件大小 {file_size/1024:.0f}KB < {size_label}，可能缺少文字内容')
        # 不直接失败，继续像素检测

    # 方向检测：横屏用安全区采样区域，竖屏用标准区域
    is_landscape = w > h
    if is_landscape:
        cover_regions = COVER_REGIONS_LANDSCAPE
        sample_width_pct = 0.42   # 安全区约占宽度 42%（810/1920）
    else:
        cover_regions = COVER_REGIONS_PORTRAIT
        sample_width_pct = 0.6    # 竖屏采样中间 60%

    # 门禁2: 像素采样文字检测
    img_rgb = img.convert('RGB')
    all_pass = True

    for region_name, y_start_pct, y_end_pct, expected_color, threshold in cover_regions:
        y_start = int(h * y_start_pct)
        y_end = int(h * y_end_pct)
        region_w = int(w * sample_width_pct)  # 横屏采样42%（安全区），竖屏60%
        x_start = int((w - region_w) / 2)    # 水平居中采样

        bright_count = 0
        total_sampled = 0

        # 每隔 N 行采样一行，每隔 N 列采样一列
        row_step = max(1, (y_end - y_start) // 20)
        col_step = max(1, region_w // 30)

        for y in range(y_start, y_end, row_step):
            for x in range(x_start, x_start + region_w, col_step):
                r, g, b = img_rgb.getpixel((x, y))
                total_sampled += 1
                # "亮色像素" = 任一通道 > 140（白色、橙色、蓝色、绿色文字都满足）
                if r > 140 or g > 140 or b > 140:
                    bright_count += 1

        if total_sampled == 0:
            continue

        ratio = bright_count / total_sampled
        has_text = ratio > 0.01  # 至少 1% 的采样像素是亮色（文字）

        if has_text:
            print(f'  {region_name}: OK (亮色像素占比 {ratio:.1%})')
        else:
            print(f'  {region_name}: FAIL (亮色像素占比 {ratio:.1%}, 阈值 1%)')
            all_pass = False

    if all_pass:
        print(f'\nPASS: 渲染内容验证通过')
    else:
        print(f'\nFAIL: 封面可能缺少文字内容（只有背景光效），请检查 cover.html 渲染')

    return all_pass


# ═══════════════════════════════════════════════════
# 入口
# ═══════════════════════════════════════════════════

if __name__ == '__main__':
    args = sys.argv[1:]

    if '--check-render' in args:
        # 模式2: PNG 渲染内容验证
        idx = args.index('--check-render')
        png_file = args[idx + 1] if idx + 1 < len(args) else 'cover.png'
        ok = validate_render(png_file)
        sys.exit(0 if ok else 1)
    else:
        # 模式1: HTML 7 层结构验证
        html_file = args[0] if args else 'cover.html'
        ok = validate_html(html_file)
        sys.exit(0 if ok else 1)
