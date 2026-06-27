from pathlib import Path
import streamlit as st
import pandas as pd

from services.state import init_state, render_sidebar
from services.ai_analyzer import analyze_result_with_ai, chat_with_ai

st.set_page_config(page_title="AI Analysis", layout="wide")
init_state()
render_sidebar()

st.title("4. AI Analysis")

if not st.session_state.execution_results:
    st.warning("아직 실행 결과가 없습니다.")
else:
    df = pd.DataFrame(st.session_state.execution_results)
    selected_tc = st.selectbox("AI 분석할 TC 선택", df["tc_id"].tolist())
    selected = df[df["tc_id"] == selected_tc].iloc[0].to_dict()

    evidence = selected.get("evidence_path")
    if evidence and Path(evidence).exists():
        st.image(evidence, caption=f"Evidence Frame: {selected.get('frame_no')}")

    if st.button("AI Analyze PASS / FAIL"):
        tc = next((x for x in st.session_state.testcases if x.get("tc_id") == selected_tc), {})

        with st.spinner("Qwen3가 PASS/FAIL 사유를 분석 중..."):
            analysis = analyze_result_with_ai(
                requirement=st.session_state.requirement,
                testcase=tc,
                result=selected,
                development_method=st.session_state.development_method,
            )

        st.session_state.ai_context = analysis
        st.subheader("AI Analysis")
        st.write(analysis)

st.divider()
st.subheader("AI Test Engineer Chat")

context = st.text_area("Context", value=st.session_state.get("ai_context", ""), height=160)
question = st.text_input("질문", placeholder="예: 이 FAIL 결과를 ISO 26262와 ATDD 관점에서 어떻게 설명할 수 있어?")

if st.button("Ask Qwen3"):
    with st.spinner("Qwen3 응답 생성 중..."):
        answer = chat_with_ai(
            user_message=question,
            context=context,
            development_method=st.session_state.development_method,
        )
    st.write(answer)