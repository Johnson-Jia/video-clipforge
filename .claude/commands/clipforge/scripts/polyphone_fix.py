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
    """处理文本中的多音字，返回替换后的文本。"""
    if not text or not any('一' <= c <= '鿿' for c in text):
        return text

    # 获取每个字的上下文感知拼音
    pinyin_list = pinyin(text, style=Style.TONE3)

    chars = list(text)
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
    if modified and result != text:
        changes = []
        for i, (oc, nc) in enumerate(zip(text, result)):
            if oc != nc:
                changes.append(f"  pos {i}: '{oc}' ({pinyin_list[i][0]}) → '{nc}'")
        print(f'[polyphone_fix] {len(changes)} replacement(s):')
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
            ('一行命令就能装好', '一航命令就能装好'),
            ('银行存款', '银航存款'),  # 银行 → 行=háng, edge-tts gets this right but we replace anyway
            ('行业领先', '航业领先'),
            ('行走江湖', '行走江湖'),  # 行=xíng, no change
            ('重庆火锅', '虫庆火锅'),
            ('重要通知', '重要通知'),  # 重=zhòng, default, no change
            ('几行代码', '几航代码'),
            ('音乐疗法', '音悦疗法'),
            ('快乐生活', '快乐生活'),  # 乐=lè, default, no change
        ]
        passed = 0
        for inp, expected in tests:
            result = fix(inp)
            ok = result == expected
            passed += ok
            status = 'PASS' if ok else 'FAIL'
            print(f'{status}: "{inp}" → "{result}" (expected "{expected}")')
        print(f'\nSelf-test: {passed}/{len(tests)} passed')
