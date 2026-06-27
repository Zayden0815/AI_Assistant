import streamlit as st
import pandas as pd

from services.state import init_state, render_sidebar, invalidate_validation
from services.testcase_loader import load_testcases

st.set_page_config(page_title="Test Case Import", layout="wide")
init_state()
render_sidebar()

st.title("1. Test Case Import")

uploaded = st.file_uploader(
    "Sidebar에서 Export한 JSON / Excel / PDF Test Case 업로드",
    type=["json", "xlsx", "pdf"],
)

if uploaded:
    cases = load_testcases(uploaded)

    for tc in cases:
        if not tc.get("methodology"):
            tc["methodology"] = st.session_state.development_method

    st.session_state.testcases = cases
    invalidate_validation()
    st.success(f"Loaded {len(cases)} test cases")

if st.session_state.testcases:
    st.dataframe(pd.DataFrame(st.session_state.testcases), use_container_width=True)
else:
    st.warning("아직 Test Case가 없습니다.")