from rest_framework import viewsets, permissions
from .models import Employer
from .serializers import EmployerSerializer
from project.permissions import IsOwnerOrReadOnly

class EmployerViewSet(viewsets.ModelViewSet):
    queryset = Employer.objects.select_related('user').all()
    serializer_class = EmployerSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly]

    def perform_create(self, serializer):
        # Attach logged-in user as owner
        serializer.save(user=self.request.user)
