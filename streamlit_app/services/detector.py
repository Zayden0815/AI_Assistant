import math
import cv2
import numpy as np
from ultralytics import YOLO

from config import TARGET_CLASSES, EVIDENCE_DIR


def _iou(a, b):
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    iw, ih = max(ix2 - ix1, 0), max(iy2 - iy1, 0)
    inter = iw * ih
    aa = max((ax2 - ax1) * (ay2 - ay1), 1)
    ba = max((bx2 - bx1) * (by2 - by1), 1)
    return inter / (aa + ba - inter + 1e-6)


class SimpleTracker:
    """Lightweight IoU tracker. Gives stable track_id without extra dependency."""
    def __init__(self, iou_threshold=0.25, max_missing=4):
        self.iou_threshold = iou_threshold
        self.max_missing = max_missing
        self.next_id = 1
        self.tracks = {}

    def update(self, detections):
        assigned = set()
        for det in detections:
            best_id = None
            best_score = 0.0
            for tid, tr in self.tracks.items():
                if tid in assigned:
                    continue
                if tr["mapped_object"] != det["mapped_object"]:
                    continue
                score = _iou(tr["bbox"], det["bbox"])
                if score > best_score:
                    best_score = score
                    best_id = tid
            if best_id is not None and best_score >= self.iou_threshold:
                det["track_id"] = best_id
                self.tracks[best_id] = {"bbox": det["bbox"], "mapped_object": det["mapped_object"], "missing": 0}
                assigned.add(best_id)
            else:
                tid = self.next_id
                self.next_id += 1
                det["track_id"] = tid
                self.tracks[tid] = {"bbox": det["bbox"], "mapped_object": det["mapped_object"], "missing": 0}
                assigned.add(tid)
        for tid in list(self.tracks.keys()):
            if tid not in assigned:
                self.tracks[tid]["missing"] += 1
                if self.tracks[tid]["missing"] > self.max_missing:
                    del self.tracks[tid]
        return detections


class YOLODetector:
    def __init__(self, model_path="yolov8n.pt", conf=0.35):
        self.model = YOLO(model_path)
        self.conf = conf

    def detect_frame(self, frame):
        results = self.model.predict(frame, conf=self.conf, verbose=False)
        detections = []
        if not results:
            return detections, frame.copy()
        result = results[0]
        names = result.names
        frame_h, frame_w = frame.shape[:2]
        frame_area = max(frame_w * frame_h, 1)
        for box in result.boxes:
            cls_id = int(box.cls[0])
            cls_name = names.get(cls_id, str(cls_id))
            score = float(box.conf[0])
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            mapped = TARGET_CLASSES.get(cls_name, cls_name)
            w = max(x2 - x1, 0)
            h = max(y2 - y1, 0)
            area = w * h
            detections.append({
                "class_name": cls_name,
                "mapped_object": mapped,
                "confidence": round(score, 3),
                "bbox": [x1, y1, x2, y2],
                "bbox_area": area,
                "bbox_area_ratio": round(area / frame_area, 6),
                "center_x": round((x1 + x2) / 2 / frame_w, 4) if frame_w else 0,
                "center_y": round((y1 + y2) / 2 / frame_h, 4) if frame_h else 0,
                "track_id": None,
                "flow_dx": 0.0,
                "flow_dy": 0.0,
                "flow_mag": 0.0,
            })
        return detections, frame.copy()


def compute_optical_flow(prev_gray, gray):
    if prev_gray is None or gray is None:
        return None
    return cv2.calcOpticalFlowFarneback(prev_gray, gray, None, 0.5, 3, 15, 3, 5, 1.2, 0)


def attach_flow_to_detections(detections, flow):
    if flow is None:
        return detections
    h, w = flow.shape[:2]
    for det in detections:
        x1, y1, x2, y2 = det["bbox"]
        x1, y1 = max(0, min(x1, w - 1)), max(0, min(y1, h - 1))
        x2, y2 = max(0, min(x2, w)), max(0, min(y2, h))
        if x2 <= x1 or y2 <= y1:
            continue
        region = flow[y1:y2, x1:x2]
        if region.size == 0:
            continue
        dx = float(np.median(region[..., 0]))
        dy = float(np.median(region[..., 1]))
        mag = math.sqrt(dx * dx + dy * dy)
        det["flow_dx"] = round(dx, 4)
        det["flow_dy"] = round(dy, 4)
        det["flow_mag"] = round(mag, 4)
    return detections


def draw_detections(frame, detections):
    annotated = frame.copy()
    for det in detections:
        x1, y1, x2, y2 = det["bbox"]
        label = f"ID:{det.get('track_id', '-')} {det.get('class_name', '-')} {det.get('confidence', 0):.2f} flow:{det.get('flow_mag', 0):.2f}"
        cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 255, 0), 2)
        cv2.putText(annotated, label, (x1, max(y1 - 8, 20)), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (0, 255, 0), 2)
    return annotated


