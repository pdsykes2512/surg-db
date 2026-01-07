#!/usr/bin/env python3
"""
Convert Markdown documentation to PDF using reportlab

This script converts the IMPACT documentation files to PDF format.
"""

import os
import re
from reportlab.lib.pagesizes import letter, A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle, KeepTogether
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.lib import colors

def render_table(elements, table_lines, body_style):
    """
    Render a markdown table as a ReportLab Table with automatic column width adjustment.
    """
    if len(table_lines) < 3:
        return

    # Parse table data
    rows = []
    for line in table_lines:
        # Remove leading/trailing pipes and split
        cells = [cell.strip() for cell in line.strip('|').split('|')]
        rows.append(cells)

    # Skip separator row (second row with dashes)
    if len(rows) > 1 and all('-' in cell for cell in rows[1]):
        header = rows[0]
        data_rows = rows[2:]
    else:
        header = rows[0]
        data_rows = rows[1:]

    # Create table data with header - wrap text in Paragraphs for better wrapping
    table_style_small = ParagraphStyle(
        'TableCell',
        fontName='Helvetica',
        fontSize=7,
        leading=9,
        wordWrap='CJK'
    )

    table_style_header = ParagraphStyle(
        'TableHeader',
        fontName='Helvetica-Bold',
        fontSize=7,
        leading=9,
        textColor=colors.whitesmoke,
        wordWrap='CJK'
    )

    # Wrap cells in Paragraphs for text wrapping
    table_data = []
    table_data.append([Paragraph(str(cell), table_style_header) for cell in header])
    for row in data_rows:
        table_data.append([Paragraph(str(cell), table_style_small) for cell in row])

    # Calculate available width (A4 width minus margins)
    available_width = A4[0] - 1.5*inch  # 0.75 inch margins on each side

    # Calculate column widths based on content length
    num_cols = len(header)

    # Estimate content width for each column
    col_widths = []
    for col_idx in range(num_cols):
        # Get max content length in this column
        max_len = len(header[col_idx])
        for row in data_rows:
            if col_idx < len(row):
                max_len = max(max_len, len(row[col_idx]))
        col_widths.append(max_len)

    # Normalize column widths to fit available width
    total_weight = sum(col_widths)
    if total_weight > 0:
        normalized_widths = [available_width * (w / total_weight) for w in col_widths]
    else:
        normalized_widths = [available_width / num_cols] * num_cols

    # Create ReportLab Table with calculated column widths
    table = Table(table_data, colWidths=normalized_widths, repeatRows=1)

    # Style the table
    table.setStyle(TableStyle([
        # Header row styling
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c5aa0')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),

        # Data rows styling
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),

        # Grid
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cccccc')),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#2c5aa0')),

        # Alternating row colors for readability
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f5f5f5')]),
    ]))

    elements.append(table)
    elements.append(Spacer(1, 0.2*inch))


