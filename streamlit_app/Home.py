import streamlit as st
from services.state import init_state, render_sidebar

st.set_page_config(page_title="AI Functional Safety Validation Platform", layout="wide")

init_state()
render_sidebar()

st.title("AI Functional Safety Validation Platform")
st.caption("Requirement → ISO26262 RAG → Test Case → YOLO Validation → Metrics → AI Analysis → Report")

st.markdown("""
## Final Workflow

### Shift Left
Codebeamer Requirement → ISO26262 RAG → Qwen3 Analysis → BDD/ATDD/TDD/DDD Test Case → Traceability

### Shift Right
Driving Video → YOLO Detection → Test Execution → PASS/FAIL → AI Root Cause Analysis → Evidence Report
""")

col1, col2, col3, col4 = st.columns(4)
col1.metric("Development Method", st.session_state.development_method)
col2.metric("Loaded Test Cases", len(st.session_state.testcases))
col3.metric("Execution Results", len(st.session_state.execution_results))
col4.metric("Actual Action", st.session_state.actual_action)

st.divider()
st.subheader("Platform Features")

features = [
    ("1. Test Case Import", "Sidebar에서 생성한 JSON/XLSX/PDF 테스트케이스를 불러옵니다.", "Shift Left"),
    ("2. AI Video Validation", "주행영상을 업로드하고 AI로 보행자, 차량, 신호등 등을 검출합니다.", "YOLO"),
    ("3. Execution Result", "Expected Action과 Actual Action을 비교하여 PASS / FAIL / NO_DATA를 판단합니다.", "PASS/FAIL"),
    ("4. AI Analysis", "Qwen3가 ISO26262와 개발 방법론 관점에서 실패 원인과 조치 의견을 분석합니다.", "Qwen3"),
    ("5. Report", "PDF / Excel 기반 검증 보고서를 생성합니다.", "Evidence"),
    ("6. Test Design & Metrics", "경계값 분석, 동등분할, Precision, Recall, Accuracy, F1 Score를 그래프로 확인합니다.", "Metrics"),
]

cols = st.columns(3)
for i, (title, desc, value) in enumerate(features):
    with cols[i % 3]:
        with st.container(border=True):
            st.markdown(f"### {title}")
            st.caption(value)
            st.write(desc)

st.divider()
st.info("왼쪽 사이드바 설정은 temp/streamlit_settings.json에 저장되어 페이지를 이동해도 유지됩니다.")