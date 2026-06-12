#!/usr/bin/env python3
"""validate_html_structure.py — 校验 creative/sNN.html 的 HTML 结构完整性。

防止 s11 类 bug：碎片含多余 </div>，组装进 <div class="clip" id="sNN"> 后
解析器在该多余闭合处提前关闭 #sNN 容器，导致 layer-fx/layer-content（含
phase 元素）溢出到 #root。于是 GSAP 的 `tl.set('#sNN .phase-N', ...)` 选择器
匹配不到目标，phase 切换静默失效——phase-1 全程可见、phase-2 永不出现。
HTML 解析器、GSAP、gate.py 对此均静默，只有抽帧内容对比能发现。

确定性校验（CLAUDE.md §7 管线确定化）：
1. div 标签平衡 — 无未闭合 <div>，无多余 </div>（s11 第 68 行就死在这条）
2. 顶层容器 — 必须包含 layer-content（phase 元素的安放处）

用法:
  python scripts/validate_html_structure.py --project-dir .
退出码: 0=通过, 1=发现结构错误（HARD 门禁）
"""
from __future__ import annotations

import argparse
import sys
from html.parser import HTMLParser
from pathlib import Path


class FragmentValidator(HTMLParser):
    """单碎片结构校验器：维护 div 栈，记录不平衡与顶层容器。"""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.stack: list[tuple[str, int]] = []   # (class, open_line) 未闭合的 div
        self.orphan_closes: list[int] = []       # 栈空时遇到的 </div> 行号（多余闭合）
        self.top_level: list[str] = []           # 顶层 div 的 class（栈 0→1 瞬间）

    @staticmethod
    def _cls(attrs: list[tuple[str, str | None]]) -> str:
        for k, v in attrs:
            if k == "class":
                return v or ""
        return ""

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "div":
            cls = self._cls(attrs)
            line = self.getpos()[0]
            if not self.stack:                    # 栈空 → 顶层 div
                self.top_level.append(cls)
            self.stack.append((cls, line))

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        # <div/> 自闭合（XHTML 风格），不入栈，天然平衡
        pass

    def handle_endtag(self, tag: str) -> None:
        if tag == "div":
            if not self.stack:
                self.orphan_closes.append(self.getpos()[0])
            else:
                self.stack.pop()


def validate_fragment(path: Path) -> list[str]:
    """校验单个碎片，返回错误信息列表（空=通过）。"""
    content = path.read_text(encoding="utf-8")
    v = FragmentValidator()
    v.feed(content)
    v.close()

    errors: list[str] = []

    # 检查 1：多余 </div>（最致命——组装后提前关闭 #sNN 容器，phase 溢出）
    for line_no in v.orphan_closes:
        errors.append(
            f"第 {line_no} 行：多余的 </div> — 栈已空时遇到闭合标签，组装后会提前关闭 "
            f"#sNN 容器，导致 layer-fx/layer-content 溢出到 #root，phase 切换失效"
        )

    # 检查 2：未闭合 <div>（从外到内报）
    for cls, line_no in reversed(v.stack):
        label = f'<div class="{cls}">' if cls else "<div>"
        errors.append(f"第 {line_no} 行打开的 {label} 未闭合")

    # 检查 3：顶层容器必须含 layer-content（phase 的安放处）
    if not any("layer-content" in c for c in v.top_level):
        errors.append(
            f"缺少 layer-content 顶层容器 — phase 元素将无处安放；"
            f"当前顶层 div：{v.top_level or '(无)'}"
        )

    return errors


def validate(project_dir: Path) -> int:
    """校验 creative/ 下所有 sNN.html 碎片。0=通过，1=有错误。"""
    creative_dir = project_dir / "creative"
    if not creative_dir.exists():
        print("[FAIL] creative/ 目录不存在", file=sys.stderr)
        return 1

    frags = sorted(creative_dir.glob("s[0-9][0-9].html"))
    if not frags:
        print("[FAIL] creative/ 下无 sNN.html 碎片", file=sys.stderr)
        return 1

    print(f"=== HTML 结构校验（{len(frags)} 个碎片）===")

    fail_count = 0
    for frag in frags:
        errors = validate_fragment(frag)
        if errors:
            fail_count += 1
            print(f"  [FAIL] {frag.name}")
            for e in errors:
                print(f"         {e}")
        else:
            print(f"  [OK]   {frag.name}")

    if fail_count:
        print(
            f"\n[FAIL] {fail_count}/{len(frags)} 个碎片 HTML 结构错误\n"
            f"       这些错误会导致 phase 切换失效 / 内容溢出，必须修复后再组装"
        )
        return 1

    print(
        f"\n[OK] 全部 {len(frags)} 个碎片结构完整（标签平衡 + layer-content 存在）"
    )
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(
        description="ClipForge creative/sNN.html 结构校验（标签平衡 + 三层容器）"
    )
    parser.add_argument("--project-dir", required=True, help="项目目录")
    args = parser.parse_args()

    project_dir = Path(args.project_dir).resolve()
    sys.exit(validate(project_dir))


if __name__ == "__main__":
    main()
