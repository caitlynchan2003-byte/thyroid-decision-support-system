"""report.py - generate a printable PDF medical report for a diagnosis."""

import io
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table,
                                TableStyle, HRFlowable)

TEAL = colors.HexColor("#0E7C7B")
BLUE = colors.HexColor("#1565C0")
LIGHT = colors.HexColor("#F0F7F7")


def _styles():
    s = getSampleStyleSheet()
    s.add(ParagraphStyle("Hosp", parent=s["Title"], textColor=TEAL,
                         fontSize=20, spaceAfter=2))
    s.add(ParagraphStyle("Sub", parent=s["Normal"], textColor=colors.grey,
                         fontSize=9, spaceAfter=10))
    s.add(ParagraphStyle("Sec", parent=s["Heading2"], textColor=BLUE,
                         fontSize=12, spaceBefore=12, spaceAfter=6))
    s.add(ParagraphStyle("Body", parent=s["Normal"], fontSize=10, leading=15))
    return s


def build_report(patient: dict, diagnosis: dict, treatment: dict,
                 hormones: dict, history: str, diagnosed_by: str) -> bytes:
    """Return PDF bytes for one diagnosis report.

    patient   : {name, ic_number, age, sex}
    diagnosis : {result, confidence, risk}
    treatment : {medication, dosage, lifestyle_advice, followup_weeks} or None
    hormones  : {TSH, T3, TT4, T4U, FTI}
    """
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                            topMargin=18 * mm, bottomMargin=18 * mm,
                            leftMargin=18 * mm, rightMargin=18 * mm)
    st = _styles()
    flow = []

    # header
    flow.append(Paragraph("Thyroid Clinical Decision Support Module", st["Hosp"]))
    flow.append(Paragraph("Patient Medical Report", st["Sub"]))
    flow.append(HRFlowable(width="100%", thickness=2, color=TEAL, spaceAfter=8))

    # patient details
    flow.append(Paragraph("Patient Details", st["Sec"]))
    pdata = [
        ["Name", patient.get("name", "-"), "IC Number", patient.get("ic_number", "-")],
        ["Age", str(patient.get("age", "-")), "Sex", patient.get("sex", "-")],
        ["Report date", datetime.now().strftime("%d %b %Y, %H:%M"),
         "Diagnosed by", diagnosed_by],
    ]
    t = Table(pdata, colWidths=[28 * mm, 56 * mm, 28 * mm, 56 * mm])
    t.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("TEXTCOLOR", (0, 0), (0, -1), colors.grey),
        ("TEXTCOLOR", (2, 0), (2, -1), colors.grey),
        ("FONTNAME", (1, 0), (1, -1), "Helvetica-Bold"),
        ("FONTNAME", (3, 0), (3, -1), "Helvetica-Bold"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LINEBELOW", (0, 0), (-1, -1), 0.4, colors.HexColor("#dddddd")),
    ]))
    flow.append(t)

    # diagnosis
    flow.append(Paragraph("Diagnosis", st["Sec"]))
    ddata = [["Result", diagnosis["result"]],
             ["Confidence", f"{diagnosis['confidence']}%"],
             ["Risk level", diagnosis["risk"]]]
    t = Table(ddata, colWidths=[40 * mm, 128 * mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), LIGHT),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    flow.append(t)

    # hormone results
    flow.append(Paragraph("Hormone Test Results", st["Sec"]))
    hrows = [["TSH", "T3", "TT4", "T4U", "FTI"],
             [str(hormones["TSH"]), str(hormones["T3"]), str(hormones["TT4"]),
              str(hormones["T4U"]), str(hormones["FTI"])]]
    t = Table(hrows, colWidths=[33.6 * mm] * 5)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), TEAL),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    flow.append(t)

    # medical history
    flow.append(Paragraph("Medical History", st["Sec"]))
    flow.append(Paragraph(history or "None recorded", st["Body"]))

    # treatment
    flow.append(Paragraph("Treatment Recommendation", st["Sec"]))
    if treatment:
        trows = [["Medication", treatment["medication"]],
                 ["Dosage", treatment["dosage"]],
                 ["Lifestyle advice", treatment["lifestyle_advice"]],
                 ["Follow-up", f"In {treatment['followup_weeks']} weeks"]]
        t = Table(trows, colWidths=[40 * mm, 128 * mm])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (0, -1), LIGHT),
            ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
        flow.append(t)
    else:
        flow.append(Paragraph("No treatment record found.", st["Body"]))

    # footer disclaimer
    flow.append(Spacer(1, 16))
    flow.append(HRFlowable(width="100%", thickness=0.5, color=colors.grey))
    flow.append(Paragraph(
        "This report is generated by a machine-learning decision-support tool and is "
        "intended to assist, not replace, clinical judgement.",
        ParagraphStyle("disc", fontSize=8, textColor=colors.grey, spaceBefore=6)))

    doc.build(flow)
    return buf.getvalue()