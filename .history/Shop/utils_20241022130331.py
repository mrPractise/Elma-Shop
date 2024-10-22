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
        # Add some left and right margins to the document
        doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=50, leftMargin=50)
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

        # Create a custom style for wrapped text in table cells
        wrapped_style = ParagraphStyle(
            'WrappedStyle',
            parent=styles['Normal'],
            fontSize=10,
            leading=12,  # Line height
            spaceBefore=3,
            spaceAfter=3,
            wordWrap='CJK'  # Better word wrapping
        )

        # Add items table with description column
        data = [['Product', 'Description', 'Quantity', 'Price']]
        
        # Calculate available width and adjust column proportions
        available_width = doc.width  # Total available width
        col_widths = [
            available_width * 0.25,  # Product: 25%
            available_width * 0.45,  # Description: 45%
            available_width * 0.15,  # Quantity: 15%
            available_width * 0.15   # Price: 15%
        ]
        
        # Process items and wrap long text
        for item in items:
            description = item.get('description', item.get('short_description', 'N/A'))
            # Wrap product name and description in Paragraph objects
            product_name = Paragraph(item['product_name'], wrapped_style)
            description_para = Paragraph(description, wrapped_style)
            
            data.append([
                product_name,
                description_para,
                str(item['quantity']),
                f"Ksh.{item['price']}"
            ])
        
        table = Table(data, colWidths=col_widths, repeatRows=1)
        table.setStyle(TableStyle([
            # Header styling
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('TOPPADDING', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
            
            # Body styling
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('TOPPADDING', (0, 1), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
            
            # Alignment
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),  # Header centered
            ('ALIGN', (0, 1), (0, -1), 'LEFT'),    # Product names left-aligned
            ('ALIGN', (1, 1), (1, -1), 'LEFT'),    # Descriptions left-aligned
            ('ALIGN', (2, 1), (2, -1), 'CENTER'),  # Quantity centered
            ('ALIGN', (3, 1), (3, -1), 'RIGHT'),   # Price right-aligned
            
            # Borders
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('LINEBELOW', (0, 0), (-1, 0), 2, colors.black),  # Thicker line below header
            
            # Cell padding
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            
            # Valign
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        
        elements.append(table)
        elements.append(Spacer(1, 0.25 * inch))

        # Add total (extract from order_details string)
        total_line = [line for line in order_details.split('\n') if 'Total Order Amount:' in line]
        if total_line:
            total_amount = total_line[0].split(':')[-1].strip()
            # Create custom style for total amount
            total_style = ParagraphStyle(
                'total',
                parent=normal_style,
                fontSize=24,  # 2rem = 24pt
                textColor=colors.orange,  # or colors.yellow, but orange might be more readable
                spaceAfter=12,
                alignment=1  # Center alignment (0=left, 1=center, 2=right)
            )
            total_paragraph = Paragraph(f"<b>Total Order Amount: {total_amount}</b>", total_style)
        else:
            # Keep the not available message in normal size but still styled
            total_style = ParagraphStyle(
                'total',
                parent=normal_style,
                fontSize=24,
                textColor=colors.gray
            )
            total_paragraph = Paragraph("<b>Total Order Amount: Not Available</b>", total_style)
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