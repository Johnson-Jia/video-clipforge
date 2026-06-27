import numpy as np
from PIL import Image
import tempfile, os, sys
from pathlib import Path

_CLIPFORGE_ROOT = Path(__file__).resolve().parents[2]
if str(_CLIPFORGE_ROOT) not in sys.path:
    sys.path.insert(0, str(_CLIPFORGE_ROOT))
from engine.lib.visual_qa import analyze_frame, check_safezone

def _make_frame(content_bands, width=1080, height=1920):
    """合成帧:黑底,在 content_bands=[(y0,y1),...] 画白条模拟内容行。"""
    img = np.zeros((height, width), dtype=np.uint8)
    for (y0, y1) in content_bands:
        img[y0:y1, :] = 255
    return Image.fromarray(img)

def _save_tmp(img):
    f = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    f.close()
    img.save(f.name)
    return f.name

def test_content_y_range():
    path = _save_tmp(_make_frame([(200, 300), (800, 900)]))
    try:
        r = analyze_frame(path)
        assert r["content_y"] is not None
        assert 195 <= r["content_y"][0] <= 205
        assert 895 <= r["content_y"][1] <= 905
    finally:
        os.unlink(path)

def test_blank_band_in_content_range():
    path = _save_tmp(_make_frame([(200, 300), (800, 900)]))
    try:
        r = analyze_frame(path)
        mid_bands = [b for b in r["blank_bands"] if b["y"] >= 300 and b["y"] < 800]
        assert any(b["height"] > 50 for b in mid_bands)
    finally:
        os.unlink(path)

def test_empty_frame():
    path = _save_tmp(_make_frame([]))
    try:
        r = analyze_frame(path)
        assert r["content_y"] is None
        assert r["blank_bands"] == []
    finally:
        os.unlink(path)

def test_safezone_ok():
    assert check_safezone([200, 1600])["ok"] is True

def test_safezone_top_overflow():
    r = check_safezone([100, 1600])
    assert r["ok"] is False and r["overflow"] == "top"

def test_safezone_bottom_overflow():
    r = check_safezone([200, 1800])
    assert r["ok"] is False and r["overflow"] == "bottom"

def test_safezone_boundary_inclusive():
    assert check_safezone([180, 1700])["ok"] is True   # 边界值合规

def test_safezone_empty():
    r = check_safezone(None)
    assert r["ok"] is False

def test_safezone_landscape():
    r = check_safezone([60, 1860], orientation="landscape")
    assert r["ok"] is True
