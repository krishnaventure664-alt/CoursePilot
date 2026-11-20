# backend/services/pdf_export_service.py

import io
import os
import re
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    HRFlowable,
    Table,
    TableStyle,
    PageBreak,
)
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# ----------------------------------------------------------------------
# Typography & Font Registration
# ----------------------------------------------------------------------
FONT_NORMAL = "Helvetica"
FONT_BOLD = "Helvetica-Bold"
FONT_ITALIC = "Helvetica-Oblique"

# Register TrueType Arial on Windows for crisp typography & extended Unicode
if os.path.exists("C:/Windows/Fonts/arial.ttf") and os.path.exists("C:/Windows/Fonts/arialbd.ttf"):
    try:
        pdfmetrics.registerFont(TTFont("Arial-Custom", "C:/Windows/Fonts/arial.ttf"))
        pdfmetrics.registerFont(TTFont("Arial-Bold-Custom", "C:/Windows/Fonts/arialbd.ttf"))
        if os.path.exists("C:/Windows/Fonts/ariali.ttf"):
            pdfmetrics.registerFont(TTFont("Arial-Italic-Custom", "C:/Windows/Fonts/ariali.ttf"))
            FONT_ITALIC = "Arial-Italic-Custom"
        FONT_NORMAL = "Arial-Custom"
        FONT_BOLD = "Arial-Bold-Custom"
    except Exception:
        pass


# ----------------------------------------------------------------------
# Dynamic Numbered Canvas with Header & Footer
# ----------------------------------------------------------------------
class CoursePilotNumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_decorations(self, page_count):
        self.saveState()
        page_num = self._pageNumber
        width = 612
        margin = 42

        # 1. Top Header: Only on page 2 and later (keeps cover page clean)
        if page_num > 1:
            self.setFont(FONT_BOLD, 7.5)
            self.setFillColor(colors.HexColor("#2563eb"))
            self.drawString(margin, 755, "COURSEPILOT")
            self.setFont(FONT_NORMAL, 7.5)
            self.setFillColor(colors.HexColor("#64748b"))
            self.drawString(margin + 58, 755, "•  Master Study Guide & Syllabus Notes")

            self.setStrokeColor(colors.HexColor("#e2e8f0"))
            self.setLineWidth(0.6)
            self.line(margin, 747, width - margin, 747)

        # 2. Bottom Footer: On all pages
        self.setStrokeColor(colors.HexColor("#e2e8f0"))
        self.setLineWidth(0.6)
        self.line(margin, 46, width - margin, 46)

        self.setFont(FONT_NORMAL, 7.5)
        self.setFillColor(colors.HexColor("#94a3b8"))
        self.drawString(margin, 34, "Strictly Grounded in Lecture Transcript • Zero AI Additions • CoursePilot Academic Engine")

        self.setFont(FONT_BOLD, 7.5)
        self.setFillColor(colors.HexColor("#334155"))
        self.drawRightString(width - margin, 34, f"Page {page_num} of {page_count}")
        self.restoreState()


# ----------------------------------------------------------------------
# Safe Markdown Formatting & XML Parser Recovery
# ----------------------------------------------------------------------
def inline_md(text: str) -> str:
    """Escapes XML entities and converts markdown bold, italic, and code to ReportLab tags."""
    if not text:
        return ""
    text = text.replace(r"\longrightarrow", " → ").replace(r"\rightarrow", " → ")
    text = text.replace(r"\uparrow", " ↑ ").replace(r"\downarrow", " ↓ ")
    text = re.sub(r"\\text\{([^}]+)\}", r"\1", text)
    text = re.sub(r"\$\$([^\$]+)\$\$", r"\1", text)
    text = re.sub(r"\$([^\$]+)\$", r"\1", text)
    text = re.sub(r"\\[a-zA-Z]+", "", text)

    # 1. Escape XML characters first
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    # 2. Bold + Italic: ***text*** or ___text___
    text = re.sub(r"\*\*\*(.*?)\*\*\*", r"<b><i>\1</i></b>", text)
    text = re.sub(r"___(.*?)___", r"<b><i>\1</i></b>", text)

    # 3. Bold: **text** or __text__
    text = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"__(.*?)__", r"<b>\1</b>", text)

    # 4. Italic: *text* (when not preceded or followed by another asterisk)
    text = re.sub(r"(?<!\*)\*([^\*\n]+?)\*(?!\*)", r"<i>\1</i>", text)
    text = re.sub(r"(?<!_)_([^_\n]+?)_(?!_)", r"<i>\1</i>", text)

    # 5. Inline code: `code`
    text = re.sub(
        r"`([^`]+)`",
        r'<font name="Courier" color="#0f172a" size="8"><b>\1</b></font>',
        text,
    )
    return text.strip()


