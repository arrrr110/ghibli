from rest_framework import serializers
from .models import User, UserAppProfile


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'nickname', 'phone', 'avatar', 'date_joined']
        read_only_fields = ['id', 'date_joined']


class RegisterSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=11)
    code = serializers.CharField(max_length=6)
    nickname = serializers.CharField(required=False, allow_blank=True, max_length=50)
    app_name = serializers.CharField(default='')


    def validate_phone(self, value):
        if len(value) != 11 or not value.isdigit():
            raise serializers.ValidationError('手机号格式不正确')
        return value


class PhoneCodeLoginSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=11)
    code = serializers.CharField(max_length=6)
    app_name = serializers.CharField(default='')


class WechatLoginSerializer(serializers.Serializer):
    code = serializers.CharField()
    app_name = serializers.CharField(default='')
    extra_data = serializers.JSONField(required=False, default=dict)


class UserAppProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserAppProfile
        fields = ['id', 'app_name', 'app_user_id', 'extra_data', 'created_at']
