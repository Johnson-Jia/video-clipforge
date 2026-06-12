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
    # ── 中文数字 + 行 ──
    '两行': [['liǎng'], ['háng']],
    '三行': [['sān'], ['háng']],
    '四行': [['sì'], ['háng']],
    '五行': [['wǔ'], ['háng']],
    '六行': [['liù'], ['háng']],
    '七行': [['qī'], ['háng']],
    '八行': [['bā'], ['háng']],
    '九行': [['jiǔ'], ['háng']],
    '零行': [['líng'], ['háng']],
    # ── 长(cháng) 上下文 — 防止 edge-tts 读成 zhǎng ──
    '长视频': [['cháng'], ['shì'], ['pín']],
    '长篇': [['cháng'], ['piān']],
    '长文': [['cháng'], ['wén']],
    '长尾': [['cháng'], ['wěi']],
    '长期': [['cháng'], ['qī']],
    '长线': [['cháng'], ['xiàn']],
    '长河': [['cháng'], ['hé']],
    '长途': [['cháng'], ['tú']],
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

# ── K 数字转换：edge-tts 把 K 读成英文字母 ──
# 规则：1K = 一千, 10K = 一万, 29K = 二万九千, 290K = 二十九万
# 匹配：整数或小数 + K/k（可能后面跟空格或其他非字母字符）
_K_PATTERN = re.compile(r'(\d+\.?\d*)\s*[Kk]\b')

# ── 发音易错词替换 ──
# edge-tts 容易读错的常用词 → 同义且无歧义的替代
_PRONUNCIATION_FIXES = {
    '干嘛': '干什么',
}


def _convert_k_to_chinese(num_str: str) -> str:
    """将数字字符串 + K 转为中文读法。

    规则：
      一位数字 + K = X千    (1K → 一千, 5K → 五千)
      两位数字 + K = X万X千  (10K → 一万, 29K → 二万九千)
      三位数字 + K = XX万X千  (150K → 十五万, 290K → 二十九万)
    """
    num = float(num_str)
    has_decimal = '.' in num_str
    cn_digits = '零一二三四五六七八九'

    def digit_to_cn(d: int) -> str:
        return cn_digits[d]

    def int_to_cn(n: int) -> str:
        """0-999 整数转中文（无单位，纯数字拼接）"""
        if n == 0:
            return '零'
        s = ''
        hundreds = n // 100
        if hundreds > 0:
            s += digit_to_cn(hundreds) + '百'
            n %= 100
            if n > 0 and n < 10:
                s += '零'
        tens = n // 10
        if tens > 0:
            if tens > 1 or hundreds > 0:
                s += digit_to_cn(tens) + '十'
            else:
                s += '十'  # 10-19 的十不需要"一十"
            n %= 10
        elif hundreds and hundreds > 0 and n > 0:
            pass  # already added 零
        if n > 0:
            s += digit_to_cn(n)
        return s

    if has_decimal:
        int_part = int(num)
        dec_str = num_str.split('.')[1].rstrip('0')
        # 小数部分逐位读：28.8K = 二万八千八百
        wan = int_part // 10
        qian = int_part % 10
        result = ''
        if wan > 0:
            result += digit_to_cn(wan) + '万'
        if qian > 0:
            result += digit_to_cn(qian) + '千'
        for d in dec_str:
            result += digit_to_cn(int(d)) + '百'
            break  # 只处理一位小数
        return result.rstrip('零') or '零'

    int_val = int(num)
    if int_val < 10:
        # X K = X千
        return digit_to_cn(int_val) + '千'
    elif int_val < 100:
        # XX K = X万X千
        wan = int_val // 10
        qian = int_val % 10
        result = ''
        if wan == 1:
            result = '一万'
        else:
            result = digit_to_cn(wan) + '万'
        if qian > 0:
            result += digit_to_cn(qian) + '千'
        return result
    else:
        # XXX K = XX万X千
        wan_part = int_val // 10
        qian = int_val % 10
        result = int_to_cn(wan_part) + '万'
        if qian > 0:
            result += digit_to_cn(qian) + '千'
        return result


