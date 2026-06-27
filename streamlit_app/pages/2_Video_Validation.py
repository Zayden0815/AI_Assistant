import streamlit as st
import pandas as pd
import plotly.express as px

from services.state import init_state, render_sidebar
from config import UPLOAD_DIR
from services.detector import YOLODetector, process_video
from services.executor import validate_testcases, make_validation_signature

st.set_page_config(page_title="Video Motion Validation", layout="wide")
init_state()
render_sidebar()

st.title("2. Video Motion Validation")
st.caption("YOLO Object Detection + Tracking ID + Optical Flow + Temporal Event Validation")

col_video, col_result = st.columns([2, 1])

with col_video:
    video_file = st.file_uploader("Upload Driving Video", type=["mp4", "avi", "mov"])
    if video_file:
        video_path = UPLOAD_DIR / video_file.name
        video_path.write_bytes(video_file.read())
        if st.session_state.get("current_video_path") != str(video_path):
            st.session_state.current_video_path = str(video_path)
            st.session_state.execution_results = []
            st.session_state.video_result = None
            st.session_state.last_validation_signature = ""
            st.session_state.validation_status = "Video changed. Please run validation again."
        st.video(str(video_path))

with col_result:
    st.subheader("Current Settings")
    st.write("Requirement:", st.session_state.requirement[:120] + ("..." if len(st.session_state.requirement) > 120 else ""))
    st.write("Method:", st.session_state.development_method)
    st.write("YOLO Model:", st.session_state.yolo_model)
    st.write("Confidence:", st.session_state.confidence)
    st.write("Frame Step:", st.session_state.frame_step)
    st.write("Max Frames:", st.session_state.max_frames)
    st.write("Actual Action:", st.session_state.actual_action)
    st.write("Status:", st.session_state.validation_status)
    run = st.button("Run Video Motion Validation", type="primary")

if run:
    if not st.session_state.get("current_video_path"):
        st.error("영상을 먼저 업로드하세요.")
    elif not st.session_state.testcases:
        st.error("Test Case를 먼저 Import 하세요.")
    else:
        signature = make_validation_signature(
            requirement=st.session_state.requirement,
            testcases=st.session_state.testcases,
            video_path=st.session_state.current_video_path,
            settings={"development_method": st.session_state.development_method, "yolo_model": st.session_state.yolo_model, "confidence": st.session_state.confidence, "frame_step": st.session_state.frame_step, "max_frames": st.session_state.max_frames, "actual_action": st.session_state.actual_action},
        )
        with st.spinner("YOLO + Tracking + Optical Flow + Temporal Validation 실행 중..."):
            detector = YOLODetector(model_path=st.session_state.yolo_model, conf=st.session_state.confidence)
            video_result = process_video(st.session_state.current_video_path, detector, frame_step=int(st.session_state.frame_step), max_frames=int(st.session_state.max_frames))
            st.session_state.video_result = video_result
            st.session_state.execution_results = validate_testcases(st.session_state.testcases, video_result["processed_frames"], requirement=st.session_state.requirement, manual_actual_action=st.session_state.actual_action, temporal_summary=video_result.get("temporal_summary", {}))
            st.session_state.last_validation_signature = signature
            st.session_state.validation_status = "Video motion validation completed."
        st.success("Video motion validation completed")

if st.session_state.video_result:
    st.subheader("Evidence Preview")
    frames = st.session_state.video_result["processed_frames"]
    st.write(f"Processed Frames: {len(frames)}")
    cols = st.columns(3)
    for i, frame in enumerate(frames[:9]):
        with cols[i % 3]:
            st.image(frame["evidence_path"], caption=f"Frame {frame['frame_no']} / {frame['timestamp_sec']}s")
    st.subheader("Video Motion Summary Dashboard")
    temporal = st.session_state.video_result.get("temporal_summary", {})
    left, right = st.columns([1, 1.25])
    with left:
        c1, c2 = st.columns(2)
        c1.metric("Ego Motion State", temporal.get("ego_motion_state", "UNKNOWN"))
        c2.metric("Processed Frames", temporal.get("processed_frame_count", 0))
        metric_df = pd.DataFrame([
            {"Metric": "Approaching", "Count": len(temporal.get("approaching_objects", []))},
            {"Metric": "Moving", "Count": len(temporal.get("moving_objects", []))},
            {"Metric": "Persistent", "Count": len(temporal.get("persistent_objects", []))},
            {"Metric": "Stable", "Count": len(temporal.get("stable_objects", []))},
            {"Metric": "Receding", "Count": len(temporal.get("receding_objects", []))},
            {"Metric": "Unstable Conf.", "Count": len(temporal.get("confidence_unstable_objects", []))},
        ])
        fig_metric = px.bar(metric_df, x="Metric", y="Count", text="Count", title="Tracked Object Motion Counts")
        fig_metric.update_layout(height=330, margin=dict(l=20, r=20, t=50, b=20))
        st.plotly_chart(fig_metric, use_container_width=True)
    with right:
        summaries = temporal.get("object_summaries", {})
        if summaries:
            rows = []
            for key, s in summaries.items():
                rows.append({"Track": key, "Object": s.get("object", "-"), "Track ID": s.get("track_id", "-"), "Motion": s.get("motion_state", "UNKNOWN"), "Event Range": s.get("event_frame_range", "-"), "Area Change %": round(float(s.get("area_delta_ratio", 0)) * 100, 2), "Avg Flow": float(s.get("avg_flow_magnitude", 0)), "Center Move": float(s.get("center_move", 0)), "Avg Confidence": float(s.get("avg_confidence", 0))})
            obj_df = pd.DataFrame(rows)
            fig_area = px.bar(obj_df, x="Track", y="Area Change %", color="Motion", text="Area Change %", title="Object Approach / Recede by BBox Area Change")
            fig_area.update_layout(height=330, margin=dict(l=20, r=20, t=50, b=20))
            st.plotly_chart(fig_area, use_container_width=True)
            st.dataframe(obj_df, use_container_width=True)
        else:
            st.warning("Video motion summary가 없습니다. 검출 객체가 부족하거나 frame_step이 너무 클 수 있습니다.")
    if temporal.get("object_summaries"):
        st.subheader("Motion Trend")
        trend_rows = []
        for frame in frames:
            for det in frame.get("detections", []):
                trend_rows.append({"Frame": frame.get("frame_no"), "Time": frame.get("timestamp_sec"), "Track": f"{det.get('mapped_object')}_T{det.get('track_id')}", "Object": det.get("mapped_object") or det.get("class_name"), "Confidence": det.get("confidence", 0), "BBox Area Ratio": det.get("bbox_area_ratio", 0), "Flow Magnitude": det.get("flow_mag", 0)})
        if trend_rows:
            trend_df = pd.DataFrame(trend_rows)
            tab1, tab2, tab3 = st.tabs(["Confidence Trend", "BBox Area Trend", "Optical Flow Trend"])
            with tab1:
                st.plotly_chart(px.line(trend_df, x="Frame", y="Confidence", color="Track", markers=True, title="Object Confidence Across Frames"), use_container_width=True)
            with tab2:
                st.plotly_chart(px.line(trend_df, x="Frame", y="BBox Area Ratio", color="Track", markers=True, title="BBox Area Ratio Across Frames"), use_container_width=True)
            with tab3:
                st.plotly_chart(px.line(trend_df, x="Frame", y="Flow Magnitude", color="Track", markers=True, title="Optical Flow Magnitude Across Frames"), use_container_width=True)

if st.session_state.execution_results:
    st.subheader("Validation Result Preview")
    st.dataframe(st.session_state.execution_results, use_container_width=True)
