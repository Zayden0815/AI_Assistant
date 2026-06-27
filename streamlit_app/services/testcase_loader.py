import json
import pandas as pd


def load_testcases(uploaded_file):
    name = uploaded_file.name.lower()

    if name.endswith(".json"):
        data = json.load(uploaded_file)

        if isinstance(data, dict):
            if isinstance(data.get("test_cases"), list):
                return normalize_cases(data["test_cases"])

            if data.get("testcase"):
                return parse_testcase_text(data["testcase"])

        if isinstance(data, list):
            return normalize_cases(data)

    if name.endswith(".xlsx"):
        return load_excel_testcases(uploaded_file)

    return []


def load_excel_testcases(uploaded_file):
    xls = pd.ExcelFile(uploaded_file)

    candidate_sheets = [
        "Test Cases",
        "Test Case",
        "TestCases",
        "Safety Report",
        "Functional Safety Report",
    ]

    selected_df = None

    for sheet in candidate_sheets:
        if sheet in xls.sheet_names:
            df = pd.read_excel(uploaded_file, sheet_name=sheet)
            if has_testcase_columns(df):
                selected_df = df
                break

    if selected_df is None:
        for sheet in xls.sheet_names:
            df = pd.read_excel(uploaded_file, sheet_name=sheet)
            if has_testcase_columns(df):
                selected_df = df
                break

    if selected_df is None:
        # 마지막 fallback: 첫 번째 시트 읽기
        selected_df = pd.read_excel(uploaded_file, sheet_name=xls.sheet_names[0])

    return dataframe_to_testcases(selected_df)


def has_testcase_columns(df):
    cols = [str(c).lower().strip() for c in df.columns]

    keywords = [
        "tc id",
        "tc_id",
        "title",
        "given",
        "when",
        "then",
        "expected action",
        "expected_action",
        "test cases",
    ]

    return any(k in cols for k in keywords)


def dataframe_to_testcases(df):
    df = df.fillna("")

    cols = {str(c).lower().strip(): c for c in df.columns}

    def col(*names):
        for n in names:
            key = n.lower().strip()
            if key in cols:
                return cols[key]
        return None

    idc = col("TC ID", "TC_ID", "tc_id")
    titlec = col("Title", "title")
    givenc = col("Given", "given", "Arrange", "Acceptance Criteria", "Domain")
    whenc = col("When", "when", "Act", "Trigger")
    thenc = col("Then", "then", "Assert", "Expected Rule")
    expc = col("Expected Action", "expected_action", "Expected")
    methodc = col("Verification Method", "verification_method", "Method")
    devc = col("Development Method", "Methodology", "methodology")

    # Excel이 한 셀에 Test Cases 텍스트 블록으로 들어간 경우
    text_col = col("Test Cases", "Generated Test Cases", "testcase")
    if text_col:
        full_text = "\n\n".join(str(v) for v in df[text_col].tolist() if str(v).strip())
        parsed = parse_testcase_text(full_text)
        if parsed:
            return parsed

    rows = []

    for _, r in df.iterrows():
        tc_id = str(r.get(idc, "")).strip() if idc else ""
        title = str(r.get(titlec, "")).strip() if titlec else ""
        given = str(r.get(givenc, "")).strip() if givenc else ""
        when = str(r.get(whenc, "")).strip() if whenc else ""
        then = str(r.get(thenc, "")).strip() if thenc else ""
        expected = str(r.get(expc, "")).strip() if expc else ""
        method = str(r.get(methodc, "")).strip() if methodc else ""
        dev = str(r.get(devc, "")).strip() if devc else ""

        # 빈 행 제거
        if not any([tc_id, title, given, when, then, expected]):
            continue

        rows.append(
            {
                "tc_id": tc_id,
                "title": title,
                "given": given,
                "when": when,
                "then": then,
                "expected_action": expected,
                "verification_method": method,
                "methodology": dev,
            }
        )

    return normalize_cases(rows)


def normalize_cases(cases):
    normalized = []

    for i, tc in enumerate(cases, start=1):
        if not isinstance(tc, dict):
            continue

        normalized.append(
            {
                "tc_id": str(tc.get("tc_id") or tc.get("TC ID") or tc.get("TC_ID") or f"TC-{i:03d}"),
                "title": str(tc.get("title") or tc.get("Title") or ""),
                "given": str(tc.get("given") or tc.get("Given") or tc.get("arrange") or tc.get("Arrange") or ""),
                "when": str(tc.get("when") or tc.get("When") or tc.get("act") or tc.get("Act") or ""),
                "then": str(tc.get("then") or tc.get("Then") or tc.get("assert") or tc.get("Assert") or ""),
                "expected_action": str(tc.get("expected_action") or tc.get("Expected Action") or tc.get("expected") or tc.get("Expected") or ""),
                "verification_method": str(tc.get("verification_method") or tc.get("Verification Method") or ""),
                "methodology": str(tc.get("methodology") or tc.get("Development Method") or ""),
            }
        )

    return normalized


def parse_testcase_text(text):
    cases = []

    for block in str(text or "").split("\n\n"):
        lines = [line.strip() for line in block.splitlines() if line.strip()]

        if not lines:
            continue

        first = lines[0]

        if " - " in first:
            tc_id, title = first.split(" - ", 1)
        else:
            tc_id, title = first, ""

        def after(*prefixes):
            for prefix in prefixes:
                for line in lines:
                    if line.lower().startswith(prefix.lower()):
                        return line.split(":", 1)[1].strip() if ":" in line else ""
            return ""

        cases.append(
            {
                "tc_id": tc_id.strip(),
                "title": title.strip(),
                "given": after("Given:", "Arrange:", "Acceptance Criteria:", "Domain:"),
                "when": after("When:", "Act:", "Trigger:"),
                "then": after("Then:", "Assert:", "Expected Rule:"),
                "expected_action": after("Expected Action:", "Expected:"),
                "verification_method": after("Verification Method:"),
                "methodology": after("Methodology:", "Development Method:"),
            }
        )

    return normalize_cases(cases)