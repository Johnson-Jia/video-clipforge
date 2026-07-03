"""电影级剪辑映射（流程固化层）：分镜字段 → 渲染。

创意自由（LLM，stage3）：选 shot_size/camera_move/transition 的值
流程固化（本模块）：映射到 GSAP 相机动画 / phase 过渡 / 布局密度（脚本确定，LLM 不碰）

铁律：LLM 不碰映射逻辑；本模块不碰创意选值。非法值 → 默认兜底（不阻塞管线）。
"""
from __future__ import annotations

SHOT_SIZES = {"大远景", "远景", "全景", "中景", "近景", "特写", "大特写"}
CAMERA_MOVES = {"固定", "推", "拉", "摇", "俯仰", "移", "跟", "手持", "环绕", "变焦", "第一视角", "荷兰角"}
TRANSITIONS = {"硬切", "叠化", "淡入", "淡出", "黑场"}

DEFAULT_SHOT_SIZE = "中景"
DEFAULT_CAMERA_MOVE = "固定"
DEFAULT_TRANSITION = "硬切"


def camera_move_to_gsap(sid: str, camera_move: str, start: float, duration: float) -> str:
    """运镜 → GSAP 相机动画 JS（对 .layer-content 内容层，全代码库统一，在场景 duration 内）。

    返回 JS 语句（无 ; 结尾，由调用方拼）；固定/第一视角/跟 → 返 ""（无相机动画）。
    非法 camera_move → 默认固定 → ""。
    """
    cm = camera_move if camera_move in CAMERA_MOVES else DEFAULT_CAMERA_MOVE
    sel = f"#{sid} .layer-content"
    if cm == "推":
        return (f"tl.fromTo('{sel}',{{scale:1.0}},"
                f"{{scale:1.1,duration:{duration:.2f},ease:'power2.inOut'}},{start:.2f})")
    if cm == "拉":
        return (f"tl.fromTo('{sel}',{{scale:1.0}},"
                f"{{scale:0.9,duration:{duration:.2f},ease:'power2.inOut'}},{start:.2f})")
    if cm == "摇":
        return (f"tl.fromTo('{sel}',{{x:0}},"
                f"{{x:60,duration:{duration:.2f},ease:'sine.inOut'}},{start:.2f})")
    if cm == "俯仰":
        return (f"tl.fromTo('{sel}',{{y:0}},"
                f"{{y:-60,duration:{duration:.2f},ease:'sine.inOut'}},{start:.2f})")
    if cm == "移":
        return (f"tl.fromTo('{sel}',{{x:0,y:0}},"
                f"{{x:80,y:-40,duration:{duration:.2f},ease:'none'}},{start:.2f})")
    if cm == "手持":
        repeat = max(0, int(duration // 0.5) - 1)
        return (f"tl.to('{sel}',"
                f"{{x:'+=10',y:'+=8',rotation:'+=1',duration:0.5,repeat:{repeat},"
                f"yoyo:true,ease:'sine.inOut'}},{start:.2f})")
    if cm == "环绕":
        return (f"tl.fromTo('{sel}',{{rotation:0}},"
                f"{{rotation:5,duration:{duration:.2f},ease:'power1.inOut'}},{start:.2f})")
    if cm == "变焦":
        return (f"tl.fromTo('{sel}',{{scale:1.0}},"
                f"{{scale:1.2,duration:0.3,ease:'power3.out'}},{start:.2f})")
    if cm == "荷兰角":
        return f"tl.set('{sel}',{{rotation:-5}},{start:.2f})"
    return ""


def transition_to_phase(prev_sid: str, cur_sid: str, t: float, transition: str) -> list[str]:
    """转场 → GSAP phase 过渡 JS 语句列表（镜间：前镜 → 当前镜，时刻 t）。

    硬切=即时 set；叠化=前镜 fade out 0.4s；淡入=当前镜 fade in 0.5s；
    淡出=前镜 fade out 0.5s 后当前镜入；黑场=经 opacity:0 三步过渡。
    非法 transition → 默认硬切。
    """
    tr = transition if transition in TRANSITIONS else DEFAULT_TRANSITION
    if tr == "硬切":
        return [
            f"tl.set('#{prev_sid}',{{opacity:0}},{t:.2f})",
            f"tl.set('#{cur_sid}',{{opacity:1}},{t:.2f})",
        ]
    if tr == "叠化":
        return [
            f"tl.to('#{prev_sid}',{{opacity:0,duration:0.4,ease:'power1.inOut'}},{t:.2f})",
            f"tl.set('#{cur_sid}',{{opacity:1}},{t:.2f})",
        ]
    if tr == "淡入":
        return [
            f"tl.set('#{prev_sid}',{{opacity:0}},{t:.2f})",
            f"tl.to('#{cur_sid}',{{opacity:1,duration:0.5,ease:'power1.out'}},{t:.2f})",
        ]
    if tr == "淡出":
        return [
            f"tl.to('#{prev_sid}',{{opacity:0,duration:0.5,ease:'power1.inOut'}},{t:.2f})",
            f"tl.set('#{cur_sid}',{{opacity:1}},{t + 0.5:.2f})",
        ]
    if tr == "黑场":
        return [
            f"tl.to('#{prev_sid}',{{opacity:0,duration:0.25}},{t:.2f})",
            f"tl.set('#{cur_sid}',{{opacity:0}},{t:.2f})",
            f"tl.to('#{cur_sid}',{{opacity:1,duration:0.25}},{t + 0.25:.2f})",
        ]
    return []


def shot_size_to_density(shot_size: str) -> str:
    """景别 → 布局密度（density_hint）：generous/standard/compact。半确定引导。

    特写/大特写 → generous；远景/大远景 → compact；其余 standard。非法 → standard。
    """
    ss = shot_size if shot_size in SHOT_SIZES else DEFAULT_SHOT_SIZE
    if ss in ("特写", "大特写"):
        return "generous"
    if ss in ("全景", "远景", "大远景"):
        return "compact"
    return "standard"
