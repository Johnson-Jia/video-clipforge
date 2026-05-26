#!/usr/bin/env python3
"""
封面 7 层结构验证

解析 cover.html，检查 stage7-delivery.md §7.1 要求的 7 层视觉层次是否全部存在。
作为 render_cover.sh 的前置门禁：缺少任何一层直接 exit 1。

用法:
  python validate_cover.py cover.html
"""

import re
import sys
import io

# Windows GBK 终端兼容
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# 7 层必须存在的 CSS class / HTML 结构
# (层序号, 层名称, 检测方式: class名 或 标签名)
REQUIRED_LAYERS = [
    (1, '中文日期',      r'class="[^"]*\bdate\b'),
    (2, '场景标签',      r'class="[^"]*\bscene-label\b'),
    (3, '胶囊徽章',      r'class="[^"]*\bbadge\b'),
    (4, '主标题',        r'class="[^"]*\bmain-title\b'),
    (5, '渐变分隔线',    r'class="[^"]*\bdivider\b'),
    (6, '数据说明',      r'class="[^"]*\bdata-subtitle\b'),
    (7, '数据卡片',      r'class="[^"]*\bcards\b'),
]

# 额外检查：背景双层光晕
OPTIONAL_CHECKS = [
    ('暖色光晕', r'class="[^"]*\bglow-warm\b'),
    ('冷色光晕', r'class="[^"]*\bglow-cool\b'),
]


def validate(html_path: str) -> bool:
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

    for layer_num, layer_name, pattern in REQUIRED_LAYERS:
        if re.search(pattern, content):
            print(f'  Layer {layer_num}: {layer_name} ✓')
        else:
            print(f'  Layer {layer_num}: {layer_name} ✗ MISSING')
            missing.append(layer_name)
            all_pass = False

    # 光晕检查（警告但不失败）
    for check_name, pattern in OPTIONAL_CHECKS:
        if not re.search(pattern, content):
            print(f'  WARNING: {check_name} 缺失（建议添加）')

    if not all_pass:
        print(f'\nFAIL: 缺少 {len(missing)} 层: {", ".join(missing)}')
        print('修复: 参照 stage7-delivery.md §7.1 封面 HTML 模板，补充缺失层级')
    else:
        print(f'\nPASS: 7 层结构验证通过')

    return all_pass


if __name__ == '__main__':
    html_file = sys.argv[1] if len(sys.argv) > 1 else 'cover.html'
    ok = validate(html_file)
    sys.exit(0 if ok else 1)
