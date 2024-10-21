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

from .models import Cart, CartItem

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


def get_product_image(item, normal_style):
    try:
        image_url = item['image_url']
        if not image_url.startswith(('http://', 'https://')):
            image_url = urljoin(settings.BASE_URL, image_url)
        
        logger.info(f"Fetching image from URL: {image_url}")
        response = requests.get(image_url, stream=True, timeout=30)  # Increased timeout
        response.raise_for_status()
        
        img = Image(BytesIO(response.content))
        img.drawHeight = 1 * inch
        img.drawWidth = 1 * inch
        aspect = img._img.getSize()[0] / float(img._img.getSize()[1])
        if aspect > 1:
            img.drawHeight = img.drawWidth / aspect
        else:
            img.drawWidth = img.drawHeight * aspect
        return img
    except requests.RequestException as e:
        logger.error(f"Failed to fetch image for {item['product_name']}: {str(e)}")
    except Exception as e:
        logger.error(f"Error processing image for {item['product_name']}: {str(e)}")
    
    # Fallback: Return a placeholder or text if image can't be fetched or processed
    return Paragraph("Image not available", normal_style)


def generate_order_pdf(order_details, items, order_number):
    try:
        filename = f"order_{order_number.replace('/', '_')}.pdf"
        filepath = os.path.join(settings.MEDIA_ROOT, 'order_pdfs', filename)
        
        os.makedirs(os.path.dirname(filepath), exist_ok=True)

        doc = SimpleDocTemplate(filepath, pagesize=letter)
        elements = []

        styles = getSampleStyleSheet()
        title_style = styles['Heading1']
        normal_style = styles['Normal']

        elements.append(Paragraph(f"Order Details - {order_number}", title_style))
        for line in order_details.split('\n'):
            elements.append(Paragraph(line, normal_style))
        elements.append(Spacer(1, 0.25*inch))

        elements.append(Paragraph("Order Items", title_style))
        for item in items:
            data = [
                [Paragraph(f"<b>{item['product_name']}</b>", normal_style), get_product_image(item, normal_style)],
                [f"Quantity: {item['quantity']}", f"Price: Ksh.{item['price']}"],
                [f"Total: Ksh.{item['total']}", '']
            ]

            t = Table(data, colWidths=[4 * inch, 2 * inch])
            t.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 12),
                ('TOPPADDING', (0, 0), (-1, -1), 12),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ]))
            elements.append(t)
            elements.append(Spacer(1, 0.25 * inch))

        # Add the total amount section
        total_amount = order_details.split('\n')[-1].split(':')[-1].strip()
        total_paragraph = Paragraph(f"Total Order Amount: {total_amount}", 
                                    ParagraphStyle(name='TotalAmount', parent=normal_style, backColor=colors.yellow))
        elements.append(total_paragraph)
        elements.append(Spacer(1, 0.25 * inch))
        
        doc.build(elements)

        pdf_url = urljoin(settings.MEDIA_URL, f'order_pdfs/{filename}')
        logger.info(f"PDF generated for order {order_number}: filename={filename}, relative_url={pdf_url}")
        
        return filename, pdf_url

    except Exception as e:
        logger.error(f"Failed to generate PDF for order {order_number}: {str(e)}")
        return None, None