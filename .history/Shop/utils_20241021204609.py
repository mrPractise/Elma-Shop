import os
import logging
from io import BytesIO
from urllib.parse import urljoin

import requests
from PIL import Image as PILImage
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from django.conf import settings
from django.core.cache import cache
from celery import shared_task, current_task
from django.db.models import Prefetch

from .models import Cart, CartItem, Order, OrderItem, Product, ProductImage

# Configure logging
logger = logging.getLogger('Shop')

def get_cart_quantities(request):
    if not request.session.session_key:
        return {}
    
    cart = Cart.objects.filter(session__session_key=request.session.session_key, is_active=True).first()
    if not cart:
        return {}
    
    cart_items = CartItem.objects.filter(cart=cart)
    return {str(item.product_id): item.quantity for item in cart_items}

def get_cached_image(image_url, size=(1*inch, 1*inch)):
    cache_key = f"image_{image_url}_{size[0]}x{size[1]}"
    cached_image = cache.get(cache_key)
    if cached_image:
        return cached_image
    
    try:
        if not image_url.startswith(('http://', 'https://')):
            image_url = urljoin(settings.BASE_URL, image_url)
        
        response = requests.get(image_url, stream=True, timeout=10)
        response.raise_for_status()
        
        img = Image(BytesIO(response.content), width=size[0], height=size[1])
        cache.set(cache_key, img, timeout=3600)  # Cache for 1 hour
        return img
    except Exception as e:
        logger.error(f"Error processing image from {image_url}: {str(e)}")
        return None

def get_order_items(order):
    return order.items.select_related('product').prefetch_related(
        Prefetch('product__images', queryset=ProductImage.objects.filter(is_primary=True))
    )

@shared_task(bind=True)
def generate_order_pdf_async(self, order_id):
    try:
        order = Order.objects.get(id=order_id)
        order_items = get_order_items(order)
        
        filename = f"order_{order.order_number.replace('/', '_')}.pdf"
        filepath = os.path.join(settings.MEDIA_ROOT, 'order_pdfs', filename)
        
        os.makedirs(os.path.dirname(filepath), exist_ok=True)

        doc = SimpleDocTemplate(filepath, pagesize=letter)
        elements = []

        styles = getSampleStyleSheet()
        title_style = styles['Heading1']
        normal_style = styles['Normal']
        total_style = ParagraphStyle(
            'TotalStyle',
            parent=normal_style,
            fontSize=18,
            backColor=colors.yellow,
            borderPadding=(4, 4, 4, 4),
        )

        elements.append(Paragraph(f"Order Details - {order.order_number}", title_style))
        
        order_details = [
            f"Order Date: {order.created_at}",
            f"Customer: {order.user.get_full_name()}",
            f"Shipping Address: {order.shipping_address}",
        ]
        for line in order_details:
            elements.append(Paragraph(line, normal_style))
        elements.append(Spacer(1, 0.25*inch))

        elements.append(Paragraph("Order Items", title_style))
        
        total_steps = len(order_items) + 2
        current_step = 0

        for item in order_items:
            data = [
                [Paragraph(f"<b>{item.product.name}</b>", normal_style), 
                 get_cached_image(item.product.images.first().image.url) or Paragraph("Image not available", normal_style)],
                [f"Quantity: {item.quantity}", f"Price: Ksh.{item.price}"],
                [f"Total: Ksh.{item.get_total()}", '']
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
            
            current_step += 1
            self.update_state(state='PROGRESS', meta={'current': current_step, 'total': total_steps})

        elements.append(Paragraph(f"Total Amount: Ksh.{order.get_total_cost()}", total_style))

        doc.build(elements)

        pdf_url = urljoin(settings.MEDIA_URL, f'order_pdfs/{filename}')
        logger.info(f"PDF generated for order {order.order_number}: filename={filename}, relative_url={pdf_url}")
        
        current_step += 1
        self.update_state(state='PROGRESS', meta={'current': current_step, 'total': total_steps})
        
        return filename, pdf_url

    except Exception as e:
        logger.error(f"Failed to generate PDF for order {order_id}: {str(e)}")
        return None, None

def generate_pdfs_in_batch(order_ids):
    for order_id in order_ids:
        generate_order_pdf_async.delay(order_id)

# Example usage in a view
from django.http import JsonResponse

def generate_order_pdf_view(request, order_id):
    task = generate_order_pdf_async.delay(order_id)
    return JsonResponse({"task_id": task.id})

def check_pdf_generation_status(request, task_id):
    task = generate_order_pdf_async.AsyncResult(task_id)
    if task.state == 'PENDING':
        response = {
            'state': task.state,
            'status': 'Pending...'
        }
    elif task.state != 'FAILURE':
        response = {
            'state': task.state,
            'current': task.info.get('current', 0),
            'total': task.info.get('total', 1),
            'status': task.info.get('status', '')
        }
        if task.state == 'SUCCESS':
            response['result'] = task.get()
    else:
        response = {
            'state': task.state,
            'status': str(task.info),
        }
    return JsonResponse(response)