from rest_framework import viewsets
from rest_framework.permissions import AllowAny
from .models import Vacancy
from .serializers import VacancySerializer

class VacancyViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Vacancy.objects.all()
    serializer_class = VacancySerializer
    permission_classes = [AllowAny]