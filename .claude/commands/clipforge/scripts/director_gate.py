#!/usr/bin/env python3
"""
导演门禁 — HTML 设计意图验证（渲染前运行）

用法: python scripts/director_gate.py [项目目录]
  项目目录默认为当前目录

检查项:
  1. 字号层级（冲击层 ≥ 2× 标签层）
  2. 光晕存在性 + opacity 范围（0.15~0.6）
  3. 关键文字 text-shadow
  4. 相邻场景背景差异（防止视觉单调）
  5. CSS 变量实际使用
  6. layer-fx 内容非空

退出码: 0=通过, 1=有设计问题需要修复

依赖: 无外部依赖，纯 Python 标准库
"""

import re
import sys
import os

# Windows GBK console cannot encode Unicode symbols (✓✗⚠)
if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if sys.stderr and hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')


def main():
    project_dir = sys.argv[1] if len(sys.argv) > 1 else "."
    html_path = os.path.join(project_dir, "index.html")

    if not os.path.exists(html_path):
        print(f"ERROR: {html_path} 不存在")
        sys.exit(1)

    with open(html_path, "r", encoding="utf-8", errors="ignore") as f:
        html = f.read()

    PASS = 0
    FAIL = 0
    WARN = 0

    def ok(msg):
        nonlocal PASS
        PASS += 1
        print(f"  \033[32m✓ {msg}\033[0m")

    def fail(msg):
        nonlocal FAIL
        FAIL += 1
        print(f"  \033[31m✗ {msg}\033[0m")

    def warn(msg):
        nonlocal WARN
        WARN += 1
        print(f"  \033[33m⚠ {msg}\033[0m")

    print("=" * 50)
    print("  导演门禁 — HTML 设计意图验证")
    print("=" * 50)

    # ── 1. 字号层级 ──
    print("\n── 1. 字号层级 ──")
    font_sizes = [int(x) for x in re.findall(r'font-size:\s*(\d+)px', html)]
    if font_sizes:
        max_fs = max(font_sizes)
        min_fs = min(font_sizes)
        ratio = max_fs / min_fs if min_fs > 0 else 0
        if ratio < 2:
            fail(f"字号层级不足: 最大 {max_fs}px / 最小 {min_fs}px = {ratio:.1f}x（应 ≥ 2x）")
        elif ratio < 2.5:
            warn(f"字号层级偏弱: {max_fs}px / {min_fs}px = {ratio:.1f}x（建议 ≥ 3x）")
        else:
            ok(f"字号层级: {max_fs}px / {min_fs}px = {ratio:.1f}x")

        # 检查是否有冲击层（≥ 80px）
        impact_sizes = [s for s in font_sizes if s >= 80]
        if impact_sizes:
            ok(f"冲击层字号存在: {sorted(set(impact_sizes), reverse=True)}px")
        else:
            warn("无冲击层字号（≥ 80px），hook/climax 可能缺乏冲击力")
    else:
        fail("未找到 font-size 声明")

    # 1b. 字号绝对值下限（render-safety §3.1 竖屏）
    # 三道防线：① class font-size 下限 ② 内联 font-size 下限 ③ 非 px 单位量化拦截。
    # 全量扫描：所有 CSS class 的 font-size 都检查（不限白名单），
    # 只有纯几何/纯装饰 class 豁免；含可见文字的容器（进度条百分比等）不豁免。
    print("\n── 1b. 字号绝对值下限（render-safety §3.1）──")
    MIN_TEXT = 32   # 任何可见文本下限 (render-safety §3.1)
    # 纯几何/纯装饰 class 豁免（无可见文字：光晕、进度槽、圆点、分隔线、布局容器）。
    # vs-bar* 系列承载进度条百分比文字，不豁免，正常受 MIN_TEXT 约束。
    # layer-content 48px 是全局继承兜底基准（非容器内文字），保留豁免。
    FONT_SIZE_EXEMPT = {
        'fx-glow', 'fx-line', 'fx-dot', 'fx-pulse', 'fx-drift', 'fx-spin', 'fx-blink',
        'kpi-line', 'tl-dot', 'divider', 'phase', 'clip',
        'layer-bg', 'layer-fx', 'layer-content',
    }

    # 收集 CSS：index.html <style> 块 + creative/style.css
    css_texts = []
    for _sm in re.finditer(r'<style[^>]*>(.*?)</style>', html, re.DOTALL):
        css_texts.append(_sm.group(1))
    style_css_path = os.path.join(project_dir, "creative", "style.css")
    if os.path.exists(style_css_path):
        with open(style_css_path, "r", encoding="utf-8", errors="ignore") as f:
            css_texts.append(f.read())
    css = "\n".join(css_texts)
    # 剥离 CSS 注释：注释里的废弃/示例样式（如 /* font-size:1.2rem */）不生效，
    # 但会被正则误判为违规。剥离后再扫描，只校验实际生效的声明。
    css = re.sub(r'/\*.*?\*/', '', css, flags=re.DOTALL)

    font_violations = []
    if css:
        # ① 全量扫描所有 .cls{font-size:Npx}
        class_sizes = {}
        for m in re.finditer(r'\.([\w-]+)\s*\{[^}]*font-size:\s*(\d+)px', css):
            class_sizes[m.group(1)] = int(m.group(2))
        for cls, size in sorted(class_sizes.items()):
            if cls in FONT_SIZE_EXEMPT:
                continue
            if size < MIN_TEXT:
                font_violations.append(f".{cls}={size}px < {MIN_TEXT}px(下限)")

        # ② 扫描内联 style font-size（双引号 + 单引号都扫，堵单引号绕过）
        for m in re.finditer(r'''style=["'][^"']*font-size:\s*(\d+)px''', html):
            inline_size = int(m.group(1))
            if inline_size < MIN_TEXT:
                font_violations.append(f"内联 font-size={inline_size}px < {MIN_TEXT}px(下限)")

        # ③ 非 px 单位 / CSS 函数 font-size —— 绕过量化校验，FAIL
        #    门禁靠 px 绝对值做下限校验，rem/em/vw/% 与 var()/clamp()/calc() 无法量化
        #    → 强制 px 约定（render-safety）。inherit 等关键字不触发（跟随父级，由兜底层管）。
        REL_UNIT = r'(?:rem|em|ex|ch|vw|vh|vmin|vmax|%)'
        CSS_FUNC = r'(?:var|clamp|min|max|calc)\('
        # set 去重：style.css 同时存在于 index.html <style> 内嵌 + creative/style.css 文件，
        # 双扫会让计数翻倍；用 set 统一去重。
        non_px = set(re.findall(r'font-size:\s*[\d.]+' + REL_UNIT, css))
        non_px |= set(re.findall(r'''style=["'][^"']*font-size:\s*[\d.]+''' + REL_UNIT, html))
        func_fs = set(re.findall(r'font-size:\s*' + CSS_FUNC, css))
        func_fs |= set(re.findall(r'''style=["'][^"']*font-size:\s*''' + CSS_FUNC, html))
        if non_px:
            font_violations.append(f"非 px 单位 font-size（无法量化，必须用 px）: {sorted(non_px)[:5]}")
        if func_fs:
            font_violations.append(f"CSS 函数 font-size（无法量化，必须用 px）: 检测到 {len(func_fs)} 处 var/clamp/min/max/calc")

        if font_violations:
            fail(f"字号门禁: {'; '.join(font_violations)}")
        elif class_sizes:
            ok(f"所有文本字号 ≥ {MIN_TEXT}px 最低标准（全量扫描 {len(class_sizes)} 个 class）")
        else:
            warn("CSS 中未找到命名的字号 class，跳过绝对值检查")
    else:
        warn("未找到 CSS（<style> 块或 creative/style.css），跳过字号绝对值检查")

    # ── 2. 光晕存在性 + opacity 范围 ──
    print("\n── 2. 光晕系统 ──")
    # 查找有 blur 的圆形元素（光晕）
    glow_blocks = re.findall(
        r'([.#][\w-]+)\s*\{[^}]*filter:\s*blur\(\d+px\)[^}]*\}',
        html, re.DOTALL
    )
    if glow_blocks:
        ok(f"光晕元素: {len(set(glow_blocks))} 种")

        # 检查这些光晕的 opacity
        glow_opacities = []
        for block_match in re.finditer(
            r'([.#][\w-]+)\s*\{([^}]*filter:\s*blur\(\d+px\)[^}]*)\}',
            html, re.DOTALL
        ):
            op_match = re.search(r'opacity:\s*([\d.]+)', block_match.group(2))
            if op_match:
                glow_opacities.append(float(op_match.group(1)))

        if glow_opacities:
            low_opacity = [o for o in glow_opacities if o < 0.15]
            high_opacity = [o for o in glow_opacities if o > 0.6]
            if low_opacity:
                fail(f"光晕 opacity < 0.15: {low_opacity}（H.264 编码后不可见）")
            if high_opacity:
                fail(f"光晕 opacity > 0.6: {high_opacity}（抢内容视觉权重）")
            if not low_opacity and not high_opacity:
                ok(f"光晕 opacity 范围: {min(glow_opacities):.2f} ~ {max(glow_opacities):.2f}")

            # 检查是否有暖冷双光晕
            warm_colors = re.findall(r'(?:#f0b429|#f5a623|#ff6b35|240\s*,\s*180\s*,\s*41|255\s*,\s*107\s*,\s*53)', html)
            cool_colors = re.findall(r'(?:#00e5a0|#00b4d8|#6c63ff|0\s*,\s*229\s*,\s*160|0\s*,\s*180\s*,\s*216)', html)
            if warm_colors and cool_colors:
                ok("暖冷双光晕存在")
            elif warm_colors or cool_colors:
                warn("只有单色调光晕，缺少暖冷对比")
            else:
                warn("未检测到标准暖/冷光晕颜色")
    else:
        warn("未检测到 filter:blur 光晕元素")

    # ── 3. text-shadow ──
    print("\n── 3. 文字可读性 ──")
    text_shadow_count = len(re.findall(r'text-shadow:', html))
    if text_shadow_count >= 3:
        ok(f"text-shadow 使用: {text_shadow_count} 处")
    elif text_shadow_count > 0:
        warn(f"text-shadow 偏少: {text_shadow_count} 处（建议关键文字都加）")
    else:
        fail("无 text-shadow — 深色背景上文字浮不起来")

    # text-shadow blur 半径检查（过大发光糊文字，2026-06-15 模糊事故根治）
    # 支持多 shadow（逗号分隔）：text-shadow: 0 0 10px #fff, 0 0 20px #fff
    shadow_decls = re.findall(r'text-shadow:\s*([^;}>]+)', html)
    shadow_blurs = []
    for _decl in shadow_decls:
        for _shadow in _decl.split(','):
            _nums = re.findall(r'([\d.]+)px', _shadow)
            if _nums:
                shadow_blurs.append(float(_nums[-1]))  # 最后一个 px 值（blur；无 blur 时是 v offset，小值不触发 >16）
    if shadow_blurs:
        big_blurs = sorted({b for b in shadow_blurs if b > 16})
        if big_blurs:
            warn(f"text-shadow blur 过大（>16px）: {big_blurs}px — 过大发光让小字边缘重影发虚（24px+ 糊掉 38px 小字），建议普通文字 ≤12px、大字 ≤16px")
        else:
            ok(f"text-shadow blur 合理（最大 {max(shadow_blurs):.0f}px）")

    # ── 3.4b 渐变文字白端点（手机 OLED 过曝 + 深背景灰暗，feedback-gradient-text-brightness）──
    # 渐变文字（linear-gradient + background-clip:text）端点含纯白 → 手机高亮屏过曝刺眼/深背景灰暗无力
    white_in_gradient = []
    for _g in re.findall(r'linear-gradient\([^)]*\)', html):
        if re.search(r'#fff\b|#ffffff|rgba?\(\s*255\s*,\s*255\s*,\s*255', _g, re.IGNORECASE):
            white_in_gradient.append(_g[:70])
    if white_in_gradient:
        warn(f"渐变含纯白端点: {white_in_gradient[:2]} — 手机 OLED 高亮屏过曝(刺眼/层次糊)/深背景灰暗。改同色系高饱和端点(domain→lighten(domain)→domain)，禁 #fff（text-effects.md §渐变）")
    else:
        ok("渐变无纯白端点（同色系高饱和，手机/深背景都清晰）")

    # ── 3.5 文字完整性（禁 ellipsis 截断）──
    # 短视频手机端文字必须完整可读，text-overflow:ellipsis 截断（如项目名 SkillSpect...）不可读。
    # 通用扫 CSS 属性，不依赖 class 名——LLM 自创任何结构只要用了 ellipsis 都拦。
    ellipsis_count = len(re.findall(r'text-overflow:\s*ellipsis', html, re.IGNORECASE))
    if ellipsis_count > 0:
        fail(f"发现 {ellipsis_count} 处 text-overflow:ellipsis（短视频文字必须完整显示，禁省略号截断——手机端不可读。改 width:100% + word-break:break-word 让长名换行完整显示）")
    else:
        ok("无 text-overflow:ellipsis（content 层文字完整显示）")

    # ── 3.5b 项目名溢出（禁 nowrap 推出屏幕，2026-06-21 codebase-memory-mcp 事故）──
    # nowrap 让长 owner/repo 项目名溢出屏幕右边不可见。通用扫 .pfc-name 的 white-space:nowrap，
    # 强制 word-break:break-word 换行完整显示（与 seed pattern P-layout-project-name-row + 组件库一致）。
    nowrap_in_pfcname = re.findall(r'\.pfc-name\s*\{[^}]*white-space:\s*nowrap', html, re.IGNORECASE)
    if nowrap_in_pfcname:
        fail(f"发现 {len(nowrap_in_pfcname)} 处 .pfc-name 含 white-space:nowrap（长项目名 owner/repo 会溢出屏幕右边不可见。改 width:100% + word-break:break-word 让长名换行完整显示）")
    else:
        ok("无 .pfc-name nowrap（项目名 word-break 完整显示）")

    # ── 4. 相邻场景背景差异 ──
    print("\n── 4. 场景视觉反差 ──")
    # 提取场景类名
    scene_classes = re.findall(r'\.s-(\w+)\s*\{', html)
    if len(scene_classes) >= 2:
        # 提取每个场景的 background/gradient
        scene_gradients = {}
        for sc in scene_classes:
            pattern = rf'\.s-{sc}\s*\{{([^}}]*)\}}'
            match = re.search(pattern, html)
            if match:
                bg = match.group(1)
                gradients = re.findall(r'gradient\([^)]+\)', bg)
                bg_colors = re.findall(r'#[0-9a-fA-F]{6}', bg)
                scene_gradients[sc] = {
                    'gradients': gradients,
                    'colors': bg_colors,
                }

        # 比较相邻场景
        scene_names = list(scene_gradients.keys())
        identical_pairs = []
        for i in range(len(scene_names) - 1):
            s1 = scene_gradients[scene_names[i]]
            s2 = scene_gradients[scene_names[i + 1]]
            g1 = s1['gradients'][0] if s1['gradients'] else ''
            g2 = s2['gradients'][0] if s2['gradients'] else ''
            if g1 and g2 and g1 == g2:
                identical_pairs.append((scene_names[i], scene_names[i + 1]))

        if identical_pairs:
            fail(f"相邻场景背景相同: {identical_pairs}（观众会觉得没换画面）")
        else:
            ok(f"相邻场景背景均有差异（{len(scene_names)} 个场景）")
    else:
        warn(f"场景数不足（{len(scene_classes)}），跳过反差检查")

    # ── 5. CSS 变量实际使用 ──
    print("\n── 5. CSS 变量使用 ──")
    var_declarations = re.findall(r'--([\w-]+)\s*:', html)
    if var_declarations:
        for var in set(var_declarations):
            usage_count = len(re.findall(rf'var\(--{re.escape(var)}\)', html))
            if usage_count == 0:
                warn(f"--{var}: 声明了但未使用")
            elif usage_count == 1:
                ok(f"--{var}: 使用 {usage_count} 次")
            else:
                ok(f"--{var}: 使用 {usage_count} 次")
    else:
        warn("无 CSS 变量声明")

    # ── 6. layer-fx 内容检查 ──
    print("\n── 6. 三层架构完整性 ──")
    layer_fx_blocks = re.findall(r'class="layer-fx"', html)
    layer_bg_blocks = re.findall(r'class="layer-bg"', html)
    layer_content_blocks = re.findall(r'class="layer-content"', html)

    ok(f"layer-bg: {len(layer_bg_blocks)} 个") if layer_bg_blocks else warn("layer-bg 缺失")
    ok(f"layer-fx: {len(layer_fx_blocks)} 个") if layer_fx_blocks else warn("layer-fx 缺失")
    ok(f"layer-content: {len(layer_content_blocks)} 个") if layer_content_blocks else warn("layer-content 缺失")

    # 检查 layer-fx 是否有实际内容（不只是空 div）
    fx_with_content = 0
    fx_empty = 0
    for fx_match in re.finditer(r'class="layer-fx"([^>]*>)((?:(?!</div>).)*?)</div>', html, re.DOTALL):
        content = fx_match.group(2).strip()
        # 去掉空白后还有内容
        content_clean = re.sub(r'\s+', '', content)
        if content_clean:
            fx_with_content += 1
        else:
            fx_empty += 1

    if fx_empty > 0:
        warn(f"layer-fx 有 {fx_empty} 个空容器（特效层没内容）")
    if fx_with_content > 0:
        ok(f"layer-fx 有 {fx_with_content} 个含内容的层")

    # ── 7. HyperFrames 结构完整性 ──
    print("\n── 7. HyperFrames 结构完整性 ──")

    # __timelines 必须是 {} 不是 []
    if re.search(r'window\.__timelines\s*=\s*\[\]', html):
        fail("__timelines 是 []（应为 {}）")
    elif re.search(r'window\.__timelines\s*=\s*(window\.__timelines\s*\|\|\s*)?\{', html):
        ok("__timelines 是 {} 对象")
    else:
        fail("__timelines 未定义或格式异常")

    # timeline paused: true
    if re.search(r'paused:\s*true', html):
        ok("timeline 设置了 paused: true")
    else:
        fail("timeline 未设置 paused: true（渲染会立即播放，导致时间线错误）")

    # data-composition-id 在根元素上
    if re.search(r'data-composition-id', html):
        ok("有 data-composition-id")
    else:
        fail("缺少 data-composition-id（HyperFrames 无法识别 composition）")

    # 内容元素 opacity:0 检查（先剥离 @keyframes 动画帧，避免把动画起始 opacity:0 误判为内容隐藏）
    html_no_kf = re.sub(r'@keyframes\s+[\w-]+\s*\{(?:[^{}]|\{[^{}]*\})*\}', '', html, flags=re.DOTALL)
    all_opacity_zero = len(re.findall(r'opacity:\s*0\s*;', html_no_kf))
    bg_glow_opacity = len(re.findall(
        r'(?:glow-orb|grid-overlay|layer-bg)[^}]*opacity:\s*0\s*;', html, re.DOTALL
    ))
    anim_opacity = len(re.findall(
        r'\.anim-in[^}]*opacity:\s*0\s*;', html, re.DOTALL
    ))
    content_opacity_zero = max(0, all_opacity_zero - bg_glow_opacity - anim_opacity)

    if content_opacity_zero > 5:
        fail(f"内容元素有 {content_opacity_zero} 处 opacity:0（会导致黑屏，应删除或改用 GSAP fromTo）")
    elif content_opacity_zero > 0:
        warn(f"内容元素有 {content_opacity_zero} 处 opacity:0（确认不是初始隐藏状态）")
    else:
        ok("内容元素无多余 opacity:0")

    # gsap.from() 应改为 fromTo
    from_count = len(re.findall(r'tl\.from\(', html))
    if from_count > 0:
        fail(f"使用了 {from_count} 处 gsap.from()（应改为 fromTo 防止黑屏）")
    else:
        ok("未使用 gsap.from()")

    # ── 8. 单层 padding 检查 ──
    print("\n── 8. 单层 padding 原则 ──")
    # 检测 scene-wrap 和 .phase 是否同时有 padding
    scene_wrap_padded = bool(re.search(
        r'\.scene-wrap[^{]*\{[^}]*padding\s*:\s*\d+', html, re.DOTALL
    )) or bool(re.search(
        r'class="scene-wrap"[^>]*style="[^"]*padding', html
    ))
    phase_padded = bool(re.search(
        r'\.phase\s*\{[^}]*padding\s*:\s*\d+', html, re.DOTALL
    ))

    if scene_wrap_padded and phase_padded:
        fail("scene-wrap 和 .phase 同时有 padding（双重 padding 导致内容偏左上，可用宽度仅 74%）— 删掉其中一层")
    elif not scene_wrap_padded and not phase_padded:
        warn("scene-wrap 和 .phase 均无 padding（内容可能贴边缘或塌陷）")
    else:
        which = ".scene-wrap" if scene_wrap_padded else ".phase"
        ok(f"安全区 padding 只在 {which} 一层设置（单层 padding 原则通过）")

    # ── 汇总 ──
    print("\n" + "=" * 50)
    print(f"  导演门禁: {PASS} 通过  {FAIL} 失败  {WARN} 警告")
    print("=" * 50)

    if FAIL > 0:
        print(f"\n\033[31m  导演门禁未通过 — 修复上述 ✗ 项后再渲染\033[0m")
        sys.exit(1)
    elif WARN > 3:
        print(f"\n\033[33m  警告较多（{WARN}），建议检查后再渲染\033[0m")
        sys.exit(0)
    else:
        print(f"\n\033[32m  导演门禁通过\033[0m")
        sys.exit(0)


if __name__ == "__main__":
    main()
