from rest_framework import viewsets, mixins, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Candidate, Application, BotMessage
from .serializers import CandidateSerializer, ApplicationSerializer, BotMessageSerializer
from rest_framework.permissions import AllowAny, IsAuthenticated
from project.permissions import IsOwnerOrReadOnly
from django_filters.rest_framework import DjangoFilterBackend

class CandidateViewSet(viewsets.ModelViewSet):
    queryset = Candidate.objects.all()
    serializer_class = CandidateSerializer
    permission_classes = [IsAuthenticated]  # only authenticated users can CRUD candidates (adjust if needed)
    filterset_fields = ['email','city']
    search_fields = ['name','email','resume_text']

class ApplicationViewSet(viewsets.ModelViewSet):
    queryset = Application.objects.select_related('candidate','vacancy').all()
    serializer_class = ApplicationSerializer
    permission_classes = [AllowAny]  # allow anonymous apply endpoint; restrict others below
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['vacancy','status']

    def get_permissions(self):
        # Allow anyone to create (apply), but other actions require auth
        if self.action in ['create']:
            return [AllowAny()]
        return [IsAuthenticated()]

    def perform_create(self, serializer):
        application = serializer.save()
        # Trigger background analysis task via Celery (we'll create task later)
        from analytics.tasks import analyze_application_task
        task = analyze_application_task.delay(application.id)
        # attach task id into meta for tracking
        application.meta.update({'analysis_task_id': task.id})
        application.save()

    @action(detail=True, methods=['GET'])
    def messages(self, request, pk=None):
        app = self.get_object()
        msgs = app.messages.all().order_by('created_at')
        serializer = BotMessageSerializer(msgs, many=True)
        return Response(serializer.data)

class BotMessageViewSet(viewsets.ModelViewSet):
    queryset = BotMessage.objects.select_related('application').all()
    serializer_class = BotMessageSerializer
    permission_classes = [IsOwnerOrReadOnly]
    filterset_fields = ['application','sender']
