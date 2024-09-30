from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls import url
from django.views.static import serve 

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('Shop.urls'))
]

urlpatterns = [
  url(r'^media/(?P<path>.*)$', serve,{'document_root': settings.MEDIA_ROOT}),
  url(r'^static/(?P<path>.*)$', serve,{'document_root': settings.STATIC_ROOT}),
]
