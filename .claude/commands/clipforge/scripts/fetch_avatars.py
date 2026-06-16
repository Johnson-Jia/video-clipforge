#!/usr/bin/env python3
"""
下载 GitHub 项目代表性图片（多源优先级链），圆形裁剪，回写 avatar_path + avatar_source。

优先级（用户确认）：
  1. 项目 logo    — 仓库根目录 logo/icon/brand 位图文件（gh api contents）
  2. 组织 logo    — owner 是 Organization 时的组织头像（gh api orgs，商标非肖像）
  3. 领域图标     — topics 映射 simple-icons 彩色 SVG（svglib 转 PNG）
  4. 语言 logo    — primary language 映射 simple-icons 彩色 SVG（svglib 转 PNG）
  5. 作者头像     — owner.avatar_url 兜底（⚠️ 肖像权风险，最后才用）

位图源（项目/组织/作者）→ PIL 圆形裁剪（充满）；图标源（领域/语言）→ svglib 转 PNG + 加 padding 居中圆形（避免方形图标被裁角）。

用法: python scripts/fetch_avatars.py --project-dir <dir>
依赖: Pillow（必装，圆形裁剪）+ svglib+reportlab（语言/领域图标，可选；未装则源 3/4 跳过）
"""
import argparse
import io
import json
import os
import subprocess
import sys
import time
import urllib.request

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

AVATAR_SIZE = 240
GH_SLEEP = 0.2

# 语言 → (simple-icons slug, 品牌色 hex)
LANG_ICON = {
    'Python': ('python', '3776AB'), 'JavaScript': ('javascript', 'F7DF1E'),
    'TypeScript': ('typescript', '3178C8'), 'Rust': ('rust', 'CE422B'),
    'Go': ('go', '00ADD8'), 'Java': ('openjdk', '437291'), 'Ruby': ('ruby', 'CC342D'),
    'PHP': ('php', '777BB4'), 'C++': ('cplusplus', '00599C'), 'C': ('c', 'A8B9CC'),
    'C#': ('csharp', '512BD4'), 'Swift': ('swift', 'FA7343'), 'Kotlin': ('kotlin', '7F52FF'),
    'HTML': ('html5', 'E34F26'), 'CSS': ('css3', '1572B6'), 'Shell': ('gnubash', '4EAA25'),
    'PowerShell': ('powershell', '5391FE'), 'Dart': ('dart', '0175C2'),
    'Lua': ('lua', '2C2D72'), 'Scala': ('scala', 'DC322F'), 'Elixir': ('elixir', '4B275F'),
    'Vue': ('vuedotjs', '42B883'), 'Svelte': ('svelte', 'FF3E00'),
    'Solidity': ('solidity', '363636'), 'Dockerfile': ('docker', '2496ED'),
    'Jupyter Notebook': ('jupyter', 'F37626'), 'TeX': ('latex', '008080'),
    'Zig': ('zig', 'F7A41D'), 'GDScript': ('godotengine', '478CBF'),
    'Astro': ('astro', 'FF5D01'), 'MDX': ('markdown', '755C48'),
    'Makefile': ('gnubash', '4EAA25'), 'Objective-C': ('objectivec', '438EFF'),
    'R': ('rlang', '276DC3'), 'Haskell': ('haskell', '5D4F85'),
}

