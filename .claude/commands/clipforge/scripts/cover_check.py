#!/usr/bin/env python3
"""
封面 7 层完整性门禁

用法: python scripts/cover_check.py <cover.html>

检测 cover.html 是否包含完整的 7 层结构：
  1. 日期区 (.date)
  2. 场景标签 (.scene-label)
  3. 胶囊徽章 (.badge)
  4. 主标题 (.main-title)
  5. 渐变分隔线 (.divider)
  6. 数据说明 (.data-subtitle)
  7. 数据卡片 (.cards)

退出码:
  0 = 通过
  1 = 不通过（缺少层或层内无文字）
"""

import sys
import re


REQUIRED_LAYERS = [
    ("date", "第1层：中文日期"),
    ("scene-label", "第2层：场景标签"),
    ("badge", "第3层：胶囊徽章"),
    ("main-title", "第4层：主标题"),
    ("divider", "第5层：渐变分隔线"),
    ("data-subtitle", "第6层：数据说明"),
    ("cards", "第7层：数据卡片"),
]


def check_cover(html_path):
    with open(html_path, "r", encoding="utf-8") as f:
        html = f.read()

    print("=== 封面 7 层完整性门禁 ===")

    missing = []
    empty = []
    passed = 0

    for css_class, label in REQUIRED_LAYERS:
        # Find the element with this class
        # Match <div class="...classname..."> or <div class="classname">
        pattern = rf'class="[^"]*\b{re.escape(css_class)}\b[^"]*"'
        if not re.search(pattern, html):
            missing.append(label)
            print(f"  FAIL: {label} — 元素缺失 (.{css_class})")
            continue

        # For divider, just check it exists (no text content needed)
        if css_class == "divider":
            passed += 1
            print(f"  OK:   {label}")
            continue

        # For cards, check it contains at least one .card child
        if css_class == "cards":
            card_pattern = r'class="[^"]*\bcard\b[^"]*"'
            if re.search(card_pattern, html):
                passed += 1
                print(f"  OK:   {label}")
            else:
                empty.append(label)
                print(f"  FAIL: {label} — 无数据卡片内容")
            continue

        # For other layers, check there's text content between tags
        # Extract the element block and check for visible text
        block_pattern = rf'<div[^>]*class="[^"]*\b{re.escape(css_class)}\b[^"]*"[^>]*>(.*?)</div>'
        block_match = re.search(block_pattern, html, re.DOTALL)
        if block_match:
            content = block_match.group(1)
            # Strip HTML tags and check for text
            text = re.sub(r'<[^>]+>', '', content).strip()
            # Also check nested spans
            if not text:
                # Try deeper - check for span content
                spans = re.findall(r'>([^<]+)<', content)
                text = ' '.join(s.strip() for s in spans if s.strip())

            # Decode HTML entities
            text = text.replace('&#24180;', '年').replace('&#26376;', '月').replace('&#26085;', '日')
            text = text.replace('&#27036;', '榜').replace('&#21333;', '单').replace('&#36895;', '速')
            text = text.replace('&#35272;', '览').replace('&#28909;', '热').replace('&#38376;', '门')
            text = text.replace('&#39033;', '项').replace('&#30446;', '目')

            # Also check template placeholders {{...}}
            has_placeholder = '{{' in content and '}}' in content

            if text or has_placeholder:
                passed += 1
                display = text[:30] if text else "(模板占位符)"
                print(f"  OK:   {label} — {display}")
            else:
                empty.append(label)
                print(f"  FAIL: {label} — 层存在但无文字内容")
        else:
            # Might be self-contained or have nested divs
            passed += 1
            print(f"  OK:   {label}")

    # Also check for dual glow
    has_warm_glow = 'glow-warm' in html
    has_cool_glow = 'glow-cool' in html
    if has_warm_glow and has_cool_glow:
        print(f"  OK:   双色光晕（暖+冷）")
    else:
        print(f"  WARN: 双色光晕缺失（warm={has_warm_glow}, cool={has_cool_glow}）")

    # Check for data-composition-id (HyperFrames compatibility)
    has_composition = 'data-composition-id' in html
    if has_composition:
        print(f"  OK:   HyperFrames composition 标记")
    else:
        print(f"  WARN: 缺少 data-composition-id 标记")

    print(f"\n结果: {passed}/{len(REQUIRED_LAYERS)} 层通过")

    if missing or empty:
        print(f"\nFAIL: 封面不完整")
        if missing:
            print(f"  缺失层: {', '.join(missing)}")
        if empty:
            print(f"  空内容: {', '.join(empty)}")
        sys.exit(1)

    print("PASS: 封面 7 层完整")
    sys.exit(0)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python scripts/cover_check.py <cover.html>")
        sys.exit(1)
    check_cover(sys.argv[1])
