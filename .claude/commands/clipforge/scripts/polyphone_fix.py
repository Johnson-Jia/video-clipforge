#!/usr/bin/env python3
"""
多音字自动预处理器

在 TTS 前自动检测和替换多音字，修复 edge-tts 发音错误。
原理：pypinyin 上下文感知拼音 + 自定义词组修正 → 同音无歧义字替换。

用法:
  from polyphone_fix import fix
  cleaned = fix("一行命令就能装好")  # → "一航命令就能装好"

  # 或命令行
  python polyphone_fix.py "一行命令就能装好"
"""

import re
from pypinyin import pinyin, Style, load_phrases_dict

# ═══════════════════════════════════════════════════
# 外文品牌名 → TTS 可发音中文映射
# ═══════════════════════════════════════════════════
# 规则：
# - 中文 TTS 引擎无法正确发音的外文品牌名必须映射
# - 使用品牌官方中文名或通用中文译名
# - TTS 可正确发音的（如 "Python"、"Rust"）不需要映射
# - 大小写不敏感匹配
BRAND_PRONUNCIATION_MAP = {
    # 大模型
    'Qwen':       '千问',
    'Qwen3':      '千问三',
    'Qwen3.7':    '千问三点七',
    'Qwen3.7-max': '千问三点七max',
    'ChatGPT':    'ChatGPT',       # TTS 可直接发音，保留
    'Claude':     '克劳德',
    'Claude Code':'克劳德扣得',
    'Gemini':     'Gemini',        # TTS 可发音
    'GLM':        'GLM',           # 三个字母 TTS 可拼读
    'DeepSeek':   '深度求索',
    'Llama':      '拉玛',
    'Mistral':    '密斯特拉尔',
    'Midjourney': '中途',
    # 开发工具
    'Copilot':    '副驾驶',
    'HuggingFace': '哈金Face',
    'Supabase':   '苏帕贝斯',
    'Vercel':     '维尔塞尔',
    'Netlify':    '奈特利菲',
    'PostgreSQL': 'PostgreSQL',    # TTS 基本可发音
}

# 构建匹配用的正则：按 key 长度降序排列（长匹配优先）
_BRAND_KEYS_SORTED = sorted(BRAND_PRONUNCIATION_MAP.keys(), key=len, reverse=True)
_BRAND_PATTERN = re.compile(
    r'\b(' + '|'.join(re.escape(k) for k in _BRAND_KEYS_SORTED) + r')\b',
    re.IGNORECASE | re.ASCII
)

# ── 自定义词组：修正 pypinyin 本身判断错误的短语 ──
_CUSTOM_PHRASES = {
    '一行': [['yì'], ['háng']],
    '第三行': [['dì'], ['sān'], ['háng']],
    '每行': [['měi'], ['háng']],
    '这行': [['zhè'], ['háng']],
    '那行': [['nà'], ['háng']],
    '上行': [['shàng'], ['háng']],
    '下行': [['xià'], ['háng']],
    '中行': [['zhōng'], ['háng']],
    '十行': [['shí'], ['háng']],
    '百行': [['bǎi'], ['háng']],
    '千行': [['qiān'], ['háng']],
    '万行': [['wàn'], ['háng']],
    '几行': [['jǐ'], ['háng']],
    '多行': [['duō'], ['háng']],
    '首行': [['shǒu'], ['háng']],
    '末行': [['mò'], ['háng']],
    '空行': [['kōng'], ['háng']],
    '代码行': [['dài'], ['mǎ'], ['háng']],
    '命令行': [['mìng'], ['lìng'], ['háng']],
}

