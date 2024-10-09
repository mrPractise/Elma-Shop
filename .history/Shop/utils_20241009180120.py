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


def get_cart_quantities(request):
    if not request.session.session_key:
        return {}
    
    cart = Cart.objects.filter(session__session_key=request.session.session_key, is_active=True).first()
    if not cart:
        return {}
    
    cart_items = CartItem.objects.filter(cart=cart)
    return {item.product_id: item.quantity for item in cart_items}



def generate_order_pdf(order_details, items):
    # Generate a unique filename
    filename = f"order_{uuid.uuid4()}.pdf"
    filepath = os.path.join(settings.MEDIA_ROOT, 'order_pdfs', filename)
    
    # Ensure the directory exists
    os.makedirs(os.path.dirname(filepath), exist_ok=True)

    # Create the PDF document
    doc = SimpleDocTemplate(filepath, pagesize=letter)
    elements = []

    # Styles
    styles = getSampleStyleSheet()
    title_style = styles['Heading1']
    normal_style = styles['Normal']

    # Add order details
    elements.append(Paragraph("Order Details", title_style))
    for line in order_details.split('\n'):
        elements.append(Paragraph(line, normal_style))
    elements.append(Spacer(1, 0.25*inch))

    # Add items
    elements.append(Paragraph("Order Items", title_style))
    for item in items:
        # Create a table for each item
        data = [
            [Paragraph(f"<b>{item['product_name']}</b>", normal_style), ''],
            [f"Quantity: {item['quantity']}", f"Price: Ksh.{item['price']}"],
            [f"Total: Ksh.{item['total']}", '']
        ]

        # Try to add the image
        try:
            response = requests.get(item['image_url'], timeout=10)
            img = Image(BytesIO(response.content), width=1.5*inch, height=1.5*inch)
            data[0][1] = img
        except:
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

    # Build the PDF
    doc.build(elements)

    # Generate the URL for the PDF
    pdf_url = os.path.join(settings.MEDIA_URL, 'order_pdfs', filename)

    return filename, pdf_url