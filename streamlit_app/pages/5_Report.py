from pathlib import Path
import streamlit as st
import pandas as pd

from services.state import init_state, render_sidebar
from services.report_generator import generate_pdf_report, generate_excel_report

st.set_page_config(page_title="Report", layout="wide")
init_state()
render_sidebar()

st.title("5. Validation Report")

if not st.session_state.execution_results:
    st.warning("아직 실행 결과가 없습니다.")
else:
    st.dataframe(pd.DataFrame(st.session_state.execution_results), use_container_width=True)

    col_pdf, col_xlsx = st.columns(2)

    with col_pdf:
        if st.button("Generate PDF Validation Report"):
            path = generate_pdf_report(
                st.session_state.requirement,
                st.session_state.execution_results,
                development_method=st.session_state.development_method,
            )
            st.success(f"PDF generated: {path}")
            with open(path, "rb") as f:
                st.download_button("Download PDF", f, file_name=Path(path).name)

    with col_xlsx:
        if st.button("Generate Excel Validation Report"):
            path = generate_excel_report(
                st.session_state.execution_results,
                development_method=st.session_state.development_method,
            )
            st.success(f"Excel generated: {path}")
            with open(path, "rb") as f:
                st.download_button("Download Excel", f, file_name=Path(path).name)