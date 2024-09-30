from .models import Cart, CartItem
from PIL import Image, ImageDraw, ImageFont
import os
import uuid
from io import BytesIO
import requests
from django.conf import settings
def get_cart_quantities(request):
    if not request.session.session_key:
        return {}
    
    cart = Cart.objects.filter(session__session_key=request.session.session_key, is_active=True).first()
    if not cart:
        return {}
    
    cart_items = CartItem.objects.filter(cart=cart)
    return {item.product_id: item.quantity for item in cart_items}


def generate_order_image(order_details, items):
    # Create a new image with white background
    img_width = 800
    img_height = 200 + (len(items) * 250)  # Increase height per item
    img = Image.new('RGB', (img_width, img_height), color='white')
    d = ImageDraw.Draw(img)
    
    # Use a larger, more readable font
    try:
        font = ImageFont.truetype("arial.ttf", 16)
        large_font = ImageFont.truetype("arial.ttf", 20)
    except IOError:
        font = ImageFont.load_default()
        large_font = ImageFont.load_default()
    
    # Write the order details on the image
    y_offset = 10
    for line in order_details.split('\n'):
        d.text((10, y_offset), line, fill=(0,0,0), font=large_font)
        y_offset += 25  # Increase line spacing
    
    # Add product images and details
    for index, item in enumerate(items):
        y_offset += 50  # Add space between items
        
        # Add alternating background for items
        if index % 2 == 0:
            d.rectangle([0, y_offset, img_width, y_offset+170], fill=(245,245,245))  # Light gray
        
        # Download and paste the product image
        try:
            response = requests.get(item['image_url'])
            product_img = Image.open(BytesIO(response.content))
            product_img.thumbnail((150, 150))  # Larger thumbnail
            img.paste(product_img, (10, y_offset))
        except:
            # If image download fails, draw a placeholder
            d.rectangle([10, y_offset, 160, y_offset+150], outline="black", fill="lightgray")
            d.text((15, y_offset+60), "No Image", fill=(0,0,0), font=font)
        
        # Write product details with color
        d.text((180, y_offset), f"Product: {item['product_name']}", fill=(0,0,255), font=font)  # Blue
        d.text((180, y_offset + 30), f"Quantity: {item['quantity']}", fill=(0,0,0), font=font)
        d.text((180, y_offset + 60), f"Price: Ksh.{item['price']}", fill=(0,128,0), font=font)  # Green
        total = float(item['price']) * int(item['quantity'])
        d.text((180, y_offset + 90), f"Total: Ksh.{total:.2f}", fill=(255,0,0), font=font)  # Red
        
        # Add a border around the item
        d.rectangle([5, y_offset-5, img_width-5, y_offset+165], outline="black")
        
        y_offset += 170  # Move to next product
    
    # Generate a unique filename
    filename = f"order_{uuid.uuid4()}.png"
    filepath = os.path.join(settings.MEDIA_ROOT, 'order_images', filename)
    
    # Ensure the directory exists
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    
    # Save the image
    img.save(filepath)
    
    return filename
