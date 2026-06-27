# Streamlit Final App

## 폴더 위치

D:\11\AI_ASSISTANT\streamlit_app

## 실행

```powershell
cd "D:\11\AI_ASSISTANT\streamlit_app"
pip install -r requirements.txt
streamlit run Home.py
```

## 구조

streamlit_app/
├── Home.py
├── config.py
├── pages/
│   ├── 1_Test_Case_Import.py
│   ├── 2_Video_Validation.py
│   ├── 3_Execution_Result.py
│   ├── 4_AI_Analysis.py
│   └── 5_Report.py
└── services/
    ├── state.py
    ├── testcase_loader.py
    ├── detector.py
    ├── executor.py
    ├── ai_analyzer.py
    └── report_generator.py

## 핵심 기능

- 모든 페이지에 공통 Sidebar 설정
- Requirement / BDD / ATDD / TDD / DDD / YOLO 설정 / Actual Action 공통 관리
- JSON/XLSX Test Case Import
- YOLO 주행 영상 객체 검출
- PASS / FAIL / NO_DATA 판정
- Qwen3 기반 AI 분석
- PDF / Excel Report 생성