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
from urllib.parse import urljoin
import re
from urllib.parse import quote


def get_cart_quantities(request):
    if not request.session.session_key:
        return {}
    
    cart = Cart.objects.filter(session__session_key=request.session.session_key, is_active=True).first()
    if not cart:
        return {}
    
    cart_items = CartItem.objects.filter(cart=cart)
    return {item.product_id: item.quantity for item in cart_items}



def generate_order_pdf(order_details, items, order_number):
    # ... (previous code remains the same)

    for item in items:
        # ... (previous code remains the same)

        # Try to add the image
        try:
            # Ensure the image URL is absolute
            image_url = item['image_url']
            if not image_url.startswith(('http://', 'https://')):
                image_url = urljoin(settings.BASE_URL, quote(image_url))
            
            print(f"Fetching image from URL: {image_url}")  # Log the image URL
            response = requests.get(image_url, timeout=30, verify=False)  # Increased timeout, disabled SSL verification
            response.raise_for_status()  # Raise an exception for bad responses
            
            content_type = response.headers.get('content-type', '').lower()
            if 'image' in content_type:
                img = Image(BytesIO(response.content))
                img.drawHeight = 1.5 * inch
                img.drawWidth = 1.5 * inch
                data[0][1] = img
            else:
                raise ValueError(f"Unexpected content type: {content_type}")
        except requests.RequestException as e:
            print(f"Failed to fetch image. Error: {str(e)}")
            data[0][1] = Paragraph("Image not available (Network Error)", normal_style)
        except ValueError as e:
            print(f"Invalid image data. Error: {str(e)}")
            data[0][1] = Paragraph("Image not available (Invalid Data)", normal_style)
        except Exception as e:
            print(f"Error processing image: {str(e)}")
            data[0][1] = Paragraph("Image not available (Processing Error)", normal_style)

        # ... (rest of the code remains the same)