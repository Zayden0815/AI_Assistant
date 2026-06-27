from pydantic import BaseModel
from typing import List, Optional

class AnalyzeRequest(BaseModel):
    requirement_text: str
    iso_part: str = "all"
    top_k: int = 5
    output_type: str = "analysis"
    auto_tc_number: bool = True
    tc_prefix: str = "TC"

class GenerateRequest(BaseModel):
    requirement_text: str
    tc_prefix: str = "TC"
    auto_tc_number: bool = True

class TraceabilityRequest(BaseModel):
    requirement_text: str
    test_cases: Optional[List[dict]] = None

class ReportRequest(BaseModel):
    requirement_text: str
    iso_reference: Optional[List[dict]] = None
    hazard: str = ""
    asil: str = ""
    safety_goal: str = ""
    fsr: str = ""
    tsr: str = ""
    test_cases: Optional[List[dict]] = None
    traceability: Optional[dict] = None