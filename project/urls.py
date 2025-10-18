from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse


def root_view(request):
    return JsonResponse({
        "status": "ok",
        "message": "SmartBot API is running 🚀",
        "docs": "/api/",
    })


urlpatterns = [
    path('', root_view, name='root'),
    path('admin/', admin.site.urls),
    path('api/', include('project.api_urls')),
]