def safe_paragraph(formatted_xml: str, style: ParagraphStyle) -> Paragraph:
    """Creates a Paragraph, safely recovering if ReportLab's XML parser sees malformed tags."""
    try:
        return Paragraph(formatted_xml, style)
    except Exception:
        plain = re.sub(r"<[^>]+>", "", formatted_xml)
        plain = plain.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
        return Paragraph(plain, style)


# ----------------------------------------------------------------------
# Main Markdown to PDF Compiler
# ----------------------------------------------------------------------
def markdown_to_pdf_bytes(title: str, markdown_text: str, subtitle: str = "") -> bytes:
    """Compiles markdown notes into a modern, publication-grade study guide PDF."""
    buffer = io.BytesIO()
    printable_width = 528.0

    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=42,
        rightMargin=42,
        topMargin=54,
        bottomMargin=54,
    )

    # Styles - Clean CoursePilot Light Aesthetic matching on-screen NotionDocumentViewer
    cover_eyebrow_style = ParagraphStyle("CovEye", fontName=FONT_BOLD, fontSize=8.5, leading=11, textColor=colors.HexColor("#2563eb"), spaceAfter=4)
    cover_title_style = ParagraphStyle("CovTitle", fontName=FONT_BOLD, fontSize=17, leading=22, textColor=colors.HexColor("#09090b"), spaceAfter=5)
    cover_sub_style = ParagraphStyle("CovSub", fontName=FONT_NORMAL, fontSize=9.5, leading=14, textColor=colors.HexColor("#71717a"), spaceAfter=6)
    cover_meta_style = ParagraphStyle("CovMeta", fontName=FONT_NORMAL, fontSize=8, leading=11, textColor=colors.HexColor("#059669"))

    lec_title_style = ParagraphStyle("LecTitle", fontName=FONT_BOLD, fontSize=14, leading=19, textColor=colors.HexColor("#09090b"))
    lec_sub_style = ParagraphStyle("LecSub", fontName=FONT_NORMAL, fontSize=8.5, leading=12, textColor=colors.HexColor("#71717a"), spaceBefore=3)

    sec_title_style = ParagraphStyle("SecTitle", fontName=FONT_BOLD, fontSize=11, leading=15, textColor=colors.HexColor("#1d4ed8"))
    q_title_style = ParagraphStyle("QTitle", fontName=FONT_BOLD, fontSize=11, leading=15, textColor=colors.HexColor("#09090b"))

    ans_style = ParagraphStyle("Ans", fontName=FONT_NORMAL, fontSize=10, leading=14.5, textColor=colors.HexColor("#14532d"))
    tip_style = ParagraphStyle("Tip", fontName=FONT_NORMAL, fontSize=10, leading=14.5, textColor=colors.HexColor("#78350f"))
    flow_callout_style = ParagraphStyle("FlowCallout", fontName=FONT_NORMAL, fontSize=10, leading=14.5, textColor=colors.HexColor("#172554"))
    quote_style = ParagraphStyle("Quote", fontName=FONT_ITALIC, fontSize=9.5, leading=14, textColor=colors.HexColor("#3f3f46"))

    h2_style = ParagraphStyle("H2_Custom", fontName=FONT_BOLD, fontSize=13, leading=17, textColor=colors.HexColor("#09090b"), spaceBefore=14, spaceAfter=5, keepWithNext=True)
    h3_style = ParagraphStyle("H3_Custom", fontName=FONT_BOLD, fontSize=10.5, leading=14.5, textColor=colors.HexColor("#2563eb"), spaceBefore=10, spaceAfter=4, keepWithNext=True)
    h4_style = ParagraphStyle("H4_Custom", fontName=FONT_BOLD, fontSize=10, leading=14, textColor=colors.HexColor("#3f3f46"), spaceBefore=7, spaceAfter=3, keepWithNext=True)

    # Standard body: 10.5pt with 15.5pt line-height gives optimal optical reading rhythm
    body_style = ParagraphStyle("Body_Custom", fontName=FONT_NORMAL, fontSize=10.5, leading=15.5, textColor=colors.HexColor("#27272a"), spaceAfter=5)
    bullet_style = ParagraphStyle("Bullet_Custom", parent=body_style, fontSize=10, leading=15, leftIndent=16, firstLineIndent=-10, spaceAfter=4)
    sub_bullet_style = ParagraphStyle("SubBullet_Custom", parent=body_style, fontSize=9.5, leading=14, leftIndent=26, firstLineIndent=-10, spaceAfter=3)
    toc_style = ParagraphStyle("TOC_Custom", fontName=FONT_NORMAL, fontSize=9.5, leading=13.5, textColor=colors.HexColor("#09090b"), spaceAfter=3)

    story = []

    # 1. Page 1 Header Cover Card (Notion Clean Card with Blue Accent)
    clean_title = inline_md(title)
    cov_content = [
        safe_paragraph("⚡ COURSEPILOT • STUDY NOTES", cover_eyebrow_style),
        safe_paragraph(clean_title, cover_title_style),
    ]
    if subtitle:
        cov_content.append(safe_paragraph(inline_md(subtitle), cover_sub_style))
    cov_content.append(safe_paragraph("✓ Grounded in Transcript • Verified Key Concepts • Complete Syllabus Notes", cover_meta_style))

    cov_table = Table([[cov_content]], colWidths=[printable_width])
    cov_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
        ('TOPPADDING', (0, 0), (-1, -1), 14),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 14),
        ('LEFTPADDING', (0, 0), (-1, -1), 16),
        ('RIGHTPADDING', (0, 0), (-1, -1), 16),
        ('LINELEFT', (0, 0), (-1, -1), 4, colors.HexColor("#2563eb")),
        ('BOX', (0, 0), (-1, -1), 0.8, colors.HexColor("#e4e4e7")),
    ]))
    story.append(cov_table)
    story.append(Spacer(1, 12))

    lines = markdown_text.split("\n")
    i = 0
    total_lines = len(lines)
    lecture_count = 0
    in_toc = False

    while i < total_lines:
        raw_line = lines[i]
        line = raw_line.strip()

        if not line:
            story.append(Spacer(1, 5.5))
            i += 1
            continue

        # Skip document title if repeated as the very first line
        if i == 0 and line.startswith("# "):
            i += 1
            continue

        # Check if entering Table of Contents
        if "Table of Contents" in line:
            in_toc = True
            story.append(safe_paragraph("<b>📑 Table of Contents</b>", h2_style))
            story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#e2e8f0"), spaceBefore=2, spaceAfter=4))
            i += 1
            continue

        # Dividers (--- or ***)
        if re.match(r"^(\-{3,}|\*{3,}|_{3,})$", line):
            in_toc = False  # TOC typically ends at divider
            story.append(HRFlowable(width="100%", thickness=0.6, color=colors.HexColor("#e2e8f0"), spaceBefore=5, spaceAfter=5))
            i += 1
            continue

        # Blockquotes (> ...)
        if line.startswith(">"):
            quote_text = line.lstrip("> ").strip()
            p = safe_paragraph(f"<i>{inline_md(quote_text)}</i>", quote_style)
            t = Table([[p]], colWidths=[printable_width])
            t.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
                ('LEFTPADDING', (0, 0), (-1, -1), 10),
                ('RIGHTPADDING', (0, 0), (-1, -1), 10),
                ('TOPPADDING', (0, 0), (-1, -1), 7),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 7),
                ('LINELEFT', (0, 0), (-1, -1), 2.5, colors.HexColor("#94a3b8")),
            ]))
            story.append(Spacer(1, 3))
            story.append(t)
            story.append(Spacer(1, 5))
            i += 1
            continue

        # Markdown Tables (| col | col |)
        is_table_line = (line.startswith("|") and line.endswith("|")) or (line.count("|") >= 2 and not line.startswith("#"))
        if is_table_line:
            table_lines = [line]
            while i + 1 < total_lines:
                next_l = lines[i + 1].strip()
                if (next_l.startswith("|") and next_l.endswith("|")) or (next_l.count("|") >= 2 and not next_l.startswith("#")):
                    i += 1
                    table_lines.append(next_l)
                else:
                    break

            table_data = []
            for t_idx, t_line in enumerate(table_lines):
                # Skip markdown separator row like |---|---|
                if re.match(r"^\|?\s*[-:]+\s*\|", t_line):
                    continue
                cells = [c.strip() for c in t_line.strip("|").split("|")]
                row_cells = []
                for cell in cells:
                    p_style = ParagraphStyle(
                        "TableCellBold" if t_idx == 0 else "TableCellNormal",
                        fontName=FONT_BOLD if t_idx == 0 else FONT_NORMAL,
                        fontSize=9,
                        leading=13,
                        textColor=colors.HexColor("#0f172a" if t_idx == 0 else "#334155"),
                    )
                    row_cells.append(safe_paragraph(inline_md(cell), p_style))
                table_data.append(row_cells)

            if table_data:
                num_cols = max(len(r) for r in table_data)
                col_w = printable_width / max(num_cols, 1)
                t_obj = Table(table_data, colWidths=[col_w] * num_cols)
                t_obj.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                    ('TOPPADDING', (0, 0), (-1, -1), 6),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                    ('LEFTPADDING', (0, 0), (-1, -1), 8),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 8),
                    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
                ]))
                story.append(Spacer(1, 4))
                story.append(t_obj)
                story.append(Spacer(1, 6))
            i += 1
            continue

        # Major Chapter / Lecture Headers (# Lecture ... or # 📖 Lecture ...)
        if re.match(r"^#\s+(📖\s*)?Lecture\s+\d+", line, re.IGNORECASE):
            in_toc = False
            clean_l_title = re.sub(r"^#\s+(📖\s*)?", "", line).strip()
            lecture_count += 1
            if lecture_count > 1:
                story.append(PageBreak())

            p1 = safe_paragraph(f"<b>{inline_md(clean_l_title)}</b>", lec_title_style)
            p2 = safe_paragraph("Comprehensive Lecture Notes • Verified Syllabus Breakdown", lec_sub_style)
            t = Table([[[p1, p2]]], colWidths=[printable_width])
            t.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
                ('LEFTPADDING', (0, 0), (-1, -1), 12),
                ('RIGHTPADDING', (0, 0), (-1, -1), 12),
                ('TOPPADDING', (0, 0), (-1, -1), 7),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 7),
                ('LINELEFT', (0, 0), (-1, -1), 3.5, colors.HexColor("#1e40af")),
                ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ]))
            story.append(Spacer(1, 8))
            story.append(t)
            story.append(Spacer(1, 8))
            i += 1
            continue

        # Plain # Header (e.g. Unit Study Notes)
        if line.startswith("# ") and not line.startswith("## "):
            in_toc = False
            h1_text = line[2:].strip()
            story.append(safe_paragraph(f"<b>{inline_md(h1_text)}</b>", lec_title_style))
            story.append(HRFlowable(width="100%", thickness=0.8, color=colors.HexColor("#cbd5e1"), spaceBefore=3, spaceAfter=5))
            i += 1
            continue

        # Section Milestones (### ⏱️ Section ... or ### Section ...)
        if re.match(r"^###\s+.*(⏱️|Section\s+\d+)", line, re.IGNORECASE):
            in_toc = False
            sec_title = line.lstrip("#").strip()
            p = safe_paragraph(f"⏱️ <b>{inline_md(sec_title)}</b>", sec_title_style)
            t = Table([[p]], colWidths=[printable_width])
            t.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#eff6ff")),
                ('LEFTPADDING', (0, 0), (-1, -1), 10),
                ('RIGHTPADDING', (0, 0), (-1, -1), 10),
                ('TOPPADDING', (0, 0), (-1, -1), 7),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 7),
                ('LINELEFT', (0, 0), (-1, -1), 3, colors.HexColor("#3b82f6")),
                ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#bfdbfe")),
            ]))
            story.append(Spacer(1, 6))
            story.append(t)
            story.append(Spacer(1, 6))
            i += 1
            continue

        # Question Headers (### Question ... or Question \d+:)
        if re.match(r"^###\s+Question\s+\d+", line, re.IGNORECASE):
            in_toc = False
            q_title = line.lstrip("#").strip()
            p = safe_paragraph(f"🎯 <b>{inline_md(q_title)}</b>", q_title_style)
            t = Table([[p]], colWidths=[printable_width])
            t.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
                ('LEFTPADDING', (0, 0), (-1, -1), 10),
                ('RIGHTPADDING', (0, 0), (-1, -1), 10),
                ('TOPPADDING', (0, 0), (-1, -1), 7),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 7),
                ('LINELEFT', (0, 0), (-1, -1), 3, colors.HexColor("#6366f1")),
                ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ]))
            story.append(Spacer(1, 6))
            story.append(t)
            story.append(Spacer(1, 5))
            i += 1
            continue

        # Section Subheadings (## ...)
        if line.startswith("## "):
            in_toc = False
            sub_title = line[3:].strip()
            story.append(safe_paragraph(f"<b>{inline_md(sub_title)}</b>", h2_style))
            story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#e2e8f0"), spaceBefore=2, spaceAfter=4))
            i += 1
            continue

        # Minor Subheadings (### ...)
        if line.startswith("### "):
            in_toc = False
            sub_title = line[4:].strip()
            story.append(safe_paragraph(f"<b>{inline_md(sub_title)}</b>", h3_style))
            i += 1
            continue

        # Minor Sub-subheadings (#### ...)
        if line.startswith("#### "):
            in_toc = False
            sub_title = line[5:].strip()
            story.append(safe_paragraph(f"<b>{inline_md(sub_title)}</b>", h4_style))
            i += 1
            continue

        # Verified Answer Callout Box
        if re.search(r"(\*\*\s*Answer\s*:\s*\*\*|\bAnswer\s*:\s*)", line, re.IGNORECASE):
            ans_clean = re.sub(r"^\s*(\*|-|\d+\.)\s*", "", line)
            ans_clean = re.sub(r"^\s*\*\*\s*Answer\s*:\s*\*\*\s*", "", ans_clean, flags=re.IGNORECASE)
            ans_clean = re.sub(r"^\s*Answer\s*:\s*", "", ans_clean, flags=re.IGNORECASE)
            p = safe_paragraph(f"<b>✓ Verified Answer:</b> {inline_md(ans_clean)}", ans_style)
            t = Table([[p]], colWidths=[printable_width])
            t.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#f0fdf4")),
                ('LEFTPADDING', (0, 0), (-1, -1), 10),
                ('RIGHTPADDING', (0, 0), (-1, -1), 10),
                ('TOPPADDING', (0, 0), (-1, -1), 7),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 7),
                ('LINELEFT', (0, 0), (-1, -1), 3, colors.HexColor("#16a34a")),
                ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#bbf7d0")),
            ]))
            story.append(Spacer(1, 3))
            story.append(t)
            story.append(Spacer(1, 5))
            i += 1
            continue

        # Whiteboard Warning / Exam Tip Callout Box
        if re.search(r"(\*\*\s*(Whiteboard\s+Warning|Exam\s+Tip|Exam\s+Relevance)\s*:\s*\*\*)", line, re.IGNORECASE):
            tip_match = re.search(r"\*\*\s*(Whiteboard\s+Warning|Exam\s+Tip|Exam\s+Relevance)\s*:\s*\*\*\s*(.*)", line, re.IGNORECASE)
            if tip_match:
                label = tip_match.group(1).strip()
                tip_text = tip_match.group(2).strip()
                p = safe_paragraph(f"<b>💡 {label}:</b> {inline_md(tip_text)}", tip_style)
                t = Table([[p]], colWidths=[printable_width])
                t.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#fffbeb")),
                    ('LEFTPADDING', (0, 0), (-1, -1), 10),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 10),
                    ('TOPPADDING', (0, 0), (-1, -1), 5),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
                    ('LINELEFT', (0, 0), (-1, -1), 3, colors.HexColor("#f59e0b")),
                    ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#fde68a")),
                ]))
                story.append(Spacer(1, 3))
                story.append(t)
                story.append(Spacer(1, 5))
                i += 1
                continue

        # Table of Contents Items (e.g. 1. **Lecture Title**)
        if in_toc and re.match(r"^\d+\.\s+", line):
            num_match = re.match(r"^(\d+)\.\s+(.*)", line)
            if num_match:
                num = num_match.group(1)
                item_text = num_match.group(2)
                story.append(safe_paragraph(f"<b>{num}.</b>  {inline_md(item_text)}", toc_style))
                i += 1
                continue

        # Process / Concept Flow Callout Card (lines containing →)
        if "→" in line:
            flow_clean = re.sub(r"^\s*(\*|-|\d+\.)\s*", "", line)
            p = safe_paragraph(f"{inline_md(flow_clean)}", flow_callout_style)
            t = Table([[p]], colWidths=[printable_width])
            t.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#eff6ff")),
                ('LEFTPADDING', (0, 0), (-1, -1), 12),
                ('RIGHTPADDING', (0, 0), (-1, -1), 12),
                ('TOPPADDING', (0, 0), (-1, -1), 7),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 7),
                ('LINELEFT', (0, 0), (-1, -1), 3.5, colors.HexColor("#3b82f6")),
                ('BOX', (0, 0), (-1, -1), 0.6, colors.HexColor("#bfdbfe")),
            ]))
            story.append(Spacer(1, 3))
            story.append(t)
            story.append(Spacer(1, 4))
            i += 1
            continue

        # Nested sub-bullet (e.g. 4 spaces or 2 tabs indentation)
        if raw_line.startswith("    * ") or raw_line.startswith("    - ") or raw_line.startswith("  * ") or raw_line.startswith("  - "):
            clean_item = line.lstrip("*- ").strip()
            story.append(safe_paragraph(f'<font color="#3b82f6">●</font>  {inline_md(clean_item)}', sub_bullet_style))
            i += 1
            continue

        # Top-level bullet
        if line.startswith("* ") or line.startswith("- "):
            clean_item = line[2:].strip()
            story.append(safe_paragraph(f'<font color="#3b82f6">●</font>  {inline_md(clean_item)}', bullet_style))
            i += 1
            continue

        # Numbered list (e.g. 1. , 2. )
        num_match = re.match(r"^(\d+)\.\s+(.*)", line)
        if num_match:
            num = num_match.group(1)
            item_text = num_match.group(2)
            story.append(safe_paragraph(f"<b>{num}.</b>  {inline_md(item_text)}", bullet_style))
            i += 1
            continue

        # Regular Body Paragraph
        story.append(safe_paragraph(inline_md(line), body_style))
        i += 1

    doc.build(story, canvasmaker=CoursePilotNumberedCanvas)
    return buffer.getvalue()