def process_video(video_path, detector, frame_step=30, max_frames=80):
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video: {video_path}")
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    tracker = SimpleTracker()
    processed = []
    frame_no = 0
    used = 0
    prev_gray = None
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        if frame_no % int(frame_step) == 0:
            flow = compute_optical_flow(prev_gray, gray)
            detections, _ = detector.detect_frame(frame)
            detections = tracker.update(detections)
            detections = attach_flow_to_detections(detections, flow)
            annotated = draw_detections(frame, detections)
            evidence_path = EVIDENCE_DIR / f"frame_{frame_no}.jpg"
            cv2.imwrite(str(evidence_path), annotated)
            processed.append({"frame_no": frame_no, "timestamp_sec": round(frame_no / fps, 2), "detections": detections, "evidence_path": str(evidence_path)})
            used += 1
            if used >= int(max_frames):
                break
        prev_gray = gray
        frame_no += 1
    cap.release()
    return {"fps": fps, "total_frames": total_frames, "processed_frames": processed, "temporal_summary": build_temporal_summary(processed)}


def build_temporal_summary(processed_frames):
    tracks = {}
    for frame in processed_frames:
        for det in frame.get("detections", []):
            tid = det.get("track_id")
            key = f"{det.get('mapped_object')}_T{tid}" if tid is not None else f"{det.get('mapped_object')}_{det.get('class_name')}"
            tracks.setdefault(key, {"object": det.get("mapped_object") or det.get("class_name"), "track_id": tid, "points": []})
            tracks[key]["points"].append({
                "frame_no": frame.get("frame_no"),
                "timestamp_sec": frame.get("timestamp_sec"),
                "area_ratio": float(det.get("bbox_area_ratio", 0)),
                "center_x": float(det.get("center_x", 0)),
                "center_y": float(det.get("center_y", 0)),
                "confidence": float(det.get("confidence", 0)),
                "flow_mag": float(det.get("flow_mag", 0)),
                "evidence_path": frame.get("evidence_path", ""),
            })
    object_summaries = {}
    approaching_objects, stable_objects, receding_objects, moving_objects = [], [], [], []
    persistent_objects, confidence_unstable_objects = [], []
    for key, bundle in tracks.items():
        pts = sorted(bundle["points"], key=lambda x: x["frame_no"])
        if not pts:
            continue
        first, last = pts[0], pts[-1]
        areas = [p["area_ratio"] for p in pts]
        confs = [p["confidence"] for p in pts]
        flows = [p["flow_mag"] for p in pts]
        delta_ratio = (areas[-1] - areas[0]) / max(areas[0], 0.000001)
        avg_conf = sum(confs) / len(confs)
        conf_range = max(confs) - min(confs) if confs else 0
        avg_flow = sum(flows) / len(flows) if flows else 0
        center_dx = last["center_x"] - first["center_x"]
        center_dy = last["center_y"] - first["center_y"]
        center_move = math.sqrt(center_dx * center_dx + center_dy * center_dy)
        if delta_ratio > 0.20:
            motion = "APPROACHING"; approaching_objects.append(key)
        elif delta_ratio < -0.20:
            motion = "RECEDING"; receding_objects.append(key)
        elif avg_flow > 1.5 or center_move > 0.06:
            motion = "MOVING_LATERAL"; moving_objects.append(key)
        else:
            motion = "STABLE"; stable_objects.append(key)
        if len(pts) >= 3:
            persistent_objects.append(key)
        if conf_range > 0.35:
            confidence_unstable_objects.append(key)
        object_summaries[key] = {
            "object": bundle["object"], "track_id": bundle["track_id"], "detections": len(pts),
            "first_frame": first["frame_no"], "last_frame": last["frame_no"],
            "event_frame_range": f"{first['frame_no']} → {last['frame_no']}",
            "first_area_ratio": round(areas[0], 6), "last_area_ratio": round(areas[-1], 6),
            "area_delta_ratio": round(delta_ratio, 4), "avg_confidence": round(avg_conf, 3),
            "confidence_range": round(conf_range, 3), "avg_flow_magnitude": round(avg_flow, 4),
            "center_move": round(center_move, 4), "motion_state": motion,
            "evidence_path": last.get("evidence_path", ""),
        }
    if approaching_objects:
        ego = "APPROACHING_OBJECT"
    elif moving_objects:
        ego = "OBJECT_MOTION_DETECTED"
    elif stable_objects and not approaching_objects and not receding_objects:
        ego = "STABLE_OR_STOPPED"
    elif receding_objects and not approaching_objects:
        ego = "MOVING_AWAY_OR_OBJECT_RECEDING"
    else:
        ego = "UNKNOWN"
    return {"object_summaries": object_summaries, "approaching_objects": approaching_objects, "stable_objects": stable_objects, "receding_objects": receding_objects, "moving_objects": moving_objects, "persistent_objects": persistent_objects, "confidence_unstable_objects": confidence_unstable_objects, "ego_motion_state": ego, "processed_frame_count": len(processed_frames)}
