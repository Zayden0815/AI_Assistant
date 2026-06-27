import json
from pathlib import Path
import streamlit as st

METHODS = ["BDD", "ATDD", "TDD", "DDD"]
ACTIONS = ["AUTO_INFER", "BRAKE", "KEEP_DRIVING", "SLOW_DOWN", "WARNING", "SAFE_STATE"]

BASE_DIR = Path(__file__).resolve().parents[1]
TEMP_DIR = BASE_DIR / "temp"
TEMP_DIR.mkdir(parents=True, exist_ok=True)
SETTINGS_PATH = TEMP_DIR / "streamlit_settings.json"

DEFAULTS = {
    "requirement": "Vehicle shall stop when pedestrian is detected.",
    "development_method": "ATDD",
    "actual_action": "AUTO_INFER",
    "yolo_model": "yolov8n.pt",
    "confidence": 0.35,
    "frame_step": 30,
    "max_frames": 80,
    "testcases": [],
    "video_result": None,
    "execution_results": [],
    "ai_context": "",
    "current_video_path": "",
    "last_validation_signature": "",
    "validation_status": "Not executed",
}


SETTING_KEYS = [
    "requirement",
    "development_method",
    "actual_action",
    "yolo_model",
    "confidence",
    "frame_step",
    "max_frames",
]


def _load_settings_file():
    if not SETTINGS_PATH.exists():
        return {}
    try:
        return json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_settings_file():
    data = {key: st.session_state.get(key, DEFAULTS[key]) for key in SETTING_KEYS}
    SETTINGS_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def init_state():
    saved = _load_settings_file()

    for key, value in DEFAULTS.items():
        if key not in st.session_state:
            st.session_state[key] = saved.get(key, value)

    # Widget keys are separate from real state keys.
    for key in SETTING_KEYS:
        ui_key = f"ui_{key}"
        if ui_key not in st.session_state:
            st.session_state[ui_key] = st.session_state.get(key, DEFAULTS[key])


def invalidate_validation():
    st.session_state.execution_results = []
    st.session_state.ai_context = ""
    st.session_state.last_validation_signature = ""
    st.session_state.validation_status = "Settings changed. Please run validation again."


def _sync_from_widget(key):
    ui_key = f"ui_{key}"
    st.session_state[key] = st.session_state.get(ui_key, DEFAULTS[key])
    _save_settings_file()
    invalidate_validation()


def _sync_all_ui_from_state():
    for key in SETTING_KEYS:
        st.session_state[f"ui_{key}"] = st.session_state.get(key, DEFAULTS[key])


def reset_settings():
    for key in SETTING_KEYS:
        st.session_state[key] = DEFAULTS[key]
    _sync_all_ui_from_state()
    _save_settings_file()
    invalidate_validation()


def render_sidebar():
    init_state()

    st.sidebar.title("Validation Settings")

    st.sidebar.text_area(
        "Requirement",
        key="ui_requirement",
        height=120,
        on_change=lambda: _sync_from_widget("requirement"),
    )

    st.sidebar.selectbox(
        "Development Method",
        METHODS,
        key="ui_development_method",
        on_change=lambda: _sync_from_widget("development_method"),
    )

    st.sidebar.divider()

    st.sidebar.text_input(
        "YOLO Model",
        key="ui_yolo_model",
        on_change=lambda: _sync_from_widget("yolo_model"),
    )

    st.sidebar.slider(
        "YOLO Confidence",
        0.10,
        0.90,
        key="ui_confidence",
        step=0.05,
        on_change=lambda: _sync_from_widget("confidence"),
    )

    st.sidebar.number_input(
        "Frame Step",
        min_value=1,
        max_value=300,
        key="ui_frame_step",
        on_change=lambda: _sync_from_widget("frame_step"),
    )

    st.sidebar.number_input(
        "Max Frames",
        min_value=1,
        max_value=500,
        key="ui_max_frames",
        on_change=lambda: _sync_from_widget("max_frames"),
    )

    st.sidebar.selectbox(
        "Actual Vehicle Action",
        ACTIONS,
        key="ui_actual_action",
        help="AUTO_INFER uses requirement + test case + YOLO detections. Manual values force one action for all cases.",
        on_change=lambda: _sync_from_widget("actual_action"),
    )

    st.sidebar.divider()

    if st.sidebar.button("Reset settings"):
        reset_settings()
        st.rerun()

    st.sidebar.caption("Shared state")
    st.sidebar.write("Requirement:", st.session_state.requirement[:45] + ("..." if len(st.session_state.requirement) > 45 else ""))
    st.sidebar.write("Method:", st.session_state.development_method)
    st.sidebar.write("Actual Action:", st.session_state.actual_action)
    st.sidebar.write("Test Cases:", len(st.session_state.testcases))
    st.sidebar.write("Execution Results:", len(st.session_state.execution_results))
    st.sidebar.write("Status:", st.session_state.validation_status)