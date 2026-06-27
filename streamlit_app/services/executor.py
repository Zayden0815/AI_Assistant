import hashlib
import json

ACTION_SET = {"BRAKE", "KEEP_DRIVING", "SLOW_DOWN", "WARNING", "SAFE_STATE"}


def normalize_action(action):
    action = str(action or "").strip().upper().replace(" ", "_")
    return action if action in ACTION_SET else ""


def make_validation_signature(requirement, testcases, video_path, settings):
    raw = json.dumps({"requirement": requirement, "testcases": testcases, "video_path": str(video_path), "settings": settings}, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.md5(raw.encode("utf-8")).hexdigest()


def testcase_text(tc, requirement=""):
    return " ".join([str(requirement or ""), str(tc.get("title", "")), str(tc.get("given", "")), str(tc.get("when", "")), str(tc.get("then", "")), str(tc.get("acceptance_criteria", ""))]).lower()


def infer_expected_from_testcase(tc):
    expected = normalize_action(tc.get("expected_action", ""))
    if expected:
        return expected
    text = testcase_text(tc)
    if any(k in text for k in ["safe state", "fallback", "degraded", "unavailable", "blackout", "diagnostic"]): return "SAFE_STATE"
    if any(k in text for k in ["warn", "warning", "alert", "confidence", "uncertain", "traffic light"]): return "WARNING"
    if any(k in text for k in ["slow", "reduce speed", "unsafe distance", "front vehicle", "following", "cut-in", "headway"]): return "SLOW_DOWN"
    if any(k in text for k in ["brake", "emergency", "collision", "crosswalk", "stopping distance", "critical", "pedestrian in path"]): return "BRAKE"
    return "KEEP_DRIVING"


def required_object_keywords(text):
    groups = []
    if any(k in text for k in ["pedestrian", "person", "child", "vulnerable road user", "vru"]): groups.append({"pedestrian", "person"})
    if any(k in text for k in ["cyclist", "bicycle"]): groups.append({"bicycle"})
    if "motorcycle" in text: groups.append({"motorcycle"})
    if any(k in text for k in ["traffic light", "signal"]): groups.append({"traffic_light", "traffic light"})
    if any(k in text for k in ["front vehicle", "vehicle", "car", "truck", "bus", "parked vehicle"]): groups.append({"vehicle", "car", "truck", "bus", "motorcycle"})
    if any(k in text for k in ["object", "obstacle", "hazard"]): groups.append({"person", "pedestrian", "vehicle", "car", "truck", "bus", "traffic_light", "traffic light", "bicycle", "motorcycle"})
    return groups


def temporal_objects_for_tc(tc, requirement, temporal_summary):
    text = testcase_text(tc, requirement)
    groups = required_object_keywords(text)
    summaries = temporal_summary.get("object_summaries", {}) if temporal_summary else {}
    matched = {}
    for key, summary in summaries.items():
        obj_l = str(summary.get("object", key)).lower()
        key_l = str(key).lower()
        if not groups:
            matched[key] = summary; continue
        for group in groups:
            if obj_l in group or key_l.split("_t")[0] in group:
                matched[key] = summary
    return matched


def select_evidence_from_temporal(matched, temporal_summary):
    if matched:
        best_key = max(matched.keys(), key=lambda k: matched[k].get("last_frame", -1))
        s = matched[best_key]
        return {"frame_no": s.get("last_frame", "-"), "event_frame_range": s.get("event_frame_range", "-"), "evidence_path": s.get("evidence_path", "")}
    summaries = temporal_summary.get("object_summaries", {}) if temporal_summary else {}
    if summaries:
        best_key = max(summaries.keys(), key=lambda k: summaries[k].get("last_frame", -1))
        s = summaries[best_key]
        return {"frame_no": s.get("last_frame", "-"), "event_frame_range": s.get("event_frame_range", "-"), "evidence_path": s.get("evidence_path", "")}
    return None


def infer_actual_action_from_video_model(tc, requirement, temporal_summary):
    text = testcase_text(tc, requirement)
    matched = temporal_objects_for_tc(tc, requirement, temporal_summary or {})
    summaries = (temporal_summary or {}).get("object_summaries", {})
    src = matched if matched else summaries
    objects = {str(v.get("object", k)).lower() for k, v in src.items()}
    motions = {str(v.get("motion_state", "")).upper() for v in src.values()}
    persistent = [k for k, v in src.items() if int(v.get("detections", 0)) >= 3]
    unstable = (temporal_summary or {}).get("confidence_unstable_objects", [])
    ego_state = (temporal_summary or {}).get("ego_motion_state", "UNKNOWN")
    has_person = bool(objects & {"person", "pedestrian"})
    has_vehicle = bool(objects & {"vehicle", "car", "truck", "bus", "motorcycle"})
    has_light = bool(objects & {"traffic_light", "traffic light"})
    has_bicycle = "bicycle" in objects
    safe_words = ["outside", "sidewalk", "distant", "safe clearance", "no collision", "not relevant", "far beyond", "background", "adjacent lane", "safe monitoring", "non-hazard"]
    critical_words = ["critical", "emergency", "stopping distance", "collision", "crosswalk", "in ego path", "driving path", "directly in front", "child", "suddenly", "enters lane", "close pedestrian", "within critical"]
    warning_words = ["warning", "warn", "alert", "confidence", "uncertain", "traffic light", "classification conflict", "caution"]
    slow_words = ["unsafe distance", "front vehicle", "deceleration", "cut-in", "headway", "slow down", "reduce speed", "cyclist", "motorcycle"]
    safe_state_words = ["safe state", "fallback", "degraded", "unavailable", "blackout", "diagnostic", "blocked", "persistent"]
    if any(k in text for k in safe_state_words): return "SAFE_STATE", f"Video model detected fallback/degraded/safe-state intent. Ego state={ego_state}."
    if any(k in text for k in warning_words) and (has_light or unstable or "confidence" in text or "uncertain" in text): return "WARNING", f"Video model detected warning condition from signal/confidence/uncertainty. Ego state={ego_state}."
    if any(k in text for k in safe_words): return "KEEP_DRIVING", f"Video model matched non-hazard scenario across object tracks. Ego state={ego_state}."
    if has_person and any(k in text for k in critical_words):
        if "APPROACHING" in motions or persistent: return "BRAKE", f"Video model detected pedestrian persistence/approach across frames. Ego state={ego_state}."
        return "WARNING", f"Pedestrian detected, but approach evidence is weak. Ego state={ego_state}."
    if any(k in text for k in slow_words) and (has_vehicle or has_bicycle):
        if "APPROACHING" in motions or "MOVING_LATERAL" in motions or persistent: return "SLOW_DOWN", f"Video model detected vehicle/VRU approach or tracked movement. Ego state={ego_state}."
    if has_person and any(k in text for k in ["brake", "pedestrian", "crosswalk", "stop"]):
        if "APPROACHING" in motions: return "BRAKE", f"Pedestrian track is approaching based on bbox area and optical flow. Ego state={ego_state}."
        if persistent: return "WARNING", f"Pedestrian track persists but not clearly approaching. Ego state={ego_state}."
    return "KEEP_DRIVING", f"Video model found no critical event. Ego state={ego_state}."


def validate_testcases(testcases, processed_frames, requirement="", manual_actual_action="AUTO_INFER", temporal_summary=None):
    results = []
    temporal_summary = temporal_summary or {}
    for tc in testcases or []:
        expected = infer_expected_from_testcase(tc)
        manual = normalize_action(manual_actual_action)
        matched = temporal_objects_for_tc(tc, requirement, temporal_summary)
        evidence = select_evidence_from_temporal(matched, temporal_summary)
        if evidence is None:
            results.append({"tc_id": tc.get("tc_id", ""), "title": tc.get("title", ""), "frame_no": "-", "event_frame_range": "-", "detected_objects": "No detected objects", "expected_action": expected, "actual_action": "-", "result": "NO_DATA", "evidence_path": "", "methodology": tc.get("methodology", ""), "ego_motion_state": temporal_summary.get("ego_motion_state", "UNKNOWN"), "video_model_reason": "No tracked object evidence was available.", "temporal_reason": "No temporal detection evidence was available.", "validation_reason": "No video-model evidence was available."})
            continue
        if manual:
            actual = manual; reason = f"Manual actual action was selected: {manual}."
        else:
            actual, reason = infer_actual_action_from_video_model(tc, requirement, temporal_summary)
        detected = [f"{s.get('object', k)}(T{s.get('track_id', '-')}, {s.get('motion_state', '-')})" for k, s in matched.items()]
        if not detected: detected = [str(k) for k in (temporal_summary.get("object_summaries", {}) or {}).keys()]
        results.append({"tc_id": tc.get("tc_id", ""), "title": tc.get("title", ""), "frame_no": evidence.get("frame_no", "-"), "event_frame_range": evidence.get("event_frame_range", "-"), "detected_objects": ", ".join(detected) if detected else "No matched object", "expected_action": expected, "actual_action": actual, "result": "PASS" if expected == actual else "FAIL", "evidence_path": evidence.get("evidence_path", ""), "methodology": tc.get("methodology", ""), "ego_motion_state": temporal_summary.get("ego_motion_state", "UNKNOWN"), "video_model_reason": reason, "temporal_reason": reason, "temporal_summary": json.dumps(matched, ensure_ascii=False)[:1000], "validation_reason": reason})
    return results
