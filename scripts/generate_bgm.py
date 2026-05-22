"""
智能配乐生成脚本 v3.0
====================
从内容文件自动提炼情绪，生成匹配的配乐。支持自定义提示词、情绪模板、参考风格、场景驱动。

使用方法:
  # 从项目内容文件自动分析情绪
  python generate_bgm.py --content-dir ../my-project --output bgm.wav

  # 自定义提示词
  python generate_bgm.py --prompt "mysterious dark ambient with guqin" --output bgm.wav

  # 指定情绪 + 参考风格
  python generate_bgm.py --mood mysterious --reference ghost_in_shell --output bgm.wav

  # 场景驱动多段拼接
  python generate_bgm.py --scene-file scenes.json --output bgm.wav

  # 指定时长
  python generate_bgm.py --mood epic --duration 45 --output bgm.wav

依赖:
  pip install torch transformers scipy
"""
import os
import sys
import json
import argparse
import numpy as np
import torch
import scipy.io.wavfile as wavfile
from pathlib import Path
from transformers import MusicgenForConditionalGeneration, AutoProcessor


# ═══════════════════════════════════════════════════════════════
# 情绪模板（不绑定固定风格，根据内容选择）
# ═══════════════════════════════════════════════════════════════

MOOD_TEMPLATES = {
    "suspense": (
        "mysterious dark ambient, sparse piano notes over deep drone, "
        "tension building with rising frequencies, cold metallic reverb, "
        "slow heartbeat rhythm, cinematic suspense, no vocals"
    ),
    "intense": (
        "aggressive industrial synthwave, driving bass at 140 BPM, "
        "distorted synth stabs, rapid arpeggios, pounding drums, "
        "wall of sound intensity, confrontational energy, no vocals"
    ),
    "epic": (
        "epic cinematic orchestral synth, thundering bass drops, "
        "massive choral swells, dramatic string ostinato, "
        "building to euphoric climax, heroic yet dark, "
        "128 BPM pulse, no vocals"
    ),
    "melancholic": (
        "bittersweet piano melody, gentle string accompaniment, "
        "melancholic minor key, rain-on-glass atmosphere, "
        "slowly evolving pads, nostalgic and reflective, "
        "intimate and personal, no vocals"
    ),
    "hopeful": (
        "bright synthesizer lead, major key progression, "
        "uplifting arpeggios, warm analog bass, "
        "building from gentle to triumphant, "
        "ethereal choir pads, hopeful crescendo, "
        "120 BPM, no vocals"
    ),
    "cyberpunk": (
        "dark cyberpunk synthwave, neon-tinged synthesizers, "
        "pulsing sub-bass at 128 BPM, retro-futuristic pads, "
        "glitch percussion, atmospheric tension, "
        "cold digital warmth, industrial textures, no vocals"
    ),
    "mysterious": (
        "ethereal ambient, distant choral echoes, "
        "celestial pads with slow evolution, "
        "mystical atmosphere, reverb-drenched textures, "
        "sparse melodic fragments, enigmatic, no vocals"
    ),
    "energetic": (
        "high-energy electronic, driving four-on-the-floor kick, "
        "pulsing bass line, bright synth arpeggios, "
        "festival-ready drops, euphoric build-ups, "
        "128 BPM, powerful and kinetic, no vocals"
    ),
    "oriental": (
        "traditional Chinese instruments meet dark ambient, "
        "guqin harmonics over deep bass drone, "
        "bamboo flute echoes, mystical Eastern atmosphere, "
        "fate and destiny, slowly evolving, "
        "80 BPM, no vocals"
    ),
    "warm": (
        "warm acoustic guitar, gentle piano chords, "
        "soft strings, comforting atmosphere, "
        "intimate and personal, feel-good vibes, "
        "natural reverb, 90 BPM, no vocals"
    ),
    "dark_ambient": (
        "deep drone textures, sub-bass frequencies, "
        "sparse metallic sounds, cavernous reverb, "
        "oppressive atmosphere, slowly shifting, "
        "minimalist, no vocals"
    ),
    "triumphant": (
        "powerful brass fanfare, driving percussion, "
        "building orchestral crescendo, major key, "
        "confident and victorious, heroic, "
        "120 BPM, no vocals"
    ),
}

# ═══════════════════════════════════════════════════════════════
# 参考风格模板
# ═══════════════════════════════════════════════════════════════

