from .models import Cart, CartItem
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.utils import ImageReader
from reportlab.lib.units import inch
import requests
from io import BytesIO
import os
import uuid
from django.conf import settings
from urllib.parse import urljoin, quote
import re
import logging
from PIL import Image as PILImage

def get_cart_quantities(request):
    if not request.session.session_key:
        return {}
    
    cart = Cart.objects.filter(session__session_key=request.session.session_key, is_active=True).first()
    if not cart:
        return {}
    
    cart_items = CartItem.objects.filter(cart=cart)
    return {item.product_id: item.quantity for item in cart_items}

def fetch_image(image_url):
    try:
        response = requests.get(image_url, timeout=10)
        response.raise_for_status()
        return PILImage.open(BytesIO(response.content))
    except Exception as e:
        logging.error(f"Error fetching image from {image_url}: {str(e)}")
        return None

def generate_order_pdf(order_details, items, order_number):
    pdf_filename = f"order_{order_number}.pdf"
    doc = SimpleDocTemplate(pdf_filename, pagesize=letter)
    elements = []
    
    styles = getSampleStyleSheet()
    title_style = styles['Heading1']
    normal_style = styles['Normal']
    
    elements.append(Paragraph(f"Order Details - {order_number}", title_style))
    elements.append(Paragraph(order_details, normal_style))
    elements.append(Spacer(1, 0.25 * inch))
    
    elements.append(Paragraph("Order Items", title_style))
    for item in items:
        try:
            item_name = item.get('name', 'Unknown Item')
            item_image_url = item.get('image', '')  # Note: changed from 'image_url' to 'image'
            item_quantity = item.get('quantity', 0)
            item_price = item.get('price', '0')
            
            img = fetch_image(item_image_url)
            
            if img:
                img.thumbnail((100, 100))  # Resize image
                img_buffer = BytesIO()
                img.save(img_buffer, format='PNG')
                img_buffer.seek(0)
                img_reader = ImageReader(img_buffer)
            else:
                img_reader = None  # Or use a placeholder image
            
            data = [
                [Paragraph(f"<b>{item_name}</b>", normal_style), img_reader or ''],
                [f"Quantity: {item_quantity}", f"Price: Ksh.{item_price}"],
                [f"Total: Ksh.{float(item_price) * int(item_quantity)}", '']
            ]
            
            t = Table(data, colWidths=[4 * inch, 2 * inch])
            t.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('TOPPADDING', (0, 0), (-1, -1), 5),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
                ('BOX', (0, 0), (-1, -1), 1, colors.black),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ]))
            elements.append(t)
            elements.append(Spacer(1, 0.25 * inch))
            
        except Exception as e:
            logging.error(f"Error processing item: {str(e)}", exc_info=True)
            elements.append(Paragraph(f"Failed to add item: {item.get('name', 'Unknown Item')}", normal_style))
    
    doc.build(elements)
    return pdf_filename