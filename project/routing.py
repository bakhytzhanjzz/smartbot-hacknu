# project/routing.py
from django.urls import re_path
from candidates.consumers import ApplicationConsumer

websocket_urlpatterns = [
    re_path(r"^ws/applications/(?P<application_id>\d+)/$", ApplicationConsumer.as_asgi()),
]
