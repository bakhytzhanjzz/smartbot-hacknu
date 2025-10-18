# jobs/urls.py
from django.urls import path
from rest_framework.response import Response
from rest_framework.decorators import api_view

@api_view(["GET"])
def stub(request):
    return Response({"ok": True, "app": "jobs"})

urlpatterns = [
    path('', stub, name='jobs-stub'),
]
