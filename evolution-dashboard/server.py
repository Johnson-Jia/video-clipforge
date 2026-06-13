"""ClipForge 自进化可视化仪表盘后端。

独立于 clipforge 技能包的运营工具：单向消费 clipforge 数据
（patterns/deltas/thresholds/regression/performance），提供可视化 + 权重调整 API。
依赖方向：dashboard → clipforge（只读为主，写仅 dimension_weights/pattern weight）。

启动：cd evolution-dashboard && python server.py → http://127.0.0.1:8765
"""
from __future__ import annotations
import http.server
import json
import os
import socketserver
import statistics
import sys
from collections import defaultdict
from pathlib import Path
from urllib.parse import urlparse

# ── 路径解析（独立于 clipforge 技能包）──
DASHBOARD_DIR = Path(__file__).parent
PROJECT_ROOT = DASHBOARD_DIR.parent
CLIPFORGE_ROOT = PROJECT_ROOT / ".claude" / "commands" / "clipforge"
WORKSPACE = PROJECT_ROOT / "workspace"
sys.path.insert(0, str(CLIPFORGE_ROOT))
sys.path.insert(0, str(CLIPFORGE_ROOT / "scripts"))
os.environ.setdefault("CLIPFORGE_CATEGORY", "github")

import yaml  # noqa: E402
from engine.lib.thresholds import load as load_thresholds  # noqa: E402
from engine.lib.delta import load_deltas  # noqa: E402
from engine.success_analyzer import save_pattern, _platform_success_score  # noqa: E402
import auto_evolve as ae  # noqa: E402（触发其 sys.path/engine import + UTF-8 stdout）
from auto_evolve import (  # noqa: E402
    _classify_topic, _read_narration, _read_cover_attrs, _percentile_rank,
)
from engine.attribution import _classify_hook_type  # noqa: E402
from engine.lib.data_paths import all_pattern_files, pattern_file, dimension_weights_file  # noqa: E402

DIM_WEIGHTS_FILE = dimension_weights_file()
TEMPLATES_DIR = DASHBOARD_DIR / "templates"
STATIC_DIR = DASHBOARD_DIR / "static"
PORT = 8765


# ── 数据读取（只读聚合）──────────────────────────────────────────────────────

def load_patterns_all() -> list[dict]:
    """读所有 pattern 全字段（含 evidence），供仪表盘展示。"""
    out = []
    for fp in all_pattern_files():
        try:
            d = yaml.safe_load(fp.read_text("utf-8"))
        except Exception:
            continue
        if not d:
            continue
        parts = (d.get("id") or fp.stem).split("-", 2)
        dim = parts[1] if (len(parts) >= 3 and parts[0] == "P"
                           and parts[1] in ("topic", "hook", "cover", "narration")) else None
        ev = d.get("evidence") or {}
        pref = d.get("as_preference") or {}
        out.append({
            "id": d.get("id") or fp.stem,
            "seed": d.get("seed") is True,
            "category": d.get("category"),
            "skill_scope": d.get("skill_scope"),
            "dim": dim,
            "weight": pref.get("weight", "MEDIUM"),
            "text": pref.get("text", ""),
            "status": ev.get("status", "active"),
            "trend": ev.get("trend"),
            "decline_streak": ev.get("decline_streak", 0),
            "sample_size": ev.get("sample_size", 0),
            "avg_reach": ev.get("avg_reach"),
            "recent_reach": ev.get("recent_reach"),
            "recent_excess": ev.get("recent_excess"),
            "market_avg_at_birth": ev.get("market_avg_at_birth"),
            "market_avg_current": ev.get("market_avg_current"),
            "window_end": ev.get("window_end"),
        })
    return out


def load_dimensions() -> dict:
    if not DIM_WEIGHTS_FILE.exists():
        return {"topic": 1.0, "hook": 1.0, "cover": 1.0, "narration": 1.0}
    try:
        d = yaml.safe_load(DIM_WEIGHTS_FILE.read_text("utf-8")) or {}
        return {k: float(d.get(k, 1.0)) for k in ("topic", "hook", "cover", "narration")}
    except Exception:
        return {"topic": 1.0, "hook": 1.0, "cover": 1.0, "narration": 1.0}


def load_regression() -> dict:
    src = WORKSPACE / "sources"
    files = sorted(src.glob("regression-*.json")) if src.exists() else []
    if not files:
        return {"available": False}
    try:
        return json.loads(files[-1].read_text("utf-8"))
    except Exception:
        return {"available": False}


