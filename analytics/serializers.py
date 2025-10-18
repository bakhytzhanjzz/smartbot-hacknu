from rest_framework import serializers
from .models import RelevanceResult

class RelevanceResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = RelevanceResult
        fields = ('id','application','score','reasons','summary','computed_at')
        read_only_fields = ('id','computed_at')
