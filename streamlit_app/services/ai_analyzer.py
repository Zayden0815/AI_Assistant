import requests
from config import OLLAMA_URL, OLLAMA_MODEL

def method_guide(method):
    return {
        "BDD": "BDD: Feature, Scenario, Given-When-Then 관점으로 PASS/FAIL을 설명한다.",
        "ATDD": "ATDD: Acceptance Criteria 충족 여부와 사용자 수용조건 중심으로 설명한다.",
        "TDD": "TDD: Arrange-Act-Assert, assertion 실패/성공 관점으로 설명한다.",
        "DDD": "DDD: Bounded Context, Entity, Aggregate, Domain Rule 위반 여부 중심으로 설명한다.",
    }.get(method, "BDD 관점으로 설명한다.")

def ask_ai(prompt):
    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
            },
            timeout=180,
        )
        response.raise_for_status()
        return response.json().get("response", "")
    except Exception as e:
        return f"AI 분석 실패: {e}"

def analyze_result_with_ai(requirement, testcase, result, development_method="BDD"):
    prompt = f"""
너는 모빌리티 기능안전 테스트 엔지니어다.

아래 주행영상 기반 테스트 결과를 보고 PASS/FAIL 판정 사유를 분석해라.
ISO 26262 관점과 개발방법론 관점을 함께 적용해라.

[Development Method]
{development_method}

[Method Guide]
{method_guide(development_method)}

[Requirement]
{requirement}

[Test Case]
{testcase}

[Execution Result]
TC ID: {result.get("tc_id")}
Detected Objects: {result.get("detected_objects")}
Frame: {result.get("frame_no")}
Expected Action: {result.get("expected_action")}
Actual Action: {result.get("actual_action")}
Result: {result.get("result")}
Evidence: {result.get("evidence_path")}

출력 형식:
1. 판정 요약
2. PASS 또는 FAIL 사유
3. {development_method} 관점 해석
4. 기능안전 관점 리스크
5. 추가 확인이 필요한 데이터
6. 테스트 엔지니어 조치 의견
"""
    return ask_ai(prompt)

def chat_with_ai(user_message, context="", development_method="BDD"):
    prompt = f"""
너는 AI Functional Safety Validation Platform의 테스트 엔지니어 보조 AI다.
사용자의 질문에 대해 ISO 26262, 테스트케이스, 영상 검증, PASS/FAIL 분석 관점으로 답변해라.

[Development Method]
{development_method}

[Method Guide]
{method_guide(development_method)}

[Context]
{context}

[Question]
{user_message}
"""
    return ask_ai(prompt)