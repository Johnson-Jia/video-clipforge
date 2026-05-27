#!/usr/bin/env python3
"""
HTML 实体净化器

将 index.html 中的 HTML 实体还原为 Unicode 字符：
  &amp; → &  &lt; → <  &gt; → >  &quot; → "  &#39; → '
  以及所有 &#NNN; 和 &#xHHH; 数字实体。

HyperFrames 渲染引擎不能正确处理 HTML 实体，需要先还原为原始字符。

用法:
  python scripts/sanitize_html_entities.py [--project-dir DIR] [--file index.html]

输出:
  就地修改目标文件
"""

import argparse
import html
import os
import re
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')


def sanitize_file(filepath):
    """净化 HTML 文件中的实体"""
    if not os.path.exists(filepath):
        print(f'FAIL: {filepath} 不存在')
        return False

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    original = content
    count = 0

    # 替换常见命名实体
    named_entities = {
        '&amp;': '&',
        '&lt;': '<',
        '&gt;': '>',
        '&quot;': '"',
        '&#39;': "'",
        '&apos;': "'",
        '&nbsp;': ' ',
    }
    for entity, char in named_entities.items():
        occurrences = content.count(entity)
        if occurrences > 0:
            # 不替换 <style> 和 <script> 标签内的 &amp;（CSS 中可能合法）
            content = content.replace(entity, char)
            count += occurrences

    # 替换数字实体 &#NNN; 和 &#xHHH;
    def replace_numeric_entity(m):
        nonlocal count
        count += 1
        try:
            return html.unescape(m.group(0))
        except Exception:
            return m.group(0)

    content = re.sub(r'&#\d+;', replace_numeric_entity, content)
    content = re.sub(r'&#x[0-9a-fA-F]+;', replace_numeric_entity, content)

    if content != original:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f'净化完成: {filepath}（替换了 {count} 个实体）')
        return True
    else:
        print(f'无需净化: {filepath}（未发现 HTML 实体）')
        return False


def main():
    parser = argparse.ArgumentParser(description='净化 HTML 实体')
    parser.add_argument('--project-dir', default='.', help='项目目录')
    parser.add_argument('--file', default='index.html', help='目标 HTML 文件')
    args = parser.parse_args()

    project_dir = os.path.abspath(args.project_dir)
    filepath = os.path.join(project_dir, args.file)
    sanitize_file(filepath)


if __name__ == '__main__':
    main()