# 领域/topic → (simple-icons slug, 品牌色 hex)
TOPIC_ICON = {
    'ai': ('openai', '412991'), 'machine-learning': ('tensorflow', 'FF6F00'),
    'deep-learning': ('pytorch', 'EE4C2C'), 'ml': ('tensorflow', 'FF6F00'),
    'llm': ('openai', '412991'), 'chatbot': ('openai', '412991'),
    'gpt': ('openai', '412991'), 'neural-network': ('tensorflow', 'FF6F00'),
    'pytorch': ('pytorch', 'EE4C2C'), 'tensorflow': ('tensorflow', 'FF6F00'),
    'huggingface': ('huggingface', 'FFD21E'), 'agent': ('openai', '412991'),
    'ai-agent': ('openai', '412991'), 'ai-agents': ('openai', '412991'),
    'security': ('openssl', '721412'), 'cybersecurity': ('openssl', '721412'),
    'privacy': ('openssl', '721412'), 'encryption': ('openssl', '721412'),
    'react': ('react', '61DAFB'), 'vue': ('vuedotjs', '42B883'),
    'angular': ('angular', 'DD0031'), 'svelte': ('svelte', 'FF3E00'),
    'nextjs': ('nextdotjs', '000000'), 'nuxt': ('nuxtdotjs', '00DC82'),
    'frontend': ('react', '61DAFB'), 'web': ('html5', 'E34F26'),
    'webdev': ('html5', 'E34F26'), 'nodejs': ('nodedotjs', '339933'),
    'node': ('nodedotjs', '339933'), 'deno': ('deno', '000000'),
    'database': ('postgresql', '336791'), 'sql': ('postgresql', '336791'),
    'postgresql': ('postgresql', '336791'), 'mysql': ('mysql', '4479A1'),
    'mongodb': ('mongodb', '47A248'), 'redis': ('redis', 'DC382D'),
    'sqlite': ('sqlite', '003B57'), 'supabase': ('supabase', '3FCF8E'),
    'docker': ('docker', '2496ED'), 'kubernetes': ('kubernetes', '326CE5'),
    'k8s': ('kubernetes', '326CE5'), 'devops': ('docker', '2496ED'),
    'ci-cd': ('githubactions', '2088FF'), 'github-actions': ('githubactions', '2088FF'),
    'aws': ('amazonaws', 'FF9900'), 'azure': ('microsoftazure', '0078D4'),
    'gcp': ('googlecloud', '4285F4'), 'cloud': ('amazonaws', 'FF9900'),
    'terraform': ('terraform', '7B42BC'),
    'blockchain': ('ethereum', '3C3C3D'), 'web3': ('ethereum', '3C3C3D'),
    'ethereum': ('ethereum', '3C3C3D'), 'bitcoin': ('bitcoin', 'F7931A'),
    'crypto': ('bitcoin', 'F7931A'), 'solana': ('solana', '9945FF'),
    'game': ('unity', 'FFFFFF'), 'gamedev': ('unity', 'FFFFFF'),
    'unity': ('unity', 'FFFFFF'), 'unreal': ('unrealengine', '0E1128'),
    'godot': ('godotengine', '478CBF'),
    'cli': ('gnubash', '4EAA25'), 'terminal': ('gnubash', '4EAA25'),
    'api': ('fastapi', '009688'), 'framework': ('react', '61DAFB'),
    'iot': ('espressif', 'E7352D'), 'markdown': ('markdown', '755C48'),
    'docs': ('markdown', '755C48'), 'music': ('spotify', '1DB954'),
    'audio': ('spotify', '1DB954'), 'linux': ('linux', 'FCC624'),
    'editor': ('vscodium', '3C99D4'), 'vscode': ('vscodium', '3C99D4'),
}

SVG_CDN = "https://cdn.simpleicons.org/{slug}/{hexc}"


def make_circular(img, size=AVATAR_SIZE):
    """位图圆形裁剪（充满，适合照片/Logo）。"""
    from PIL import Image, ImageDraw
    img = img.convert("RGBA").resize((size, size), Image.LANCZOS)
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, size, size), fill=255)
    out = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    out.paste(img, (0, 0), mask)
    return out


def make_circular_icon(img, size=AVATAR_SIZE, icon_ratio=0.7):
    """图标圆形裁剪（缩放 70% 居中 + 透明边距 + 圆形 mask，避免方形图标被裁角）。"""
    from PIL import Image, ImageDraw
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    iw = int(size * icon_ratio)
    icon = img.convert("RGBA").resize((iw, iw), Image.LANCZOS)
    canvas.paste(icon, ((size - iw) // 2, (size - iw) // 2), icon)
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, size, size), fill=255)
    out = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    out.paste(canvas, (0, 0), mask)
    return out


def svg_bytes_to_pil(svg_data):
    """svglib + reportlab 把 SVG bytes → PIL Image。"""
    from svglib.svglib import svg2rlg
    from reportlab.graphics import renderPM
    tmp = io.BytesIO(svg_data)
    drawing = svg2rlg(tmp)
    return renderPM.drawToPIL(drawing)


def gh_api_json(path):
    env = os.environ.copy(); env["MSYS_NO_PATHCONV"] = "1"
    try:
        r = subprocess.run(["gh", "api", path], capture_output=True, text=True, timeout=15, env=env)
        time.sleep(GH_SLEEP)
        if r.returncode == 0 and r.stdout.strip():
            return json.loads(r.stdout)
    except (subprocess.TimeoutExpired, OSError, json.JSONDecodeError):
        pass
    return None


