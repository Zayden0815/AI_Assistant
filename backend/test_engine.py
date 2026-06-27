def analyze_requirement(requirement_text: str):
    req = requirement_text.lower()
    if "pedestrian" in req or "person" in req or "보행자" in req:
        return {
            "hazard": "Vehicle may collide with a pedestrian if braking is not activated.",
            "asil": "ASIL D candidate",
            "safety_goal": "Prevent pedestrian collision caused by failure to brake.",
            "fsr": "Vehicle shall activate braking when a pedestrian is detected in the driving path.",
            "tsr": "ADAS decision module shall send BRAKE command when pedestrian detection confidence exceeds the safety threshold."
        }
    if "traffic light" in req or "red light" in req or "신호등" in req:
        return {
            "hazard": "Vehicle may enter an intersection during a red traffic light.",
            "asil": "ASIL C candidate",
            "safety_goal": "Prevent unsafe intersection entry when a red traffic light is detected.",
            "fsr": "Vehicle shall stop when a red traffic light is detected.",
            "tsr": "Traffic light recognition module shall provide RED_LIGHT event to decision module."
        }
    if "brake" in req or "브레이크" in req or "제동" in req:
        return {
            "hazard": "Vehicle may fail to decelerate or stop under unsafe conditions.",
            "asil": "ASIL C/D candidate",
            "safety_goal": "Prevent unreasonable risk caused by braking function failure.",
            "fsr": "Vehicle shall enter a safe braking or warning state when a braking-related fault or hazard is detected.",
            "tsr": "Vehicle control module shall monitor brake command consistency and report diagnostic faults."
        }
    return {
        "hazard": "Potential unsafe behavior if the requirement is not correctly implemented.",
        "asil": "ASIL candidate requires HARA analysis.",
        "safety_goal": "Prevent unreasonable risk caused by malfunctioning behavior.",
        "fsr": "System shall detect unsafe conditions and transition to a safe state.",
        "tsr": "Technical safety mechanism shall monitor input/output consistency and provide diagnostic reaction."
    }

def generate_test_cases(requirement_text: str, prefix: str = "TC", auto_number: bool = True):
    req = requirement_text.lower()
    def tc_id(n):
        return f"{prefix}-{str(n).zfill(3)}" if auto_number else ""
    if "pedestrian" in req or "person" in req or "보행자" in req:
        return [
            {"tc_id": tc_id(1), "title": "Pedestrian detected while vehicle is moving", "given": "Pedestrian is detected in front of the vehicle and vehicle speed is 30 km/h", "when": "The ADAS decision logic is executed", "then": "Vehicle shall activate braking", "expected_action": "BRAKE", "verification_method": "Simulation / Video-based validation"},
            {"tc_id": tc_id(2), "title": "No pedestrian detected", "given": "No pedestrian is detected and vehicle speed is 30 km/h", "when": "The ADAS decision logic is executed", "then": "Vehicle shall keep driving", "expected_action": "KEEP_DRIVING", "verification_method": "Functional scenario validation"},
            {"tc_id": tc_id(3), "title": "Pedestrian detected but brake not activated", "given": "Pedestrian is detected in front of the vehicle", "when": "Actual vehicle action is KEEP_DRIVING", "then": "Test shall fail because expected action is BRAKE", "expected_action": "BRAKE", "verification_method": "Negative scenario validation"}
        ]
    if "traffic light" in req or "red light" in req or "신호등" in req:
        return [
            {"tc_id": tc_id(1), "title": "Red traffic light detected", "given": "Red traffic light is detected ahead", "when": "The vehicle approaches the intersection", "then": "Vehicle shall stop", "expected_action": "BRAKE", "verification_method": "Scenario validation"},
            {"tc_id": tc_id(2), "title": "Green traffic light detected", "given": "Green traffic light is detected ahead", "when": "The vehicle approaches the intersection", "then": "Vehicle shall keep driving", "expected_action": "KEEP_DRIVING", "verification_method": "Functional validation"}
        ]
    return [
        {"tc_id": tc_id(1), "title": "Normal condition validation", "given": "System receives valid input", "when": "The function is executed", "then": "Expected safe action shall be performed", "expected_action": "SAFE_ACTION", "verification_method": "Requirement-based test"},
        {"tc_id": tc_id(2), "title": "Abnormal condition validation", "given": "System receives abnormal or unsafe input", "when": "The function is executed", "then": "System shall transition to safe state", "expected_action": "SAFE_STATE", "verification_method": "Negative / robustness test"}
    ]

def build_traceability(requirement_text: str, test_cases):
    return {
        "requirement": "REQ-001",
        "hazard": "HZ-001",
        "safety_goal": "SG-001",
        "fsr": "FSR-001",
        "tsr": "TSR-001",
        "test_cases": [tc.get("tc_id", "") for tc in test_cases],
        "chain": ["REQ-001", "HZ-001", "SG-001", "FSR-001", "TSR-001"] + [tc.get("tc_id", "") for tc in test_cases]
    }

def related_parts_from_sources(sources):
    parts, pages = [], []
    for s in sources:
        part, page = s.get("part"), s.get("page")
        if part and part not in parts:
            parts.append(part)
        if page and page not in pages:
            pages.append(page)
    return parts, pages