from django.utils.cache import patch_cache_control
from django.conf import settings

def cache_control_middleware(get_response):
    def middleware(request):
        response = get_response(request)
        if request.path.startswith(settings.MEDIA_URL) and request.path.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
            patch_cache_control(response, max_age=3600*24*30)  # Cache for 30 days
        return response
    return middleware