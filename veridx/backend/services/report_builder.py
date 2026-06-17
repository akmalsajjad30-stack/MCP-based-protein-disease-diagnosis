"""PDF report generator using ReportLab."""
import os
import html
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.colors import HexColor, white, black
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT

DARK_BG = HexColor("#0d1117")
ACCENT = HexColor("#0f766e")  # Professional dark teal
WARN = HexColor("#b91c1c")    # Dark red warning color
MUTED = HexColor("#4b5563")   # Professional muted dark gray
WHITE = white

def escape_html(text):
    return html.escape(str(text)) if text else ""

def generate_pdf_report(patient: dict, diagnosis: dict, output_path: str):
    doc = SimpleDocTemplate(
        output_path, pagesize=A4,
        leftMargin=15*mm, rightMargin=15*mm,
        topMargin=15*mm, bottomMargin=15*mm
    )
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle("Title", fontSize=20, textColor=ACCENT,
                                 alignment=TA_CENTER, spaceAfter=4, leading=24, fontName="Helvetica-Bold")
    sub_style = ParagraphStyle("Sub", fontSize=10, textColor=MUTED,
                               alignment=TA_CENTER, spaceAfter=8, leading=12, fontName="Helvetica")
    warn_style = ParagraphStyle("Warn", fontSize=9, textColor=WARN,
                                alignment=TA_CENTER, spaceAfter=8, leading=11, fontName="Helvetica-Oblique")
    section_style = ParagraphStyle("Section", fontSize=12, textColor=ACCENT,
                                   spaceBefore=8, spaceAfter=6, leading=15, fontName="Helvetica-Bold")
    body_style = ParagraphStyle("Body", fontSize=9, textColor=black,
                                spaceAfter=4, leading=13, fontName="Helvetica")
    
    cell_style = ParagraphStyle("CellBody", fontSize=8, textColor=black,
                                leading=10, fontName="Helvetica")
    cell_header_style = ParagraphStyle("CellHeader", fontSize=8, textColor=white,
                                       leading=10, fontName="Helvetica-Bold")
    
    patient_cell_style = ParagraphStyle("PatientCell", fontSize=8, textColor=black, leading=10, fontName="Helvetica")
    patient_label_style = ParagraphStyle("PatientLabel", fontSize=8, textColor=MUTED, leading=10, fontName="Helvetica-Bold")

    def cell_p(text, style=cell_style):
        return Paragraph(escape_html(text), style)

    story = []

    # Header
    story.append(Paragraph("VeriDX Clinical Intelligence Oracle", title_style))
    story.append(Paragraph("AI-Powered Diagnostic Intelligence Report", sub_style))
    story.append(Paragraph(
        "⚠ NOT A CLINICAL DIAGNOSIS — For review by a licensed medical professional only.",
        warn_style
    ))
    story.append(HRFlowable(width="100%", thickness=1.5, color=ACCENT, spaceBefore=4, spaceAfter=8))

    # Patient summary
    story.append(Paragraph("Patient Profile", section_style))
    patient_data = [
        [cell_p("Age", patient_label_style), cell_p(patient.get("age", "N/A"), patient_cell_style), 
         cell_p("Sex", patient_label_style), cell_p(patient.get("sex", "N/A"), patient_cell_style)],
        [cell_p("BMI", patient_label_style), cell_p(patient.get("bmi", "N/A"), patient_cell_style), 
         cell_p("BP", patient_label_style), cell_p(patient.get("blood_pressure", "N/A"), patient_cell_style)],
        [cell_p("Symptoms", patient_label_style), cell_p(", ".join(patient.get("symptoms", [])) if isinstance(patient.get("symptoms"), list) else str(patient.get("symptoms", "N/A")), patient_cell_style), 
         cell_p("Meds", patient_label_style), cell_p(", ".join(patient.get("medications", [])) if isinstance(patient.get("medications"), list) else str(patient.get("medications", "None")), patient_cell_style)],
    ]
    pt = Table(patient_data, colWidths=[25*mm, 65*mm, 25*mm, 65*mm])
    pt.setStyle(TableStyle([
        ("GRID", (0,0), (-1,-1), 0.5, HexColor("#e5e7eb")),
        ("ROWBACKGROUNDS", (0,0), (-1,-1), [HexColor("#f9fafb"), white]),
        ("PADDING", (0,0), (-1,-1), 5),
        ("VALIGN", (0,0), (-1,-1), "TOP"),
    ]))
    story.append(pt)
    story.append(Spacer(1, 4))

    # Executive summary
    if diagnosis.get("summary"):
        story.append(Paragraph("Executive Summary", section_style))
        story.append(Paragraph(escape_html(diagnosis["summary"]), body_style))
        story.append(Spacer(1, 4))

    # Differential Diagnosis table
    diff_diag = diagnosis.get("differential_diagnosis", [])
    if diff_diag:
        story.append(Paragraph("Differential Diagnosis", section_style))
        table_data = [[
            cell_p("Rank", cell_header_style),
            cell_p("Condition", cell_header_style),
            cell_p("ICD-10", cell_header_style),
            cell_p("Confidence", cell_header_style),
            cell_p("Evidence", cell_header_style)
        ]]
        for d in diff_diag[:8]:
            conf = d.get("confidence", 0)
            conf_str = f"{int(conf*100)}%" if isinstance(conf, float) else str(conf)
            sources = ", ".join(d.get("evidence_sources", []))
            table_data.append([
                cell_p(d.get("rank", ""), cell_style),
                cell_p(d.get("condition", ""), cell_style),
                cell_p(d.get("icd10", "N/A"), cell_style),
                cell_p(conf_str, cell_style),
                cell_p(sources, cell_style),
            ])
        dt = Table(table_data, colWidths=[12*mm, 55*mm, 22*mm, 22*mm, 69*mm])
        dt.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), ACCENT),
            ("GRID", (0,0), (-1,-1), 0.5, HexColor("#d1d5db")),
            ("ROWBACKGROUNDS", (0,1), (-1,-1), [white, HexColor("#f0fdf4")]),
            ("PADDING", (0,0), (-1,-1), 5),
            ("VALIGN", (0,0), (-1,-1), "TOP"),
        ]))
        story.append(dt)
        story.append(Spacer(1, 4))

    # Diagnostic Tests
    tests = diagnosis.get("diagnostic_tests", [])
    if tests:
        story.append(Paragraph("Recommended Diagnostic Tests", section_style))
        test_data = [[
            cell_p("Test", cell_header_style),
            cell_p("Priority", cell_header_style),
            cell_p("Targets", cell_header_style),
            cell_p("Source", cell_header_style)
        ]]
        for t in tests[:10]:
            test_data.append([
                cell_p(t.get("test", ""), cell_style),
                cell_p(t.get("priority", "").upper(), cell_style),
                cell_p(t.get("targets_condition", ""), cell_style),
                cell_p(t.get("source", ""), cell_style),
            ])
        tt = Table(test_data, colWidths=[65*mm, 25*mm, 45*mm, 45*mm])
        tt.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), ACCENT),
            ("GRID", (0,0), (-1,-1), 0.5, HexColor("#d1d5db")),
            ("ROWBACKGROUNDS", (0,1), (-1,-1), [white, HexColor("#eff6ff")]),
            ("PADDING", (0,0), (-1,-1), 5),
            ("VALIGN", (0,0), (-1,-1), "TOP"),
        ]))
        story.append(tt)
        story.append(Spacer(1, 4))

    # Lifestyle Recommendations
    lifestyle = diagnosis.get("lifestyle_recommendations", [])
    if lifestyle:
        story.append(Paragraph("Lifestyle Recommendations", section_style))
        for item in lifestyle[:8]:
            cat = item.get("category", "").upper()
            rec = item.get("recommendation", "")
            ev = item.get("evidence", "")
            story.append(Paragraph(
                f"<b>[{escape_html(cat)}]</b> {escape_html(rec)} <i>({escape_html(ev)})</i>", body_style
            ))

    # Drug Review
    drug_review = diagnosis.get("drug_review", [])
    if drug_review:
        story.append(Spacer(1, 4))
        story.append(Paragraph("Medication Safety Review", section_style))
        for d in drug_review:
            risk = d.get("risk_level", "low").upper()
            color = "#dc2626" if risk == "HIGH" else "#d97706" if risk == "MODERATE" else "#16a34a"
            signals = ", ".join(d.get("adverse_signals", []))
            story.append(Paragraph(
                f"<b>{escape_html(d.get('drug',''))}</b> — Risk: <font color='{color}'><b>{escape_html(risk)}</b></font> | "
                f"Recommendation: {escape_html(d.get('recommendation',''))} | "
                f"Signals: {escape_html(signals)}",
                body_style
            ))

    # Disclaimer
    story.append(Spacer(1, 12))
    story.append(HRFlowable(width="100%", thickness=1, color=WARN, spaceBefore=4, spaceAfter=4))
    disclaimer = diagnosis.get("disclaimer", (
        "This report is NOT a clinical diagnosis. All findings are generated by AI "
        "and must be reviewed by a licensed medical professional before any clinical "
        "decision is made. VeriDX is intended for research and informational purposes only."
    ))
    story.append(Paragraph(escape_html(disclaimer), ParagraphStyle(
        "Disclaimer", fontSize=8, textColor=WARN, alignment=TA_CENTER, leading=10, fontName="Helvetica-Oblique"
    )))

    doc.build(story)
