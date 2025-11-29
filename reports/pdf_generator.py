from io import BytesIO
from datetime import datetime


class ReportGenerator:
    def __init__(self, student, school, term):
        self.student = student
        self.school = school
        self.term = term
        self.buffer = BytesIO()

    def generate_pdf(self, subject_results, term_result, attendance, behaviour, report_code):
        """Generate PDF report card matching Ghana Education Service format.

        Parameters
        ----------
        subject_results : Iterable
            Collection of per-subject score objects. Each object is expected to expose:
              - task, homework, group_work, project_work, class_test (numeric components making class score)
              - exam_score (numeric, already scaled to 50%)
              - class_subject.subject.name (subject display name)
              - optional remark (free-text, will be word-wrapped if present)
        term_result : object | None
            Optional aggregated term result (e.g. with overall_average attribute). Currently used only for potential future summary.
        attendance : object | None
            Expected attributes: days_present, total_days.
        behaviour : object | None
            Placeholder for future behavioural metrics (e.g. conduct, attitude). Not presently rendered beyond labels.
        report_code : str | None
            Unique identifier for the report instance (can be displayed later for audits).

        Notes
        -----
        - Layout is constrained to single A4 page; subject rows capped.
        - Default grading scale A/B/C/D/F applied if school provides no custom `get_grade_for_score`.
        - Remarks column shows grade by default; if a `remark` attribute exists on a subject result it supersedes grade.
        """
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.lib import colors
            from reportlab.lib.units import inch
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
            from reportlab.lib.utils import ImageReader
        except Exception as e:
            raise RuntimeError("reportlab is not installed. Add 'reportlab' to requirements to enable PDF generation.") from e
            
        doc = SimpleDocTemplate(self.buffer, pagesize=A4,
                    rightMargin=0.5*inch, leftMargin=0.5*inch,
                    topMargin=0.3*inch, bottomMargin=0.45*inch)
        
        elements = []
        styles = getSampleStyleSheet()
        
        # Custom styles matching the GES format
        title_style = ParagraphStyle(
            'SchoolTitle',
            parent=styles['Heading1'],
            fontSize=13,
            textColor=colors.black,
            spaceAfter=1,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        )
        
        subtitle_style = ParagraphStyle(
            'SchoolSubtitle',
            parent=styles['Normal'],
            fontSize=11,
            alignment=TA_CENTER,
            spaceAfter=1,
            fontName='Helvetica-Bold'
        )
        
        contact_style = ParagraphStyle(
            'ContactInfo',
            parent=styles['Normal'],
            fontSize=7.5,
            alignment=TA_CENTER,
            spaceAfter=6
        )
        
        report_header_style = ParagraphStyle(
            'ReportHeader',
            parent=styles['Normal'],
            fontSize=11.5,
            alignment=TA_CENTER,
            textColor=colors.white,
            fontName='Helvetica-Bold'
        )

        # Helper function to get images
        def _get_image(path, max_w, max_h):
            try:
                if not path:
                    return None
                reader = ImageReader(path)
                iw, ih = reader.getSize()
                scale = min(max_w/iw, max_h/ih)
                return Image(path, width=iw*scale, height=ih*scale)
            except Exception:
                return None

        school_logo = _get_image(getattr(getattr(self.school, 'logo', None), 'path', None), 0.8*inch, 0.8*inch)
        student_photo = _get_image(getattr(getattr(self.student, 'photo', None), 'path', None), 1.2*inch, 1.5*inch)

        # School Header Section (Logo | School Info | Student Photo)
        header_data = []
        
        # Left: School Logo
        left_cell = school_logo if school_logo else ""
        
        # Center: School Information
        center_content = [
            Paragraph(f"{getattr(self.school, 'name', 'SCHOOL NAME')}", title_style),
            Paragraph(f"{getattr(self.school, 'address', '')}", subtitle_style),
        ]
        
        if hasattr(self.school, 'phone_number') and self.school.phone_number:
            center_content.append(
                Paragraph(f"P. O. Box {getattr(self.school, 'location', '')} | {self.school.phone_number}", contact_style)
            )
        if hasattr(self.school, 'email') and self.school.email:
            center_content.append(
                Paragraph(f"Email: {self.school.email}", contact_style)
            )
        
        # Right: Student Photo placeholder or actual photo
        right_cell = student_photo if student_photo else Paragraph("STUDENT<br/>PHOTO", contact_style)
        
        header_data.append([left_cell, center_content, right_cell])
        
        header_table = Table(header_data, colWidths=[1*inch, 4.5*inch, 1.5*inch])
        header_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, 0), 'CENTER'),
            ('ALIGN', (1, 0), (1, 0), 'CENTER'),
            ('ALIGN', (2, 0), (2, 0), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ]))
        elements.append(header_table)
        elements.append(Spacer(1, 0.08*inch))

        # Report Title Bar (Black background like in image)
        report_title_data = [[Paragraph("TERMINAL REPORT SHEET", report_header_style)]]
        report_title_table = Table(report_title_data, colWidths=[7*inch])
        report_title_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.black),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 11.5),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        elements.append(report_title_table)
        elements.append(Spacer(1, 0.12*inch))

        # Student Information Section
        # Student name and class fallbacks for preview/sample objects
        student_name = (
            getattr(self.student, 'full_name', None)
            or (getattr(self.student, 'get_full_name', lambda: None)() or None)
            or (f"{getattr(self.student, 'first_name', '')} {getattr(self.student, 'last_name', '')}".strip())
        )

        class_obj = getattr(self.student, 'current_class', None)
        class_level_display = getattr(class_obj, 'level_display', None) if class_obj else None
        class_level = getattr(class_obj, 'level', '') if class_obj else ''
        class_name = f"{class_level_display or class_level}"
        if class_obj and getattr(class_obj, 'section', None):
            class_name += f" {class_obj.section}"

        academic_year = getattr(self.term, 'academic_year', None)
        if isinstance(academic_year, str):
            year_name = academic_year
        else:
            year_name = getattr(academic_year, 'name', '2023/2024') if academic_year else '2023/2024'
        
        student_info = [
            f"NAME:...{student_name}...CLASS: {class_name}",
            f"ACADEMIC YEAR: {year_name}    TERM: {getattr(self.term, 'get_name_display', lambda: 'FIRST (1)')()}    CLASS NO:.....",
            f"CLASS TEACHER:...{getattr(getattr(class_obj, 'class_teacher', None), 'get_full_name', lambda: '')()}...POSITION:....."
        ]
        
        for info in student_info:
            elements.append(Paragraph(info, styles['Normal']))
        elements.append(Spacer(1, 0.08*inch))

        # Subjects Table
        subjects_header = [
            ['SUBJECTS', 'Class Score\n50%', 'Exams\nScore 50%', 'Total Score\n100%', 'Position', 'Remarks']
        ]
        
        subjects_data = []
        for result in subject_results:
            class_score = (result.task + result.homework + result.group_work + 
                          result.project_work + result.class_test) / 2  # Convert to 50%
            exam_score = result.exam_score  # Already out of 50
            total = class_score + exam_score
            grade = self._get_grade(total)
            # Use custom remark if available; fall back to grade letter
            custom_remark = getattr(result, 'remark', None)
            remark_text = custom_remark if (isinstance(custom_remark, str) and custom_remark.strip()) else grade
            subjects_data.append([
                result.class_subject.subject.name,
                f"{class_score:.1f}",
                f"{exam_score:.1f}", 
                f"{total:.1f}",
                "",  # Position - to be calculated
                remark_text
            ])
        
        # Add empty rows to match template for common subjects
        common_subjects = ['English Language', 'Mathematics', 'Integrated Science', 'Social Studies', 
                         'Religious & Moral Edu.', 'Ghanaian Language', 'Computing', 
                         'Career Technology', 'Creative Arts']
        
        existing_subjects = {result.class_subject.subject.name for result in subject_results}
        for subject in common_subjects:
            if subject not in existing_subjects:
                subjects_data.append([subject, "", "", "", "", ""])

        # Enforce one-page layout by capping rows
        max_subject_rows = 12
        if len(subjects_data) > max_subject_rows:
            subjects_data = subjects_data[:max_subject_rows]

        all_subjects_data = subjects_header + subjects_data
        
        subjects_table = Table(all_subjects_data, colWidths=[2.15*inch, 0.82*inch, 0.82*inch, 0.82*inch, 0.6*inch, 0.79*inch])
        subjects_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8.5),
            ('TOPPADDING', (0, 0), (-1, -1), 2),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        elements.append(subjects_table)
        elements.append(Spacer(1, 0.08*inch))

        # Grading Scale (small reference box)
        scale_data = [
            ['GRADE', 'SCORE RANGE'],
            ['A', '80 - 100'],
            ['B', '70 - 79'],
            ['C', '60 - 69'],
            ['D', '50 - 59'],
            ['F', '0 - 49'],
        ]
        scale_table = Table(scale_data, colWidths=[0.7*inch, 1.0*inch])
        scale_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.black),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 7.5),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('TOPPADDING', (0, 0), (-1, -1), 2),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ]))
        elements.append(scale_table)
        elements.append(Spacer(1, 0.08*inch))

        # Attendance and Additional Sections
        attendance_info = f"ATTENDANCE:...{getattr(attendance, 'days_present', '')}...OUT OF:...{getattr(attendance, 'total_days', '')}...PROMOTED TO:..."
        elements.append(Paragraph(attendance_info, styles['Normal']))
        elements.append(Spacer(1, 0.08*inch))

        sections = [
            "CONDUCT:",
            "ATTITUDE:",
            "INTEREST:",
            "CLASS TEACHER'S REMARKS:",
            "HEAD TEACHER'S REMARKS:"
        ]

        for section in sections:
            elements.append(Paragraph(section, styles['Normal']))
            elements.append(Paragraph("." * 80, styles['Normal']))
            elements.append(Spacer(1, 0.04*inch))

        # Signature Section
        elements.append(Spacer(1, 0.22*inch))
        signature_data = [
            ['', '', ''],
            ['...................................', '...................................', '...................................'],
            ['CLASS TEACHER', 'HEAD TEACHER', 'PARENT/GUARDIAN'],
        ]

        signature_table = Table(signature_data, colWidths=[2.3*inch, 2.3*inch, 2.3*inch])
        signature_table.setStyle(TableStyle([
            ('FONTNAME', (0, 2), (-1, 2), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOTTOMPADDING', (0, 2), (-1, 2), 8),
        ]))
        elements.append(signature_table)

        # Build PDF
        doc.build(elements)
        self.buffer.seek(0)
        return self.buffer

    def _get_grade(self, score):
        """Get grade based on school's grading scale or default"""
        if hasattr(self.school, 'get_grade_for_score'):
            return self.school.get_grade_for_score(score)
        
        # Default grading scale
        if score >= 80:
            return 'A'
        elif score >= 70:
            return 'B'
        elif score >= 60:
            return 'C'
        elif score >= 50:
            return 'D'
        else:
            return 'F'

    def get_file_data(self):
        """Return the PDF data"""
        return self.buffer.getvalue()