# ── 多音字替换映射 ──
# 格式: 字 → {拼音(含声调数字): 替换字}
# 替换字选择标准: 同拼音同声调、无多音歧义、常用字
# 只列出 edge-tts 会读错的非默认读音
_POLYPHONE_MAP = {
    '行': {'hang2': '航'},
    '长': {'zhang3': '掌'},
    '重': {'chong2': '虫'},
    '乐': {'yue4': '悦'},
    '会': {'kuai4': '快'},
    '得': {'dei3': '得'},  # 得 as modal is rare, skip
    '几': {'ji1': '机'},
    '处': {'chu4': '触'},  # 处 as place: chù → 触 (but 触 is chù too)
    '为': {'wei4': '未'},  # 为 as "because": wèi → 未
}

# 初始化：加载自定义词组
load_phrases_dict(_CUSTOM_PHRASES)


def fix(text: str) -> str:
    """处理文本中的品牌名外文词 + 多音字，返回替换后的文本。"""

    if not text:
        return text

    # ── 第一步：外文品牌名替换（大小写不敏感） ──
    brand_replaced = _BRAND_PATTERN.sub(
        lambda m: BRAND_PRONUNCIATION_MAP.get(
            next(k for k in _BRAND_KEYS_SORTED if k.lower() == m.group(0).lower()),
            m.group(0)
        ),
        text
    )
    if brand_replaced != text:
        changes = []
        for orig, repl in zip(text.split(), brand_replaced.split()):
            if orig != repl:
                changes.append(f"  '{orig}' -> '{repl}'")
        if changes:
            print(f'[polyphone_fix] {len(changes)} brand replacement(s):')
            for c in changes:
                print(c)

    # ── 第二步：多音字替换（原逻辑） ──
    if not any('一' <= c <= '鿿' for c in brand_replaced):
        return brand_replaced

    # 获取每个字的上下文感知拼音
    pinyin_list = pinyin(brand_replaced, style=Style.TONE3)

    chars = list(brand_replaced)
    modified = False

    for i, (char, py) in enumerate(zip(chars, pinyin_list)):
        py_str = py[0]

        # 跳过非汉字
        if not ('一' <= char <= '鿿'):
            continue

        # 检查是否在多音字映射中
        if char in _POLYPHONE_MAP:
            replacements = _POLYPHONE_MAP[char]
            if py_str in replacements:
                replacement = replacements[py_str]
                chars[i] = replacement
                modified = True

    result = ''.join(chars)
    if modified and result != brand_replaced:
        changes = []
        for i, (oc, nc) in enumerate(zip(brand_replaced, result)):
            if oc != nc:
                changes.append(f"  pos {i}: '{oc}' ({pinyin_list[i][0]}) → '{nc}'")
        print(f'[polyphone_fix] {len(changes)} polyphone replacement(s):')
        for c in changes:
            print(c)

    return result


if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1:
        text = sys.argv[1]
        print(f'Input:  {text}')
        print(f'Output: {fix(text)}')
    else:
        # 自检测试
        tests = [
            # 多音字
            ('一行命令就能装好', '一航命令就能装好'),
            ('命令行', '命令航'),
            ('银行存款', '银航存款'),
            ('行业领先', '航业领先'),
            ('行走江湖', '行走江湖'),
            ('重庆火锅', '虫庆火锅'),
            ('重要通知', '重要通知'),
            ('几行代码', '几航代码'),
            ('音乐疗法', '音悦疗法'),
            ('快乐生活', '快乐生活'),
            # 品牌名
            ('Qwen只有21分', '千问只有21分'),
            ('GLM vs Qwen3.7', 'GLM vs 千问三点七'),
            ('用了三个月智谱GLM大模型', '用了三个月智谱GLM大模型'),
            ('结果Qwen说进全球前三了', '结果千问说进全球前三了'),
            # 品牌名 + 多音字组合
            ('Qwen跑了一行命令', '千问跑了一航命令'),
        ]
        passed = 0
        for inp, expected in tests:
            result = fix(inp)
            ok = result == expected
            passed += ok
            status = 'PASS' if ok else 'FAIL'
            print(f'{status}: "{inp}" → "{result}" (expected "{expected}")')
        print(f'\nSelf-test: {passed}/{len(tests)} passed')
