from pathlib import Path
import json
import re
import requests

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

from rag_engine import ISO26262RAG
from export_service import export_pdf, export_excel, export_json


app = FastAPI(title="AI Functional Safety Validation Assistant")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

rag = None

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "qwen3:4b"


class AnalyzeRequest(BaseModel):
    requirement_text: str
    iso_part: str = "all"
    top_k: int = 8
    output_type: str = "analysis"
    tc_prefix: str = "ATDD"
    auto_tc_number: bool = True
    development_method: str = "ATDD"
    document_template: str = "safety_report"
    export_format: str = "json"
    asil_policy: str = "candidate"


class GenerateRequest(BaseModel):
    requirement_text: str
    tc_prefix: str = "ATDD"
    auto_tc_number: bool = True
    development_method: str = "ATDD"
    document_template: str = "test_case_sheet"
    output_type: str = "testcase"
    asil_policy: str = "candidate"


class TraceabilityRequest(BaseModel):
    requirement_text: str
    test_cases: list[dict] | None = None
    development_method: str = "ATDD"
    document_template: str = "traceability_matrix"


class ReportRequest(BaseModel):
    requirement_text: str
    iso_reference: list[dict] | None = None
    hazard: str = ""
    asil: str = ""
    asil_candidate: str = ""
    asil_basis: str = ""
    safety_goal: str = ""
    fsr: str = ""
    tsr: str = ""
    test_cases: list[dict] | None = None
    traceability: dict | None = None
    development_method: str = "ATDD"
    document_template: str = "safety_report"
    output_type: str = "report"


class ExportRequest(BaseModel):
    requirement: str = ""
    related_parts: str = ""
    referenced_pages: str = ""
    iso: str = ""
    hazard: str = ""
    safety: str = ""
    testcase: str = ""
    trace: str = ""
    export_format: str = "json"
    document_template: str = "safety_report"
    development_method: str = "ATDD"
    test_cases: list[dict] | None = None
    iso_reference: list[dict] | None = None
    traceability: dict | None = None
    asil_candidate: str = ""
    asil_basis: str = ""


@app.on_event("startup")
def startup_event():
    global rag
    print("Loading ISO26262 FAISS RAG...")
    rag = ISO26262RAG()
    print("Backend ready.")


@app.get("/")
def root():
    return {"status": "running", "service": "AI Functional Safety Validation Assistant"}


def build_parts(sources):
    parts = sorted(list({str(s.get("part", "Unknown")) for s in sources}))
    pages = sorted(list({str(s.get("page", "-")) for s in sources}))
    return parts, pages


def apply_tc_prefix(test_cases, prefix="ATDD", auto=True):
    if not isinstance(test_cases, list):
        return []
    if not auto:
        return test_cases
    out = []
    for i, tc in enumerate(test_cases, start=1):
        if not isinstance(tc, dict):
            continue
        item = dict(tc)
        item["tc_id"] = f"{prefix}-{str(i).zfill(3)}"
        out.append(item)
    return out


def extract_json(raw: str):
    if not raw:
        raise ValueError("Empty LLM response")

    cleaned = raw.strip()
    cleaned = re.sub(r"<think>.*?</think>", "", cleaned, flags=re.S).strip()

    start = cleaned.find("{")
    end = cleaned.rfind("}") + 1

    if start < 0 or end <= start:
        raise ValueError("No JSON object found in LLM response")

    return json.loads(cleaned[start:end])


def method_guide(method):
    return {
        "BDD": "BDD: Use Feature, Scenario, Given, When, Then.",
        "ATDD": "ATDD: Use User Story and Acceptance Criteria. Focus on acceptance conditions.",
        "TDD": "TDD: Use Unit Under Test, Arrange, Act, Assert, Mock/Stub.",
        "DDD": "DDD: Use Bounded Context, Entity, Aggregate, Domain Service, Domain Rule.",
    }.get(method, "ATDD: Use Acceptance Criteria.")