def markdown_to_reportlab(markdown_file, pdf_file):
    """
    Convert a Markdown file to PDF using reportlab.

    This is a basic converter that handles:
    - Headers (# ## ### etc.)
    - Paragraphs
    - Lists (- and *)
    - Code blocks (```)
    - Bold (**text**)
    - Italic (*text*)
    - Tables (basic)
    """

    # Read the markdown file
    with open(markdown_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # Create PDF
    doc = SimpleDocTemplate(pdf_file, pagesize=A4,
                            rightMargin=0.75*inch, leftMargin=0.75*inch,
                            topMargin=1*inch, bottomMargin=0.75*inch)

    # Container for the 'Flowable' objects
    elements = []

    # Define styles
    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#1a1a1a'),
        spaceAfter=30,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )

    h1_style = ParagraphStyle(
        'CustomH1',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#2c5aa0'),
        spaceBefore=20,
        spaceAfter=12,
        fontName='Helvetica-Bold'
    )

    h2_style = ParagraphStyle(
        'CustomH2',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#2c5aa0'),
        spaceBefore=16,
        spaceAfter=10,
        fontName='Helvetica-Bold'
    )

    h3_style = ParagraphStyle(
        'CustomH3',
        parent=styles['Heading3'],
        fontSize=12,
        textColor=colors.HexColor('#444444'),
        spaceBefore=12,
        spaceAfter=8,
        fontName='Helvetica-Bold'
    )

    body_style = ParagraphStyle(
        'CustomBody',
        parent=styles['BodyText'],
        fontSize=10,
        leading=14,
        alignment=TA_JUSTIFY,
        spaceAfter=8
    )

    code_style = ParagraphStyle(
        'Code',
        parent=styles['Code'],
        fontSize=7,
        leading=9,
        leftIndent=15,
        rightIndent=15,
        spaceBefore=8,
        spaceAfter=8,
        backColor=colors.HexColor('#f8f8f8'),
        textColor=colors.HexColor('#2d2d2d'),
        fontName='Courier',
        borderColor=colors.HexColor('#dddddd'),
        borderWidth=1,
        borderPadding=10
    )

    bullet_style = ParagraphStyle(
        'Bullet',
        parent=styles['BodyText'],
        fontSize=10,
        leftIndent=20,
        bulletIndent=10,
        spaceAfter=6
    )

    # Split content into lines
    lines = content.split('\n')

    in_code_block = False
    code_lines = []
    is_first_header = True
    in_table = False
    table_lines = []

    i = 0
    while i < len(lines):
        line = lines[i]

        # Skip empty lines at the start
        if not line.strip() and len(elements) == 0:
            i += 1
            continue

        # Code blocks
        if line.strip().startswith('```'):
            if not in_code_block:
                in_code_block = True
                code_lines = []
            else:
                # End of code block
                in_code_block = False
                if code_lines:
                    # Determine if this is a wide ASCII art diagram
                    max_line_len = max(len(line) for line in code_lines) if code_lines else 0

                    # Use smaller font for wide diagrams
                    if max_line_len > 60:
                        font_size = 5
                        line_height = 6
                    else:
                        font_size = 6
                        line_height = 7

                    # Use a table to preserve formatting for ASCII art and diagrams
                    # This prevents line breaks and maintains monospace layout
                    code_rows = []
                    for code_line in code_lines:
                        # Don't escape or modify - keep original characters
                        # Just preserve spaces with non-breaking spaces
                        line_text = code_line.replace(' ', '\u00a0')
                        code_rows.append([line_text])

                    # Create a table for the code block to preserve formatting
                    code_table = Table(code_rows, colWidths=[6.8*inch])
                    code_table.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f8f8f8')),
                        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#dddddd')),
                        ('FONTNAME', (0, 0), (-1, -1), 'Courier'),
                        ('FONTSIZE', (0, 0), (-1, -1), font_size),
                        ('LEADING', (0, 0), (-1, -1), line_height),
                        ('LEFTPADDING', (0, 0), (-1, -1), 6),
                        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
                        ('TOPPADDING', (0, 0), (-1, -1), 4),
                        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                    ]))
                    elements.append(code_table)
                    elements.append(Spacer(1, 0.15*inch))
            i += 1
            continue

        if in_code_block:
            code_lines.append(line)
            i += 1
            continue

        # Detect table start
        if '|' in line and not in_table:
            # Check if this is a markdown table
            if line.strip().startswith('|'):
                in_table = True
                table_lines = [line]
                i += 1
                continue

        # Collect table lines
        if in_table:
            if '|' in line:
                table_lines.append(line)
                i += 1
                continue
            else:
                # End of table - render it
                in_table = False
                if len(table_lines) > 2:  # Need at least header, separator, and one row
                    render_table(elements, table_lines, body_style)
                table_lines = []
                # Continue processing this line (don't increment i)
                continue

        # Headers
        if line.startswith('# '):
            text = line[2:].strip()
            if is_first_header:
                elements.append(Paragraph(text, title_style))
                is_first_header = False
            else:
                elements.append(PageBreak())
                elements.append(Paragraph(text, h1_style))
            elements.append(Spacer(1, 0.2*inch))

        elif line.startswith('## '):
            text = line[3:].strip()
            elements.append(Paragraph(text, h1_style))
            elements.append(Spacer(1, 0.15*inch))

        elif line.startswith('### '):
            text = line[4:].strip()
            elements.append(Paragraph(text, h2_style))
            elements.append(Spacer(1, 0.1*inch))

        elif line.startswith('#### '):
            text = line[5:].strip()
            elements.append(Paragraph(text, h3_style))
            elements.append(Spacer(1, 0.08*inch))

        # Bullet lists
        elif line.strip().startswith('- ') or line.strip().startswith('* '):
            text = line.strip()[2:]
            # Simple formatting
            text = format_inline(text)
            elements.append(Paragraph(f'• {text}', bullet_style))

        # Horizontal rule
        elif line.strip() == '---' or line.strip() == '***':
            elements.append(Spacer(1, 0.1*inch))
            elements.append(Paragraph('<para align="center">_______________</para>', body_style))
            elements.append(Spacer(1, 0.1*inch))

        # Regular paragraph
        elif line.strip():
            text = format_inline(line.strip())
            # Skip table of contents markers
            if not text.startswith('[') and '](#' not in text:
                elements.append(Paragraph(text, body_style))

        # Empty line
        else:
            if elements:  # Don't add spacer at the very beginning
                elements.append(Spacer(1, 0.05*inch))

        i += 1

    # Build PDF
    try:
        doc.build(elements)
        print(f"✅ Successfully created: {pdf_file}")
        return True
    except Exception as e:
        print(f"❌ Error creating {pdf_file}: {e}")
        return False


