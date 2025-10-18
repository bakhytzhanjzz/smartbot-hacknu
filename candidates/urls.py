from rest_framework.routers import DefaultRouter
from .views import CandidateViewSet, ApplicationViewSet, BotMessageViewSet

router = DefaultRouter()
router.register(r'people', CandidateViewSet, basename='candidate')
router.register(r'applications', ApplicationViewSet, basename='application')
router.register(r'messages', BotMessageViewSet, basename='botmessage')

urlpatterns = router.urls
