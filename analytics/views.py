from rest_framework import viewsets
from .models import RelevanceResult
from .serializers import RelevanceResultSerializer
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from project.permissions import IsOwnerOrReadOnly

class RelevanceResultViewSet(viewsets.ModelViewSet):
    queryset = RelevanceResult.objects.select_related('application').all()
    serializer_class = RelevanceResultSerializer
    permission_classes = [IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly]