def fallback_response(requirement, method, prefix):
    return {
        "hazard": "Preliminary hazard: potential violation of safety-related vehicle behavior. HARA is required.",
        "asil_candidate": "B~D",
        "asil_basis": "Final ASIL cannot be confirmed from requirement text alone. Severity, Exposure, and Controllability must be evaluated through HARA.",
        "safety_goal": "The system shall prevent or mitigate hazardous vehicle behavior related to the requirement.",
        "fsr": "The system shall monitor the relevant driving condition and trigger the appropriate safety action.",
        "tsr": "The technical implementation shall detect the condition, evaluate risk, and issue the required control command or fallback state.",
        "methodology_notes": method_guide(method),
        "test_cases": [
            {
                "tc_id": f"{prefix}-001",
                "title": "Requirement acceptance validation",
                "given": requirement,
                "when": "The system evaluates the driving condition",
                "then": "The expected safety action shall be performed",
                "expected_action": "WARNING",
                "verification_method": "Requirement-based validation",
                "methodology": method
            }
        ],
        "traceability": {
            "requirement": "REQ-001",
            "hazard": "HZ-001",
            "safety_goal": "SG-001",
            "fsr": "FSR-001",
            "tsr": "TSR-001",
            "test_cases": [f"{prefix}-001"],
            "development_method": method,
            "chain": ["REQ-001", "HZ-001", "SG-001", "FSR-001", "TSR-001", f"{prefix}-001"]
        }
    }


def ask_qwen3(requirement, sources, development_method="ATDD", tc_prefix="ATDD", auto_tc_number=True, output_type="analysis", document_template="safety_report", asil_policy="candidate"):
    context = "\n\n".join(
        [
            f"""[Source {i + 1}]
Part: {s.get('part')}
Clause: {s.get('clause')}
Page: {s.get('page')}
Content:
{s.get('content')}
"""
            for i, s in enumerate(sources or [])
        ]
    )

    if not context.strip():
        context = "No strong ISO26262 evidence was retrieved. Provide a preliminary engineering analysis and clearly mark HARA as required."

    asil_instruction = """
ASIL policy:
- Do not return only "근거 부족".
- If Severity, Exposure, and Controllability are missing, return ASIL Candidate such as B~D.
- Clearly state "HARA Required".
- Explain which HARA inputs are missing: vehicle speed, road type, exposure frequency, controllability, operational design domain.
"""

    if asil_policy == "strict":
        asil_instruction = """
ASIL policy:
- Use only retrieved ISO26262 evidence.
- If ASIL cannot be determined, say HARA Required and list missing HARA inputs.
"""

    prompt = f"""
You are an ISO 26262 functional safety test engineer AI.

Use the retrieved ISO26262 evidence first.
If evidence is limited, do not stop at "insufficient evidence".
Provide a preliminary engineering output and mark assumptions clearly.

[Requirement]
{requirement}

[Development Method]
{development_method}

[Method Guide]
{method_guide(development_method)}

[Output Type]
{output_type}

[Document Template]
{document_template}

{asil_instruction}

[ISO26262 Evidence]
{context}

Return JSON only.
Do not include markdown.
Do not include explanations outside JSON.

Required JSON schema:
{{
  "hazard": "",
  "asil_candidate": "",
  "asil_basis": "",
  "required_hara_inputs": "",
  "safety_goal": "",
  "fsr": "",
  "tsr": "",
  "methodology_notes": "",
  "test_cases": [
    {{
      "tc_id": "{tc_prefix}-001",
      "title": "",
      "given": "",
      "when": "",
      "then": "",
      "expected_action": "BRAKE | KEEP_DRIVING | SLOW_DOWN | WARNING | SAFE_STATE",
      "verification_method": "",
      "methodology": "{development_method}"
    }}
  ],
  "traceability": {{
    "requirement": "REQ-001",
    "hazard": "HZ-001",
    "safety_goal": "SG-001",
    "fsr": "FSR-001",
    "tsr": "TSR-001",
    "test_cases": ["{tc_prefix}-001"],
    "development_method": "{development_method}",
    "chain": ["REQ-001", "HZ-001", "SG-001", "FSR-001", "TSR-001", "{tc_prefix}-001"]
  }}
}}
"""

    try:
        response = requests.post(
            OLLAMA_URL,
            json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False},
            timeout=300,
        )
        response.raise_for_status()
        raw = response.json().get("response", "")
        parsed = extract_json(raw)
    except Exception as e:
        print(f"[QWEN ERROR] {e}")
        parsed = fallback_response(requirement, development_method, tc_prefix)
        parsed["methodology_notes"] += f" | LLM fallback used: {e}"

    parsed["test_cases"] = apply_tc_prefix(
        parsed.get("test_cases", []),
        prefix=tc_prefix,
        auto=auto_tc_number,
    )

    if not parsed.get("traceability"):
        parsed["traceability"] = {}

    parsed["traceability"]["development_method"] = development_method
    parsed["traceability"]["test_cases"] = [
        tc.get("tc_id", "") for tc in parsed.get("test_cases", [])
    ]

    if not parsed.get("asil_candidate") and parsed.get("asil"):
        parsed["asil_candidate"] = parsed.get("asil")

    if not parsed.get("asil_candidate"):
        parsed["asil_candidate"] = "B~D"

    if not parsed.get("asil_basis"):
        parsed["asil_basis"] = "HARA Required. Final ASIL requires Severity, Exposure, and Controllability assessment."

    return parsed