REFERENCE_STYLES = {
    "blade_runner": "Vangelis-inspired dark ambient synthesizer, ethereal pads, distant brass swells, dystopian atmosphere, slow evolving texture, reverb-drenched, cinematic noir",
    "cyberpunk_2077": "aggressive industrial cyberpunk, distorted bass, glitch percussion, futuristic synth leads, heavy sub-bass drops, gritty electronic, adrenaline-pumping",
    "evangelion": "Shiro Sagisu inspired orchestral, string ostinato, dramatic piano melody, powerful build-up, melancholic yet epic, choral elements, emotional intensity",
    "interstellar": "Hans Zimmer inspired, deep organ drone, ticking clock motif, emotional piano melody, building orchestral crescendo, vast space atmosphere, awe-inspiring",
    "stranger_things": "80s retro synthwave, arpeggiated synth bass, nostalgic pads, pulsing rhythm, dark and mysterious, John Carpenter style, analog warmth",
    "ghost_in_shell": "Kenji Kawai inspired, ambient electronic, deep bass drones, traditional Asian instruments mixed with synth, contemplative, cybernetic meditation",
    "tron_legacy": "Daft Punk inspired electronic orchestral, filtered synth sweeps, driving bass, digital grid atmosphere, sleek and futuristic, rhythmic precision",
    "akira": "Geinoh Yamashirogumi inspired, experimental electronic, traditional drums mixed with synth, chaotic energy, powerful crescendo, Japanese cyberpunk",
    "spirited_away": "Joe Hisaishi inspired, gentle piano with orchestral warmth, whimsical and bittersweet, magical atmosphere, delicate melodies",
    "three_body": "cold minimalist, deep space drone, mathematical precision, existential dread, vast cosmic emptiness, slowly evolving texture",
    "kung_fu_hustle": "traditional Chinese percussion with modern orchestral, dramatic timing, martial arts energy, playful yet powerful",
    "inception": "Hans Zimmer, BRAAAM brass, building tension, layered complexity, mind-bending atmosphere, powerful climaxes",
}

# ═══════════════════════════════════════════════════════════════
# 内容分析：从项目文件提炼情绪
# ═══════════════════════════════════════════════════════════════

# 关键词 → 情绪映射
KEYWORD_MOOD_MAP = {
    # 命理/玄学
    "命运": "mysterious", "八字": "oriental", "五行": "oriental", "卦": "mysterious",
    "占卜": "mysterious", "易经": "oriental", "风水": "mysterious", "命理": "oriental",
    "推演": "suspense", "天命": "mysterious", "宿命": "melancholic", "因果": "mysterious",
    "玄学": "mysterious", "紫微": "oriental", "星盘": "mysterious",
    # 科技/AI
    "AI": "cyberpunk", "人工智能": "cyberpunk", "算法": "cyberpunk", "数据": "cyberpunk",
    "模型": "cyberpunk", "深度学习": "cyberpunk", "大模型": "epic", "GPT": "cyberpunk",
    "智能体": "intense", "自动化": "energetic",
    # 情感/故事
    "爱情": "melancholic", "离别": "melancholic", "回忆": "melancholic", "思念": "melancholic",
    "成长": "hopeful", "坚持": "triumphant", "梦想": "hopeful", "勇气": "triumphant",
    "温暖": "warm", "治愈": "warm", "陪伴": "warm",
    # 商业/产品
    "发布": "triumphant", "突破": "epic", "创新": "energetic", "领先": "triumphant",
    "战略": "intense", "竞争": "intense",
    # 恐怖/悬疑
    "恐怖": "dark_ambient", "诡异": "dark_ambient", "惊悚": "suspense",
    "悬疑": "suspense", "谜": "mysterious",
    # 自然
    "山": "warm", "海": "mysterious", "森林": "warm", "星空": "mysterious",
    "日出": "hopeful", "雨": "melancholic",
}


