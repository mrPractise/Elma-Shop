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

        for key, value in order_details.items():
            if key != 'items':
                elements.append(Paragraph(f"<b>{key.replace('_', ' ').title()}:</b> {value}", normal_style))
        
        elements.append(Spacer(1, 0.25 * inch))

        # Add items table
        data = [['Product', 'Quantity', 'Price']]
        for item in items:
            data.append([item['product_name'], str(item['quantity']), f"Ksh.{item['price']}"])
        
        table = Table(data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 14),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 12),
            ('TOPPADDING', (0, 1), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        elements.append(table)
        elements.append(Spacer(1, 0.25 * inch))

        # Add total
        total_amount = order_details.get('total_amount', 'N/A')
        if total_amount != 'N/A':
            total_style = ParagraphStyle('total', parent=normal_style, backColor=colors.yellow)
            total_paragraph = Paragraph(f"<b>Total Order Amount: Ksh.{total_amount}</b>", total_style)
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
