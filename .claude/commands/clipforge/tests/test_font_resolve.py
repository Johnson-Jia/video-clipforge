"""字体三级回退测试（缺口2）：assets SRC_MAP → 字体目录(env/config) → 自动下载 cache。

字体目录参照工作目录处理（data_paths.get_fonts_dir：env CLIPFORGE_FONTS_DIR > ~/.claude/clipforge-config.json 的 fonts_dir），
持久化在 config.json（跨会话/项目），env 用于临时覆盖。
"""
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent))
from scripts.s6_assemble_html import resolve_font_files, _parse_google_fonts_css


class TestResolveFontFiles(unittest.TestCase):
    """三级回退：SRC_MAP(assets/cache) → 字体目录(env/config) → 下载。"""

    def test_src_map_assets_hit(self):
        """1级：SRC_MAP assets 文件存在 → 用 assets，不查字体目录/不下载。"""
        with tempfile.TemporaryDirectory() as td:
            assets = Path(td) / "assets"; assets.mkdir()
            cache = Path(td) / "cache"
            f = assets / "F.woff2"; f.write_text("x")
            with patch("scripts.s6_assemble_html._FONT_SRCS", {"F": [("assets/F.woff2", 400)]}):
                dl = []
                r = resolve_font_files("F", assets, cache,
                    downloader=lambda fam, c: dl.append(fam) or [])
            self.assertEqual(r, [(f, 400, "")])
            self.assertEqual(dl, [])

    def test_local_dir_hit(self):
        """2级：SRC_MAP 无 + 字体目录(get_fonts_dir)有匹配文件 → 用本地，不下载。"""
        with tempfile.TemporaryDirectory() as td:
            assets = Path(td) / "a"; assets.mkdir()
            cache = Path(td) / "c"
            local = Path(td) / "myfonts"; local.mkdir()
            (local / "MaShanZheng.woff2").write_text("x")
            with patch("scripts.s6_assemble_html._FONT_SRCS", {}), \
                 patch("engine.lib.data_paths.get_fonts_dir", return_value=str(local)):
                dl = []
                r = resolve_font_files("Ma Shan Zheng", assets, cache,
                    downloader=lambda fam, c: dl.append(fam) or [(cache / "x", 400)])
            self.assertEqual(len(r), 1)
            self.assertIn("mashan", str(r[0][0]).lower().replace("-", "").replace("_", ""))
            self.assertEqual(dl, [])

    def test_download_fallback(self):
        """3级：SRC_MAP 无 + 字体目录无 → 调用 downloader 下载到 cache。"""
        with tempfile.TemporaryDirectory() as td:
            assets = Path(td) / "a"; assets.mkdir()
            cache = Path(td) / "c"
            dl_ret = [(cache / "ma-shan-zheng" / "400.woff2", 400, "")]
            called = []
            def dl(fam, c):
                called.append(fam); return dl_ret
            with patch("scripts.s6_assemble_html._FONT_SRCS", {}), \
                 patch("engine.lib.data_paths.get_fonts_dir", return_value=None):
                r = resolve_font_files("Ma Shan Zheng", assets, cache, downloader=dl)
            self.assertEqual(r, dl_ret)
            self.assertEqual(called, ["Ma Shan Zheng"])

    def test_nothing_found(self):
        """全无 → 空列表，调用方降级 fallback。"""
        with tempfile.TemporaryDirectory() as td:
            assets = Path(td) / "a"; assets.mkdir()
            cache = Path(td) / "c"
            with patch("scripts.s6_assemble_html._FONT_SRCS", {}), \
                 patch("engine.lib.data_paths.get_fonts_dir", return_value=None):
                r = resolve_font_files("UnknownFont", assets, cache,
                    downloader=lambda f, c: [])
            self.assertEqual(r, [])


class TestParseGoogleFontsCss(unittest.TestCase):
    """Google Fonts CSS 分段解析（中文字体多 unicode-range 切片，bug 核心：不能覆盖）。"""

    def test_single_slice(self):
        css = "@font-face { font-family: 'F'; font-weight: 400; src: url(https://x/a.woff2) format('woff2'); unicode-range: U+0-100; }"
        self.assertEqual(_parse_google_fonts_css(css),
                         [(400, "https://x/a.woff2", "U+0-100")])

    def test_multi_slice_same_weight_not_overwrite(self):
        """同 weight 多切片（中文字体分段）—— 必须全部保留，旧逻辑 dest 覆盖只留 1 个是 bug。"""
        css = (
            "@font-face { font-family: 'Ma Shan Zheng'; font-weight: 400; "
            "src: url(https://x/s1.woff2) format('woff2'); unicode-range: U+0-100; }"
            "@font-face { font-family: 'Ma Shan Zheng'; font-weight: 400; "
            "src: url(https://x/s2.woff2) format('woff2'); unicode-range: U+100-200; }"
        )
        r = _parse_google_fonts_css(css)
        self.assertEqual(len(r), 2)
        self.assertEqual(r[0], (400, "https://x/s1.woff2", "U+0-100"))
        self.assertEqual(r[1], (400, "https://x/s2.woff2", "U+100-200"))

    def test_no_unicode_range(self):
        """无 unicode-range（西文字体）→ 空串。"""
        css = "@font-face { font-family: 'F'; font-weight: 700; src: url(https://x/a.woff2) format('woff2'); }"
        self.assertEqual(_parse_google_fonts_css(css),
                         [(700, "https://x/a.woff2", "")])


class TestGetFontsDirConfig(unittest.TestCase):
    """字体目录 config 回退（参照 workspace）：env > config.json fonts_dir。"""

    def test_env_overrides_config(self):
        """env 优先于 config（临时覆盖）。"""
        with tempfile.TemporaryDirectory() as td:
            env_dir = Path(td) / "env"; env_dir.mkdir()
            cfg_dir = Path(td) / "cfg"; cfg_dir.mkdir()
            with patch.dict(os.environ, {"CLIPFORGE_FONTS_DIR": str(env_dir)}), \
                 patch("engine.lib.data_paths.get_config", return_value={"fonts_dir": str(cfg_dir)}):
                from engine.lib.data_paths import get_fonts_dir
                self.assertEqual(get_fonts_dir(), str(env_dir))

    def test_config_when_no_env(self):
        """无 env → 用 config fonts_dir（持久指定）。"""
        with tempfile.TemporaryDirectory() as td:
            cfg_dir = Path(td) / "cfg"; cfg_dir.mkdir()
            env = {k: v for k, v in os.environ.items() if k != "CLIPFORGE_FONTS_DIR"}
            with patch.dict(os.environ, env, clear=True), \
                 patch("engine.lib.data_paths.get_config", return_value={"fonts_dir": str(cfg_dir)}):
                from engine.lib.data_paths import get_fonts_dir
                self.assertEqual(get_fonts_dir(), str(cfg_dir))

    def test_none_when_neither(self):
        """env 和 config 都无 → None（自动下载 fallback）。"""
        env = {k: v for k, v in os.environ.items() if k != "CLIPFORGE_FONTS_DIR"}
        with patch.dict(os.environ, env, clear=True), \
             patch("engine.lib.data_paths.get_config", return_value={}):
            from engine.lib.data_paths import get_fonts_dir
            self.assertIsNone(get_fonts_dir())


if __name__ == "__main__":
    unittest.main()
