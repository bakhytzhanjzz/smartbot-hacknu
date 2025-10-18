from rest_framework import serializers
from .models import Employer
from django.contrib.auth import get_user_model

User = get_user_model()

class UserPublicSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id','username','email','first_name','last_name')

class EmployerSerializer(serializers.ModelSerializer):
    user = UserPublicSerializer(read_only=True)

    class Meta:
        model = Employer
        fields = ('id','user','company_name','website','created_at')
        read_only_fields = ('id','created_at','user')
