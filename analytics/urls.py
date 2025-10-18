from rest_framework.routers import DefaultRouter
from .views import RelevanceResultViewSet

router = DefaultRouter()
router.register(r'', RelevanceResultViewSet, basename='relevance')

urlpatterns = router.urls