def format_inline(text):
    """
    Format inline markdown elements (bold, italic, code, links).
    """
    # Escape HTML entities first
    text = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

    # Links: [text](url) - convert to text first to avoid nested formatting issues
    text = re.sub(r'\[(.+?)\]\(.+?\)', r'\1', text)

    # Inline code: `code` (do before bold/italic to avoid conflicts)
    text = re.sub(r'`(.+?)`', r'<font name="Courier" color="#c7254e">\1</font>', text)

    # Bold: **text** or __text__
    text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
    text = re.sub(r'__(.+?)__', r'<b>\1</b>', text)

    # Italic: *text* or _text_ (but not in file paths or underscores in names)
    # Only handle single asterisks surrounded by spaces or at boundaries
    text = re.sub(r'(?<![*\w])\*([^*]+?)\*(?![*\w])', r'<i>\1</i>', text)
    # For underscores, be more conservative - only in specific contexts
    # Skip underscore italics as they're often in filenames

    return text


def main():
    """Convert all documentation markdown files to PDF."""

    # Documentation directory
    docs_dir = '/root/impact/docs'

    # Documentation files to convert
    doc_files = [
        'USER_GUIDE.md',
        'DEPLOYMENT_GUIDE.md',
        'TECHNICAL_SPECIFICATIONS.md',
        'SECURITY_AND_COMPLIANCE.md',
        'COSD_EXPORT.md'
    ]

    print("=" * 60)
    print("IMPACT Documentation to PDF Converter")
    print("=" * 60)
    print()

    successful = 0
    failed = 0

    for doc_file in doc_files:
        markdown_path = os.path.join(docs_dir, doc_file)
        pdf_filename = doc_file.replace('.md', '.pdf')
        pdf_path = os.path.join(docs_dir, pdf_filename)

        if not os.path.exists(markdown_path):
            print(f"⚠️  Skipping {doc_file} (not found)")
            failed += 1
            continue

        print(f"Converting: {doc_file}")
        print(f"  → {pdf_filename}")

        if markdown_to_reportlab(markdown_path, pdf_path):
            successful += 1
            file_size = os.path.getsize(pdf_path) / 1024  # KB
            print(f"  Size: {file_size:.1f} KB")
        else:
            failed += 1

        print()

    print("=" * 60)
    print(f"Conversion complete:")
    print(f"  ✅ Successful: {successful}")
    print(f"  ❌ Failed: {failed}")
    print(f"  📁 Output directory: {docs_dir}")
    print("=" * 60)


if __name__ == '__main__':
    main()
