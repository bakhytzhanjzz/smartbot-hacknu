from rest_framework.routers import DefaultRouter
from .views import VacancyViewSet

router = DefaultRouter()
router.register(r'', VacancyViewSet, basename='vacancy')
urlpatterns = router.urls