@app.post("/analyze")
def analyze(req: AnalyzeRequest):
    sources = rag.search(query=req.requirement_text, top_k=req.top_k, iso_part=req.iso_part)

    qwen = ask_qwen3(
        requirement=req.requirement_text,
        sources=sources,
        development_method=req.development_method,
        tc_prefix=req.tc_prefix,
        auto_tc_number=req.auto_tc_number,
        output_type=req.output_type,
        document_template=req.document_template,
        asil_policy=req.asil_policy,
    )

    related_parts, pages = build_parts(sources)

    iso_reference = [
        {
            "part": s.get("part", "Unknown"),
            "clause": s.get("clause", "Unknown"),
            "page": s.get("page", "-"),
            "score": s.get("score", 0),
            "summary": str(s.get("content", ""))[:800],
        }
        for s in sources
    ]

    return {
        "requirement": req.requirement_text,
        "iso_reference": iso_reference,
        "related_iso_parts": related_parts,
        "referenced_pages": pages,
        "hazard": qwen.get("hazard", ""),
        "asil_candidate": qwen.get("asil_candidate", ""),
        "asil": qwen.get("asil_candidate", ""),
        "asil_basis": qwen.get("asil_basis", ""),
        "required_hara_inputs": qwen.get("required_hara_inputs", ""),
        "safety_goal": qwen.get("safety_goal", ""),
        "fsr": qwen.get("fsr", ""),
        "tsr": qwen.get("tsr", ""),
        "methodology_notes": qwen.get("methodology_notes", ""),
        "development_method": req.development_method,
        "test_cases": qwen.get("test_cases", []),
        "traceability": qwen.get("traceability", {}),
    }


@app.post("/generate-testcases")
def generate(req: GenerateRequest):
    sources = rag.search(query=req.requirement_text, top_k=8, iso_part="all")
    qwen = ask_qwen3(
        requirement=req.requirement_text,
        sources=sources,
        development_method=req.development_method,
        tc_prefix=req.tc_prefix,
        auto_tc_number=req.auto_tc_number,
        output_type=req.output_type,
        document_template=req.document_template,
        asil_policy=req.asil_policy,
    )
    return {"test_cases": qwen.get("test_cases", [])}


@app.post("/generate-traceability")
def traceability(req: TraceabilityRequest):
    tcs = req.test_cases or []
    return {
        "traceability": {
            "requirement": "REQ-001",
            "hazard": "HZ-001",
            "safety_goal": "SG-001",
            "fsr": "FSR-001",
            "tsr": "TSR-001",
            "test_cases": [tc.get("tc_id", "") for tc in tcs],
            "development_method": req.development_method,
            "chain": ["REQ-001", "HZ-001", "SG-001", "FSR-001", "TSR-001"] + [tc.get("tc_id", "") for tc in tcs],
        }
    }


@app.post("/generate-report")
def report(req: ReportRequest):
    return {
        "title": "AI Functional Safety Validation Report",
        "requirement": req.requirement_text,
        "development_method": req.development_method,
        "iso_reference": req.iso_reference or [],
        "hazard": req.hazard,
        "asil_candidate": req.asil_candidate or req.asil,
        "asil_basis": req.asil_basis,
        "safety_goal": req.safety_goal,
        "fsr": req.fsr,
        "tsr": req.tsr,
        "test_cases": req.test_cases or [],
        "traceability": req.traceability or {},
        "message": f"Report data generated for {req.development_method}. Use Export Document.",
    }


@app.post("/export-document")
def export_document(req: ExportRequest):
    data = req.model_dump()
    fmt = (req.export_format or "json").lower()

    if fmt == "json":
        file_path = export_json(data)
        media_type = "application/json"
    elif fmt == "excel":
        file_path = export_excel(data)
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    else:
        file_path = export_pdf(data)
        media_type = "application/pdf"

    return FileResponse(
        path=file_path,
        media_type=media_type,
        filename=Path(file_path).name,
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="127.0.0.1", port=8000, reload=True)