def aggregate_projects() -> dict:
    """读所有 performance.json → 项目级 reach/quality/维度（复用 auto_evolve 分类器）。"""
    raw = []
    for pf in sorted(WORKSPACE.rglob("performance.json")):
        proj = pf.parent
        try:
            data = json.loads(pf.read_text("utf-8"))
        except Exception:
            continue
        plats = data.get("platforms", {})
        plats = plats if isinstance(plats, dict) else {}
        per_plat = {k: v for k, v in plats.items()
                    if isinstance(v, dict) and (v.get("plays") or v.get("impressions"))}
        if not per_plat:
            continue
        narr = _read_narration(proj)
        try:
            rel = str(proj.relative_to(WORKSPACE))
        except ValueError:
            rel = proj.name
        _parts = rel.replace("\\", "/").split("/")
        _date = "-".join(_parts[:3]) if len(_parts) >= 3 else ""
        raw.append({
            "name": proj.name, "path": rel, "date": _date,
            "per_plat": per_plat,
            "hook_type": _classify_hook_type(narr["hook_text"]),
            "topic": _classify_topic(proj),
            "cover": (_read_cover_attrs(proj) or {}).get("color_bias", "未知"),
        })
    plat_pools = defaultdict(list)
    for r in raw:
        for p, d in r["per_plat"].items():
            plat_pools[p].append(float(d.get("plays", 0) or 0))
    for r in raw:
        reach_pcts = [_percentile_rank(plat_pools.get(p, []), float(d.get("plays", 0) or 0))
                      for p, d in r["per_plat"].items()]
        r["n_platforms"] = len(r["per_plat"])
        r["reach"] = round(statistics.mean(reach_pcts), 3) if reach_pcts else 0.0
        r["quality"] = round(statistics.mean([_platform_success_score(d) for d in r["per_plat"].values()]), 3)
        del r["per_plat"]
    market_avg = round(statistics.mean(r["reach"] for r in raw), 3) if raw else 0.0

    def _grp(key):
        g = defaultdict(list)
        for r in raw:
            g[r[key]].append(r)
        return {k: {"count": len(v), "avg_reach": round(statistics.mean(x["reach"] for x in v), 3)}
                for k, v in g.items()}

    return {
        "projects": raw, "market_avg": market_avg,
        "topic_analysis": _grp("topic"), "hook_analysis": _grp("hook_type"), "cover_analysis": _grp("cover"),
    }


def overview() -> dict:
    agg = aggregate_projects()
    return {
        "patterns": load_patterns_all(),
        "dimensions": load_dimensions(),
        "thresholds": load_thresholds(),
        "regression": load_regression(),
        "deltas": load_deltas(),
        "projects": agg["projects"],
        "market_avg": agg["market_avg"],
        "topic_analysis": agg["topic_analysis"],
        "hook_analysis": agg["hook_analysis"],
        "cover_analysis": agg["cover_analysis"],
    }


# ── 写回（read-modify-write，保留全字段）──────────────────────────────────────

def update_pattern(pid: str, weight: str | None = None, status: str | None = None) -> bool:
    fp = pattern_file(pid)
    if not fp.exists():
        return False
    d = yaml.safe_load(fp.read_text("utf-8"))
    if not d:
        return False
    changed = False
    if weight in ("LOW", "MEDIUM", "HIGH"):
        pref = d.setdefault("as_preference", {})
        if pref.get("weight") != weight:
            pref["weight"] = weight
            changed = True
    if status in ("active", "deprecated"):
        ev = d.setdefault("evidence", {})
        if ev.get("status") != status:
            ev["status"] = status
            changed = True
    if changed:
        save_pattern(d)
    return changed


def update_dimension(dim: str, weight: float) -> bool:
    if dim not in ("topic", "hook", "cover", "narration"):
        return False
    d = load_dimensions()
    d[dim] = max(0.0, min(2.0, float(weight)))
    DIM_WEIGHTS_FILE.write_text(
        yaml.dump(d, allow_unicode=True, default_flow_style=False), encoding="utf-8")
    return True


# ── HTTP 路由 ─────────────────────────────────────────────────────────────────

class Handler(http.server.BaseHTTPRequestHandler):
    def _json(self, obj, code=200):
        body = json.dumps(obj, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _file(self, path: Path, mime: str):
        if not path.exists():
            self.send_error(404)
            return
        body = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = urlparse(self.path).path
        if path in ("/", "/index.html"):
            self._file(TEMPLATES_DIR / "index.html", "text/html; charset=utf-8")
        elif path == "/static/echarts.min.js":
            self._file(STATIC_DIR / "echarts.min.js", "application/javascript")
        elif path == "/api/overview":
            try:
                self._json(overview())
            except Exception as e:
                self._json({"error": str(e)}, 500)
        else:
            self.send_error(404)

    def do_POST(self):
        path = urlparse(self.path).path
        length = int(self.headers.get("Content-Length", 0))
        try:
            payload = json.loads(self.rfile.read(length) or b"{}")
        except Exception:
            payload = {}
        try:
            if path == "/api/pattern":
                ok = update_pattern(payload.get("id", ""), payload.get("weight"), payload.get("status"))
                self._json({"ok": ok})
            elif path == "/api/dimension":
                ok = update_dimension(payload.get("dim", ""), float(payload.get("weight", 1.0)))
                self._json({"ok": ok, "dimensions": load_dimensions()})
            else:
                self.send_error(404)
        except Exception as e:
            self._json({"error": str(e)}, 500)

    def log_message(self, fmt, *args):
        sys.stderr.write(f"[dashboard] {self.address_string()} {fmt % args}\n")


class ThreadingServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True


def main():
    srv = ThreadingServer(("127.0.0.1", PORT), Handler)
    print(f"ClipForge 自进化仪表盘：http://127.0.0.1:{PORT}")
    print(f"数据根：{CLIPFORGE_ROOT}")
    print(f"patterns:{len(all_pattern_files())} workspace:{WORKSPACE}")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\n关闭")


if __name__ == "__main__":
    main()
