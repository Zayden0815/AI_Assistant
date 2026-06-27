import streamlit as st
import pandas as pd
import plotly.express as px

from services.state import init_state, render_sidebar
from services.metrics_calculator import (
    calculate_confusion_metrics,
    metrics_to_dataframe,
    build_equivalence_partition_table,
    build_boundary_value_table,
)

st.set_page_config(page_title="Test Design & Metrics", layout="wide")
init_state()
render_sidebar()

st.title("6. Test Design & Evaluation Metrics")
st.caption("Boundary Value Analysis / Equivalence Partitioning / Precision / Recall / Accuracy / F1 Score")

tab1, tab2, tab3 = st.tabs(["Boundary & Equivalence", "Confusion Metrics", "Portfolio Insight"])

with tab1:
    st.header("Boundary Value Analysis & Equivalence Partitioning")
    col1, col2, col3 = st.columns(3)
    with col1:
        input_name = st.text_input("Input Parameter", value="Vehicle Speed")
    with col2:
        min_value = st.number_input("Minimum Valid Value", value=0.0)
    with col3:
        max_value = st.number_input("Maximum Valid Value", value=120.0)

    if min_value >= max_value:
        st.error("Minimum value must be smaller than Maximum value.")
    else:
        ep_df = build_equivalence_partition_table(min_value, max_value)
        bva_df = build_boundary_value_table(min_value, max_value)

        st.subheader("Equivalence Partitioning")
        st.dataframe(ep_df, use_container_width=True)

        ep_chart_df = pd.DataFrame([
            {"Partition": "Below Min", "Representative": min_value - 1},
            {"Partition": "Valid Mid", "Representative": (min_value + max_value) / 2},
            {"Partition": "Above Max", "Representative": max_value + 1},
        ])
        fig_ep = px.bar(ep_chart_df, x="Partition", y="Representative", text="Representative", title=f"Equivalence Partition Representative Values - {input_name}")
        st.plotly_chart(fig_ep, use_container_width=True)

        st.subheader("Boundary Value Analysis")
        st.dataframe(bva_df, use_container_width=True)

        fig_bva = px.line(bva_df, x="Position", y="Boundary Value", markers=True, title=f"Boundary Value Points - {input_name}")
        fig_bva.add_hrect(y0=min_value, y1=max_value, line_width=0, fillcolor="green", opacity=0.08)
        st.plotly_chart(fig_bva, use_container_width=True)

with tab2:
    st.header("Precision / Recall / Accuracy / F1 Score")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        tp = st.number_input("TP - True Positive", min_value=0, value=8)
    with col2:
        fp = st.number_input("FP - False Positive", min_value=0, value=2)
    with col3:
        tn = st.number_input("TN - True Negative", min_value=0, value=7)
    with col4:
        fn = st.number_input("FN - False Negative", min_value=0, value=3)

    metrics = calculate_confusion_metrics(tp, fp, tn, fn)
    metric_df = metrics_to_dataframe(metrics)

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Precision", f"{metrics['Precision'] * 100:.2f}%")
    m2.metric("Recall", f"{metrics['Recall'] * 100:.2f}%")
    m3.metric("Accuracy", f"{metrics['Accuracy'] * 100:.2f}%")
    m4.metric("F1 Score", f"{metrics['F1 Score'] * 100:.2f}%")

    fig = px.bar(metric_df, x="Metric", y="Percent", text="Percent", title="Evaluation Metrics", range_y=[0, 100])
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Confusion Matrix")
    confusion_df = pd.DataFrame([
        {"Actual / Predicted": "Actual Positive", "Predicted Positive": tp, "Predicted Negative": fn},
        {"Actual / Predicted": "Actual Negative", "Predicted Positive": fp, "Predicted Negative": tn},
    ])
    st.dataframe(confusion_df, use_container_width=True)

with tab3:
    st.header("Portfolio Insight")
    st.markdown("""
이 페이지는 테스트 엔지니어링 사고방식을 보여주는 페이지입니다.

- 요구사항 기반 테스트 설계
- 경계값 분석과 동등분할 기반 테스트 데이터 구성
- YOLO/Object Detection 결과에 대한 정량 평가
- Precision / Recall / Accuracy / F1 Score 이해
- 기능안전 관점에서 False Negative 위험 해석
""")