def extract_text_from_html(html_content):
    """从 HTML 中提取纯文本，忽略标签和样式代码"""
    import re
    # 移除 script/style 标签及内容
    text = re.sub(r'<(script|style)[^>]*>.*?</\1>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
    # 移除所有 HTML 标签
    text = re.sub(r'<[^>]+>', ' ', text)
    # 解码常见 HTML 实体
    text = text.replace('&nbsp;', ' ').replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&')
    # 合并空白
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def analyze_content(directory=None, text=None, html=None, files=None):
    """
    从多种格式的内容中提取情绪。
    directory: 目录路径，扫描下所有内容文件
    text: 纯文本/对话内容
    html: HTML 内容
    files: 指定文件路径列表
    """
    content_parts = []

    if text:
        content_parts.append(text)

    if html:
        content_parts.append(extract_text_from_html(html))

    if files:
        for fpath in files:
            p = Path(fpath)
            if not p.exists():
                continue
            raw = p.read_text(encoding="utf-8", errors="ignore")
            if p.suffix == ".html":
                content_parts.append(extract_text_from_html(raw))
            else:
                content_parts.append(raw)

    if directory:
        content_dir = Path(directory)
        for pattern in ["**/*.md", "**/*.txt", "**/*.html"]:
            for f in content_dir.glob(pattern):
                # 跳过框架配置文件
                if f.name in ("CLAUDE.md", "AGENTS.md", "README.md"):
                    continue
                try:
                    raw = f.read_text(encoding="utf-8", errors="ignore")
                    if f.suffix == ".html":
                        raw = extract_text_from_html(raw)
                    content_parts.append(raw)
                except Exception:
                    pass

    if not content_parts:
        return None, None

    full_text = "\n".join(content_parts)

    # 关键词匹配统计情绪
    mood_scores = {}
    matched_keywords = []
    for keyword, mood in KEYWORD_MOOD_MAP.items():
        count = full_text.count(keyword)
        if count > 0:
            mood_scores[mood] = mood_scores.get(mood, 0) + count
            matched_keywords.append(keyword)

    if mood_scores:
        primary_mood = max(mood_scores, key=mood_scores.get)
    else:
        primary_mood = "mysterious"

    print(f"Content analysis:", flush=True)
    print(f"  Keywords matched: {matched_keywords[:10]}", flush=True)
    print(f"  Mood scores: {mood_scores}", flush=True)
    print(f"  Primary mood: {primary_mood}", flush=True)

    return primary_mood, matched_keywords


# ═══════════════════════════════════════════════════════════════
# 场景驱动的多段配乐生成
# ═══════════════════════════════════════════════════════════════

SCENE_MOOD_MAP = {
    "opening": "mysterious",
    "reveal": "suspense",
    "analysis": "cyberpunk",
    "climax": "epic",
    "reflection": "melancholic",
    "conclusion": "hopeful",
    "outro": "melancholic",
}


def build_prompt_from_scenes(scenes_data):
    """从场景 JSON 构建完整配乐提示词"""
    if isinstance(scenes_data, str):
        with open(scenes_data) as f:
            data = json.load(f)
        scenes = data.get("scenes", data) if isinstance(data, dict) else data
    else:
        scenes = scenes_data

    moods = []
    for scene in scenes:
        mood = scene.get("mood", SCENE_MOOD_MAP.get(scene.get("type", ""), "mysterious"))
        moods.append(mood)

    primary_mood = moods[len(moods) // 2] if moods else "mysterious"
    base = MOOD_TEMPLATES.get(primary_mood, MOOD_TEMPLATES["mysterious"])

    if len(set(moods)) > 1:
        transitions = []
        mood_descs = {
            "suspense": "mysterious tension", "intense": "aggressive energy",
            "epic": "dramatic power", "melancholic": "reflective melancholy",
            "hopeful": "hopeful brightness", "cyberpunk": "cybernetic pulse",
            "mysterious": "enigmatic atmosphere", "energetic": "kinetic drive",
            "oriental": "Eastern mysticism", "warm": "warmth and comfort",
            "dark_ambient": "deep darkness", "triumphant": "victorious power",
        }
        for mood in moods:
            transitions.append(mood_descs.get(mood, "evolving texture"))
        base += f", emotional arc: {' → '.join(transitions)}"

    return base


def generate_segment(model, processor, prompt, max_tokens=500, sample_rate=32000):
    """生成单段配乐"""
    inputs = processor(text=[prompt], padding=True, return_tensors="pt")
    with torch.no_grad():
        audio = model.generate(**inputs, max_new_tokens=max_tokens)
    return audio[0, 0].cpu().numpy()


def crossfade_concat(segments, crossfade_samples):
    """交叉淡入淡出拼接多段音频"""
    if len(segments) == 1:
        return segments[0]

    result = segments[0].copy()
    for seg in segments[1:]:
        if len(result) < crossfade_samples or len(seg) < crossfade_samples:
            result = np.concatenate([result, seg])
            continue
        fade_out = np.linspace(1, 0, crossfade_samples)
        fade_in = np.linspace(0, 1, crossfade_samples)
        result[-crossfade_samples:] = result[-crossfade_samples:] * fade_out + seg[:crossfade_samples] * fade_in
        result = np.concatenate([result, seg[crossfade_samples:]])

    return result


# ═══════════════════════════════════════════════════════════════
# 主流程
# ═══════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="智能配乐生成器 — 从内容自动推导情绪")
    parser.add_argument("--output", "-o", default="bgm.wav", help="输出文件路径")
    parser.add_argument("--prompt", "-p", help="自定义配乐提示词（最高优先级）")
    parser.add_argument("--mood", "-m", choices=list(MOOD_TEMPLATES.keys()), help="预设情绪模板")
    parser.add_argument("--reference", "-r", help="参考风格（见 REFERENCE_STYLES）")
    parser.add_argument("--scene-file", "-s", help="场景 JSON 文件路径（多段拼接）")
    parser.add_argument("--content-dir", "-c", help="项目目录路径（扫描目录下所有内容文件）")
    parser.add_argument("--content-file", "-f", nargs="*", help="指定内容文件路径（支持 md/txt/html/json）")
    parser.add_argument("--content-text", "-t", help="直接传入文字内容（对话/文案）")
    parser.add_argument("--content-html", help="直接传入 HTML 内容")
    parser.add_argument("--duration", "-d", type=float, default=30, help="目标时长（秒），默认30s")
    parser.add_argument("--model", default="facebook/musicgen-small", help="MusicGen 模型")
    parser.add_argument("--proxy", help="HTTP 代理地址")
    parser.add_argument("--list", action="store_true", help="列出所有可用情绪和参考风格")

    args = parser.parse_args()

    # 列出选项
    if args.list:
        print("\n可用情绪模板:")
        for k in MOOD_TEMPLATES:
            print(f"  {k}")
        print("\n可用参考风格:")
        for k in REFERENCE_STYLES:
            print(f"  {k}")
        return

    # 设置代理
    if args.proxy:
        os.environ['http_proxy'] = args.proxy
        os.environ['https_proxy'] = args.proxy
    os.environ.pop('all_proxy', None)
    os.environ.pop('ALL_PROXY', None)

    # ── 加载模型 ──
    print("Loading MusicGen model...", flush=True)
    model = MusicgenForConditionalGeneration.from_pretrained(args.model)
    model.eval()
    processor = AutoProcessor.from_pretrained(args.model)
    sample_rate = model.config.audio_encoder.sampling_rate
    print(f"Sample rate: {sample_rate}Hz", flush=True)

    tokens_per_second = 50
    total_tokens = int(args.duration * tokens_per_second)

    # ── 构建提示词（优先级：prompt > scene-file > mood/reference > content-* > 默认）──
    if args.prompt:
        prompt = args.prompt
        print(f"\nUsing custom prompt", flush=True)
    elif args.scene_file:
        prompt = build_prompt_from_scenes(args.scene_file)
        print(f"\nUsing scene-driven prompt", flush=True)
    elif args.content_dir or args.content_file or args.content_text or args.content_html:
        auto_mood, keywords = analyze_content(
            directory=args.content_dir,
            text=args.content_text,
            html=args.content_html,
            files=args.content_file,
        )
        if args.reference and args.reference in REFERENCE_STYLES:
            prompt = f"{REFERENCE_STYLES[args.reference]}, {MOOD_TEMPLATES.get(auto_mood, '')}"
        elif auto_mood:
            prompt = MOOD_TEMPLATES.get(auto_mood, MOOD_TEMPLATES["mysterious"])
        else:
            prompt = MOOD_TEMPLATES["mysterious"]
        prompt += ", no vocals, instrumental only"
    elif args.mood or args.reference:
        parts = []
        if args.reference and args.reference in REFERENCE_STYLES:
            parts.append(REFERENCE_STYLES[args.reference])
        if args.mood:
            parts.append(MOOD_TEMPLATES[args.mood])
        prompt = ", ".join(parts) if parts else MOOD_TEMPLATES["mysterious"]
        prompt += ", no vocals, instrumental only"
    else:
        prompt = MOOD_TEMPLATES["mysterious"]

    print(f"\nPrompt: {prompt}", flush=True)
    print(f"Target duration: {args.duration}s ({total_tokens} tokens)", flush=True)

    # ── 生成音频 ──
    if args.scene_file:
        with open(args.scene_file) as f:
            data = json.load(f)
        scenes = data.get("scenes", data) if isinstance(data, dict) else data

        segments = []
        for i, scene in enumerate(scenes):
            scene_mood = scene.get("mood", SCENE_MOOD_MAP.get(scene.get("type", ""), "mysterious"))
            scene_duration = scene.get("duration", 10)
            scene_tokens = int(scene_duration * tokens_per_second)
            scene_prompt = MOOD_TEMPLATES.get(scene_mood, MOOD_TEMPLATES["mysterious"])
            print(f"  Segment {i+1}: {scene_mood} ({scene_duration}s, {scene_tokens} tokens)", flush=True)
            audio = generate_segment(model, processor, scene_prompt, scene_tokens, sample_rate)
            segments.append(audio)

        crossfade_samples = int(sample_rate * 0.5)
        final_audio = crossfade_concat(segments, crossfade_samples)
    else:
        print("Generating audio...", flush=True)
        final_audio = generate_segment(model, processor, prompt, total_tokens, sample_rate)

    # ── 保存 ──
    print(f"Saving to {args.output}...", flush=True)
    wavfile.write(args.output, rate=sample_rate, data=final_audio.astype(np.float32))

    duration = len(final_audio) / sample_rate
    print(f"Done! {duration:.1f}s saved to {args.output}", flush=True)


if __name__ == "__main__":
    main()
