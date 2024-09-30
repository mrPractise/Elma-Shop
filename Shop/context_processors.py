# In a new file, e.g., myapp/context_processors.py

from django.conf import settings
import urllib.parse

def whatsapp_url(request):
    phone_number = settings.WHATSAPP_NUMBER
    message = settings.WHATSAPP_MESSAGE
    whatsapp_url = f"https://wa.me/{phone_number}?text={urllib.parse.quote(message)}"
    return {'whatsapp_url': whatsapp_url}