import os
import re
import uuid
from io import BytesIO
import logging

import requests
from PIL import Image as PILImage
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from django.conf import settings
from urllib.parse import urljoin, quote
from reportlab.lib.colors import yellow
from reportlab.lib.units import inch
from .models import Cart, CartItem
from django.core.files.storage import default_storage
# Create a logger for your app

logger = logging.getLogger('Shop')
def get_cart_quantities(request):
    if not request.session.session_key:
        return {}
    
    cart = Cart.objects.filter(session__session_key=request.session.session_key, is_active=True).first()
    if not cart:
        return {}
    
    cart_items = CartItem.objects.filter(cart=cart)
    return {str(item.product_id): item.quantity for item in cart_items}

def generate_order_pdf(order_details, items, order_number):
    try:
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        elements = []

        styles = getSampleStyleSheet()
        normal_style = styles['Normal']

        # Add order details
        elements.append(Paragraph(f"Order Number: {order_number}", styles['Heading1']))
        elements.append(Spacer(1, 0.25 * inch))

        # Split the order_details string into lines and add each line as a paragraph
        for line in order_details.split('\n'):
            if ':' in line:
                key, value = line.split(':', 1)
                elements.append(Paragraph(f"<b>{key}:</b> {value.strip()}", normal_style))
            else:
                elements.append(Paragraph(line, normal_style))
        
        elements.append(Spacer(1, 0.25 * inch))

        # Add items table with description column
        data = [['Product', 'Description', 'Quantity', 'Price']]
        
        # Adjust column widths - total should equal to the page width minus margins
        col_widths = [120, 200, 70, 100]  # Widths in points
        
        for item in items:
            # Assuming items now includes a description field, if not, you might need to modify your items data
            description = item.get('description', item.get('short_description', 'N/A'))
            data.append([
                item['product_name'],
                description,
                str(item['quantity']),
                f"Ksh.{item['price']}"
            ])
        
        table = Table(data, colWidths=col_widths)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('ALIGN', (1, 1), (1, -1), 'LEFT'),  # Left align description column
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 14),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 12),
            ('TOPPADDING', (0, 1), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            # Word wrapping for description column
            ('WORDWRAP', (1, 1), (1, -1)),
        ]))
        elements.append(table)
        elements.append(Spacer(1, 0.25 * inch))

        # Add total (extract from order_details string)
        total_line = [line for line in order_details.split('\n') if 'Total Order Amount:' in line]
        if total_line:
            total_amount = total_line[0].split(':')[-1].strip()
            total_style = ParagraphStyle('total', parent=normal_style, backColor=colors.yellow)
            total_paragraph = Paragraph(f"<b>Total Order Amount: {total_amount}</b>", total_style)
        else:
            total_paragraph = Paragraph("<b>Total Order Amount: Not Available</b>", normal_style)
        elements.append(total_paragraph)

        # Build the PDF
        doc.build(elements)

        # Save the PDF
        pdf_filename = f'order_{order_number}.pdf'
        pdf_directory = os.path.join(settings.MEDIA_ROOT, 'order_pdfs')
        os.makedirs(pdf_directory, exist_ok=True)
        pdf_path = os.path.join(pdf_directory, pdf_filename)
        with open(pdf_path, 'wb') as f:
            f.write(buffer.getvalue())

        # Store the PDF in Django's default storage
        pdf_file = default_storage.open(pdf_filename, 'wb')
        pdf_file.write(buffer.getvalue())
        pdf_file.close()

        return pdf_filename, default_storage.url(pdf_filename)

    except Exception as e:
        logger.error(f"Failed to generate PDF for order {order_number}: {str(e)}")
        return None, None