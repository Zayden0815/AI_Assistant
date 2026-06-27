from pathlib import Path
import streamlit as st
import pandas as pd

from services.state import init_state, render_sidebar

st.set_page_config(page_title="Execution Result", layout="wide")
init_state()
render_sidebar()

st.title("3. Execution Result")

if not st.session_state.execution_results:
    st.warning("아직 실행 결과가 없습니다. 먼저 Video Motion Validation을 실행하세요.")
    st.info(st.session_state.validation_status)
else:
    df = pd.DataFrame(st.session_state.execution_results)
    st.dataframe(df, use_container_width=True)
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Method", st.session_state.development_method)
    c2.metric("PASS", len(df[df["result"] == "PASS"]))
    c3.metric("FAIL", len(df[df["result"] == "FAIL"]))
    c4.metric("NO_DATA", len(df[df["result"] == "NO_DATA"]))
    c5.metric("Ego State", df["ego_motion_state"].iloc[0] if "ego_motion_state" in df.columns and len(df) else "-")
    selected_tc = st.selectbox("Evidence 확인할 TC 선택", df["tc_id"].tolist())
    selected = df[df["tc_id"] == selected_tc].iloc[0].to_dict()
    st.subheader("Selected Result")
    st.json(selected)
    evidence = selected.get("evidence_path")
    if evidence and Path(evidence).exists():
        st.image(evidence, caption=f"Evidence Frame: {selected.get('frame_no')} / Event: {selected.get('event_frame_range', '-')}")
    if selected.get("video_model_reason"):
        st.info("Video Model Reason: " + selected["video_model_reason"])
    if selected.get("temporal_reason"):
        st.info("Temporal Reason: " + selected["temporal_reason"])
    if selected.get("validation_reason"):
        st.info("Validation Reason: " + selected["validation_reason"])
