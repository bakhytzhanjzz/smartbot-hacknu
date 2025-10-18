# jobs/views.py
from rest_framework import viewsets, permissions, filters
from .models import Vacancy
from .serializers import VacancySerializer
from project.permissions import IsOwnerOrReadOnly
from django_filters.rest_framework import DjangoFilterBackend

class VacancyViewSet(viewsets.ModelViewSet):
    queryset = Vacancy.objects.select_related('employer').all()
    serializer_class = VacancySerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['city', 'employment_type', 'is_active']
    search_fields = ['title', 'description', 'requirements']
    ordering_fields = ['created_at', 'salary_from']
    ordering = ['-created_at']

    def perform_create(self, serializer):
        # if user has employer profile, set employer automatically
        employer = getattr(self.request.user, 'employer', None)
        if employer:
            serializer.save(employer=employer)
        else:
            serializer.save()
