# project/api_urls.py
from django.urls import path, include
from rest_framework.response import Response
from rest_framework.decorators import api_view

@api_view(["GET"])
def api_root(request):
    return Response({
        "endpoints": {
            "jobs": "/api/jobs/",
            "candidates": "/api/candidates/",
            "employers": "/api/employers/",
            "analytics": "/api/analytics/",
        }
    })

urlpatterns = [
    path('', api_root, name='api-root'),
    path('jobs/', include('jobs.urls')),
    path('candidates/', include('candidates.urls')),
    path('employers/', include('employers.urls')),
    path('analytics/', include('analytics.urls')),
]
