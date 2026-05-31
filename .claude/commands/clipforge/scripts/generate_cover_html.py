#!/usr/bin/env python3
"""
封面 HTML 6 层模板生成器

从 design.md + narration_segments.json 读取元数据，生成符合 stage7-delivery.md §7.1 的 cover.html。

用法:
  python scripts/generate_cover_html.py [--project-dir DIR]

输出:
  cover.html — 写入项目目录
"""

import argparse
import json
import os
import re
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')


def parse_frontmatter(filepath):
    """解析 Markdown frontmatter，返回 dict"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    m = re.match(r'^---\s*\n(.*?)\n---', content, re.DOTALL)
    if not m:
        return {}
    meta = {}
    for line in m.group(1).split('\n'):
        if ':' in line:
            key, val = line.split(':', 1)
            meta[key.strip()] = val.strip().strip('"\'')
    return meta


def extract_title(narration_path):
    """从 narration_segments.json 提取标题（第一个 segment 的关键词）"""
    with open(narration_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    segments = data if isinstance(data, list) else data.get('segments', [])
    if segments:
        text = segments[0].get('text', '')
        # 取第一句的前 20 字作为标题候选
        first_sentence = re.split(r'[。！？\n]', text)[0].strip()
        return first_sentence[:30] if first_sentence else '精彩内容'
    return '精彩内容'


def read_design_style(project_dir):
    """从 design.md 读取风格和配色方向"""
    design_path = os.path.join(project_dir, 'design.md')
    if not os.path.exists(design_path):
        return {}, {}
    meta = parse_frontmatter(design_path)
    return meta


def generate_cover_html(project_dir, title, design_meta, scene_label="", orientation="portrait"):
    """生成封面 HTML（竖屏 7 层 / 横屏 7 层+安全区）"""
    style = design_meta.get('style', '科技赛博')
    accent_cool = '#00f5d4' if '赛博' in style or '科技' in style else '#4cc9f0'
    accent_warm = '#f9a825' if '赛博' in style or '科技' in style else '#ff6b6b'
    is_landscape = orientation == 'landscape'

    # 尝试从 content_summary.md 获取更精确标题
    summary_path = os.path.join(project_dir, 'content_summary.md')
    if os.path.exists(summary_path):
        with open(summary_path, 'r', encoding='utf-8') as f:
            first_line = f.readline().strip()
            if first_line and first_line.startswith('#'):
                first_line = first_line.lstrip('#').strip()
            if first_line and len(first_line) > 3:
                title = first_line[:40]

    # 从 douyin.md 取标签
    tags = []
    douyin_path = os.path.join(project_dir, 'douyin.md')
    if os.path.exists(douyin_path):
        with open(douyin_path, 'r', encoding='utf-8') as f:
            content = f.read()
        tag_match = re.search(r'标签[：:]\s*(.*)', content)
        if tag_match:
            tags = [t.strip() for t in tag_match.group(1).split('#') if t.strip()][:3]

    badge_text = tags[0] if tags else style
    date_text = __import__('datetime').datetime.now().strftime('%Y年%m月%d日')

    if is_landscape:
        return _generate_landscape(title, date_text, scene_label, badge_text, tags, accent_warm, accent_cool)
    else:
        return _generate_portrait(title, date_text, scene_label, badge_text, tags, accent_warm, accent_cool)


def _generate_portrait(title, date_text, scene_label, badge_text, tags, accent_warm, accent_cool):
    """竖屏封面（1080×1920）"""
    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=1080, height=1920, initial-scale=1">
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    width: 1080px; height: 1920px;
    background: linear-gradient(160deg, #0a0a0f 0%, #1a1a2e 40%, #16213e 100%);
    font-family: 'Noto Sans SC', sans-serif;
    color: white;
    overflow: hidden;
    position: relative;
  }}
  /* 背景双层光晕 */
  .glow-warm {{
    position: absolute; top: 30%; left: -10%;
    width: 600px; height: 600px;
    background: radial-gradient(circle, {accent_warm}33 0%, transparent 70%);
    border-radius: 50%;
  }}
  .glow-cool {{
    position: absolute; bottom: 20%; right: -5%;
    width: 500px; height: 500px;
    background: radial-gradient(circle, {accent_cool}22 0%, transparent 70%);
    border-radius: 50%;
  }}
  .container {{
    position: relative; z-index: 1;
    width: 100%; height: 100%;
    display: flex; flex-direction: column;
    justify-content: center; align-items: center;
    padding: 200px 80px 300px 80px;
    text-align: center;
  }}
  /* Layer 1: 日期 */
  .date {{
    font-size: 36px; color: rgba(255,255,255,0.6);
    letter-spacing: 4px; margin-bottom: 40px;
    font-weight: 300;
  }}
  /* Layer 2: 场景标签 */
  .scene-label {{
    font-size: 32px; color: {accent_cool};
    letter-spacing: 6px; text-transform: uppercase;
    margin-bottom: 30px; font-weight: 400;
  }}
  /* Layer 3: 胶囊徽章 */
  .badge {{
    display: inline-block;
    padding: 12px 36px;
    border: 2px solid {accent_cool};
    border-radius: 50px;
    font-size: 28px; color: {accent_cool};
    letter-spacing: 3px; margin-bottom: 60px;
  }}
  /* Layer 4: 主标题 */
  .main-title {{
    font-size: 72px; font-weight: 900;
    line-height: 1.2; margin-bottom: 50px;
    background: linear-gradient(135deg, #ffffff 0%, {accent_cool} 100%);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    background-clip: text;
  }}
  /* Layer 5: 渐变分隔线 */
  .divider {{
    width: 200px; height: 4px;
    background: linear-gradient(90deg, transparent, {accent_cool}, {accent_warm}, transparent);
    margin: 0 auto 50px; border-radius: 2px;
  }}
  /* Layer 6: 数据说明 */
  .data-subtitle {{
    font-size: 36px; color: rgba(255,255,255,0.7);
    font-weight: 300; margin-bottom: 30px;
  }}
  .cards {{
    display: flex; gap: 24px; justify-content: center; flex-wrap: wrap;
  }}
  .card {{
    background: rgba(255,255,255,0.06);
    border: 1px solid rgba(255,255,255,0.1);
    border-radius: 16px; padding: 24px 32px;
    font-size: 28px; color: rgba(255,255,255,0.8);
  }}
</style>
</head>
<body>
  <div class="glow-warm"></div>
  <div class="glow-cool"></div>
  <div class="container">
    <div class="date">{date_text}</div>
    <div class="scene-label">{scene_label}</div>
    <div class="badge">{badge_text}</div>
    <div class="main-title">{title}</div>
    <div class="divider"></div>
    <div class="data-subtitle">点击观看完整内容</div>
    <div class="cards">
      {"".join(f'<div class="card">{t}</div>' for t in tags[:3]) if tags else '<div class="card">AI 精选</div>'}
    </div>
  </div>
</body>
</html>'''

    return html


def _generate_landscape(title, date_text, scene_label, badge_text, tags, accent_warm, accent_cool):
    """横屏封面（1920×1080，3:4 安全区 810px 居中）"""
    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
html,body{{width:1920px;height:1080px;overflow:hidden;font-family:'PingFang SC','Microsoft YaHei',sans-serif}}
.root{{position:relative;width:1920px;height:1080px;overflow:hidden}}
.cover{{
  position:absolute;top:0;left:0;width:1920px;height:1080px;
  background:linear-gradient(120deg,#0a0a0f 0%,#1a1a2e 30%,#16213e 70%,#0d0d2a 100%);
  color:#fff;
}}
.glow-warm{{
  position:absolute;top:-80px;left:-120px;width:500px;height:500px;border-radius:50%;
  background:radial-gradient(circle,{accent_warm}25 0%,transparent 70%);filter:blur(80px);z-index:1;
}}
.glow-cool{{
  position:absolute;bottom:-100px;right:-80px;width:400px;height:400px;border-radius:50%;
  background:radial-gradient(circle,{accent_cool}18 0%,transparent 70%);filter:blur(80px);z-index:1;
}}
/* 3:4 安全区（810×1080 水平居中） */
.safe-zone{{
  position:relative;z-index:5;
  width:810px;height:100%;
  margin:0 auto;
  display:flex;flex-direction:column;
  align-items:center;justify-content:center;
}}
.date{{font-size:28px;opacity:0.6;letter-spacing:4px;margin-bottom:16px}}
.scene-label{{font-size:22px;text-transform:uppercase;letter-spacing:6px;color:{accent_cool};margin-bottom:16px}}
.badge{{
  display:inline-block;
  background:rgba(255,255,255,0.06);
  border:1px solid {accent_cool}66;
  padding:8px 24px;border-radius:50px;
  font-size:22px;font-weight:600;color:{accent_cool};margin-bottom:36px;
}}
.main-title{{
  font-size:68px;font-weight:900;text-align:center;line-height:1.25;
  letter-spacing:-2px;margin-bottom:12px;
}}
.main-title .accent{{
  background:linear-gradient(135deg,{accent_cool},{accent_warm});
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;
}}
.divider{{
  width:220px;height:3px;
  background:linear-gradient(90deg,transparent,{accent_cool},{accent_warm},transparent);
  margin-bottom:20px;
}}
.data-subtitle{{font-size:26px;font-weight:600;text-align:center;opacity:0.7;margin-bottom:20px}}
.cards{{display:flex;gap:12px;flex-wrap:wrap;justify-content:center}}
.card{{
  text-align:center;background:rgba(255,255,255,0.05);
  border:1px solid rgba(255,255,255,0.1);
  padding:14px 18px;border-radius:12px;min-width:150px;
}}
.card .val{{font-size:32px;font-weight:900;color:{accent_cool}}}
.card .lbl{{font-size:15px;opacity:0.5;margin-top:4px}}
</style>
</head>
<body>
<div class="root" data-composition-id="root" data-width="1920" data-height="1080">
<div class="cover">
  <div class="glow-warm"></div>
  <div class="glow-cool"></div>
  <div class="safe-zone">
    <div class="date">{date_text}</div>
    <div class="scene-label">{scene_label}</div>
    <div class="badge">{badge_text}</div>
    <div class="main-title">{title}</div>
    <div class="divider"></div>
    <div class="data-subtitle">点击观看完整内容</div>
    <div class="cards">
      {"".join(f'<div class="card"><div class="val">{t}</div></div>' for t in tags[:3]) if tags else '<div class="card"><div class="val">AI 精选</div></div>'}
    </div>
  </div>
</div>
<script>window.__hf = {{ duration: 1, seek: function(t) {{}} }};window.__timelines = {{}};</script>
</div>
</body>
</html>'''

    return html


def detect_orientation(project_dir):
    """从 design.md 检测方向，默认 portrait"""
    design_path = os.path.join(project_dir, 'design.md')
    if os.path.exists(design_path):
        with open(design_path, 'r', encoding='utf-8') as f:
            for line in f:
                m = re.match(r'^orientation:\s*(\w+)', line)
                if m:
                    val = m.group(1).strip().strip('"\'')
                    if val in ('landscape', 'portrait'):
                        return val
    return 'portrait'


def main():
    parser = argparse.ArgumentParser(description='生成封面 HTML 7 层模板')
    parser.add_argument('--project-dir', default='.', help='项目目录')
    parser.add_argument('--title', default=None, help='覆盖标题')
    parser.add_argument('--scene-label', default='', help='场景标签（如频道名）')
    parser.add_argument('--orientation', default=None, choices=['portrait', 'landscape'],
                        help='画布方向（默认从 design.md 自动检测）')
    args = parser.parse_args()

    project_dir = os.path.abspath(args.project_dir)

    # 方向检测：命令行参数 > design.md > 默认竖屏
    if args.orientation:
        orientation = args.orientation
    else:
        orientation = detect_orientation(project_dir)

    # 读取元数据
    narration_path = os.path.join(project_dir, 'narration_segments.json')
    design_meta = read_design_style(project_dir)

    if args.title:
        title = args.title
    elif os.path.exists(narration_path):
        title = extract_title(narration_path)
    else:
        title = '精彩内容'

    html = generate_cover_html(project_dir, title, design_meta,
                               scene_label=args.scene_label, orientation=orientation)

    output_path = os.path.join(project_dir, 'cover.html')
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f'生成封面: {output_path}')
    print(f'标题: {title}')
    print(f'方向: {orientation}')
    print(f'风格: {design_meta.get("style", "默认")}')


if __name__ == '__main__':
    main()
