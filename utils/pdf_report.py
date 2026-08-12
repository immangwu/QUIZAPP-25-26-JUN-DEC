import io
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak,
)

styles = getSampleStyleSheet()
TITLE_STYLE = ParagraphStyle("TitleStyle", parent=styles["Title"], fontSize=16, spaceAfter=4)
SUB_STYLE = ParagraphStyle("SubStyle", parent=styles["Normal"], fontSize=10, textColor=colors.HexColor("#374151"))
BODY_STYLE = ParagraphStyle("BodyStyle", parent=styles["Normal"], fontSize=10, leading=14)
QUESTION_STYLE = ParagraphStyle("QuestionStyle", parent=styles["Normal"], fontSize=10, leading=13, spaceAfter=2)


def generate_student_answer_script(result, name, reg_no, department):
    """Builds a single student's answer script (marks + right/wrong, no correct-answer text)."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=18 * mm, bottomMargin=18 * mm,
                             leftMargin=16 * mm, rightMargin=16 * mm)
    elements = []

    elements.append(Paragraph("Quiz Answer Script", TITLE_STYLE))
    elements.append(Paragraph(f"{result['subject_code']} — {result['subject_title']} · {result['quiz_title']}", SUB_STYLE))
    elements.append(Spacer(1, 6))

    info_data = [
        ["Name", name, "Register No", reg_no],
        ["Department", department.title(), "Attempt", str(result["attempt_no"])],
        ["Score", f"{result['score']} / {result['total']}", "Percentage", f"{result['percentage']}%"],
    ]
    info_table = Table(info_data, colWidths=[28 * mm, 55 * mm, 28 * mm, 55 * mm])
    info_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cbd5e1")),
    ]))
    elements.append(info_table)

    if result.get("flagged"):
        elements.append(Spacer(1, 6))
        elements.append(Paragraph(
            f"<font color='#92400e'><b>⚠ Flagged:</b> auto-stopped after "
            f"{result['tab_switch_count']} tab switches.</font>", SUB_STYLE))

    elements.append(Spacer(1, 10))
    elements.append(Paragraph("Question-wise Result (correct answers are not shown)", styles["Heading3"]))
    elements.append(Spacer(1, 4))

    for pq in result["per_question"]:
        verdict = "<font color='#166534'><b>Correct</b></font>" if pq["correct"] else "<font color='#991b1b'><b>Incorrect</b></font>"
        q_text = f"<b>Q{pq['id']}.</b> ({pq['marks']} mark) {pq['question']} — {verdict}"
        elements.append(Paragraph(q_text, QUESTION_STYLE))
        selected = pq["selected"]
        ans_text = f"Your answer: {selected}) {pq['options'].get(selected, '')}" if selected else "Your answer: Not answered"
        elements.append(Paragraph(f"{ans_text} &nbsp;&nbsp; Marks awarded: {pq['awarded']} / {pq['marks']}", SUB_STYLE))
        elements.append(Spacer(1, 4))

    doc.build(elements)
    buf.seek(0)
    return buf.getvalue()


def generate_faculty_report(records, title="Quiz Results Report"):
    """records: list of dicts with keys name, reg_no, department, subject_code, attempt_no,
    score, total, percentage, flagged, tab_switch_count, timestamp."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=14 * mm, bottomMargin=14 * mm,
                             leftMargin=12 * mm, rightMargin=12 * mm)
    elements = [Paragraph(title, TITLE_STYLE), Spacer(1, 8)]

    header = ["Name", "Reg No", "Dept", "Subject", "Quiz", "Attempt", "Score", "%", "Flagged", "Timestamp"]
    data = [header]
    for r in records:
        data.append([
            r.get("name", ""),
            r.get("reg_no", ""),
            r.get("department", ""),
            r.get("subject_code", ""),
            f"Q{r.get('quiz_no') or 1}",
            str(r.get("attempt_no", "")),
            f"{r.get('score','')}/{r.get('total','')}",
            str(r.get("percentage", "")),
            "Yes" if str(r.get("flagged")).lower() == "true" else "No",
            r.get("timestamp", ""),
        ])

    table = Table(data, repeatRows=1, colWidths=[24 * mm, 22 * mm, 13 * mm, 17 * mm, 11 * mm, 13 * mm, 15 * mm, 11 * mm, 13 * mm, 26 * mm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f2937")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 7.5),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#cbd5e1")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    elements.append(table)

    doc.build(elements)
    buf.seek(0)
    return buf.getvalue()
