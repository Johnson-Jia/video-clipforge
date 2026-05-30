"""skeleton_builder package — re-exports from the standalone skeleton_builder.py module.

This package exists to house the templates/ directory. The actual module logic
lives in the sibling skeleton_builder.py file. We re-export everything here so
that ``from engine.skeleton_builder import render_skeleton`` works correctly
despite the name overlap.
"""
import importlib.util
import sys
from pathlib import Path

_MODULE_PATH = Path(__file__).resolve().parent.parent / "skeleton_builder.py"

_spec = importlib.util.spec_from_file_location(
    "engine._skeleton_builder_impl",
    str(_MODULE_PATH),
    submodule_search_locations=[],
)
_impl = importlib.util.module_from_spec(_spec)  # type: ignore[arg-type]
sys.modules["engine._skeleton_builder_impl"] = _impl
_spec.loader.exec_module(_impl)  # type: ignore[union-attr]

# Re-export public API
IMMERSION_CSS_VARS = _impl.IMMERSION_CSS_VARS
TEMPLATES_DIR = _impl.TEMPLATES_DIR
load_json = _impl._load_json
parse_design = _impl._parse_design
build_css_variables = _impl._build_css_variables
compute_phase_breakpoints = _impl._compute_phase_breakpoints
find_text_boundary = _impl._find_text_boundary
build_scene_skeletons = _impl.build_scene_skeletons
render_skeleton = _impl.render_skeleton

__all__ = [
    "IMMERSION_CSS_VARS",
    "TEMPLATES_DIR",
    "build_scene_skeletons",
    "build_css_variables",
    "compute_phase_breakpoints",
    "find_text_boundary",
    "parse_design",
    "render_skeleton",
]
