from .models import Cart, CartItem
from PIL import Image, ImageDraw, ImageFont
import os
import uuid
from io import BytesIO
import requests
from django.conf import settings
import logging


def get_cart_quantities(request):
    if not request.session.session_key:
        return {}
    
    cart = Cart.objects.filter(session__session_key=request.session.session_key, is_active=True).first()
    if not cart:
        return {}
    
    cart_items = CartItem.objects.filter(cart=cart)
    return {item.product_id: item.quantity for item in cart_items}



logger = logging.getLogger(__name__)

def generate_order_image(order_details, items):
    img_width = 800
    img_height = 200 + (len(items) * 250)
    img = Image.new('RGB', (img_width, img_height), color='white')
    d = ImageDraw.Draw(img)
    
    try:
        font = ImageFont.truetype("arial.ttf", 16)
        large_font = ImageFont.truetype("arial.ttf", 20)
    except IOError:
        font = ImageFont.load_default()
        large_font = ImageFont.load_default()
    
    y_offset = 10
    for line in order_details.split('\n'):
        d.text((10, y_offset), line, fill=(0,0,0), font=large_font)
        y_offset += 25
    
    for index, item in enumerate(items):
        y_offset += 50
        
        if index % 2 == 0:
            d.rectangle([0, y_offset, img_width, y_offset+170], fill=(245,245,245))
        
        # Image handling
        if 'image_url' in item and item['image_url']:
            try:
                response = requests.get(item['image_url'], timeout=10)
                response.raise_for_status()  # Raises an HTTPError for bad responses
                product_img = Image.open(BytesIO(response.content))
                product_img.thumbnail((150, 150))
                img.paste(product_img, (10, y_offset))
                logger.info(f"Successfully added image for product: {item['product_name']}")
            except requests.RequestException as e:
                logger.error(f"Failed to download image for {item['product_name']}: {str(e)}")
                d.rectangle([10, y_offset, 160, y_offset+150], outline="black", fill="lightgray")
                d.text((15, y_offset+60), "Image Error", fill=(255,0,0), font=font)
            except Exception as e:
                logger.error(f"Error processing image for {item['product_name']}: {str(e)}")
                d.rectangle([10, y_offset, 160, y_offset+150], outline="black", fill="lightgray")
                d.text((15, y_offset+60), "Image Error", fill=(255,0,0), font=font)
        else:
            logger.warning(f"No image URL provided for product: {item['product_name']}")
            d.rectangle([10, y_offset, 160, y_offset+150], outline="black", fill="lightgray")
            d.text((15, y_offset+60), "No Image", fill=(0,0,0), font=font)
        
        # Write product details
        d.text((180, y_offset), f"Product: {item['product_name']}", fill=(0,0,255), font=font)
        d.text((180, y_offset + 30), f"Quantity: {item['quantity']}", fill=(0,0,0), font=font)
        d.text((180, y_offset + 60), f"Price: Ksh.{item['price']}", fill=(0,128,0), font=font)
        total = float(item['price']) * int(item['quantity'])
        d.text((180, y_offset + 90), f"Total: Ksh.{total:.2f}", fill=(255,0,0), font=font)
        
        d.rectangle([5, y_offset-5, img_width-5, y_offset+165], outline="black")
        
        y_offset += 170
    
    filename = f"order_{uuid.uuid4()}.png"
    filepath = os.path.join(settings.MEDIA_ROOT, 'order_images', filename)
    
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    
    img.save(filepath)
    logger.info(f"Order image saved: {filepath}")
    
    return filename