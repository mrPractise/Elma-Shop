from .models import Cart, CartItem
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
import requests
from io import BytesIO
import os
import uuid
from django.conf import settings
from PIL import Image as PILImage
from reportlab.lib import colors
from reportlab.lib.utils import ImageReader
from requests.exceptions import RequestException
import logging

logger = logging.getLogger(__name__)




def get_cart_quantities(request):
    if not request.session.session_key:
        return {}
    
    cart = Cart.objects.filter(session__session_key=request.session.session_key, is_active=True).first()
    if not cart:
        return {}
    
    cart_items = CartItem.objects.filter(cart=cart)
    return {item.product_id: item.quantity for item in cart_items}



def generate_order_pdf(order_details, items):
    filename = f"order_{uuid.uuid4()}.pdf"
    filepath = os.path.join(settings.MEDIA_ROOT, 'order_pdfs', filename)
    
    os.makedirs(os.path.dirname(filepath), exist_ok=True)

    doc = SimpleDocTemplate(filepath, pagesize=letter)
    elements = []

    styles = getSampleStyleSheet()
    title_style = styles['Heading1']
    normal_style = styles['Normal']

    elements.append(Paragraph("Order Details", title_style))
    for line in order_details.split('\n'):
        elements.append(Paragraph(line, normal_style))
    elements.append(Spacer(1, 0.25*inch))

    elements.append(Paragraph("Order Items", title_style))
    for item in items:
        data = [
            [Paragraph(f"<b>{item['product_name']}</b>", normal_style), ''],
            [f"Quantity: {item['quantity']}", f"Price: Ksh.{item['price']}"],
            [f"Total: Ksh.{item['total']}", '']
        ]

        try:
            response = requests.get(item['image_url'], timeout=15, verify=True)
            response.raise_for_status()
            img_data = BytesIO(response.content)
            
            with PILImage.open(img_data) as img:
                img = img.convert('RGB')
                img_io = BytesIO()
                img.save(img_io, 'JPEG')
                img_io.seek(0)
            
            img = Image(ImageReader(img_io), width=1.5*inch, height=1.5*inch)
            data[0][1] = img
        except Exception as e:
            logger.error(f"Error loading image for {item['product_name']}: {str(e)}")
            data[0][1] = Paragraph("Image not available", normal_style)

        t = Table(data, colWidths=[4*inch, 2*inch])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.white),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 12),
            ('TOPPADDING', (0, 0), (-1, -1), 12),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        elements.append(t)
        elements.append(Spacer(1, 0.25*inch))

    doc.build(elements)

    return filename