def download_url(url, timeout=20):
    req = urllib.request.Request(url, headers={"User-Agent": "ClipForge-avatar-fetch"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


# ── 5 源（返回 (data_bytes, is_icon) 或 None）──
def try_repo_logo(owner, repo):
    if not repo:
        return None
    contents = gh_api_json(f"repos/{owner}/{repo}/contents")
    if not isinstance(contents, list):
        return None
    for f in contents:
        name = (f.get("name") or "").lower()
        if any(k in name for k in ("logo", "icon", "brand")) and name.endswith((".png", ".jpg", ".jpeg", ".webp")):
            raw_url = f.get("download_url")
            if raw_url:
                try:
                    return (download_url(raw_url), False)   # 位图
                except Exception:
                    continue
    return None


def try_org_logo(owner):
    org = gh_api_json(f"orgs/{owner}")
    if isinstance(org, dict) and org.get("type") == "Organization":
        url = org.get("avatar_url")
        if url:
            try:
                return (download_url(url), False)   # 位图
            except Exception:
                pass
    return None


def try_topic_icon(topics, svglib_ok):
    if not topics or not svglib_ok:
        return None
    for t in topics:
        info = TOPIC_ICON.get((t or "").lower())
        if info:
            slug, hexc = info
            try:
                return (download_url(SVG_CDN.format(slug=slug, hexc=hexc)), True)   # SVG 图标
            except Exception:
                continue
    return None


def try_lang_icon(lang, svglib_ok):
    if not lang or not svglib_ok:
        return None
    info = LANG_ICON.get(lang)
    if not info:
        return None
    slug, hexc = info
    try:
        return (download_url(SVG_CDN.format(slug=slug, hexc=hexc)), True)   # SVG 图标
    except Exception:
        return None


def try_author_avatar(avatar_url):
    if not avatar_url:
        return None
    try:
        return (download_url(avatar_url), False)   # 位图
    except Exception:
        return None


def fetch_one(p, svglib_ok):
    """按优先级试 5 源。返回 (data, source, is_icon) 或 (None, None, None)。"""
    sources = [
        ("project_logo",  lambda: try_repo_logo(p["owner"], p.get("repo", ""))),
        ("org_logo",      lambda: try_org_logo(p["owner"])),
        ("topic",         lambda: try_topic_icon(p.get("topics"), svglib_ok)),
        ("lang_logo",     lambda: try_lang_icon(p.get("language"), svglib_ok)),
        ("author_avatar", lambda: try_author_avatar(p.get("avatar_url"))),
    ]
    for name, fn in sources:
        try:
            res = fn()
            if res:
                data, is_icon = res
                return data, name, is_icon
        except Exception:
            continue
    return None, None, None


def fetch_avatar_url_via_gh(owner, repo):
    env = os.environ.copy(); env["MSYS_NO_PATHCONV"] = "1"
    try:
        r = subprocess.run(["gh", "api", f"repos/{owner}/{repo}", "--jq", ".owner.avatar_url"],
                           capture_output=True, text=True, timeout=15, env=env)
        time.sleep(GH_SLEEP)
        if r.returncode == 0:
            return r.stdout.strip() or None
    except (subprocess.TimeoutExpired, OSError):
        pass
    return None


def save_avatar(data, target_png, is_icon):
    """位图 → make_circular；SVG 图标 → svglib 转 PNG + make_circular_icon。"""
    from PIL import Image
    if is_icon:
        pil = svg_bytes_to_pil(data)
        make_circular_icon(pil).save(target_png, "PNG", optimize=True)
    else:
        img = Image.open(io.BytesIO(data))
        make_circular(img).save(target_png, "PNG", optimize=True)


def main():
    ap = argparse.ArgumentParser(description="下载 GitHub 项目代表性图片（多源优先级）")
    ap.add_argument("--project-dir", required=True)
    args = ap.parse_args()

    raw_path = os.path.join(args.project_dir, "raw_trending.json")
    if not os.path.exists(raw_path):
        print(f"[fetch_avatars] 跳过：{raw_path} 不存在")
        return
    with open(raw_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    projects = data.get("projects", [])

    avatars_dir = os.path.join(args.project_dir, "assets", "avatars")
    os.makedirs(avatars_dir, exist_ok=True)

    try:
        import PIL  # noqa: F401
        pil_ok = True
    except ImportError:
        pil_ok = False
        print("[fetch_avatars] 警告：Pillow 未安装，所有 avatar_path 置 null")

    svglib_ok = False
    if pil_ok:
        try:
            from svglib.svglib import svg2rlg  # noqa: F401
            from reportlab.graphics import renderPM  # noqa: F401
            svglib_ok = True
        except ImportError:
            print("[fetch_avatars] 提示：svglib/reportlab 未装，语言/领域图标源跳过（pip install svglib reportlab 启用）")

    stats = {}
    for p in projects:
        owner = p.get("owner")
        if not owner:
            continue
        target = os.path.join(avatars_dir, f"{owner}.png")
        rel_path = f"assets/avatars/{owner}.png"

        if os.path.exists(target) and p.get("avatar_path"):
            p["avatar_path"] = rel_path
            src = p.get("avatar_source", "cached")
            stats[src] = stats.get(src, 0) + 1
            continue

        if not pil_ok:
            p["avatar_path"] = None
            p["avatar_source"] = None
            stats["failed"] = stats.get("failed", 0) + 1
            continue

        if not p.get("avatar_url"):
            av = fetch_avatar_url_via_gh(owner, p.get("repo", ""))
            if av:
                p["avatar_url"] = av

        data_bytes, source, is_icon = fetch_one(p, svglib_ok)
        if data_bytes and source:
            try:
                save_avatar(data_bytes, target, is_icon)
                p["avatar_path"] = rel_path
                p["avatar_source"] = source
                stats[source] = stats.get(source, 0) + 1
                continue
            except Exception as e:
                print(f"  [!] {owner}: 转换/保存失败 ({e})")

        p["avatar_path"] = None
        p["avatar_source"] = None
        stats["failed"] = stats.get("failed", 0) + 1

    with open(raw_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"[fetch_avatars] 多源优先级完成：{dict(stats)}")


if __name__ == "__main__":
    main()
