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
from urllib.parse import urljoin
import re
from urllib.parse import quote
import logging
from selenium import webdriver
from selenium.webdriver.chrome.options import Options




def get_cart_quantities(request):
    if not request.session.session_key:
        return {}
    
    cart = Cart.objects.filter(session__session_key=request.session.session_key, is_active=True).first()
    if not cart:
        return {}
    
    cart_items = CartItem.objects.filter(cart=cart)
    return {item.product_id: item.quantity for item in cart_items}





logger = logging.getLogger(__name__)



def capture_screenshot(url):
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    
    driver = webdriver.Chrome(options=chrome_options)
    try:
        driver.get(url)
        return driver.get_screenshot_as_png()
    finally:
        driver.quit()

def create_image_from_screenshot(screenshot_data, width, height):
    img = Image.open(BytesIO(screenshot_data))
    img = img.crop((0, 0, width, height))  # Adjust crop as needed
    if img.mode != 'RGB':
        img = img.convert('RGB')
    img_buffer = BytesIO()
    img.save(img_buffer, format='PNG')
    img_buffer.seek(0)
    return img_buffer



logging.basicConfig(level=logging.ERROR)

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
            screenshot_data = capture_screenshot(item['image_url'])
            img_buffer = create_image_from_screenshot(screenshot_data, 100, 100)
            
            img = Image.open(img_buffer)
            img.thumbnail((100, 100))  # Resize image
            
            data = [
                [Paragraph(f"<b>{item['name']}</b>", normal_style), ImageReader(img)],
                [f"Quantity: {item['quantity']}", f"Price: ${item['price']}"],
                [f"Total: ${item['quantity'] * item['price']}", '']
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
            
            img.close()  # Close the image after use
        except Exception as e:
            logging.error(f"Error processing item {item['name']}: {str(e)}")
            elements.append(Paragraph(f"Failed to add item: {item['name']}", normal_style))
    
    with open(pdf_filename, 'wb') as pdf_file:
        doc.build(elements)
    return pdf_filename


# Example usage
if __name__ == "__main__":
    order_details = "Customer: John Doe\nAddress: 123 Main St, Anytown, AN 12345"
    items = [
        {
            'name': 'Product 1',
            'image_url': 'https://example.com/image1.jpg',
            'quantity': 2,
            'price': 10.99
        },
        {
            'name': 'Product 2',
            'image_url': 'https://example.com/image2.jpg',
            'quantity': 1,
            'price': 24.99
        }
    ]
    order_number = "ORD-12345"
    
    pdf_file = generate_order_pdf(order_details, items, order_number)
    print(f"PDF generated: {pdf_file}")