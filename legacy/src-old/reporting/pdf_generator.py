"""
PDF Generation Module for the Hot Durham Project.

This module provides functions for generating PDFs from HTML templates. It is
designed to be a central access point for all PDF-related logic, making it easier
to integrate with other components of the application.

Key Features:
- HTML template rendering.
- PDF generation from HTML.
- Chart embedding in PDFs.
"""

import os
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML

def create_pdf_report(template_path, context, output_path):
    """Creates a PDF report from a given template and context."""
    try:
        # The loader should know where the templates are.
        template_dir = os.path.dirname(template_path)
        env = Environment(loader=FileSystemLoader(template_dir), autoescape=True)
        template = env.get_template(os.path.basename(template_path))
        
        # Render the HTML with the provided context
        html_out = template.render(context)
        
        # Write the PDF to the output path
        HTML(string=html_out, base_url=template_dir).write_pdf(output_path)
        print(f"Successfully generated PDF report at: {output_path}")
        
    except Exception as e:
        print(f"Error generating PDF report: {e}")
