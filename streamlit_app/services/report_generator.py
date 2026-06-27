from pathlib import Path
from datetime import datetime
import pandas as pd

from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4

from config import REPORT_DIR

def generate_pdf_report(requirement, results, development_method="BDD"):
    filename = f"VideoValidationReport_{development_method}_{datetime.now():%Y%m%d_%H%M%S}.pdf"
    path = REPORT_DIR / filename

    doc = SimpleDocTemplate(str(path), pagesize=A4)
    styles = getSampleStyleSheet()

    story = [
        Paragraph("AI Functional Safety Video Validation Report", styles["Title"]),
        Spacer(1, 12),
        Paragraph(f"<b>Development Method</b><br/>{development_method}", styles["BodyText"]),
        Spacer(1, 8),
        Paragraph(f"<b>Requirement</b><br/>{requirement}", styles["BodyText"]),
        Spacer(1, 12),
    ]

    rows = [["TC ID", "Frame", "Expected", "Actual", "Result"]]
    for r in results:
        rows.append([
            r.get("tc_id", ""),
            str(r.get("frame_no", "")),
            r.get("expected_action", ""),
            r.get("actual_action", ""),
            r.get("result", ""),
        ])

    table = Table(rows, colWidths=[70, 60, 90, 90, 70])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f2937")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
    ]))
    story.append(table)
    story.append(Spacer(1, 16))

    for r in results:
        story.append(Paragraph(f"<b>{r.get('tc_id')} - {r.get('result')}</b>", styles["Heading2"]))
        story.append(Paragraph(
            f"Detected: {r.get('detected_objects')}<br/>"
            f"Expected: {r.get('expected_action')}<br/>"
            f"Actual: {r.get('actual_action')}<br/>"
            f"Evidence: {r.get('evidence_path')}",
            styles["BodyText"],
        ))

        evidence = r.get("evidence_path")
        if evidence and Path(evidence).exists():
            try:
                story.append(Spacer(1, 8))
                story.append(Image(evidence, width=360, height=220))
            except Exception:
                pass

        story.append(Spacer(1, 12))

    doc.build(story)
    return path

def generate_excel_report(results, development_method="BDD"):
    filename = f"VideoValidationReport_{development_method}_{datetime.now():%Y%m%d_%H%M%S}.xlsx"
    path = REPORT_DIR / filename

    df = pd.DataFrame(results)
    df.insert(0, "development_method", development_method)
    df.to_excel(path, index=False)

    return path