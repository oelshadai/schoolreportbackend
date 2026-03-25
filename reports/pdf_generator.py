"""Professional HTML-to-PDF generator for terminal reports
Ensures 100% identical output between preview and PDF using wkhtmltopdf
"""
import os
import tempfile
import subprocess
from django.template.loader import render_to_string
from django.conf import settings
from django.http import HttpResponse


def generate_terminal_report_pdf(report_context):
    """Generate professional PDF using template's built-in print CSS
    
    Uses the same template as preview for 100% identical output.
    """
    try:
        # Ensure absolute URLs for images
        _ensure_absolute_urls(report_context)
        
        # Render template - SAME as preview
        html_content = render_to_string('reports/terminal_report.html', report_context)
        
        # Generate PDF using template's own print CSS
        return _generate_professional_pdf(html_content)
        
    except Exception as e:
        print(f"PDF generation error: {e}")
        raise e



def _ensure_absolute_urls(context):
    """Ensure all image URLs are absolute for PDF generation
    
    This is critical for wkhtmltopdf to properly load images in the PDF.
    """
    school = context.get('school')
    student = context.get('student')
    
    import pathlib

    # Convert school logo to absolute URL
    if school and hasattr(school, 'logo') and school.logo:
        try:
            logo_url = school.logo.url
            if logo_url.startswith('http://') or logo_url.startswith('https://'):
                # Already absolute (e.g. Cloudinary https://res.cloudinary.com/...)
                context['school_logo_absolute'] = logo_url
            elif hasattr(school.logo, 'path') and os.path.exists(school.logo.path):
                # Local file — use file:/// URI (correct on Windows)
                context['school_logo_absolute'] = pathlib.Path(os.path.abspath(school.logo.path)).as_uri()
            else:
                context['school_logo_absolute'] = context.get('media_url_base', '') + logo_url
        except (ValueError, AttributeError):
            context['school_logo_absolute'] = None

    # Convert student photo to absolute URL
    if student and hasattr(student, 'photo') and student.photo:
        try:
            photo_url = student.photo.url
            if photo_url.startswith('http://') or photo_url.startswith('https://'):
                context['student_photo_absolute'] = photo_url
            elif hasattr(student.photo, 'path') and os.path.exists(student.photo.path):
                context['student_photo_absolute'] = pathlib.Path(os.path.abspath(student.photo.path)).as_uri()
            else:
                context['student_photo_absolute'] = context.get('media_url_base', '') + photo_url
        except (ValueError, AttributeError):
            context['student_photo_absolute'] = None
    
    # Add PDF generation flag to context
    context['is_pdf_generation'] = True


def _generate_pdf_pdfkit(html_content):
    """Generate PDF using pdfkit (requires wkhtmltopdf) - PRIMARY METHOD
    
    This method provides the best quality and most reliable PDF generation.
    """
    try:
        import pdfkit
        
        # Configure pdfkit with wkhtmltopdf path from settings
        wkhtmltopdf_path = getattr(settings, 'WKHTMLTOPDF_CMD', 'wkhtmltopdf')
        config = pdfkit.configuration(wkhtmltopdf=wkhtmltopdf_path)
        
        # Configure options for EXACT iframe preview match
        options = {
            'page-size': 'A4',
            'margin-top': '8mm',
            'margin-right': '8mm',
            'margin-bottom': '8mm', 
            'margin-left': '8mm',
            'encoding': 'UTF-8',
            'no-outline': None,
            'enable-local-file-access': None,
            'print-media-type': None,
            'disable-smart-shrinking': None,
            'zoom': 1.0,
            'dpi': 96,
            'quiet': '',
            # Critical options for exact iframe match
            'load-error-handling': 'ignore',
            'load-media-error-handling': 'ignore',
            'javascript-delay': 500,
            'no-stop-slow-scripts': None,
            'disable-javascript': None,
            # Force exact rendering
            'viewport-size': '1024x768',
            'cookie-jar': '',
        }
        
        # Generate PDF from HTML string
        pdf_content = pdfkit.from_string(
            html_content, 
            False,  # False = return bytes instead of saving to file
            configuration=config,
            options=options
        )
        return pdf_content
        
    except ImportError:
        raise Exception("pdfkit not installed. Run: pip install pdfkit")
    except OSError as e:
        if 'wkhtmltopdf' in str(e).lower():
            raise Exception(
                "wkhtmltopdf not found. Please install from: https://wkhtmltopdf.org/downloads.html"
            )
        raise Exception(f"pdfkit generation failed: {str(e)}")
    except Exception as e:
        raise Exception(f"pdfkit generation failed: {str(e)}")


def _generate_professional_pdf(html_content):
    """Generate professional full-page PDF using wkhtmltopdf
    
    Ensures content fills entire A4 page naturally without compression.
    """
    with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as temp_html:
        temp_html.write(html_content)
        temp_html_path = temp_html.name
    
    temp_pdf = tempfile.NamedTemporaryFile(suffix='.pdf', delete=False)
    temp_pdf_path = temp_pdf.name
    temp_pdf.close()
    
    try:
        wkhtmltopdf_path = getattr(settings, 'WKHTMLTOPDF_CMD', 'wkhtmltopdf')
        
        cmd = [
            wkhtmltopdf_path,
            '--page-size', 'A4',
            # Margins must match the template @page CSS (8mm top/bottom, 10mm left/right)
            # so the report-container's height:297mm fits on exactly one page
            '--margin-top', '8mm',
            '--margin-right', '10mm',
            '--margin-bottom', '8mm',
            '--margin-left', '10mm',
            '--print-media-type',
            '--enable-local-file-access',
            '--disable-smart-shrinking',
            '--zoom', '1.0',
            '--dpi', '96',
            '--encoding', 'UTF-8',
            '--orientation', 'Portrait',
            '--viewport-size', '1024x768',
            '--javascript-delay', '500',
            '--no-stop-slow-scripts',
            '--minimum-font-size', '8',
            '--quiet',
            temp_html_path,
            temp_pdf_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, timeout=30, text=True)
        
        if result.returncode == 0 and os.path.exists(temp_pdf_path):
            with open(temp_pdf_path, 'rb') as pdf_file:
                pdf_content = pdf_file.read()
            return pdf_content
        else:
            raise Exception(f"wkhtmltopdf failed: {result.stderr}")
            
    finally:
        # Cleanup temp files
        try:
            os.unlink(temp_html_path)
            if os.path.exists(temp_pdf_path):
                os.unlink(temp_pdf_path)
        except:
            pass


class TerminalReportPDFGenerator:
    """Legacy class for backward compatibility"""
    
    def generate_pdf(self, report_context):
        """Generate PDF using HTML template method"""
        return generate_terminal_report_pdf(report_context)