# ── 正则定向替换（pypinyin 词组匹配失败时的兜底） ──
# 阿拉伯数字 + 行：pypinyin 无法匹配阿拉伯数字上下文
# "300行" → "300航", "100多行" → "100多航"
_NUMERIC_ROW_RE = re.compile(r'(\d+)\s*(多?)行')
# 中文数字组合 + 行：匹配 "四万两千行", "七千行", "一百二十行" 等
# pypinyin 无法匹配长中文数字串的上下文
_CN_NUM_CHARS = '一二三四五六七八九十百千万亿两零'
_CN_NUMERIC_ROW_RE = re.compile(f'([{_CN_NUM_CHARS}]+)行')
# 长→常：仅限已知 edge-tts 会把长读成 zhǎng 的上下文
_LONG_AS_CHANG_RE = re.compile(r'长(视频|篇|文|尾|期|线|河|途)')
# 周期长→周期常（长作后缀，edge-tts 读成 zhǎng）
_PERIOD_LONG_AS_CHANG_RE = re.compile(r'(周期)长')

# 初始化：加载自定义词组
load_phrases_dict(_CUSTOM_PHRASES)


def fix(text: str) -> str:
    """处理文本中的品牌名外文词 + K数字 + 发音易错词 + 多音字，返回替换后的文本。"""

    if not text:
        return text

    # ── 第零步：发音易错词替换（在所有处理之前） ──
    for wrong, correct in _PRONUNCIATION_FIXES.items():
        if wrong in text:
            text = text.replace(wrong, correct)
            print(f'[polyphone_fix] pronunciation fix: {wrong} → {correct}')

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

    # ── 第一步：K 数字转中文 ──
    k_replaced = _K_PATTERN.sub(
        lambda m: _convert_k_to_chinese(m.group(1)),
        brand_replaced
    )
    if k_replaced != brand_replaced:
        print(f'[polyphone_fix] K-number conversion applied')

    # ── 第一步半：正则定向替换 ──
    # 阿拉伯数字 + 行 → 航（pypinyin 无法匹配阿拉伯数字上下文）
    preprocessed = _NUMERIC_ROW_RE.sub(r'\1\2航', k_replaced)
    if preprocessed != k_replaced:
        print(f'[polyphone_fix] numeric+行 regex applied')

    # 中文数字组合 + 行 → 航（pypinyin 无法匹配长中文数字串上下文）
    preprocessed = _CN_NUMERIC_ROW_RE.sub(r'\1航', preprocessed)
    if preprocessed != k_replaced:
        print(f'[polyphone_fix] CN-numeric+行 regex applied')

    # 长→常（仅限已知误读上下文，避免全局替换影响字幕）
    preprocessed = _LONG_AS_CHANG_RE.sub(r'常\1', preprocessed)
    preprocessed = _PERIOD_LONG_AS_CHANG_RE.sub(r'\1常', preprocessed)
    if preprocessed != k_replaced:
        print(f'[polyphone_fix] 长→常 regex applied')

    # ── 第二步：多音字替换（原逻辑） ──
    if not any('一' <= c <= '鿿' for c in preprocessed):
        return preprocessed

    # 获取每个字的上下文感知拼音
    # errors=lambda 确保非汉字字符逐字符返回，维持 pinyin_list 与 chars 长度对齐
    # 否则连续外文（如 Docker、CPU）会被合并为一个元素，导致 zip 对齐错位
    pinyin_list = pinyin(preprocessed, style=Style.TONE3, errors=lambda x: list(x))

    chars = list(preprocessed)
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
    if modified and result != preprocessed:
        changes = []
        for i, (oc, nc) in enumerate(zip(preprocessed, result)):
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
            # 长视频定向替换
            ('长视频', '常视频'),
            ('长视频和短视频', '常视频和短视频'),
            # 周期长→周期常（长作后缀）
            ('企业销售周期长', '企业销售周期常'),
            ('周期长是客观现实', '周期常是客观现实'),
            # 阿拉伯数字+行
            ('300行代码', '300航代码'),
            ('100多行代码', '100多航代码'),
            # 中文大数字组合+行
            ('四万两千行Python', '四万两千航Python'),
            ('七千行TypeScript', '七千航TypeScript'),
            ('一百二十行配置', '一百二十航配置'),
            # K 数字转换
            ('1K Stars', '一千 Stars'),
            ('5K', '五千'),
            ('10K', '一万'),
            ('29K', '二万九千'),
            ('30K', '三万'),
            ('150K', '十五万'),
            ('290K', '二十九万'),
            ('28.8K', '二万八千八百'),
            ('Stars从1500暴涨到28800', 'Stars从1500暴涨到28800'),
            # 发音易错词
            ('这能干嘛', '这能干什么'),
            ('你能干嘛呢', '你能干什么呢'),
        ]
        passed = 0
        for inp, expected in tests:
            result = fix(inp)
            ok = result == expected
            passed += ok
            status = 'PASS' if ok else 'FAIL'
            print(f'{status}: "{inp}" → "{result}" (expected "{expected}")')
        print(f'\nSelf-test: {passed}/{len(tests)} passed')
