from rest_framework import serializers
from .models import User, UserAppProfile


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'nickname', 'phone', 'avatar', 'date_joined']
        read_only_fields = ['id', 'date_joined']


class SendSmsCodeSerializer(serializers.Serializer):
    """发送短信验证码的请求序列化器"""
    phone = serializers.CharField(max_length=11, help_text='手机号（11位数字）')
    purpose = serializers.ChoiceField(
        choices=['login', 'reset_password', 'bind_phone'],
        default='login',
        help_text='用途：login / reset_password / bind_phone'
    )

    def validate_phone(self, value):
        if len(value) != 11 or not value.isdigit():
            raise serializers.ValidationError('手机号格式不正确')
        return value


class PhoneCodeLoginSerializer(serializers.Serializer):
    """手机号统一登录（登录 + 自动注册）"""
    phone = serializers.CharField(max_length=11, help_text='11位手机号')
    code = serializers.CharField(max_length=6, help_text='6位短信验证码')
    app_name = serializers.CharField(default='neighbor_hub', help_text='应用标识（默认 neighbor_hub）')


class UserAppProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserAppProfile
        fields = ['id', 'app_name', 'app_user_id', 'extra_data', 'created_at']
