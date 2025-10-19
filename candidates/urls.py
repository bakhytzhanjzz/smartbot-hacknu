# candidates/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'candidates', views.CandidateViewSet)
router.register(r'applications', views.ApplicationViewSet)
router.register(r'chat-sessions', views.ChatSessionViewSet)
router.register(r'bot-messages', views.BotMessageViewSet)
router.register(r'candidate-responses', views.CandidateResponseViewSet)

urlpatterns = [
    path('', include(router.urls)),
]