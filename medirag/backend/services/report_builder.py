"""PDF report generator using ReportLab."""
import os
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.colors import HexColor, white, black
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT


DARK_BG = HexColor("#0d1117")
ACCENT = HexColor("#6ee7b7")
WARN = HexColor("#f87171")
MUTED = HexColor("#6b7280")
WHITE = white


def generate_pdf_report(patient: dict, diagnosis: dict, output_path: str):
    doc = SimpleDocTemplate(
        output_path, pagesize=A4,
        leftMargin=20*mm, rightMargin=20*mm,
        topMargin=20*mm, bottomMargin=20*mm
    )
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle("Title", fontSize=22, textColor=ACCENT,
                                 alignment=TA_CENTER, spaceAfter=4, fontName="Helvetica-Bold")
    sub_style = ParagraphStyle("Sub", fontSize=10, textColor=MUTED,
                               alignment=TA_CENTER, spaceAfter=12, fontName="Helvetica")
    warn_style = ParagraphStyle("Warn", fontSize=9, textColor=WARN,
                                alignment=TA_CENTER, spaceAfter=8, fontName="Helvetica-Oblique")
    section_style = ParagraphStyle("Section", fontSize=13, textColor=ACCENT,
                                   spaceAfter=6, fontName="Helvetica-Bold")
    body_style = ParagraphStyle("Body", fontSize=9, textColor=black,
                                spaceAfter=4, leading=14, fontName="Helvetica")

    story = []

    # Header
    story.append(Paragraph("MediRAG Clinical Intelligence Oracle", title_style))
    story.append(Paragraph("AI-Powered Diagnostic Intelligence Report", sub_style))
    story.append(Paragraph(
        "⚠ NOT A CLINICAL DIAGNOSIS — For review by a licensed medical professional only.",
        warn_style
    ))
    story.append(HRFlowable(width="100%", thickness=1, color=ACCENT))
    story.append(Spacer(1, 8))

    # Patient summary
    story.append(Paragraph("Patient Profile", section_style))
    patient_data = [
        ["Age", str(patient.get("age", "N/A")), "Sex", patient.get("sex", "N/A")],
        ["BMI", str(patient.get("bmi", "N/A")), "BP", patient.get("blood_pressure", "N/A")],
        ["Symptoms", ", ".join(patient.get("symptoms", [])) if isinstance(patient.get("symptoms"), list)
         else str(patient.get("symptoms", "N/A")), "Meds",
         ", ".join(patient.get("medications", [])) if isinstance(patient.get("medications"), list)
         else str(patient.get("medications", "None"))],
    ]
    pt = Table(patient_data, colWidths=[30*mm, 60*mm, 30*mm, 60*mm])
    pt.setStyle(TableStyle([
        ("FONTSIZE", (0,0), (-1,-1), 8),
        ("TEXTCOLOR", (0,0), (0,-1), MUTED),
        ("TEXTCOLOR", (2,0), (2,-1), MUTED),
        ("GRID", (0,0), (-1,-1), 0.5, HexColor("#e5e7eb")),
        ("ROWBACKGROUNDS", (0,0), (-1,-1), [HexColor("#f9fafb"), white]),
        ("PADDING", (0,0), (-1,-1), 4),
    ]))
    story.append(pt)
    story.append(Spacer(1, 10))

    # Executive summary
    if diagnosis.get("summary"):
        story.append(Paragraph("Executive Summary", section_style))
        story.append(Paragraph(diagnosis["summary"], body_style))
        story.append(Spacer(1, 8))

    # Differential Diagnosis table
    diff_diag = diagnosis.get("differential_diagnosis", [])
    if diff_diag:
        story.append(Paragraph("Differential Diagnosis", section_style))
        table_data = [["Rank", "Condition", "ICD-10", "Confidence", "Evidence"]]
        for d in diff_diag[:8]:
            conf = d.get("confidence", 0)
            conf_str = f"{int(conf*100)}%" if isinstance(conf, float) else str(conf)
            sources = ", ".join(d.get("evidence_sources", []))[:60]
            table_data.append([
                str(d.get("rank", "")),
                d.get("condition", "")[:35],
                d.get("icd10", "N/A"),
                conf_str,
                sources,
            ])
        dt = Table(table_data, colWidths=[12*mm, 55*mm, 22*mm, 22*mm, 59*mm])
        dt.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), ACCENT),
            ("TEXTCOLOR", (0,0), (-1,0), white),
            ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
            ("FONTSIZE", (0,0), (-1,-1), 8),
            ("GRID", (0,0), (-1,-1), 0.5, HexColor("#d1d5db")),
            ("ROWBACKGROUNDS", (0,1), (-1,-1), [white, HexColor("#f0fdf4")]),
            ("PADDING", (0,0), (-1,-1), 4),
        ]))
        story.append(dt)
        story.append(Spacer(1, 10))

    # Diagnostic Tests
    tests = diagnosis.get("diagnostic_tests", [])
    if tests:
        story.append(Paragraph("Recommended Diagnostic Tests", section_style))
        test_data = [["Test", "Priority", "Targets", "Source"]]
        for t in tests[:10]:
            test_data.append([
                t.get("test", "")[:40],
                t.get("priority", "").upper(),
                t.get("targets_condition", "")[:30],
                t.get("source", "")[:25],
            ])
        tt = Table(test_data, colWidths=[65*mm, 22*mm, 45*mm, 38*mm])
        tt.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), ACCENT),
            ("TEXTCOLOR", (0,0), (-1,0), white),
            ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
            ("FONTSIZE", (0,0), (-1,-1), 8),
            ("GRID", (0,0), (-1,-1), 0.5, HexColor("#d1d5db")),
            ("ROWBACKGROUNDS", (0,1), (-1,-1), [white, HexColor("#eff6ff")]),
            ("PADDING", (0,0), (-1,-1), 4),
        ]))
        story.append(tt)
        story.append(Spacer(1, 10))

    # Lifestyle Recommendations
    lifestyle = diagnosis.get("lifestyle_recommendations", [])
    if lifestyle:
        story.append(Paragraph("Lifestyle Recommendations", section_style))
        for item in lifestyle[:8]:
            cat = item.get("category", "").upper()
            rec = item.get("recommendation", "")
            ev = item.get("evidence", "")
            story.append(Paragraph(
                f"<b>[{cat}]</b> {rec} <i>({ev})</i>", body_style
            ))

    # Drug Review
    drug_review = diagnosis.get("drug_review", [])
    if drug_review:
        story.append(Spacer(1, 6))
        story.append(Paragraph("Medication Safety Review", section_style))
        for d in drug_review:
            risk = d.get("risk_level", "low").upper()
            color = "#dc2626" if risk == "HIGH" else "#d97706" if risk == "MODERATE" else "#16a34a"
            story.append(Paragraph(
                f"<b>{d.get('drug','')}</b> — Risk: <font color='{color}'><b>{risk}</b></font> | "
                f"Recommendation: {d.get('recommendation','')} | "
                f"Signals: {', '.join(d.get('adverse_signals', []))[:100]}",
                body_style
            ))

    # Disclaimer
    story.append(Spacer(1, 16))
    story.append(HRFlowable(width="100%", thickness=1, color=WARN))
    story.append(Spacer(1, 4))
    disclaimer = diagnosis.get("disclaimer", (
        "This report is NOT a clinical diagnosis. All findings are generated by AI "
        "and must be reviewed by a licensed medical professional before any clinical "
        "decision is made. MediRAG is intended for research and informational purposes only."
    ))
    story.append(Paragraph(disclaimer, ParagraphStyle(
        "Disclaimer", fontSize=8, textColor=WARN, alignment=TA_CENTER, fontName="Helvetica-Oblique"
    )))

    doc.build(story)
